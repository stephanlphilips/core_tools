from multiprocessing import Process
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info
from core_tools.data.SQL.SQL_database_mgr import SQL_database_init
from core_tools.data.SQL.SQL_commands import write_query_generator

class sync_agent(SQL_database_init):
    __instance = None

    def __new__(cls):
        if sync_agent.__instance is None:
            sync_agent.__instance = object.__new__(cls)
        return sync_agent.__instance

    def __init__(self):
        # super(Process, self).__init__()

        self.SQL_conn_local_info = SQL_conn_info_local
        self.SQL_conn_remote_info = SQL_conn_info_remote
        self.sample_info = sample_info

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

    def run(self):
        SQL_database_init.__init__(self)
        self.__init_database()

        # start up a timers for the db sync.
        # self.sync_measurenents_timer = Timer(5, self.sync_measurments)

    def sync_measurments(self):
        # check for measurements that need sync

        # check if table already present in the database

        # check if measurment table is already present

        # if empty --> make table

        # fill the cursurs as where the cursors are on the host

        # done.
        pass

if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
        'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')

    s = sync_agent()
    s.run()