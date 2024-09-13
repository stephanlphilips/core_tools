import os
from core_tools.data.ds.ds_hdf5 import save_hdf5_uuid, load_hdf5_uuid

from core_tools.data.sqdl import (
    init_sqdl, load_by_uuid, load_uuids_parallel, sqdl_query,
    download_hdf5, download_hdf5_parallel
    )

path = 'c:/measurements/export/2023-04'

init_sqdl("LV-2x2ML")

#%%
print("query")
# query
res = sqdl_query(
        start_time='2024-05-01',
        end_time='2024-05-10',
        starred=True,
        name_contains="Calibration"
        )
print(len(res))
#%%
# load
load_parallel = False
if load_parallel:
    # Faster parallel loading:
    datasets = load_uuids_parallel([e.uuid for e in res])
else:
    datasets = [
        load_by_uuid(e.uuid)
        for e in res
        ]


# export
for i, ds in enumerate(datasets):
    print(i, ds.exp_uuid)
    try:
        save_hdf5_uuid(ds, path)
        # check properly written..

    except Exception as ex:
        print(ex)


# Check if all measurements can be imported again.
for e in res:
    ds = load_hdf5_uuid(e.uuid, path)

#%%
print("downloading")
os.makedirs('c:/measurements/export/2024-09', exist_ok=True)
for e in res:
    print(e.uuid)
    download_hdf5(e.uuid, 'c:/measurements/export/2024-09')
# print("downloading parallel")
# for e in res:
#     download_hdf5_parallel([e.uuid for e in res], 'c:/measurements/export/2024-09')
print("reading")
# Check if all measurements can be imported again.
for e in res:
    print(e.uuid)
    ds = load_hdf5_uuid(e.uuid, path)
print("done")
