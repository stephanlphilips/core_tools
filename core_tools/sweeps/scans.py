import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import numpy as np
from qcodes import Parameter

from pulse_lib.sequencer import sequencer, index_param

from core_tools.data.measurement import Measurement, AbortMeasurement
from core_tools.sweeps.progressbar import progress_bar
from core_tools.job_mgnt.job_mgmt import queue_mgr, ExperimentJob

logger = logging.getLogger(__name__)


class Break(Exception):
    """Stops a scan and closes the dataset"""
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
    def __init__(self, param, n_points, delay=0.0, resetable=True,
                 value_after: Union[None, float]=None):
        super().__init__(f'set {param.name}', delay)
        self._param = param
        self._n_points = n_points
        self._resetable = resetable
        self._value_after = value_after

    @property
    def param(self):
        return self._param

    @property
    def n_points(self):
        return self._n_points

    @property
    def resetable(self):
        return self._resetable

    @property
    def value_after(self):
        return self._value_after

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
        '''
        Adds a function to a Scan.
        Args:
            func: function to call
            args: arguments for func
            delay (float): time to wait after calling func
            add_dataset (bool): if True calls func(*args, dataset=ds, **kwargs)
            add_last_values (bool): if True calls func(*args, add_last_values=last_param_values, **kwargs)
            kwargs: keyword arguments for func

        Notes:
            last parameter values are past as dictionary.
        '''
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


class SequenceFunction(Function):
    def __init__(self, func, *args, delay=0.0,
                 axis=None,
                 add_dataset=False, add_last_values=False, **kwargs):
        '''
        Adds a function to be run after setting sequence sweep index, but before playing sequence.
        Args:
            func: function to call
            args: arguments for func
            delay (float): time to wait after calling func
            axis (int or str): axis number or looping parameter name in sequence
            add_dataset (bool): if True calls func(*args, dataset=ds, **kwargs)
            add_last_values (bool): if True calls func(*args, add_last_values=last_param_values, **kwargs)
            kwargs: keyword arguments for func

        Notes:
            last parameter values are past as dictionary.
        '''
        super().__init__(
                func, *args, delay=delay, add_dataset=add_dataset,
                add_last_values=add_last_values, **kwargs)
        if axis is None:
            raise ValueError('Argument axis must be specified')
        self.axis = axis


class SequenceStart(Action):
    def __init__(self, sequence):
        super().__init__("play_sequence")
        self.sequence = sequence

    def play(self):
        job = self.sequence.upload()
        self.sequence.play()

        # return effective play time
        n_rep = job.n_rep if job.n_rep else 1
        total_seconds = job.playback_time * n_rep * 1e-9
        return total_seconds


class ArraySetter(Setter):
    def __init__(self, param, data, delay=0.0, resetable=True,
                 value_after: Union[None, str, float]=None):
        if isinstance(value_after, str):
            if value_after == 'start':
                value_after = data[0]
            else:
                raise Exception(f"Unknown value_after '{value_after}'")
        super().__init__(param, len(data), delay, resetable, value_after)
        self._data = data

    def __iter__(self):
        for value in self._data:
            yield value


def sweep(parameter, data, stop=None, n_points=None, delay=0.0, resetable=True,
          value_after: Union[None, str, float]=None,
          endpoint=True):
    """ Sweeps parameter over specified values.

    If stop is None, then data is assumed to be an array, otherwise data is the start value.

    Args:
        parameter (Parameter): qcodes parameter to sweep.
        data (array or float): array of values to sweep or start value of the sweep.
        stop (None or float): stop value of the sweep (inclusive is endpoint is True).
        n_points (int): number of points for sweep.
        delay (float): wait time in seconds after setting the parameter.
        resetable (bool): if True the parameter will be reset to its value before the scan.
        value_after (None, str or float):
            if not None it specifies the value set after the sweep before changing the value of the outer loop.
            value_after == 'start' sets the value to the first value of the sweep.
        endpoint (bool): if True the stop value is inclusive, otherwise it is excluded.
    """
    if stop is not None:
        start = data
        data = np.linspace(start, stop, n_points, endpoint=endpoint)
    return ArraySetter(parameter, data, delay, resetable, value_after)


class Section:
    def __init__(self, *args):
        self.args = args


@dataclass
class ActionStats:
    n: int = 0
    t: float = 0.0

    def add_time(self,  t):
        self.n += 1
        self.t += t

    def __str__(self):
        return f"{self.n:3d}: {self.t:6.3f} s ({self.t/self.n*1000.0:#.3g} ms/pt)"


@dataclass
class _MParam:
    param: Parameter
    dependencies: List[Parameter]


@dataclass
class _Block:
    setter: Optional[Setter] = None
    value: Optional[float] =  None
    actions: List[any] = field(default_factory=list)

    @property
    def loop_length(self):
        if self.setter is None:
            return 1
        return self.setter.n_points

    @property
    def name(self):
        return f"loop {self.setter.name}" if self.setter else ""


class Scan:
    verbose = False

    def __init__(self, *args, name='', reset_param=False, silent=False, snapshot_extra=None):
        self.name = name
        self.reset_param = reset_param
        self.silent = silent

        self.set_params: List[Parameter] = []
        self.m_params: List[_MParam] = []

        self._root = _Block()
        self._block_stack: List[_Block] = [self._root]

        self._meas = Measurement(self.name, silent=silent)
        self._add_actions(args)

        if name == '':
            print("WARNING: no name specified with scan! Please specify a name.")
            if len(self.set_params) == 0:
                self.name = '0D_' + self.m_params[0].name[:10]
            else:
                self.name += '{}D_'.format(len(self.set_params))
            self._meas.name = name

        self._register_params()
        self._n_pts = self._get_n_pts(self._root)

        if snapshot_extra:
            for key, value in snapshot_extra.items():
                if key not in self.meas.snapshot:
                    self._meas.add_snapshot(key, value)
                else:
                    raise Exception(f"Measurement snapshot already contains key {key}")

    def _add_actions(self, args):
        for arg in args:
            if isinstance(arg, Setter):
                self._add_setter(arg)
            elif isinstance(arg, sequencer):
                seq_params = arg.params
                # Note: reverse order, because axis=0 is fastest running and must thus be last.
                for var in seq_params[::-1]:
                    setter = ArraySetter(var, var.values, resetable=False)
                    self._add_setter(setter)
                self._actions.append(SequenceStart(arg))
                self._meas.add_snapshot('sequence', arg.metadata)
                if hasattr(arg, 'starting_lambda'):
                    raise Exception('sequencer starting_lambda is not supported anymore')
            elif isinstance(arg, Getter):
                self._add_getter(arg)
            elif isinstance(arg, SequenceFunction):
                self._insert_sequence_function(arg)
            elif isinstance(arg, Function):
                self._actions.append(arg)
            elif isinstance(arg, Section):
                section = arg
                depth = len(self._block_stack)
                self._add_actions(section.args)
                # pop stack
                self._block_stack = self._block_stack[:depth]
            else:
                # Assume it is a measurement parameter
                getter = Getter(arg)
                self._add_getter(getter)

    @property
    def _current_block(self):
        return self._block_stack[-1]

    @property
    def _actions(self):
        return self._current_block.actions

    @property
    def _dependencies(self):
        return [block.setter.param for block in self._block_stack[1:]]

    def _add_setter(self, setter):
        # Do not allow duplicate param in dependencies
        if id(setter.param) in [id(param) for param in self._dependencies]:
            raise Exception(f"Duplicate parameter {setter.param.name} in scan")
        # Register only once, allow reuse of setter in other Section
        if id(setter.param) not in [id(set_param) for set_param in self.set_params]:
            self.set_params.append(setter)
        block = _Block(setter)
        self._actions.append(block)
        self._block_stack.append(block)

    def _add_getter(self, getter):
        self._actions.append(getter)
        self.m_params.append(_MParam(getter.param, self._dependencies))

    def _register_params(self):
        for setter in self.set_params:
            self._meas.register_set_parameter(setter.param, setter.n_points)
        for m_param in self.m_params:
            self._meas.register_get_parameter(m_param.param, *m_param.dependencies)

    def _insert_sequence_function(self, seq_function):
        sequence_added = False
        for block in self._block_stack:
            setter = block.setter
            if (isinstance(setter, ArraySetter)
                    and isinstance(setter.param, index_param)
                    and (setter.param.dim == seq_function.axis or setter.param.name == seq_function.axis)):
                break
            for action in block.actions:
                if isinstance(action, SequenceStart):
                    sequence_added = True
        else:
            # axis not found.
            if not sequence_added:
                raise Exception('SequenceFunction must be added after sequence')
            raise Exception(f'sequence axis {seq_function.axis} not found in sequence')
        block.actions.insert(0, seq_function)

    def _get_n_pts(self, block):
        n_pts = 0
        for action in block.actions:
            if isinstance(action, _Block):
                n_pts += self._get_n_pts(action)
        if n_pts == 0:
            # It's a leaf. Count as 1
            n_pts = 1
        res = n_pts * block.loop_length
        return res

    def run(self):
        try:
            start = time.perf_counter()
            with self._meas as m:
                runner = Runner(m, self._root, self._n_pts, self.set_params)
                runner.run(self.reset_param, self.silent)
            duration = time.perf_counter() - start
            logger.info(f'Total duration: {duration:5.2f} s ({duration/self._n_pts*1000:5.1f} ms/pt)')
            logger.debug(f"Stats: {runner.stats}")
        except Break as b:
            logger.warning(f'Measurement break: {b}')
        except AbortMeasurement:
            logger.warning('Measurement aborted')
        except KeyboardInterrupt:
            logger.debug('Measurement interrupted', exc_info=True)
            logger.warning('Measurement interrupted')
            raise KeyboardInterrupt('Measurement interrupted') from None
        except Exception as ex:
            print(f'\n*** ERROR in measurement: {ex}')
            logger.error('Exception in measurement', exc_info=True)
            raise

        return self._meas.dataset

    def put(self, priority=1):
        '''
        put the job in a queue.
        '''
        queue = queue_mgr()
        job = ExperimentJob(priority, self)
        queue.put(job)

    def abort_measurement(self):
        '''Abort measurement.
        This is called by job queue manager.
        '''
        if self._meas:
            self._meas.abort()


class Runner:
    def __init__(self, measurement, root_block, n_pts, set_params):
        self._measurement = measurement
        self._root = root_block
        self._n_pts = n_pts
        self._set_params = set_params
        # stack with setpoints
        self._setpoints = []
        self._m_values = {}
        self._action_stats = defaultdict(ActionStats)

    def run(self, reset_param=False, silent=False):
        if reset_param:
            start_values = self._get_start_values()
        self._n = 0
        self.pbar = progress_bar(self._n_pts) if not silent else None
        try:
            self._loop(self._root.actions)
        except BaseException:
            last_index = {
                param.name: data
                for param, data in self._setpoints
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

    @property
    def stats(self):
        return {k: str(v) for k, v in self._action_stats.items()}

    def _get_start_values(self):
        return [
                (setter.param, setter.param())
                for setter in self._set_params
                if setter.resetable
                ]

    def _reset_params(self, start_values):
        for param, value in start_values:
            try:
                param(value)
            except Exception:
                logger.error(f'Failed to reset parameter {param.name}', exc_info=True)
                raise

    def _loop(self, actions: List[Action]):
        n_setters = 0
        for action in actions:
            if isinstance(action, _Block):
                n_setters += 1
                self._loop_setter(action)
                continue

            stats_name = action.name
            t_start = time.perf_counter()

            if isinstance(action, Getter):
                m_param = action.param
                value = None
                # @@@ Set None if breaking...
                try:
                    value = m_param()
                    self._m_values[m_param.name] = value
                    t_store = time.perf_counter()
                    self._measurement.add_result((m_param, value), *self._setpoints)
                    store_duration = time.perf_counter() - t_store
                    self._action_stats['store'].add_time(store_duration)
                    t_start += store_duration
                except Exception:
                    raise Exception(f'Failure getting {m_param.name}: {value}')

            elif isinstance(action, SequenceStart):
                play_time = action.play()
                self._action_stats['sequence play'].add_time(play_time)
                t_start += play_time
                stats_name = 'sequence overhead'

            elif isinstance(action, Function):
                # @@@ Skip if breaking...
                last_values = {
                    param.name: value
                    for param, value in self._setpoints
                    if param is not None
                    }
                last_values.update(self._m_values)
                action(self._measurement.dataset, last_values)

            if action._delay:
                time.sleep(action._delay)

            self._action_stats[stats_name].add_time(time.perf_counter() - t_start)

        if n_setters == 0:
            self._inc_count()

    def _loop_setter(self, block: _Block):
        setter = block.setter
        setpoint = [setter.param, None]
        self._setpoints.append(setpoint)
        try:
            for value in setter:
                try:
                    t_start = time.perf_counter()
                    # @@@ ElapsedTime?
                    # if not isinstance(action.param, ElapsedTimeParameter):
                    #     action.param(value)
                    setter.param(value)
                    if setter._delay:
                        time.sleep(setter._delay)
                    value = setter.param() # @@@ Why retrieve the value that is just written?
                    setpoint[1] = value
                    self._action_stats[setter.name].add_time(time.perf_counter()-t_start)
                    # self._action_cnt[iaction] += 1
                    self._loop(block.actions)
                except Break as b:
                    if b.exit_loop():
                        raise
                    # TODO @@@ fill missing data. Current dataset must be rectangular/box
                    # Requires current loop index and shape per m_param.
                    # => set flag in runner. Do not set/get values. Use param shape to store values.
            if setter.value_after is not None:
                setter.param(setter.value_after)
        finally:
            self._setpoints.pop()

    def _inc_count(self):
        self._n += 1
        if self.pbar is not None:
            self.pbar += 1
        if Scan.verbose:
            n = self._n
            if n % 100 == 0:
                logger.debug(f'Stats ({n}): {self.stats}')


# def run_stats():
#     # @@@ return statistics of last run
#     ...

"""
NOTE:
    Statistics are a bit strange when sequence.play is async and m_param() waits for the sequence to complete.

@@@ Add diagnostics module:
    Statistics: run, sequence
    diagnostics.set('run_stats', dict)
    Last exception with source and time. VideoMode, Scan, doNd, ...
    Diagnostics to file.
    Add 'log' to measurement??
"""
