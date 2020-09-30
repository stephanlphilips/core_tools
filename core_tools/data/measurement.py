'''
general structure:

1) call a new measurement (e.g. Measurement())

2) register the parameters that should be measured, e.g.
    m.register_set_parameter(test1, 50)
    m.register_set_parameter(test2, 50)
    m.register_get_parameter(m_param, test1, test2)

    --> the datasets specifications happens on the fly, though no memory reservation yet
    --> the parameters must be unique. Not the same parameter on different axis allowed

3) call the context manager (will ensure that data is saved in case of errors in measurement code)
    with m as ds:

        val1 = test1()
        val2 = test2()
        ds.add_result( (test1, val1), (test2, val2), (m_param, m_param()))
    
    with the measurement is entered, the dataset is concerted to a dataset in c with reserved memory.
    The synchronization process starts in a separate thread in parallel to the measurement.
    When the last result is added, the final sync to the db is performed and you are done.
'''

from core_tools.data.lib.data_class import setpoint_dataclass, m_param_dataclass
from core_tools.data.data_set import create_new_data_set
import qcodes as qc
import numpy as np

class Measurement:
    '''
    class used to describe a measurement.
    '''
    def __init__(self):
        self.setpoints = dict()
        self.m_param = dict()
        self.dataset = None

    def register_set_parameter(self, parameter, n_points):
        '''
        Parameter that is set in a measurement.

        Args:
            parameter (qcodes parameter) : parameter to be admitted to the measurement class
            n_points (int) : number of points to be set
        '''
        param_id = id(parameter)

        if param_id in self.setpoints.keys() or param_id in self.m_param.keys():
            raise ValueError("parameter is not unique, this parameter has already been provided to this measurement.")
        
        setpoint_parameter_spec = None

        if isinstance(parameter, qc.Parameter):
            setpoint_parameter_spec = setpoint_dataclass(id(parameter), n_points, parameter.name, 
                [parameter.name], [parameter.label], [parameter.unit], list(((), )), None)
        if isinstance(parameter, qc.MultiParameter):
            setpoint_parameter_spec = setpoint_dataclass(id(parameter), n_points, parameter.name,
                list(parameter.names), list(parameter.labels), list(parameter.units), list(parameter.shapes), None)

        self.setpoints[setpoint_parameter_spec.id_info] = setpoint_parameter_spec

    def register_get_parameter(self, parameter, *setpoints):
        '''
        register parameters that you want to get in a measurement
        '''
        param_id = id(parameter)

        if param_id in self.setpoints.keys() or param_id in self.m_param.keys():
            raise ValueError("parameter is not unique, this parameter has already been provided to this measurement.")

        for setpoint in setpoints:
            if id(setpoint) not in self.setpoints.keys():
                raise ValueError("setpoint {} not yet defined, please define before declaring the measurement parameter.".format(setpoint))

        m_param_parameter_spec = None

        if isinstance(parameter, qc.Parameter):
            m_param_parameter_spec = m_param_dataclass(id(parameter), parameter.name, 
                [parameter.name], [parameter.label], [parameter.unit], list(((), )), [], [])

            my_setpoints = []

        if isinstance(parameter, qc.MultiParameter):
            m_param_parameter_spec = m_param_dataclass(id(parameter), parameter.name, 
                list(parameter.names), list(parameter.labels), list(parameter.units), list(parameter.shapes), [], [])

            setpoint_local_parameter_spec = None
            for i in range(len(parameter.setpoint_names)):
                my_setpoints = []
                setpoint_local_parameter_spec = setpoint_dataclass(id(parameter.setpoint_names[i][0]), np.NaN, 
                    'local_var', list(parameter.setpoint_names[i]), list(parameter.setpoint_labels[i]),
                    list(parameter.setpoint_units[i]), [], [])
                for j in range(len(parameter.setpoints[i])):
                    data_array = parameter.setpoints[i][j]
                    setpoint_local_parameter_spec.data.append(np.asarray(data_array, order='C').flatten())
                    shape = ( parameter.shapes[i][j],)
                    setpoint_local_parameter_spec.shapes.append(shape)

                m_param_parameter_spec.setpoints_local.append(setpoint_local_parameter_spec)



        for setpoint in setpoints:
            m_param_parameter_spec.setpoints.append(self.setpoints[id(setpoint)])                

        self.m_param[m_param_parameter_spec.id_info] = m_param_parameter_spec

    def add_result(*args):
        '''
        add results to the data_set
        
        Args:
            *args : tuples of the parameter object submitted to the register parameter object and the get value.
        '''
        if self.dataset is None:
            raise ValueError('Dataset not initialized! please submit measurement in the context manager (e.g. with Measurement() ')
        
        args_dict = {}
        for arg in args:
            args_dict[id(arg[0])] = arg

        self.dataset.add_results(self.m_param, *args)

    def __enter__(self):
        # generate dataset
        self.dataset = create_new_data_set(*self.m_param.values())
        return self

    def  __exit__(self, exc_type, exc_value, exc_traceback):
        # save data
        self.dataset.mark_completed()

        if exc_type is None:
            return True
        if exc_type == KeyboardInterrupt:
            print('Keyboard Interrupt detected. Data will be saved and a neat exit will be made.')
            return True

        return False

if __name__ == '__main__':
    import qcodes as qc
    from core_tools.sweeps.sweeps import do0D
    from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import fake_digitizer, construct_1D_scan_fast, construct_2D_scan_fast
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
            self.setpoint_names = ( ("I_channel", ),   ("Q_channel", ))
            self.setpoint_shapes = ( tuple(),   tuple())
            self.setpoint_labels = ( ("I channel", ),   ('Q channel', ))
            self.setpoint_units = ( ("mV", ),   ("mV", ))
            self.i = 2
        def get_raw(self):
            self.i +=1
            return (self.i, self.i+100)


    dig = fake_digitizer("test")


    a1 = MyCounter('name1')

    a2 = MyCounter('name2')
    # d = dummy_multi_parameter_2dawg("name2")
    m1 = MyCounter('name3')
    m2 = dummy_multi_parameter_2dawg("name4")
    m3 = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, None, dig)
    m4 = construct_1D_scan_fast("P2", 10,10,5000, True, None, dig)

    meas = Measurement()
    meas.register_set_parameter(a1, 50)
    meas.register_set_parameter(a2, 50)

    meas.register_get_parameter(m4, a1, a2)

    m_param_1 = list(meas.m_param.values())[0]
    print(id(m_param_1))
    input_data  = {    }
    input_data[id(m4)] = [[25], [50]]
    input_data[id(a1)] = [10]
    input_data[id(a2)] = [5]

    m_param_1.init_data_set()
    m_param_1.write_data(input_data)
    m_param_1.write_data(input_data)
    # print(m_param_1)

    with meas as ds:
        # ds = 'blub'
        print(ds)
        # raise Exception('exception raised').with_traceback(None)
        # 5/0