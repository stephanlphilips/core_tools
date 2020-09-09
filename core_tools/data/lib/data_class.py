from dataclasses import dataclass
import numpy as np
import json

@dataclass
class data_item:
    param_id : int
    nth_set : int
    param_id_m_param : int #unique identifier for this m_param
    setpoint : bool
    setpoint_local : bool
    name_gobal : str
    name : str
    label : str
    unit : str
    dependency : str
    shape : str
    raw_data :  np.ndarray
    size : int

class dataclass_raw_parent:
    __cursors = None

    def write_data(self, input_data):
        '''
        write data to memory of the measurement

        Args:
            input_data : dict formatted as e.g. write_data({'id(parameter_1)' : parameter_1.get(), id(parameter_2) : parameter_2.get(), ..})
        '''
        if self.id_info not in input_data.keys():
            txt = 'Key not found. A write is attempted to a parameter that has not been declaired yet. '
            txt += 'Please first register the parameter with register_set_parameter/register_get_parameter '
            raise KeyError(txt)
        
        data_in = input_data[self.id_info]

        for i in range(len(data_in)):
            data = np.asarray(data_in[i]).flatten()
            self.data[i][self.cursor[i] : self.cursor[i] + data.size] = data
            self.cursor[i] += data.size

    def to_c_data(self, m_param_id, setpoint, setpoint_local, dependencies=[]):
        '''
        disassembele the dataset into a c data set

        Args:
            m_param_id (int): id of the measurement parameter where this data belongs to.
            setpoint (bool): is this data a setpoint?
            setpoint_local (bool) : is this data a local setpoint (e.g. of a multiparameter)
            dependencies (str<JSON>) : json of the dependencies
        '''
        data_items = []

        for i in range(len(self.data)):
            data_items +=[data_item(self.id_info, i, m_param_id, setpoint, setpoint_local,
                self.name, json.dumps(self.names[i]), json.dumps(self.labels[i]),
                json.dumps(self.units[i]), dependencies, json.dumps(self.shapes[i]), self.data[i], self.data[i].size)]

        return data_items

    @property
    def cursor(self):
        if self.__cursors is None:
            self.__cursors = [0] * len(self.data)

        return self.__cursors

    @cursor.setter
    def cursor(self, value):
        self.__cursors = value

@dataclass
class setpoint_dataclass(dataclass_raw_parent):
    id_info : id
    npt : int
    name : str
    names : list
    labels : list
    units : list
    shapes : list
    data : list = None

    def __repr__(self):
        description = "id :: {} \tname :: {}\tnpt :: {}\n".format(self.id_info, self.name, self.npt)
        description += "names :\t{}\tlabels :\t{}\nunits :\t{}\tshapes :\t{}\n".format(self.names, self.labels, self.units, self.shapes)

        return description

@dataclass 
class m_param_dataclass(dataclass_raw_parent):
    id_info : id 
    name : str
    names : list
    labels : list
    units : list
    shapes : list
    setpoints : list
    setpoints_local : list
    data : list = None

    def write_data(self, input_data):
        '''
        write data to memory of the measurement

        Args:
            input_data : dict formatted as e.g. write_data({'id(parameter_1)' : parameter_1.get(), id(parameter_2) : parameter_2.get(), ..})
        '''
        super().write_data(input_data)

        for setpoint in self.setpoints:
            setpoint.write_data(input_data)

    def to_c_data(self):
        data_items = []

        data_items += super().to_c_data(self.id_info, False, False, self.dependencies)
        for setpt in self.setpoints:
            data_items += setpt.to_c_data(self.id_info, True, False)

        for setpt in self.setpoints:
            data_items += setpt.to_c_data(self.id_info, False, True)

        return data_items

    def init_data_set(self):
        '''
        initialize the arrays in the dataset. This are all flat arrays.
        '''
        setpoint_shape = []
        for setpoint in self.setpoints:
            setpoint_shape += [setpoint.npt]
            setpoint.data = list()

            for shape in setpoint.shapes:
                arr = np.full([setpoint.npt] + list(shape), np.nan, order='C').flatten()
                setpoint.data.append(arr)

        self.data = list()
        for shape in self.shapes:
            arr = np.full(setpoint_shape + list(shape), np.nan, order='C').flatten()
            self.data.append(arr)

    @property
    def dependencies(self):
        dep = []
        for setpt in self.setpoints:
            dep.append(setpt.id_info)
        for setpt in self.setpoints_local:
            dep.append(setpt.id_info)
        return dep
    
    def __repr__(self):
        description = "\n########################\nMeasurement dataset info\n########################\nid :: {} \nname :: {}\n\n".format(self.id_info, self.name)
        description += "names :\t{}\nlabels :\t{}\nunits :\t{}\nshapes :\t{}\n".format(self.names, self.labels, self.units, self.shapes)
        for i in range(len(self.setpoints_local)):
            description += "\n##################\nlocal setpoint {}\n".format(i)
            description += self.setpoints_local[i].__repr__()

        for i in range(len(self.setpoints)):
            description += "\n##################\nsetpoint {}\n".format(i)
            description += self.setpoints[i].__repr__()

        return description