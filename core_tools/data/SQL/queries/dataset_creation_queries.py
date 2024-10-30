import sqlite3
from core_tools.data.SQL.SQL_common_commands import execute_statement, execute_query
from core_tools.data.SQL.SQL_common_commands import insert_row_in_table, update_table

from core_tools.data.SQL.SQL_utility import generate_uuid
from core_tools.data.SQL.connect import SQL_conn_info_local, sample_info

import psycopg2, json


def is_valid_info(arg):
    if arg is None or arg.lower() in ['', 'any', '*']:
        return False
    return True


class sample_info_queries:
    '''
    small table that holds a overview of which samples have been measured on the current system.
    '''
    table_name = 'sample_info_overview'

    @staticmethod
    def generate_table(conn):
        statement = "CREATE TABLE if not EXISTS {} (".format(sample_info_queries.table_name)
        statement += "sample_info_hash text NOT NULL UNIQUE,"
        statement += "set_up text NOT NULL,"
        statement += "project text NOT NULL,"
        statement += "sample text NOT NULL );"

        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def add_sample(conn, project=None, set_up=None, sample=None):
        if project is None and set_up is None and sample is None:
            sample, set_up, project = sample_info.sample, sample_info.set_up, sample_info.project
        if is_valid_info(sample) and is_valid_info(set_up) and is_valid_info(project):
            var_names = ('sample_info_hash', 'sample', 'set_up', 'project')
            var_values = (set_up+project+sample, sample, set_up, project)
            insert_row_in_table(conn, sample_info_queries.table_name, var_names, var_values,
                custom_statement='ON CONFLICT DO NOTHING')
            conn.commit()

def _is_sqlite_conn(conn):
    return isinstance(conn, sqlite3.Connection)

class measurement_overview_queries:
    '''
    large-ish table that holds all the inforamtion of what measurements are done.

    The raw data is saved in table measurement_parameters (Old version: data_table_queries)
    '''
    table_name="global_measurement_overview"

    @staticmethod
    def generate_table(conn):
        statement = "CREATE TABLE if not EXISTS {} (".format(measurement_overview_queries.table_name)
        statement += "id SERIAL,"
        statement += "uuid BIGINT NOT NULL unique,"

        statement += "exp_name text NOT NULL,"
        statement += "set_up text NOT NULL,"
        statement += "project text NOT NULL,"
        statement += "sample text NOT NULL,"
        statement += "creasted_by text NOT NULL," # database account used when ds was created

        statement += "start_time TIMESTAMP, "
        statement += "stop_time TIMESTAMP, "

        statement += "exp_data_location text," # Database table name of parameter table. Older datasets. [SdS]
        statement += "snapshot BYTEA, "
        statement += "metadata BYTEA,"
        statement += "keywords JSONB, "
        statement += "starred BOOL DEFAULT False, "

        statement += "completed BOOL DEFAULT False, "
        statement += "data_size int," # Total size of data. Is written at finish.
        statement += "data_cleared BOOL DEFAULT False, "     # Note [SdS]: Column is not used
        statement += "data_update_count int DEFAULT 0, " # number of times the data has been updated on local client

        statement += "data_synchronized BOOL DEFAULT False,"  # data + param table sync'd
        statement += "table_synchronized BOOL DEFAULT False," # global_measurements_overview sync'd
        statement += "sync_location text); "                  # Note [SdS]: Column is abused for migration to new measurement_parameters table
        _USING_BTREE_ = " USING BTREE " if not _is_sqlite_conn(conn) else " "
        statement += ("CREATE INDEX IF NOT EXISTS id_indexed ON {} " + _USING_BTREE_ + "(id) ;").format(measurement_overview_queries.table_name)
        statement += ("CREATE INDEX IF NOT EXISTS uuid_indexed ON {} " + _USING_BTREE_ + "(uuid) ;").format(measurement_overview_queries.table_name)
        statement += ("CREATE INDEX IF NOT EXISTS starred_indexed ON {} " + _USING_BTREE_ + "(starred) ;").format(measurement_overview_queries.table_name)
        statement += ("CREATE INDEX IF NOT EXISTS date_day_index ON {} " + _USING_BTREE_ + "(project, set_up, sample) ;").format(measurement_overview_queries.table_name)

        statement += ("CREATE INDEX IF NOT EXISTS data_synced_index ON {} " + _USING_BTREE_ + "(data_synchronized);").format(measurement_overview_queries.table_name)
        statement += ("CREATE INDEX IF NOT EXISTS table_synced_index ON {} " + _USING_BTREE_ + "(table_synchronized);").format(measurement_overview_queries.table_name)

        execute_statement(conn, statement)
        conn.commit()


    @staticmethod
    def update_local_table(conn):
        if  _is_sqlite_conn(conn):
            return measurement_overview_queries._update_local_table_sqlite(conn)

        # Only do this on local database.
        # The update of the table on the remote database takes very long and afterwards other clients with old SW crash.
        statement = "ALTER TABLE global_measurement_overview ADD COLUMN IF NOT EXISTS data_update_count int DEFAULT 0;"
        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def _update_local_table_sqlite(conn):
        statement = "ALTER TABLE global_measurement_overview ADD COLUMN data_update_count int DEFAULT 0"
        try:
            execute_statement(conn, statement, close_on_error=False)
        except sqlite3.OperationalError as e:
            if "duplicate" not in str(e):
                raise e

    @staticmethod
    def new_measurement(conn, exp_name, start_time):
        '''
        insert new measurement in the measurement table

        Args:
            exp_name (str) : name of the experiment to be executed

        Returns:
            id, uuid, SQL_datatable : id and uuid of the new measurement and the tablename for raw data storage
        '''
        if (not is_valid_info(sample_info.project)
            or not is_valid_info(sample_info.set_up)
            or not is_valid_info(sample_info.sample)):
            raise Exception(f'Sample info not valid: {sample_info}')

        uuid = generate_uuid()
        # NOTE: column sync_location is abused for migration to new format
        var_names = (
                'uuid', 'set_up', 'project', 'sample',
                'creasted_by', 'exp_name', 'sync_location', 'exp_data_location',
                'start_time')
        var_values = (
                uuid, str(sample_info.set_up), str(sample_info.project), str(sample_info.sample),
                SQL_conn_info_local.user, exp_name, 'New measurement_parameters', '',
                psycopg2.sql.SQL("TO_TIMESTAMP({})").format(psycopg2.sql.Literal(start_time))
                )

        returning = ('id', 'uuid')
        query_outcome = insert_row_in_table(conn, measurement_overview_queries.table_name,
                                            var_names, var_values, returning)

        # NOTE: SQL_datatable name is not used anymore for new measurements

        return query_outcome[0][0], query_outcome[0][1]

    def update_measurement(conn, meas_uuid,
                           stop_time=None, metadata=None, snapshot=None,
                           keywords=None, data_size=None, data_synchronized=None,
                           completed=None, table_synchronized=None,
                           data_update_count=None,):
        '''
        fill in the addional data in a record of the measurements overview table.

        Args:
            meas_uuid (int) : record that needs to be updated
            stop_time (long) : time in unix seconds since the epoch
            metadata (dict) : json string to be saved in the database
            snapshot (dict) : snapshot of the exprimental set up
            keywords (list) : keywords describing the measurement
            completed (bool) : tell that the measurement is completed.
            data_update_count (int) : data update count
        '''
        var_pairs = []
        if stop_time is not None:
            var_pairs.append(('stop_time',
                              psycopg2.sql.SQL("TO_TIMESTAMP({})").format(psycopg2.sql.Literal(stop_time))
                              ))
        if metadata is not None:
            var_pairs.append(('metadata',
                              psycopg2.Binary(str(json.dumps(metadata)).encode('ascii'))
                              ))
        if snapshot is not None:
            var_pairs.append(('snapshot',
                              psycopg2.Binary(str(json.dumps(snapshot)).encode('ascii'))
                              ))
        if keywords is not None:
            var_pairs.append(('keywords', psycopg2.extras.Json(keywords)))
        if data_size is not None:
            var_pairs.append(('data_size', data_size))
        if data_synchronized is not None:
            var_pairs.append(('data_synchronized', str(data_synchronized)))
        if completed is not None:
            var_pairs.append(('completed', str(completed)))
        if table_synchronized is not None:
            var_pairs.append(('table_synchronized', str(table_synchronized)))
        if data_update_count is not None:
            var_pairs.append(('data_update_count', data_update_count))
        var_names = [name for name, value in var_pairs]
        var_values = [value for name, value in var_pairs]

        condition = ('uuid', meas_uuid)
        update_table(conn, measurement_overview_queries.table_name, var_names, var_values, condition)

    @staticmethod
    def is_completed(conn, uuid):
        completed =  execute_query(conn,
            "SELECT completed FROM {} where uuid = {};".format(measurement_overview_queries.table_name, uuid))
        return completed[0][0]

class data_table_queries:
    '''
    these tables contain the raw data of every measurement parameter.
    '''
    @staticmethod
    def generate_table(conn, table_name):
        statement = "CREATE TABLE if not EXISTS {} ( ".format(table_name )
        statement += "id SERIAL primary key, "
        statement += "param_id BIGINT, "
        statement += "nth_set INT, "
        statement += "nth_dim INT, "
        statement += "param_id_m_param BIGINT, "
        statement += "setpoint BOOL, "
        statement += "setpoint_local BOOL, "
        statement += "name_gobal text, "
        statement += "name text NOT NULL,"
        statement += "label text NOT NULL,"
        statement += "unit text NOT NULL,"
        statement += "depencies jsonb, "
        statement += "shape jsonb, "
        statement += "write_cursor INT, "
        statement += "total_size INT, "
        statement += "oid INT, "
        statement += "synchronized BOOL DEFAULT False," # Note [SdS]: Column is not used
        statement += "sync_location text);"             # Note [SdS]: Column is not used
        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def insert_measurement_spec_in_meas_table(conn, table_name, data_item):
        '''
        instert all the info of the set and get parameters in the measurement table.

        Args:
            measurement_table (str) : name of the measurement table
            data_item (m_param_raw) : raw format of the measurement parameter
        '''
        var_names = ("param_id", "nth_set", "nth_dim", "param_id_m_param",
            "setpoint", "setpoint_local", "name_gobal", "name",
            "label", "unit", "depencies", "shape",
            "write_cursor", "total_size", "oid")

        var_values = (data_item.param_id, data_item.nth_set, data_item.nth_dim,
            data_item.param_id_m_param, data_item.setpoint, data_item.setpoint_local,
            data_item.name_gobal, data_item.name, data_item.label,
            data_item.unit, psycopg2.extras.Json(data_item.dependency), psycopg2.extras.Json(data_item.shape),
            0, data_item.size, data_item.oid)

        insert_row_in_table(conn, table_name, var_names, var_values)

    @staticmethod
    def update_cursors_in_meas_tab(conn, table_name, data_items):
        statement = ""
        for i in range(len(data_items)):
            statement += "UPDATE {} SET write_cursor = {} WHERE id = {}; ".format(table_name, data_items[i].data_buffer.cursor, i+1)

        execute_statement(conn, statement)


class measurement_parameters_queries:
    '''
    table containing the raw data of every measurement parameter.
    This is the new version that replaces class data_table_queries
    '''
    @staticmethod
    def generate_table(conn):

        statement = "CREATE TABLE if not EXISTS measurement_parameters ( "
        statement += "id SERIAL primary key, "
        statement += "exp_uuid BIGINT NOT NULL,"
        statement += "param_index INT NOT NULL,"
        statement += "param_id BIGINT, "
        statement += "nth_set INT, "
        statement += "nth_dim INT, "
        statement += "param_id_m_param BIGINT, "
        statement += "setpoint BOOL, "
        statement += "setpoint_local BOOL, "
        statement += "name_gobal text, "
        statement += "name text NOT NULL,"
        statement += "label text NOT NULL,"
        statement += "unit text NOT NULL,"
        statement += "depencies jsonb, "
        statement += "shape jsonb, "
        statement += "write_cursor INT, "
        statement += "total_size INT, "
        statement += "oid INT); "
        _USING_BTREE_ = " USING BTREE " if not _is_sqlite_conn(conn) else " "
        statement += "CREATE INDEX IF NOT EXISTS exp_uuid_index ON measurement_parameters " + _USING_BTREE_ + " (exp_uuid) ;"
        statement += "CREATE INDEX IF NOT EXISTS oid_index ON measurement_parameters " + _USING_BTREE_ + " (oid) ;"
        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def insert_measurement_params(conn, exp_uuid, data_items):
        '''
        instert all the info of the set and get parameters in the measurement table.

        Args:
            exp_uuid (int) : unique id of dataset
            data_items (list[m_param_raw]) : raw format of the measurement parameter
        '''
        var_names = (
            "exp_uuid","param_index",
            "param_id", "nth_set", "nth_dim", "param_id_m_param",
            "setpoint", "setpoint_local", "name_gobal", "name",
            "label", "unit", "depencies", "shape",
            "write_cursor", "total_size", "oid")

        for index, item in enumerate(data_items):
            var_values = (
                exp_uuid, index,
                item.param_id, item.nth_set, item.nth_dim,
                item.param_id_m_param, item.setpoint, item.setpoint_local,
                item.name_gobal, item.name, item.label,
                item.unit, psycopg2.extras.Json(item.dependency), psycopg2.extras.Json(item.shape),
                0, item.size, item.oid)

            insert_row_in_table(conn, 'measurement_parameters', var_names, var_values)

    @staticmethod
    def update_cursors_in_meas_tab(conn, exp_uuid, data_items):
        statement = ""
        for index, item in enumerate(data_items):
            statement += (
                    "UPDATE measurement_parameters "
                    f"SET write_cursor = {item.data_buffer.cursor} "
                    f"WHERE exp_uuid = {exp_uuid} AND param_index = {index}; ")

        execute_statement(conn, statement)
