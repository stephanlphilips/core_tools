from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from qcodes.dataset.measurements import Measurement
from pulse_lib.sequencer import sequencer

from core_tools.sweeps.sweep_utility import pulselib_2_qcodes, sweep_info, get_measure_data, KILL_EXP
from core_tools.job_mgnt.job_meta import job_meta

import numpy as np
import time

class scan_generic(metaclass=job_meta):
    '''
    function that handeles the loop action and defines the run class.
    '''
    def __init__(self, *args, reset_param=False):
        '''
        init of the scan function

        Args:
            args (*list) :  provide here the sweep info and meaurment parameters
            reset_param (bool) : reset the setpoint parametes to their original value after the meaurement 
        '''
        self.meas = Measurement()

        self.set_vars = []
        self.m_instr = []
        self.reset_param = reset_param

        set_points = []
        for arg in args:
            if isinstance(arg, sweep_info):
                self.meas.register_parameter(arg.param)
                self.set_vars.append(arg)
                set_points.append(arg.param)
            elif isinstance(arg, sequencer):
                set_vars_pulse_lib = pulselib_2_qcodes(arg)
                for var in set_vars_pulse_lib:
                    self.meas.register_parameter(var.param)
                    set_points.append(var.param)
                self.set_vars += set_vars_pulse_lib
            else:
                self.m_instr.append(arg)
        for instr in self.m_instr:
            self.meas.register_parameter(instr, setpoints=tuple(set_points[::-1]))
                
        self.n_tot = 1
        for swp_info in self.set_vars:
            self.n_tot *= swp_info.n_points

    def run(self):
        '''
        run function
        -- starts the meaurement and saves the data
        -- optionally also resets the paramters
        -- wrapped by the job_meta class (allows for progress bar to appear)
        '''
        with self.meas.run() as datasaver:
            self._loop(self.set_vars, self.m_instr, tuple(), datasaver)
            dataset = datasaver.dataset
        
        if self.reset_param:
            for param in self.set_vars:
                param.reset_param()

        return dataset

    def _loop(self, set_param, m_instr, to_save, datasaver):
        if len(set_param) == 0:
            if self.KILL == False:
                datasaver.add_result(*to_save, *get_measure_data(m_instr))
                self.n += 1
            else:
                raise KILL_EXP
        else:
            param_info = set_param[0]
            for value in np.linspace(param_info.start, param_info.stop, param_info.n_points):
                if not isinstance(param_info.param, ElapsedTimeParameter):
                    param_info.param(value)
                time.sleep(param_info.delay)
                self._loop(set_param[1:], m_instr, to_save + ((param_info.param, param_info.param()),), datasaver)


def do0D(*m_instr):
    '''
    do a 0D scan

    Args:
        m_instr (*list) :  list of parameters to measure
    '''
    return scan_generic(*m_instr, reset_param=False)

def do1D(param, start, stop, n_points, delay, *m_instr, reset_param=False):
    '''
    do a 1D scan

    Args:
        param (qc.Parameter) : parameter to be swept
        start (float) : start value of the sweep
        stop (float) : stop value of the sweep
        delay (float) : time to wait after the set of the parameter
        m_instr (*list) :  list of parameters to measure
        reset_param (bool) : reset the setpoint parametes to their original value after the meaurement 
    '''
    m_param = sweep_info(param, start, stop, n_points, delay)
    return scan_generic(m_param, *m_instr, reset_param=reset_param)

def do2D(param_1, start_1, stop_1, n_points_1, delay_1,
            param_2, start_2, stop_2, n_points_2, delay_2, *m_instr, reset_param=False):
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
    '''
    m_param_1 = sweep_info(param_1, start_1, stop_1, n_points_1, delay_1)
    m_param_2 = sweep_info(param_2, start_2, stop_2, n_points_2, delay_2)
    return scan_generic(m_param_2, m_param_1, *m_instr, reset_param=reset_param)

if __name__ == '__main__':

    import os
    import datetime

    import numpy as np
    import scipy.optimize as opt
    import matplotlib.pyplot as plt

    import qcodes as qc
    from qcodes.dataset.plotting import plot_dataset
    from qcodes.dataset.data_set import load_by_run_spec
    from qcodes.dataset.sqlite.database import initialise_or_create_database_at
    from qcodes.dataset.experiment_container import load_or_create_experiment
    from qcodes.tests.instrument_mocks import MockParabola

    station = qc.station.Station()
    station.add_component(MockParabola(name='MockParabola'))
    
    class MyCounter(qc.Parameter):
        def __init__(self, name):
            # only name is required
            super().__init__(name, label='Times this has been read',
                             docstring='counts how many times get has been called '
                                       'but can be reset to any integer >= 0 by set')
            self._count = 0

        # you must provide a get method, a set method, or both.
        def get_raw(self):
            self._count += 1
            return self._count

        def set_raw(self, val):
            self._count = val


    now = str(datetime.datetime.now())
    tutorial_db_path = os.path.join(os.getcwd(), 'linking_datasets_tutorial.db')
    initialise_or_create_database_at(tutorial_db_path)
    load_or_create_experiment('tutorial ' + now, 'no sample')
    my_param = MyCounter('test_instr')
    from qcodes.instrument.specialized_parameters import ElapsedTimeParameter

    x = qc.Parameter(name='x', label='Voltage_x', unit='V',
              set_cmd=None, get_cmd=None)
    y = qc.Parameter(name='y', label='Voltage_y', unit='V',
              set_cmd=None, get_cmd=None)
    timer = ElapsedTimeParameter('time')
    # do0D(my_param).run()
    # do1D(x, 0, 100, 50, 0.1 , my_param, reset_param=True).run()
    do2D(x, 0, 20, 20, 0.0, y, 0, 80, 30, 0.01, my_param).run()
    do2D(x, 0, 20, 20, 0.0, timer, 0, 80, 30, 0.1, my_param).run()