import logging
from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from core_tools.data.measurement import Measurement, AbortMeasurement
from pulse_lib.sequencer import sequencer

from core_tools.sweeps.sweep_utility import (
        SequenceStartAction,
        pulselib_2_qcodes, sweep_info
        )
from core_tools.job_mgnt.job_meta import job_meta
from core_tools.job_mgnt.job_mgmt import queue_mgr, ExperimentJob

import numpy as np
import time


logger = logging.getLogger(__name__)


class scan_generic(metaclass=job_meta):
    '''
    function that handeles the loop action and defines the run class.
    '''
    def __init__(self, *args, name='', reset_param=False, silent=False):
        '''
        init of the scan function

        Args:
            args (*list) :  provide here the sweep info and meaurment parameters
            reset_param (bool) : reset the setpoint parametes to their original value after the meaurement
            silent (bool) : If True do not print dataset id and progress bar
        '''
        self.name = name
        self.silent = silent
        self.meas = Measurement(self.name, silent)

        self.set_vars = []
        self.actions = []
        self.m_instr = []
        self.reset_param = reset_param

        set_points = []
        for arg in args:
            if isinstance(arg, sweep_info):
                self.meas.register_set_parameter(arg.param, arg.n_points)
                self.set_vars.append(arg)
                set_points.append(arg.param)
            elif isinstance(arg, sequencer):
                if arg.shape != (1, ):
                    set_vars_pulse_lib = pulselib_2_qcodes(arg)
                    for var in set_vars_pulse_lib:
                        self.meas.register_set_parameter(var.param, var.n_points)
                        self.set_vars.append(var)
                        set_points.append(var.param)
                else:
                    # Sequence without looping parameters. Only upload, no setpoints
                    self.actions.append(SequenceStartAction(arg))
                self.meas.add_snapshot('sequence', arg.metadata)
            elif arg is None:
                continue
            else:
                m_instr = arg
                self.m_instr.append(m_instr)

        for instr in self.m_instr:
            self.meas.register_get_parameter(instr, *set_points)

        self.n_tot = 1

        if name == '':
            if len(self.set_vars) == 0:
                self.name = '0D_' + self.m_instr[0].name[:10]
            else:
                print("WARNING: no name specified with scan! Please specify a name.")
                self.name += '{}D_'.format(len(self.set_vars))

        for swp_info in self.set_vars:
            self.n_tot *= swp_info.n_points

        self.meas.name = self.name

    def run(self):
        '''
        run function
        -- starts the meaurement and saves the data
        -- optionally also resets the paramters
        -- wrapped by the job_meta class (allows for progress bar to appear)
        '''
        try:
            with self.meas as ds:
                self._loop(self.set_vars, tuple(), ds)

        except AbortMeasurement:
            logger.warning('Measurement aborted')
        except KeyboardInterrupt:
            logger.warning('Measurement interrupted')
            raise KeyboardInterrupt('Measurement interrupted') from None
        except Exception as ex:
            print(f'\n*** ERROR in measurement: {ex}')
            logger.error('Exception in measurement', exc_info=True)

        finally:
            if self.reset_param:
                for param in self.set_vars:
                    try:
                        param.reset_param()
                    except:
                        logger.error(f'Failed to reset parameter {param.param.name}')

        return self.meas.dataset

    def put(self, priority = 1):
        '''
        put the job in a queue.
        '''
        queue = queue_mgr()
        job = ExperimentJob(priority, self)
        queue.put(job)

    def abort_measurement(self):
        self.meas.abort()

    def _loop(self, set_param, to_save, dataset):
        if len(set_param) == 0:
            for action in self.actions:
                action()
            m_data = []
            for instr in self.m_instr:
                m_data.append((instr, instr.get()))

            dataset.add_result(*to_save, *m_data)
            self.n += 1
        else:
            param_info = set_param[0]
            for value in param_info.values():
                if not isinstance(param_info.param, ElapsedTimeParameter):
                    param_info.param(value)
                time.sleep(param_info.delay)
                self._loop(set_param[1:], to_save + ((param_info.param, param_info.param()),), dataset)


def do0D(*m_instr, name='', silent=False):
    '''
    do a 0D scan

    Args:
        m_instr (*list) :  list of parameters to measure
    '''
    return scan_generic(*m_instr, name=name, reset_param=False, silent=silent)


def do1D(param, start, stop, n_points, delay, *m_instr, name='', reset_param=False, silent=False):
    '''
    do a 1D scan

    Args:
        param (qc.Parameter) : parameter to be swept
        start (float) : start value of the sweep
        stop (float) : stop value of the sweep
        delay (float) : time to wait after the set of the parameter
        m_instr (*list) :  list of parameters to measure
        reset_param (bool) : reset the setpoint parametes to their original value after the meaurement
        silent (bool) : If True do not print dataset id and progress bar
    '''
    m_param = sweep_info(param, start, stop, n_points, delay)
    return scan_generic(m_param, *m_instr,name=name, reset_param=reset_param, silent=silent)


def do2D(param_1, start_1, stop_1, n_points_1, delay_1,
            param_2, start_2, stop_2, n_points_2, delay_2, *m_instr, name='',
            reset_param=False, silent=False):
    '''
    do a 2D scan

    Args:
        param_1 (qc.Parameter) : parameter to be swept
        start_1 (float) : start value of the sweep
        stop_1 (float) : stop value of the sweep
        delay_1 (float) : time to wait after the set of the parameter
        param_2 (qc.Parameter) : parameter to be swept
        start_2 (float) : start value of the sweep
        stop_2 (float) : stop value of the sweep
        delay_2 (float) : time to wait after the set of the parameter
        m_instr (*list) :  list of parameters to measure
        reset_param (bool) : reset the setpoint parametes to their original value after the meaurement
        silent (bool) : If True do not print dataset id and progress bar
    '''
    m_param_1 = sweep_info(param_1, start_1, stop_1, n_points_1, delay_1)
    m_param_2 = sweep_info(param_2, start_2, stop_2, n_points_2, delay_2)
    return scan_generic(m_param_2, m_param_1, *m_instr,
                        name=name, reset_param=reset_param, silent=silent)
