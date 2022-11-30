import logging
import time
import numpy as np

from core_tools.data.measurement import Measurement
from core_tools.sweeps.progressbar import progress_bar
from pulse_lib.sequencer import sequencer
from core_tools.sweeps.sweep_utility import KILL_EXP
from core_tools.job_mgnt.job_mgmt import queue_mgr, ExperimentJob

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
            kwargs['last_values'] = {
                    param.name:value
                    for param,value in last_values
                    if param is not None
                    }
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

        self.setters = [] # @@@ set_params
        self.m_instr = [] # @@@ get_params

        for arg in args:
            if isinstance(arg, Setter):
                self.setters.append(arg)
                self.actions.append(arg)
            elif isinstance(arg, sequencer):
                # TODO @@@@ check order of parameters
                seq_params = arg.params
                for var in seq_params:
                    setter = ArraySetter(var, var.values, resetable=False)
                    self.setters.append(setter)
                    self.actions.append(setter)
                self.actions.append(Function(_start_sequence, arg))
                self.meas.add_snapshot('sequence', arg.metadata)
                if hasattr(arg, 'starting_lambda'):
                    print('WARNING: sequencer starting_lambda is not supported anymore')
            elif isinstance(arg, Getter):
                self.actions.append(arg)
                self.m_instr.append(arg.param)
            elif isinstance(arg, Function):
                self.actions.append(arg)
            else:
                self.actions.append(Getter(arg))
                self.m_instr.append(arg)

        set_params = []
        self.n_tot = 1
        for setter in self.setters:
            self.meas.register_set_parameter(setter.param, setter.n_points)
            set_params.append(setter.param)
            self.n_tot *= setter.n_points

        for instr in self.m_instr:
            self.meas.register_get_parameter(instr, *set_params)

        if name == '':
            if len(self.setters) == 0:
                self.name = '0D_' + self.m_instr[0].name[:10]
            else:
                self.name += '{}D_'.format(len(self.setters))

        self.meas.name = self.name

    def run(self):
        try:
            n_params = len(self.setters) + len(self.m_instr)
            start = time.perf_counter()
            with self.meas as m:
                runner = Runner(m, self.actions, n_params, self.n_tot)
                runner.run(self.reset_param, self.silent)
            duration = time.perf_counter() - start
            logging.info(f'Total duration: {duration:5.2f} s ({duration/self.n_tot*1000:5.1f} ms/pt)')
        except Break as b:
            logging.warning(f'Measurement break: {b}')
        except KILL_EXP:
            # Note: KILL is used by job mgmnt
            logging.warning('Measurement aborted')
        except KeyboardInterrupt:
            logging.warning('Measurement interrupted')
            raise KeyboardInterrupt('Measurement interrupted') from None
        except Exception as ex:
            print(f'\n*** ERROR in measurement: {ex}')
            logging.error('Exception in measurement', exc_info=True)
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
    def __init__(self, measurement, actions, n_param, n_tot):
        self._measurement = measurement
        self._actions = actions
        self._n_tot = n_tot
        self._n = 0
        self._data = [[None,None]]*n_param
        self._action_duration = [0.0]*len(actions)
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
                param.name:data
                for action,(param,data) in zip(self._actions, self._data)
                if isinstance(action, Setter)
                }
            msg = f'Measurement stopped at {last_index}'
            if not silent:
                print('\n'+msg, flush=True)
            logging.info(msg)
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
                    logging.error(f'Failed to reset parameter {param.name}')

    def _loop(self, iaction=0, iparam=0):
        if iaction == len(self._actions):
            # end of action list: store results
            self._push_results()
            self._inc_count()
            return

        action = self._actions[iaction]
        if isinstance(action, Setter):
            self._loop_setter(action, iaction, iparam)
            return

        try:
            t_start = time.perf_counter()
            next_param = iparam
            if isinstance(action, Getter):
                next_param += 1
                value = action.param()
                self._data[iparam] = [action.param, value]

            elif isinstance(action, Function):
                if action.add_dataset:
                    self._push_results(iparam)
                action(self._measurement.dataset, self._data)

            if action._delay:
                time.sleep(action._delay)
            self._action_duration[iaction] += time.perf_counter()-t_start
            self._loop(iaction+1, next_param)
        except Break:
            for i in range(iparam, len(self._data)):
                self._data[i][1] = None
            self._push_results()
            raise

    def _loop_setter(self, action, iaction, iparam):
        for value in action:
            try:
                t_start = time.perf_counter()
                action.param(value)
                value = action.param()
                self._data[iparam] = [action.param, value]
                if action._delay:
                    time.sleep(action._delay)
                self._action_duration[iaction] += time.perf_counter()-t_start
                self._loop(iaction+1, iparam+1)
            except Break as b:
                if b.exit_loop():
                    raise
                # TODO @@@ fill missing data?? dataset must be rectangular/box
                # what should be the values for the setters when they are not actually set?

    def _inc_count(self):
        self._n += 1
        if self.pbar is not None:
            self.pbar += 1
        n = self._n
        if n % 10 == 0:
            t_actions = {action.name:f'{self._action_duration[i]*1000/n:4.1f}'
                         for i,action in enumerate(self._actions)}
            t_store = self._store_duration*1000/n
            logging.debug(f'npt:{n} actions: {t_actions} store:{t_store:5.1f} ms')

    def _push_results(self, iparam=None):
        t_start = time.perf_counter()
        if iparam is not None:
            data = self._data[self._n_data:iparam]
            self._n_data = iparam
        else:
            data = self._data[self._n_data:]
            self._n_data = 0
        self._measurement.add_result(*data)
        self._store_duration += time.perf_counter()-t_start
