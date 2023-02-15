import logging
import time
import numpy as np

from core_tools.data.measurement import Measurement
from core_tools.sweeps.progressbar import progress_bar
from pulse_lib.sequencer import sequencer
from core_tools.sweeps.sweep_utility import KILL_EXP
from core_tools.job_mgnt.job_mgmt import queue_mgr, ExperimentJob

logger = logging.getLogger(__name__)

class Break(Exception):
    # TODO @@@ allow loop parameter to break to
    def __init__(self, msg, loops=None):
        super().__init__(msg)
        self._loops = loops

    def exit_loop(self):
        if self._loops is None:
            return True
        self._loops -= 1
        return self._loops > 0

class Action:
    def __init__(self, name, delay=0.0):
        self._delay = delay
        self.name = name

    @property
    def delay(self):
        return self._delay

class Setter(Action):
    def __init__(self, param, n_points, delay=0.0, resetable=True):
        super().__init__(f'set {param.name}', delay)
        self._param = param
        self._n_points = n_points
        self._resetable = resetable

    @property
    def param(self):
        return self._param

    @property
    def n_points(self):
        return self._n_points

    @property
    def resetable(self):
        return self._resetable

    def __iter__(self):
        raise NotImplementedError()

class Getter(Action):
    def __init__(self, param, delay=0.0):
        super().__init__(f'get {param.name}', delay)
        self._param = param

    @property
    def param(self):
        return self._param


class Function(Action):
    def __init__(self, func, *args, delay=0.0, add_dataset=False,
                 add_last_values=False, **kwargs):
        super().__init__(f'do {func.__name__}', delay)
        self._func = func
        self._add_dataset = add_dataset
        self._add_last_values = add_last_values
        self._args = args
        self._kwargs = kwargs

    @property
    def add_dataset(self):
        return self._add_dataset

    def __call__(self, dataset, last_values):
        if self._add_dataset or self._add_last_values:
            kwargs = self._kwargs.copy()
        else:
            kwargs = self._kwargs
        if self._add_dataset:
            kwargs['dataset'] = dataset
        if self._add_last_values:
            kwargs['last_values'] = last_values
        self._func(*self._args, **kwargs)


def _start_sequence(sequence):
    sequence.upload()
    sequence.play()


class ArraySetter(Setter):
    def __init__(self, param, data, delay=0.0, resetable=True):
        super().__init__(param, len(data), delay, resetable)
        self._data = data

    def __iter__(self):
        for value in self._data:
            yield value


def sweep(parameter, data, stop=None, n_points=None, delay=0.0, resetable=True):
    if stop is not None:
        start = data
        data = np.linspace(start, stop, n_points)
    return ArraySetter(parameter, data, delay, resetable)


class Scan:
    def __init__(self, *args, name='', reset_param=False, silent=False):
        self.name = name
        self.reset_param = reset_param
        self.silent = silent

        self.actions = []
        self.meas = Measurement(self.name, silent=silent)

        self.set_params = []
        self.m_params = []
        self.loop_shape = []

        for arg in args:
            if isinstance(arg, Setter):
                self._add_setter(arg)
            elif isinstance(arg, sequencer):
                seq_params = arg.params
                # Note: reverse order, because axis=0 is fastest running and must thus be last.
                for var in seq_params[::-1]:
                    setter = ArraySetter(var, var.values, resetable=False)
                    self._add_setter(setter)
                self.actions.append(Function(_start_sequence, arg))
                self.meas.add_snapshot('sequence', arg.metadata)
                if hasattr(arg, 'starting_lambda'):
                    print('WARNING: sequencer starting_lambda is not supported anymore')
            elif isinstance(arg, Getter):
                self._add_getter(arg)
            elif isinstance(arg, Function):
                self.actions.append(arg)
            else:
                # Assume it is a measurement parameter
                getter = Getter(arg)
                self._add_getter(getter)

        if name == '':
            if len(self.set_params) == 0:
                self.name = '0D_' + self.m_params[0].name[:10]
            else:
                self.name += '{}D_'.format(len(self.set_params))

        self.meas.name = self.name

    def _add_setter(self, setter):
        self.meas.register_set_parameter(setter.param, setter.n_points)
        self.set_params.append(setter.param)
        self.actions.append(setter)
        self.loop_shape.append(setter.n_points)

    def _add_getter(self, getter):
        self.actions.append(getter)
        self.m_params.append(getter.param)
        self.meas.register_get_parameter(getter.param, *self.set_params)


    def run(self):
        try:
            start = time.perf_counter()
            with self.meas as m:
                runner = Runner(m, self.actions, self.loop_shape)
                runner.run(self.reset_param, self.silent)
            duration = time.perf_counter() - start
            n_tot = np.prod(self.loop_shape) if len(self.loop_shape) > 0 else 1
            logger.info(f'Total duration: {duration:5.2f} s ({duration/n_tot*1000:5.1f} ms/pt)')
        except Break as b:
            logger.warning(f'Measurement break: {b}')
        except KILL_EXP:
            # Note: KILL is used by job mgmnt
            logger.warning('Measurement aborted')
        except KeyboardInterrupt:
            logger.warning('Measurement interrupted')
            raise KeyboardInterrupt('Measurement interrupted') from None
        except Exception as ex:
            print(f'\n*** ERROR in measurement: {ex}')
            logger.error('Exception in measurement', exc_info=True)
            raise

        return self.meas.dataset

    def put(self, priority = 1):
        '''
        put the job in a queue.
        '''
        def abort_measurement():
            if self.KILL:
                raise KILL_EXP()
        self.KILL = False
        self.actions.append(Function(abort_measurement))
        queue = queue_mgr()
        job = ExperimentJob(priority, self)
        queue.put(job)


class Runner:
    def __init__(self, measurement, actions, loop_shape):
        self._measurement = measurement
        self._actions = actions
        self._n_tot = np.prod(loop_shape) if len(loop_shape) > 0 else 1
        self._n = 0
        self._setpoints = [[None,None]]*len(loop_shape)
        self._m_values = {}
        self._action_duration = [0.0]*len(actions)
        self._action_cnt = [0]*len(actions)
        self._store_duration = 0.0

    def run(self, reset_param=False, silent=False):
        if reset_param:
            start_values = self._get_start_values()
        self._n_data = 0
        self.pbar = progress_bar(self._n_tot) if not silent else None
        try:
            self._loop()
        except:
            last_index = {
                param.name:data for param,data in self._setpoints
                }
            msg = f'Measurement stopped at {last_index}'
            if not silent:
                print('\n'+msg, flush=True)
            logger.info(msg)
            raise
        finally:
            if self.pbar is not None:
                self.pbar.close()
            if reset_param:
                self._reset_params(start_values)

    def _get_start_values(self):
        return [
                (action.param, action.param())
                if isinstance(action, Setter) and action.resetable else (None,None)
                for action in self._actions
                ]

    def _reset_params(self, start_values):
        for param,value in start_values:
            if param is not None:
                try:
                    param(value)
                except:
                    logger.error(f'Failed to reset parameter {param.name}')

    def _loop(self, iaction=0, iparam=0):
        if iaction == len(self._actions):
            self._inc_count()
            return

        action = self._actions[iaction]
        if isinstance(action, Setter):
            self._loop_setter(action, iaction, iparam)
            return

        try:
            t_start = time.perf_counter()

            if isinstance(action, Getter):
                m_param = action.param
                value = m_param()
                self._m_values[m_param.name] = value
                t_store = time.perf_counter()
                self._measurement.add_result((m_param, value), *self._setpoints)
                self._store_duration += time.perf_counter()-t_store

            elif isinstance(action, Function):
                last_values = {
                    param.name:value
                    for param,value in self._setpoints
                    if param is not None
                    }
                last_values.update(self._m_values)
                action(self._measurement.dataset, last_values)

            if action._delay:
                time.sleep(action._delay)

            self._action_duration[iaction] += time.perf_counter()-t_start
            self._action_cnt[iaction] += 1
            self._loop(iaction+1, iparam)
        except Break:
            for i in range(iparam, len(self._setpoints)):
                self._setpoints[i][1] = None
            raise

    def _loop_setter(self, action, iaction, iparam):
        for value in action:
            try:
                t_start = time.perf_counter()
                action.param(value)
                value = action.param()
                self._setpoints[iparam] = [action.param, value]
                if action._delay:
                    time.sleep(action._delay)
                self._action_duration[iaction] += time.perf_counter()-t_start
                self._action_cnt[iaction] += 1
                self._loop(iaction+1, iparam+1)
            except Break as b:
                if b.exit_loop():
                    raise
                # TODO @@@ fill missing data. dataset must be rectangular/box
                # Requires current loop index and shape per m_param.

    def _inc_count(self):
        self._n += 1
        if self.pbar is not None:
            self.pbar += 1
        n = self._n
        if n % 1 == 0:
            t_actions = {
                action.name: f'{self._action_duration[i]*1000/self._action_cnt[i]:4.1f}'
                for i,action in enumerate(self._actions)
                }
            t_store = self._store_duration*1000/n
            logger.debug(f'npt:{n} actions: {t_actions} store:{t_store:5.1f} ms')

