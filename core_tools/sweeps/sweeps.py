from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from core_tools.data.measurement import Measurement
from pulse_lib.sequencer import sequencer

from core_tools.sweeps.sweep_utility import pulselib_2_qcodes, sweep_info, get_measure_data, KILL_EXP
from core_tools.job_mgnt.job_meta import job_meta
from core_tools.job_mgnt.job_mgmt import queue_mgr, ExperimentJob

import numpy as np
import time

class scan_generic(metaclass=job_meta):
    '''
    function that handeles the loop action and defines the run class.
    '''
    def __init__(self, *args, name='', reset_param=False):
        '''
        init of the scan function

        Args:
            args (*list) :  provide here the sweep info and meaurment parameters
            reset_param (bool) : reset the setpoint parametes to their original value after the meaurement 
        '''
        self.name = name
        self.meas = Measurement(self.name)

        self.set_vars = []
        self.m_instr = []
        self.reset_param = reset_param

        set_points = []
        for arg in args:
            if isinstance(arg, sweep_info):
                self.meas.register_set_parameter(arg.param, arg.n_points)
                self.set_vars.append(arg)
                set_points.append(arg.param)
            elif isinstance(arg, sequencer):
                set_vars_pulse_lib = pulselib_2_qcodes(arg)
                for var in set_vars_pulse_lib:
                    self.meas.register_set_parameter(var.param, var.n_points)
                    self.set_vars.append(var)
                    set_points.append(var.param)
            elif arg is None:
                continue
            else:
                self.m_instr.append(arg)

        for instr in self.m_instr:
            self.meas.register_get_parameter(instr, *set_points)
                
        self.n_tot = 1

        if name == '':
            if len(self.set_vars) == 0:
                self.name = '0D_' + self.m_instr[0].name[:10]
            else:
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
        with self.meas as ds:
            self._loop(self.set_vars, self.m_instr, tuple(), ds)
        
        if self.reset_param:
            for param in self.set_vars:
                try:
                    param.reset_param()
                except:
                    pass

        return self.meas.dataset

    def put(self, priority = 1):
        '''
        put the job in a queue.
        '''
        queue = queue_mgr()
        job = ExperimentJob(priority, self)

    def _loop(self, set_param, m_instr, to_save, dataset):
        if len(set_param) == 0:
            if self.KILL == False:
                dataset.add_result(*to_save, *get_measure_data(m_instr))
                self.n += 1
            else:
                raise KILL_EXP
        else:
            param_info = set_param[0]
            for value in np.linspace(param_info.start, param_info.stop, param_info.n_points):
                if not isinstance(param_info.param, ElapsedTimeParameter):
                    param_info.param(value)
                time.sleep(param_info.delay)
                self._loop(set_param[1:], m_instr, to_save + ((param_info.param, param_info.param()),), dataset)


def do0D(*m_instr, name=''):
    '''
    do a 0D scan

    Args:
        m_instr (*list) :  list of parameters to measure
    '''
    return scan_generic(*m_instr, name=name, reset_param=False)

def do1D(param, start, stop, n_points, delay, *m_instr, name='', reset_param=False):
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
    return scan_generic(m_param, *m_instr,name=name, reset_param=reset_param)

def do2D(param_1, start_1, stop_1, n_points_1, delay_1,
            param_2, start_2, stop_2, n_points_2, delay_2, *m_instr, name='', reset_param=False):
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
    return scan_generic(m_param_2, m_param_1, *m_instr, name=name, reset_param=reset_param)

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

    class dummy_multi_parameter_2dawg(qc.MultiParameter):
        def __init__(self, name, label=None, unit=None):
            
            super().__init__(name=name,
                             instrument=None,
                             names=("test12","test1234"),
                             shapes=( tuple() , tuple() ),
                             labels=( "digitzer_response",  "D2"),
                             units=("unit1", "unit2"), )
            self.setpoints = ( tuple(),  tuple())
            self.setpoint_shapes = ( tuple(),   tuple())
            self.setpoint_labels = ( ("I channel", ),   ('Q channel', ))
            self.setpoint_units = ( ("mV", ),   ("mV", ))
            self.setpoint_names = ( ("I_channel", ),   ("Q_channel", ))
            self.i = 2
        def get_raw(self):
            self.i +=1
            return (self.i, self.i+100)


    import qcodes
    from qcodes import Parameter, Station
    from qcodes.tests.instrument_mocks import DummyInstrument

    station = Station()
    instr = DummyInstrument('instr', gates=['input', 'output', 'gain'])
    instr.gain(42)
    # station.add_component(p)
    station.add_component(instr)

    from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
    # set_up_local_storage("xld_user", "XLDspin001", "vandersypen_data", "6dot", "XLD", "testing")

    now = str(datetime.datetime.now())
    path = os.path.join(os.getcwd(), 'test.db')
    initialise_or_create_database_at(path)
    load_or_create_experiment('tutorial ' + now, 'no sample')
    my_param = MyCounter('test_instr')
    from qcodes.instrument.specialized_parameters import ElapsedTimeParameter

    x = qc.Parameter(name='x', label='Voltage_x', unit='V',
              set_cmd=None, get_cmd=None)
    y = qc.Parameter(name='y', label='Voltage_y', unit='V',
              set_cmd=None, get_cmd=None)
    timer = ElapsedTimeParameter('time')
    my_param_multi_test =dummy_multi_parameter_2dawg('param')

    from sweep_utility import sweep_info

    s = sweep_info(x,10,100,10,0)
    print(s.param(5))
    print(s.param)
    s.param = 5
    # from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import construct_1D_scan_fast,construct_2D_scan_fast, fake_digitizer
    # param_1D = construct_1D_scan_fast("P2", 10,10,5000, True, None, fake_digitizer('test'))
    # param_2D = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, None, fake_digitizer('test'))
    # data_1D = param_1D.get()
    # do0D(param_2D).run()
    # do1D(x, 0,5,100, 0.01, param_1D).run()
    from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import construct_1D_scan_fast,construct_2D_scan_fast, fake_digitizer
    param_1D = construct_1D_scan_fast("P2", 10,10,5000, True, None, fake_digitizer('test'), 2, 1e9)
    param_2D = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, None, fake_digitizer('test'), 2, 1e9)
    # data_1D = param_1D.get()
    # do0D(param_2D).run()
    print(param_2D.shapes)
    print(param_2D.setpoints)
    ds = do0D(param_2D).run()
    # print(ds)
    # do1D(x, 0,5,100, 0.01, my_param).run()

    # do2D(y, 0,5,100, 0.001,x, 0,5,100, 0.001, my_param).run()

    print(station.snapshot())
    