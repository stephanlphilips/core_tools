from multiprocessing import Process
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info


class sync_agent(SQL_database_init, Process):
	__instance = None

	def __new__(cls):
		if sync_agent.__instance is None:
			sync_agent.__instance = object.__new__(cls)
		return sync_agent.__instance

    def __init__(self, local_info, remote_info, sample_info):
    	super(Process, self).__init__()

        self.SQL_conn_local_info = local_info
        self.SQL_conn_remote_info = remote_info
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
    	# assign a copy of the info object (copy memory space of process A to process B)
    	SQL_conn_info_local = self.SQL_conn_local_info
    	SQL_conn_info_remote = self.SQL_conn_remote_info
    	sample_info = self.sample_info

    	# start up the connection
    	super(SQL_database_init, self).__init__()

    	# start up a timers for the db sync.
    	self.sync_measurenents_timer = Timer(5, self.sync_measurments)

    def sync_measurments(self):
    	# check for measurements that need sync

    	# check if table already present in the database

    	# check if measurment table is already present

    	# if empty --> make table

    	# fill the cursurs as where the cursors are on the host

    	# done.


if __name__ == '__main__':
	sync_agent()