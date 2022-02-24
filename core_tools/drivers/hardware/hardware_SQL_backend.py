from core_tools.data.SQL.SQL_common_commands import execute_statement, execute_query
from core_tools.data.SQL.SQL_common_commands import select_elements_in_table, insert_row_in_table, update_table
from core_tools.data.SQL.connect import sample_info

import psycopg2, json
import numpy as np

class virtual_gate_queries:
    @staticmethod
    def generate_table(conn):
        statement = "CREATE TABLE if not EXISTS {} (".format(virtual_gate_queries.table_name())
        statement += "name text NOT NULL UNIQUE,"
        statement += "real_gates bytea ,"
        statement += "virtual_gates bytea ,"
        statement += "vg_matrix bytea );"

        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def get_virtual_gate_matrix(conn, name):
        res = select_elements_in_table(conn, virtual_gate_queries.table_name(),  ('real_gates', 'virtual_gates', 'vg_matrix'), where=('name', name))

        if len(res) == 0: #if empty
            return list(), list(), np.asarray([[],])

        return json.loads(res[0]['real_gates'].tobytes()), json.loads(res[0]['virtual_gates'].tobytes()), np.asarray(json.loads(res[0]['vg_matrix'].tobytes()))

    @staticmethod
    def set_virtual_gate_matrix(conn, name, real_gates, virtual_gates, vg_matrix):

        var_names = ('name', 'real_gates', 'virtual_gates', 'vg_matrix')

        var_values = (name, psycopg2.Binary('{}'.format(json.dumps(real_gates)).encode('ascii')),
                            psycopg2.Binary(json.dumps(virtual_gates).encode('ascii')),
                            psycopg2.Binary(json.dumps(vg_matrix.tolist()).encode('ascii')))

        if not virtual_gate_queries.check_var_in_table_exist(conn, name):
            insert_row_in_table(conn, virtual_gate_queries.table_name(), ('name',), (name,))
        update_table(conn, virtual_gate_queries.table_name(), var_names, var_values, condition=('name', name))

        conn.commit()

    @staticmethod
    def check_var_in_table_exist(conn, name):
        return_data = select_elements_in_table(conn, virtual_gate_queries.table_name(), ('name', ), where=('name', name), dict_cursor=False)

        if len(return_data) == 0 or return_data[0][0] is None:
            return False
        return True

    @staticmethod
    def check_table_exist(conn):
        return_data = execute_query(conn, "SELECT to_regclass('{}');".format(virtual_gate_queries.table_name()))

        if len(return_data) == 0 or return_data[0][0] is None:
            return False
        return True

    @staticmethod
    def table_name():
        sample, set_up, project = sample_info.sample, sample_info.set_up, sample_info.project
        return (set_up+project+sample+'_virtual_gates').replace(" ", "_").replace('-', '_')


class AWG_2_dac_ratio_queries:
    @staticmethod
    def generate_table(conn):
        statement = "CREATE TABLE if not EXISTS {} (".format(AWG_2_dac_ratio_queries.table_name())
        statement += "name text NOT NULL UNIQUE,"
        statement += "real_gates bytea ,"
        statement += "ratios bytea );"

        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def get_AWG_2_dac_ratios(conn, name):
        res = select_elements_in_table(conn, AWG_2_dac_ratio_queries.table_name(), ('real_gates', 'ratios'), where=('name', name))

        gate_ratio_pairs = dict()

        if len(res) != 0:
            gates, ratios = json.loads(res[0]['real_gates'].tobytes()), json.loads(res[0]['ratios'].tobytes())
            for i in range(len(gates)):
                gate_ratio_pairs[gates[i]] = ratios[i]

        return gate_ratio_pairs

    @staticmethod
    def set_AWG_2_dac_ratios(conn, name, gate_ratio_pairs):
        gates =  list(gate_ratio_pairs.keys())
        ratios = list(gate_ratio_pairs.values())

        var_names = ('name', 'real_gates', 'ratios')
        var_values = (name, psycopg2.Binary(json.dumps(gates).encode('ascii')),
                            psycopg2.Binary(json.dumps(list(ratios)).encode('ascii')))

        if not AWG_2_dac_ratio_queries.check_exist(conn, name):
            insert_row_in_table(conn, AWG_2_dac_ratio_queries.table_name(), ('name',), (name, ))
        update_table(conn, AWG_2_dac_ratio_queries.table_name(), var_names, var_values, condition= ('name', name))

        conn.commit()

    @staticmethod
    def check_exist(conn, name):
        return_data = execute_query(conn, "SELECT name FROM {} WHERE name = '{}';".format(AWG_2_dac_ratio_queries.table_name(), name))

        if len(return_data) == 0 or return_data[0][0] is None:
            return False
        return True

    @staticmethod
    def table_name():
        sample, set_up, project = sample_info.sample, sample_info.set_up, sample_info.project
        return (set_up+project+sample+'_AWG_to_DAC_ratios').replace(" ", "_").replace('-', '_')


class RF_readout_settings_queries:
    @staticmethod
    def generate_table(conn):
        statement = "CREATE TABLE if not EXISTS {} (".format(RF_readout_settings_queries.table_name())
        statement += "name text NOT NULL UNIQUE,"
        statement += "freq double precision,"
        statement += "power double precision,"
        statement += "freq_step double precision);"

        execute_statement(conn, statement)
        conn.commit()

    @staticmethod
    def get_RF_readout_settings(conn, name):
        statement = "SELECT freq, power, freq_step FROM {} WHERE name = {};".format(RF_readout_settings_queries.table_name(), text(name))
        res = execute_query(conn, statement)

        return res[0][0], res[0][1], res[0][2]

    @staticmethod
    def set_RF_readout_settings(conn, name, freq, power, freq_step):
        var_names = ('name', 'freq', 'power', 'freq_step')
        var_values = (text(name), freq, power, freq_step)

        if not RF_readout_settings_queries.check_exist(conn, name):
            execute_statement(conn, "INSERT INTO {} (name ) VALUES ({} ) ".format(RF_readout_settings_queries.table_name(), text(name)))
        update_table(conn, RF_readout_settings_queries.table_name(), var_names, var_values, condition="name = '{}'".format(name))

        conn.commit()

    @staticmethod
    def check_exist(conn, name):
        return_data = execute_query(conn, "SELECT name FROM {} WHERE name = '{}';".format(RF_readout_settings_queries.table_name(), name))

        if len(return_data) == 0 or return_data[0][0] is None:
            return False
        return True

    @staticmethod
    def table_name():
        sample, set_up, project = sample_info.sample, sample_info.set_up, sample_info.project
        return (set_up+project+sample+'_RF_readout_settings').replace(" ", "_").replace('-', '_')



if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager
    import numpy as np
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')
    # set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
    #     'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')
    s = SQL_database_manager()
    conn = s.conn_local
    # virtual_gate_queries.generate_table(conn)

    # r_gates = ['P1', 'P2', 'P3']
    # v_gates = ['vP1', 'vP2', 'vP3']
    # matrix = np.eye(3)

    # a,b,c = virtual_gate_queries.get_virtual_gate_matrix(conn, 'test2')
    # print(a, b, c)
    # print(c.shape)

    AWG_2_dac_ratio_queries.generate_table(conn)

    gates_value_pair = {'P1':0.21, 'P2':0.21, 'P3':0.21}
    AWG_2_dac_ratio_queries.set_AWG_2_dac_ratios(conn, 'config2', gates_value_pair)
    ratios = AWG_2_dac_ratio_queries.get_AWG_2_dac_ratios(conn, 'config2')
    print(ratios)


    # RF_readout_settings_queries.generate_table(conn)
    # RF_readout_settings_queries.set_RF_readout_settings(conn, 'src_1', 1e6, -5, 1e3)
    # a,b,c=  RF_readout_settings_queries.get_RF_readout_settings(conn, 'src_1')
    # print(a,b,c)