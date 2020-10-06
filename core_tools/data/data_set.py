from core_tools.data.SQL.SQL_database_mgr import SQL_database_manager
from core_tools.data.SQL.connector import sample_info
from dataclasses import dataclass, field
import numpy as np
import time
import datetime
import json

def create_new_data_set(experiment_name, *m_params):
    '''
    generates a dataclass for a given set of measurement parameters

    Args:
        *m_params (m_param_dataset) : datasets of the measurement parameters
    '''
    ds = data_set_raw(exp_name=experiment_name)

    # intialize the buffers for the measurement
    for m_param in m_params:
        m_param.init_data_dataclass()
        ds.measurement_parameters += [m_param]
        ds.measurement_parameters_raw += m_param.to_SQL_data_structure()

    SQL_mgr = SQL_database_manager()
    SQL_mgr.register_measurement(ds)

    return data_set(ds)

@dataclass
class data_set_raw:
    exp_id : int = None
    exp_name : str = None

    set_up : str = field(default_factory=lambda: sample_info.set_up)
    project : str = field(default_factory=lambda: sample_info.project)
    sample : str = field(default_factory=lambda: sample_info.sample)
    
    SQL_datatable : str = None
    measurement_parameters : list = field(default_factory=lambda: [])
    measurement_parameters_raw : list = field(default_factory=lambda: [])
    
    UNIX_start_time : int = None
    UNIX_stop_time : int = None
    
    uploaded_complete : bool = None
    
    snapshot : str = None
    metadata : str = None

    completed : bool = False
    writecount : int = 0

@dataclass
class m_param_raw:
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
    size : int
    oid : int
    data_buffer : any

class data_set_desciptor(object):
    def __init__(self, variable, is_time=False, is_JSON=False):
        self.var = variable
        self.is_time = is_time
        self.is_JSON = is_JSON
    def __get__(self, obj, objtype):
        if self.is_time:
            return datetime.datetime.fromtimestamp(getattr(getattr(obj,"_data_set__data_set_raw"), self.var))
        if self.is_JSON:
            return json.loads(getattr(getattr(obj,"_data_set__data_set_raw"), self.var))

        return getattr(getattr(obj,"_data_set__data_set_raw"), self.var)

class data_set:
    run_id = data_set_desciptor('exp_id')
    running = data_set_desciptor('uploaded_complete')
    
    table_name = data_set_desciptor('SQL_table_name')
    name = data_set_desciptor('exp_name')
    
    exp_id = data_set_desciptor('exp_id')
    exp_name = data_set_desciptor('exp_name')
    
    project = data_set_desciptor('project')
    set_up = data_set_desciptor('set_up')
    sample_name = data_set_desciptor('sample')
    
    metadata_raw = data_set_desciptor('metadata')
    snapshot_raw = data_set_desciptor('snapshot')
    metadata = data_set_desciptor('metadata', is_JSON=True)
    snapshot = data_set_desciptor('snapshot', is_JSON=True)
    
    run_timestamp = data_set_desciptor('UNIX_start_time', is_time=True)
    run_timestamp_raw = data_set_desciptor('UNIX_start_time')
    completed_timestamp = data_set_desciptor('UNIX_stop_time', is_time=True)
    completed_timestamp_raw = data_set_desciptor('UNIX_stop_time')

    def __init__(self, ds_raw):
        self.id = None
        self.__initialized = False
        self.__data_set_raw = ds_raw
        self.__property_managment_list = []

        self.last_commit = time.time()

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
        '''
        mark dataset complete. Stop updating the database and allow garbage collector to release memory.
        '''
        self.__data_set_raw.completed = True
        self.__write_to_db(True)
        SQL_mgr = SQL_database_manager()
        SQL_mgr.finish_measurement(self.__data_set_raw)

    def add_result(self, input_data):
        '''
        Add results to the dataset

        Args:
            input_data (dict<int, list<np.ndarray>>) : dict with as key the id of the measured parameter and the data that is measured.
        '''
        for m_param in self.__data_set_raw.measurement_parameters:
            if m_param.id_info in input_data.keys():
                m_param.write_data(input_data)

        self.__write_to_db()

    def __write_to_db(self, force = False):
        '''
        update values every 200ms to the database.
        '''
        current_time = time.time() 
        if current_time - self.last_commit > 0.2 or force==True:
            self.last_commit=current_time
            SQL_mgr = SQL_database_manager()
            SQL_mgr.update_write_cursors(self.__data_set_raw)


if __name__ == '__main__':
    sample_info("project", "set_up", "sample")
    ds = data_set_raw(exp_name='test')

    print(ds.project)
    
    dc = data_set(ds)

    # print(dc.run_id)
    # print(dc.run_timestamp_raw)
    # print(dc.snapshot)
    # print(dc.run_timestamp)

    # a = setpoint_dataclass(5, 10, 30, [50], [50], [50], [50])
    # print(setpoint_dataclass(5, 10, 30, [50], [50], [50], [50]))
    # print(a)

