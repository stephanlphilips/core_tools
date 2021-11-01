import json
import time
import logging

from core_tools.data.SQL.SQL_common_commands import execute_query, select_elements_in_table
from core_tools.data.ds.data_set_raw import data_set_raw, m_param_raw

from core_tools.data.SQL.buffer_writer import buffer_reader

class load_ds_queries:
    table_name = "global_measurement_overview"

    @staticmethod
    def check_uuid(conn, exp_uuid):
        statement = "SELECT uuid FROM {} WHERE uuid = {};".format(load_ds_queries.table_name, exp_uuid);
        return load_ds_queries.__check_exist(conn, statement)

    @staticmethod
    def check_id(conn, exp_id):
        statement = "SELECT id FROM {} WHERE id = {};".format(load_ds_queries.table_name, exp_id);
        return load_ds_queries.__check_exist(conn, statement)

    @staticmethod
    def check_table_name(conn, meas_table_name):
        statement = "SELECT to_regclass('{}');".format(meas_table_name);
        return load_ds_queries.__check_exist(conn, statement)

    @staticmethod
    def id_to_uuid(conn, exp_id):
        statement = "SELECT id, uuid FROM {} WHERE id = {};".format(load_ds_queries.table_name, exp_id);
        return_data = execute_query(conn, statement)

        if len(return_data) != 0 and len(return_data[0]) == 2:
            return return_data[0][1]
        else:
            raise ValueError('uuid for exp_id {} does not exist.'.format(exp_id))

    @staticmethod
    def is_running(conn, exp_uuid):
        return_data = select_elements_in_table(conn, load_ds_queries.table_name, var_names=('completed', ),
            where = ("uuid", exp_uuid))

        return return_data[0][0]

    @staticmethod
    def get_dataset_raw(conn, exp_uuid):
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

        ds.measurement_parameters_raw = load_ds_queries.__get_dataset_raw_dataclasses(conn, ds.SQL_datatable)
        return ds

    @staticmethod
    def __get_dataset_raw_dataclasses(conn, table_name):
        var_names =    ("param_id", "nth_set", "nth_dim", "param_id_m_param",
                    "setpoint", "setpoint_local", "name_gobal", "name", "label",
                    "unit", "depencies", "shape", "total_size", "oid")

        return_data = select_elements_in_table(conn, table_name, var_names, dict_cursor=False)

        data_raw = []
        for row in return_data:
            raw_data_row = m_param_raw(*row)
            raw_data_row.data_buffer = buffer_reader(conn, raw_data_row.oid, raw_data_row.shape)
            data_raw.append(raw_data_row)

        return data_raw

    @staticmethod
    def __check_exist(conn, statement):
        return_data = execute_query(conn, statement)

        if len(return_data) == 0 or return_data[0][0] is None:
            return False
        return True