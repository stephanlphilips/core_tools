from dataclasses import dataclass
import numpy as np
import time
import datetime
import json

@dataclass
class data_item:
    name : str
    label : str
    unit : str
    dependency : list
    shape : list
    raw_data :  np.ndarray

@dataclass
class data_set_raw:
    data_entries : list = None
    SQL_table_name : str = None
    exp_id : int = None
    exp_name : str = None
    set_up : str = None
    project : str = None
    sample : str = None
    UNIX_start_time : int = None
    UNIX_stop_time : int = None
    uploaded_complete : bool = None
    snapshot : str = None
    metadata : str = None


class dataset_raw_parent:
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

        print('start',self.cursor)
        for i in range(len(data_in)):
            data = np.asarray(data_in[i]).flatten()
            self.data[i][self.cursor[i] : self.cursor[i] + data.size] = data
            self.cursor[i] += data.size
        print(self.cursor)

    @property
    def cursor(self):
        if self.__cursors is None:
            self.__cursors = [0] * len(self.data)

        return self.__cursors

    @cursor.setter
    def cursor(self, value):
        self.__cursors = value

@dataclass
class setpoint_dataset(dataset_raw_parent):
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
class m_param_dataset(dataset_raw_parent):
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
        super().write_data(input_data)

        for setpoint in self.setpoints:
            setpoint.write_data(input_data)

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

    def to_c_data(self):
        '''
        make c object that countain pointers to the data that needs to be uploaded.
        '''
        pass

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

class data_class_desciptor(object):
    def __init__(self, variable, is_time=False, is_JSON=False):
        self.var = variable
        self.is_time = is_time
        self.is_JSON = is_JSON
    def __get__(self, obj, objtype):
        if self.is_time:
            return datetime.datetime.fromtimestamp(getattr(getattr(obj,"_data_class__data_set_raw"), self.var))
        if self.is_JSON:
            return json.loads(getattr(getattr(obj,"_data_class__data_set_raw"), self.var))

        return getattr(getattr(obj,"_data_class__data_set_raw"), self.var)

def create_new_data_set(m_param):
    '''
    generates a dataclass for a given set of measurement parameters

    Args:
        m_param (m_param_dataset) : dataset of the measurement parameters
    '''
    pass

    


class data_class:
    run_id = data_class_desciptor('exp_id')
    running = data_class_desciptor('uploaded_complete')
    
    table_name = data_class_desciptor('SQL_table_name')
    name = data_class_desciptor('exp_name')
    
    exp_id = data_class_desciptor('exp_id')
    exp_name = data_class_desciptor('exp_name')
    
    project = data_class_desciptor('project')
    set_up = data_class_desciptor('set_up')
    sample_name = data_class_desciptor('sample')
    
    metadata_raw = data_class_desciptor('metadata')
    snapshot_raw = data_class_desciptor('snapshot')
    metadata = data_class_desciptor('metadata', is_JSON=True)
    snapshot = data_class_desciptor('snapshot', is_JSON=True)
    
    run_timestamp = data_class_desciptor('UNIX_start_time', is_time=True)
    run_timestamp_raw = data_class_desciptor('UNIX_start_time')
    completed_timestamp = data_class_desciptor('UNIX_stop_time', is_time=True)
    completed_timestamp_raw = data_class_desciptor('UNIX_stop_time')

    def __init__(self, ds_raw):
        self.id = None
        self.__initialized = False
        self.__data_set_raw = ds_raw
        self.__property_managment_list = []

    def __init_properties(self):
        # make easy_access_properties x,y,z, z1,z2, y2, ...
        pass

    def __generate_data_variables(self):
        pass

    def add_metadata(self, metadata):
        pass

    def add_snapshot(self, snapshot):
        pass

    def mark_completed(self):
        self.__data_set_raw.completed = True

    def add_result(self, *args):
        pass

if __name__ == '__main__':
    ds = data_set_raw([], 'test_table', 1, 'rabi', 'XLD', '5dot', '6D3S', time.time(), 0, False, "[1,2,3]", "[]")

    dc = data_class(ds)

    print(dc.run_id)
    print(dc.run_timestamp_raw)
    print(dc.snapshot)
    print(dc.run_timestamp)
    a = setpoint_dataset(5, 10, 30, [50], [50], [50], [50])
    print(setpoint_dataset(5, 10, 30, [50], [50], [50], [50]))
    print(a)

