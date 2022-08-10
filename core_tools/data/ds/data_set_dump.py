from core_tools.data.SQL.queries.dataset_loading_queries import load_ds_queries
from core_tools.data.SQL.SQL_common_commands import execute_query, select_elements_in_table
from core_tools.data.ds.data_set_raw import data_set_raw, m_param_raw
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager
from core_tools.data.ds.data_set_core import  data_set
from core_tools.data.SQL.SQL_dataset_creator import SQL_dataset_creator

from core_tools.data.SQL.buffer_writer import buffer_reader, buffer_reference
import h5py, json, pickle, os
import numpy as np

'''
not the most clean/efficient, but it works ...
'''

def dump_data_to_HDF5(exp_uuid, file_location):
    try:
        os.mkdir(file_location)
    except:
        pass

    f = h5py.File(f"{file_location}/{exp_uuid}.hdf5", "w")

    # TODO use fetch_raw_dataset_by_UUID instead of this copy/pasted code below.
    if load_ds_queries.check_uuid(SQL_database_manager().conn_local, exp_uuid):
        conn = SQL_database_manager().conn_local
    elif load_ds_queries.check_uuid(SQL_database_manager().conn_remote, exp_uuid):
        conn = SQL_database_manager().conn_remote
        sync = sync2local
    else:
        raise ValueError("the uuid {}, does not exist in the local/remote database.".format(exp_uuid))

    data = select_elements_in_table(conn, load_ds_queries.table_name, var_names=('*',),
        where = ("uuid", exp_uuid))[0]

    if data['stop_time'] is None:
        data['stop_time'] = data['start_time']

    if data['snapshot'] is not None:
        data['snapshot'] = json.loads(data['snapshot'].tobytes())

    if data['metadata'] is not None:
        data['metadata'] = json.loads(data['metadata'].tobytes())

    ds = data_set_raw(exp_id=data['id'], exp_uuid=data['uuid'], exp_name=data['exp_name'],
        set_up = data['set_up'], project = data['project'], sample = data['sample'],
        UNIX_start_time=data['start_time'].timestamp(), UNIX_stop_time=data['stop_time'].timestamp(),
        SQL_datatable=data['exp_data_location'],snapshot=data['snapshot'], metadata=data['metadata'],
        keywords=data['keywords'], completed=data['completed'],)

    var_names =    ("param_id", "nth_set", "nth_dim", "param_id_m_param",
                    "setpoint", "setpoint_local", "name_gobal", "name", "label",
                    "unit", "depencies", "shape", "total_size", "oid")

    return_data = select_elements_in_table(conn, ds.SQL_datatable, var_names, dict_cursor=False)

    data_raw = []
    for row in return_data:
        raw_data_row = m_param_raw(*row)
        raw_data_row.data_buffer = raw_data_row.oid # buffer_reader(conn, raw_data_row.oid, raw_data_row.shape)
        data = buffer_reader(conn, raw_data_row.oid, raw_data_row.shape)
        f.create_dataset(f"{raw_data_row.oid}", data.buffer.shape)
        f[f"{raw_data_row.oid}"][:] = data.buffer
        data_raw.append(raw_data_row)

    # TODO replace pickle by decent storage. Pickle loads fails whenever one of the stored classes changes.
    pickle.dump([ds,data_raw], open( f"{file_location}/{exp_uuid}.p",  "wb" ))

    SQL_mgr = SQL_dataset_creator()
    return data_set(SQL_mgr.fetch_raw_dataset_by_UUID(exp_uuid))

def load_data_from_HDF5(exp_uuid, file_location):
    f = h5py.File(f"{file_location}/{exp_uuid}.hdf5", "r")
    # TODO replace pickle by decent storage. Pickle loads fails whenever one of the stored classes changes.
    ds, data_raw = pickle.load(open( f"{file_location}/{exp_uuid}.p", 'rb'))

    for raw_data_row in data_raw:
        raw_data_row.data_buffer = buffer_reference(np.reshape(
                                np.asarray(f[str(raw_data_row.data_buffer)]), raw_data_row.shape))
    ds.measurement_parameters_raw = data_raw

    return data_set(ds)
