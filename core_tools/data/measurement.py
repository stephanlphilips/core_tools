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
import logging

logger = logging.getLogger(__name__)


class Measurement:
    '''
    class used to describe a measurement.
    '''

    def __init__(self, name, silent=False):
        self.silent = silent
        self.setpoints = dict()
        self.m_param = dict()
        self.dataset = None
        self.name = name
        self.snapshot = dict()
        self.void_parameters = []

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
            setpoint_parameter_spec = setpoint_dataclass(
                id(parameter), n_points, parameter.name,
                [parameter.name], [parameter.label], [parameter.unit])
        if isinstance(parameter, qc.MultiParameter):
            setpoint_parameter_spec = setpoint_dataclass(
                id(parameter), n_points, parameter.name,
                list(parameter.names), list(parameter.labels),
                list(parameter.units), list(parameter.shapes))

        self.setpoints[setpoint_parameter_spec.id_info] = setpoint_parameter_spec
        self._add_param_snapshot(parameter)

    def register_get_parameter(self, parameter, *setpoints):
        '''
        register parameters that you want to get in a measurement
        '''
        param_id = id(parameter)

        if param_id in self.setpoints.keys() or param_id in self.m_param.keys():
            raise ValueError("parameter is not unique, this parameter has already exists in this measurement.")

        for setpoint in setpoints:
            if id(setpoint) not in self.setpoints.keys():
                raise ValueError(
                    f"setpoint {setpoint} not yet defined. Define before declaring the measurement parameter.")

        m_param_parameter_spec = None

        if isinstance(parameter, str):
            raise Exception(f"'{parameter}' is not a Parameter")

        if isinstance(parameter, qc.Parameter):
            m_param_parameter_spec = m_param_dataclass(
                id(parameter), parameter.name,
                [parameter.name], [parameter.label], [parameter.unit])

        if isinstance(parameter, qc.MultiParameter):
            if len(parameter.names) == 0:
                self.void_parameters.append(parameter)
                logger.warning(f'Parameter {parameter.name} returns no data. Skipping parameter!')
                return
            m_param_parameter_spec = m_param_dataclass(
                id(parameter), parameter.name,
                list(parameter.names), list(parameter.labels),
                list(parameter.units), list(parameter.shapes))

            setpoint_local_parameter_spec = None
            for i in range(len(parameter.setpoints)):
                my_local_setpoints = []
                cum_shape = tuple()
                for j in range(len(parameter.setpoints[i])):
                    # a bit of a local hack, in setpoints, sometimes copies are made of the setpoint name
                    # this can cause in uniquess of the keys, therefore the extra multiplications
                    # (should more or less ensure uniqueness).
                    setpoint_local_parameter_spec = setpoint_dataclass(
                        id(parameter.setpoint_names[i][j])*10*(i+1), np.NaN,
                        'local_var',
                        [parameter.setpoint_names[i][j]],
                        [parameter.setpoint_labels[i][j]],
                        [parameter.setpoint_units[i][j]],
                        [], [])
                    data_array = parameter.setpoints[i][j]
                    shape = (parameter.shapes[i][j], )
                    cum_shape += shape
                    # qcodes setpoints (N, (N*M), ..) or simple coretools: (N, M, ...)?
                    if isinstance(data_array[0], tuple):
                        shape = cum_shape
                    setpoint_local_parameter_spec.shapes.append(shape)
                    setpoint_local_parameter_spec.generate_data_buffer()
                    setpoint_local_parameter_spec.write_data(
                        {setpoint_local_parameter_spec.id_info: np.asarray(data_array, order='C')})
                    my_local_setpoints.append(setpoint_local_parameter_spec)
                m_param_parameter_spec.setpoints_local.append(my_local_setpoints)

        if m_param_parameter_spec is None:
            raise Exception(f'Unknown parameter type: {type(parameter)}')

        for setpoint in setpoints:
            m_param_parameter_spec.setpoints.append(copy.copy(self.setpoints[id(setpoint)]))

        self.m_param[m_param_parameter_spec.id_info] = m_param_parameter_spec
        self._add_param_snapshot(parameter)

    def _add_param_snapshot(self, param):
        try:
            self.snapshot[param.name] = param.snapshot()
        except Exception:
            logger.error('Parameter snapshot failed', exc_info=True)

    def add_snapshot(self, name, snapshot):
        self.snapshot[name] = snapshot

    def add_result(self, *args):
        '''
        add results to the data_set

        Args:
            *args : tuples of the parameter object submitted to the register parameter object and the get value.
        '''
        if self.dataset is None:
            raise ValueError(
                'Dataset not initialized! Start measurement using context manager, e.g. "with Measurement():')

        args_dict = {}
        for arg in args:
            args_dict[id(arg[0])] = arg[1]

        self.dataset.add_result(args_dict)

    def __enter__(self):
        # generate dataset
        if len(self.m_param) == 0:
            if self.void_parameters:
                raise Exception('Measurement parameters do not return any data.')
            else:
                raise Exception('No measurement parameters specified')
        self.dataset = create_new_data_set(self.name, self.snapshot, *self.m_param.values())
        msg = f'Starting measurement with id : {self.dataset.exp_id} - {self.name}'
        logger.info(msg)
        if not self.silent:
            print(f'\n{msg}', flush=True)

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # save data
        self.dataset.mark_completed()

        if exc_type is None:
            return True
        if exc_type == KeyboardInterrupt:
            print('\nMeasurement aborted with keyboard interrupt. Data has been saved.')
            return False

        return False
