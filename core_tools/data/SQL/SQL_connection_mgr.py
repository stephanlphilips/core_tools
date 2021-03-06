from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote, sample_info
from core_tools.data.SQL.queries.dataset_creation_queries import sample_info_queries, measurement_overview_queries
import psycopg2
import time

class SQL_database_init:
    conn_local = None
    conn_remote = None
    last_commit = 0

    def _connect(self):
        self.SQL_conn_info_local = SQL_conn_info_local
        self.SQL_conn_info_remote = SQL_conn_info_remote
        self.sample_info = sample_info

        if self.conn_local is None:     
            self.conn_local = psycopg2.connect(dbname=SQL_conn_info_local.dbname, user=SQL_conn_info_local.user, 
                password=SQL_conn_info_local.passwd, host=SQL_conn_info_local.host, port=SQL_conn_info_local.port)
        if self.conn_remote is None:
            self.conn_remote = psycopg2.connect(dbname=SQL_conn_info_remote.dbname, user=SQL_conn_info_remote.user, 
                password=SQL_conn_info_remote.passwd, host=SQL_conn_info_remote.host, port=SQL_conn_info_remote.port)

        self.last_commit = time.time()

    @property
    def local_conn_active(self):
        if self.SQL_conn_info_local.host == 'localhost':
            return True
        return False

    @property
    def remote_conn_active(self):
        if self.SQL_conn_info_remote.host != 'localhost':
            return True
        return False
       

class SQL_database_manager(SQL_database_init):
    __instance = None

    def __new__(cls):
        if SQL_database_manager.__instance is None:
            SQL_database_manager.__instance = object.__new__(cls)
            SQL_database_init._connect(SQL_database_manager.__instance)
            
            sample_info_queries.generate_table(SQL_database_manager.__instance.conn_local)
            sample_info_queries.add_sample(SQL_database_manager.__instance.conn_local)
            
            measurement_overview_queries.generate_table(SQL_database_manager.__instance.conn_local)

        return SQL_database_manager.__instance


class SQL_sync_manager(SQL_database_init):
    __instance = None

    def __new__(cls):
        if SQL_sync_manager.__instance is None:
            SQL_sync_manager.__instance = object.__new__(cls)
            SQL_database_init._connect(SQL_sync_manager.__instance)
            
            if SQL_sync_manager.__instance.remote_conn_active != True or SQL_sync_manager.__instance.remote_conn_active != True:
                raise ValueError('In order to start the sync manager, a local and remote connection need to be provided.')

            sample_info_queries.generate_table(SQL_sync_manager.__instance.conn_local)
            measurement_overview_queries.generate_table(SQL_sync_manager.__instance.conn_local)

            sample_info_queries.generate_table(SQL_sync_manager.__instance.conn_remote)
            measurement_overview_queries.generate_table(SQL_sync_manager.__instance.conn_remote)

        return SQL_sync_manager.__instance


if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project', 'test_set_up', 'test_sample')
    # set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
    #     'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')
    s = SQL_database_manager()
    print(s)

    s2 = SQL_database_manager()

    print(s2)