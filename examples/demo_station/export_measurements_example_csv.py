# -*- coding: utf-8 -*-
"""
Created on Mon Sep 20 10:09:56 2021

@author: sdesnoo
"""
import core_tools as ct
from core_tools.data.ds.reader import load_by_uuid
from core_tools.data.SQL.queries.dataset_gui_queries import query_for_measurement_results

from core_tools.data.ds.export_csv import save_csv

ct.configure('./setup_config/ct_config_laptop.yaml')

path = 'c:/measurements/export/DQPT'

res = query_for_measurement_results.search_query(
        start_time='2023-01-01',
        end_time='2023-01-03 23:59',
        name='DQPT',
        remote=True
        )

# export
for e in res:
    ds = load_by_uuid(e.uuid)
    # vars=-1 -> save only last variable of dataset
    save_csv(ds, path, vars=-1, metadata=True)
    # save named variable and specify filename
    save_csv(ds, path, name=f'read12_{ds.exp_uuid}.txt', vars=['read12_0p'], metadata=True)


