
from .ds_hdf5 import load_hdf5_uuid
from .data_set import load_by_uuid as db_load_by_uuid

data_location = None

def set_data_location(location):
    global data_location
    data_location = location

def load_by_uuid(uuid):
    if data_location is None:
        return db_load_by_uuid(uuid)
    else:
        return load_hdf5_uuid(uuid, data_location)
