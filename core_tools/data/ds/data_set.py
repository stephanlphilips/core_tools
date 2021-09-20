import logging
from core_tools.data.ds.data_set_core import data_set_raw, data_set
from core_tools.data.SQL.SQL_dataset_creator import SQL_dataset_creator
import json
import qcodes as qc

def load_by_id(exp_id):
    '''
    load a dataset by specifying its id (search in local db)

    args:
        exp_id (int) : id of the experiment you want to load
    '''
    SQL_mgr = SQL_dataset_creator()
    return data_set(SQL_mgr.fetch_raw_dataset_by_Id(exp_id))

def load_by_uuid(exp_uuid, copy2localdb=False):
    '''
    load a dataset by specifying its uuid (searches in local and remote db)

    args:
        exp_uuid (int) : uuid of the experiment you want to load
        copy2localdb (bool): copy measurement to local database if only in remote
    '''
    SQL_mgr = SQL_dataset_creator()
    return data_set(SQL_mgr.fetch_raw_dataset_by_UUID(exp_uuid, copy2localdb))

def create_new_data_set(experiment_name, *m_params):
    '''
    generates a dataclass for a given set of measurement parameters

    Args:
        *m_params (m_param_dataset) : datasets of the measurement parameters
    '''
    ds = data_set_raw(exp_name=experiment_name)

    if qc.Station.default is not None:
        snapshot = qc.Station.default.snapshot()
        snapshot_json = json.dumps({'station': snapshot}, cls=qc.utils.helpers.NumpyJSONEncoder)
        ds.snapshot = json.loads(snapshot_json)
    else:
        logging.error('No station configured')
        snapshot_json = ''

    # intialize the buffers for the measurement
    for m_param in m_params:
        m_param.init_data_dataclass()
        ds.measurement_parameters += [m_param]
        ds.measurement_parameters_raw += m_param.to_SQL_data_structure()

    SQL_mgr = SQL_dataset_creator()
    SQL_mgr.register_measurement(ds)

    ds.snapshot = json.dumps(snapshot_json)

    return data_set(ds)

if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage

    set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

    ds= (load_by_id(92))
    print(ds.snapshot)
    print(ds.metadata)
    # print(ds.m1.z())
    # print(ds.m1.x())
    # print(ds.m1.y())