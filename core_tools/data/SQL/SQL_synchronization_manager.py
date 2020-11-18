from multiprocessing import Process
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info
from core_tools.data.SQL.SQL_database_mgr import SQL_database_init
from core_tools.data.SQL.SQL_commands import write_query_generator
from core_tools.data.SQL.sync_mgr_queries import sync_mgr_query

import time

class sync_agent(SQL_database_init):
    __instance = None

    def __new__(cls):
        if sync_agent.__instance is None:
            sync_agent.__instance = object.__new__(cls)
        return sync_agent.__instance

    def __init__(self):
        # super(Process, self).__init__()
        self.SQL_conn_info_local = SQL_conn_info_local
        self.SQL_conn_info_remote = SQL_conn_info_remote
        self.sample_info = sample_info
        self.run()
    def __init_database(self):
        '''
        check if the database has been set up correctly. Will generate a new overview table
        for all the measurements in case it is empty
        '''
        cur = self.conn_remote.cursor()
        cur.execute(write_query_generator.generate_data_overview_tables())
        cur.execute(write_query_generator.generate_measurement_table())
        self.conn_remote.commit()
        cur.close()

    def reconnect(self):
        print("No connection ...")

    def run(self):
        SQL_database_init.__init__(self)
        
        self.__init_database()
        self.do_sync = True
        print('Synchronisation manager started. Synced items will appear as you go.')
        while self.do_sync == True:
            m = sync_mgr_query.check_meas_4_upload(self)

            # TODO -- move this check to dataset creastion..
            sync_mgr_query.mark_incomplete_completed(self, m)

            for m_id in m:
                table = sync_mgr_query.cpy_meas_info_to_remote_meas_table(self, m_id)
                sync_mgr_query.generate_meaurement_data_table(self, table)
                sync_mgr_query.fill_and_sync_measurement_table(self, table)
                sync_mgr_query.check_if_sync_done(self, m_id, table)
            # except:
            #     self.reconnect()
            time.sleep(2)

if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
        'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')

    s = sync_agent()
    s.run()