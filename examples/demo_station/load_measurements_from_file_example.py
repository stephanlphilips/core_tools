from core_tools.data.ds.reader import load_by_uuid, set_data_location
from glob import glob
import os

path = 'c:/measurements/test_export'

# Set data location for load_by_uuid.
# When path is set it will use the path and not the database
set_data_location(path)

files = glob(path+'/ds_*.hdf5')
# Check if all measurements can be imported again.
for fname in files:
    name = os.path.basename(fname)
    uuid = int(name[3:-5])

    d = load_by_uuid(uuid)
    print(f'loaded {uuid}')
