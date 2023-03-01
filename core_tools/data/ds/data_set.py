import logging
from core_tools.data.ds.data_set_core import  data_set
from core_tools.data.ds.data_set_raw import data_set_raw
from core_tools.data.SQL.SQL_dataset_creator import SQL_dataset_creator
import json
import qcodes as qc
from qcodes.utils.helpers import NumpyJSONEncoder

logger = logging.getLogger(__name__)

DATA_POINTS_MAX = 20_000_000
DATASET_SIZE_WARNING = 50_000_000
DATASET_SIZE_MAX = 200_000_000

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

def create_new_data_set(experiment_name, measurement_snapshot, *m_params):
    '''
    generates a dataclass for a given set of measurement parameters

    Args:
        experiment_name (str) : name of experiment
        measurement_snapshot (dict[str,Any]) : snapshot of measurement parameters
        *m_params (m_param_dataset) : datasets of the measurement parameters
    '''
    SQL_mgr = SQL_dataset_creator()
    if SQL_mgr.conn is None:
        raise Exception('No database connection set up')

    ds = data_set_raw(exp_name=experiment_name)

    if qc.Station.default is not None:
        station_snapshot = qc.Station.default.snapshot()
        snapshot = {'station': station_snapshot}
    else:
        logger.warning('No station configured. No snapshot will be stored.')
        snapshot = {'station': None}

    # intialize the buffers for the measurement
    for m_param in m_params:
        m_param.init_data_dataclass()
        ds.measurement_parameters += [m_param]
        ds.measurement_parameters_raw += m_param.to_SQL_data_structure()

    total_size = 0
    for m_param_raw in ds.measurement_parameters_raw:
        if m_param_raw.size > DATA_POINTS_MAX:
            raise Exception(f'Measurement with shape {m_param_raw.shape} is too big for storage')
        total_size += m_param_raw.size
    if total_size > DATASET_SIZE_MAX:
        raise Exception(f'Dataset with {total_size} values is too big for storage')
    if total_size > DATASET_SIZE_WARNING:
        print(f'Dataset with {total_size} values is quite big for storage')

    snapshot['measurement'] = measurement_snapshot

    # encode and decode to convert all numpy arrays and complex numbers to jsonable lists and dictionaries
    snapshot_json = json.dumps(snapshot, cls=NumpyJSONEncoder)
    snapshot = json.loads(snapshot_json)

    ds.snapshot = snapshot

    SQL_mgr.register_measurement(ds)

    return data_set(ds)

if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage,set_up_remote_storage

    set_up_remote_storage('131.180.205.81', 5432, 'xld_measurement_pc', 'XLDspin001', 'spin_data', "6dot", "XLD", "6D3S - SQ20-20-5-18-4")

    ds= (load_by_id(23000))
    print(ds.snapshot['station']['instruments']['gates']['parameters'].keys())

    for key in ds.snapshot['station']['instruments']['gates']['parameters'].keys():
        print(key, ds.snapshot['station']['instruments']['gates']['parameters'][key]['value'])
    # print(ds.metadata)
    # print(ds.m1.z())
    # print(ds.m1.x())
    # print(ds.m1.y())