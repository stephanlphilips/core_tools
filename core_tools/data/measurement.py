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
from core_tools.data.ds.data_set import create_new_data_set

import qcodes as qc
import numpy as np
import copy

class Measurement:
    '''
    class used to describe a measurement.
    '''
    def __init__(self, name):
        self.setpoints = dict()
        self.m_param = dict()
        self.dataset = None
        self.name = name

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
                [parameter.name], [parameter.label], [parameter.unit])
        if isinstance(parameter, qc.MultiParameter):
            setpoint_parameter_spec = setpoint_dataclass(id(parameter), n_points, parameter.name,
                list(parameter.names), list(parameter.labels), list(parameter.units), list(parameter.shapes))

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
                [parameter.name], [parameter.label], [parameter.unit])

        if isinstance(parameter, qc.MultiParameter):
            m_param_parameter_spec = m_param_dataclass(id(parameter), parameter.name, 
                list(parameter.names), list(parameter.labels), list(parameter.units), list(parameter.shapes))

            setpoint_local_parameter_spec = None
            for i in range(len(parameter.setpoints)):
                my_local_setpoints = []
                for j in range(len(parameter.setpoints[i])):
                    # a bit of a local hack, in setpoints, sometimes copies are made of the setpoint name
                    # this can cause in uniquess of the keys, therefore the extra multiplications (should more or less ensure uniqueness).
                    #cleaner solution                    
                    setpoint_local_parameter_spec = setpoint_dataclass(id(parameter.setpoint_names[i][j])*10*(i+1), np.NaN, 
                        'local_var', [parameter.setpoint_names[i][j]], [parameter.setpoint_labels[i][j]],
                        [parameter.setpoint_units[i][j]], [], [])
                    data_array = parameter.setpoints[i][j]
                    shape = ( parameter.shapes[i][j],)
                    setpoint_local_parameter_spec.shapes.append(shape)
                    setpoint_local_parameter_spec.generate_data_buffer()  
                    setpoint_local_parameter_spec.write_data({setpoint_local_parameter_spec.id_info : np.asarray(data_array, order='C')})
                    my_local_setpoints.append(setpoint_local_parameter_spec)
                m_param_parameter_spec.setpoints_local.append(my_local_setpoints)


        for setpoint in setpoints:
            m_param_parameter_spec.setpoints.append(copy.copy(self.setpoints[id(setpoint)]))        

        self.m_param[m_param_parameter_spec.id_info] = m_param_parameter_spec

    def add_result(self, *args):
        '''
        add results to the data_set
        
        Args:
            *args : tuples of the parameter object submitted to the register parameter object and the get value.
        '''
        if self.dataset is None:
            raise ValueError('Dataset not initialized! please submit measurement in the context manager (e.g. with Measurement() ')
        
        args_dict = {}
        for arg in args:
            args_dict[id(arg[0])] = arg[1]

        self.dataset.add_result(args_dict)

    def __enter__(self):
        # generate dataset
        self.dataset = create_new_data_set(self.name, *self.m_param.values())

        return self

    def  __exit__(self, exc_type, exc_value, exc_traceback):
        # save data
        self.dataset.mark_completed()

        if exc_type is None:
            return True
        if exc_type == KeyboardInterrupt:
            print('Keyboard Interrupt detected. Data will be saved and a neat exit will be made.')
            return False

        return False