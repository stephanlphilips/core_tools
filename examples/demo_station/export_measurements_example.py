# -*- coding: utf-8 -*-
"""
Created on Mon Sep 20 10:09:56 2021

@author: sdesnoo
"""
import core_tools as ct
from core_tools.data.ds.reader import load_by_uuid, set_data_location
from core_tools.data.ds.ds_hdf5 import save_hdf5_uuid
from core_tools.data.SQL.queries.dataset_gui_queries import query_for_measurement_results

ct.configure('./setup_config/ct_config_measurement.yaml')

path = 'c:/measurements/export/2021-09'

res = query_for_measurement_results.search_query(
        start_time='2021-09-08',
        end_time='2021-09-08 23:59',
        remote=True
        )

# export
for e in res:
    ds = load_by_uuid(e.uuid)
    save_hdf5_uuid(ds, path)

# Set data location for load_by_uuid.
# When path is set it will use the path and not the database
set_data_location(path)

# Check if all measurements can be imported again.
for e in res:
    d = load_by_uuid(e.uuid)

