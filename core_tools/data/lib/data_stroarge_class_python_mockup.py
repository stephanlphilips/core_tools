from dataclasses import dataclass
import numpy as np
import time
import datetime
import json

def create_new_data_set(*m_params):
    '''
    generates a dataclass for a given set of measurement parameters

    Args:
        *m_params (m_param_dataset) : datasets of the measurement parameters
    '''
    # get exp_id and SQL info TODO!!
    ds = data_set_raw([], 'SQL_table_name', 50, 'exp_name', 'set_up', 'project', 'sample')

    for m_param in m_params:
        m_param.init_data_set()
        ds.data_entries += m_param.to_SQL_data_structure()

    return data_set(ds)

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

    completed : bool = False
    writecount : int = 0

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

    def add_result(self, m_params, input_data):
        '''
        Add results to the dataset

        Args:
            m_params (list) : list with the meaurement parameters for this experiment.
            input_data (dict<int, list<np.ndarray>>) : dict with as key the id of the measured parameter and the data that is measured.
        '''
        for m_param in m_params:
            if m_param.id_info in input_data.keys():
                m_param.write_data(input_data)

        # let the sql server know that a update has happened.
        self.__data_set_raw.writecount += 1

if __name__ == '__main__':
    ds = data_set_raw([], 'test_table', 1, 'rabi', 'XLD', '5dot', '6D3S', time.time(), 0, False, "[1,2,3]", "[]")

    dc = data_set(ds)

    print(dc.run_id)
    print(dc.run_timestamp_raw)
    print(dc.snapshot)
    print(dc.run_timestamp)
    a = setpoint_dataclass(5, 10, 30, [50], [50], [50], [50])
    print(setpoint_dataclass(5, 10, 30, [50], [50], [50], [50]))
    print(a)

