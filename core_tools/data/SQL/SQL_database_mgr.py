from core_tools.data.SQL.connector import SQL_conn_info, sample_info
from core_tools.data.SQL.SQL_commands import query_generator

import psycopg2
import time
import json

class SQL_database_manager:
	conn = None
	last_commit = 0

	__instance = None

	def __new__(cls):
		if SQL_database_manager.__instance is None:
			SQL_database_manager.__instance = object.__new__(cls)
		return SQL_database_manager.__instance

	def __init__(self):
		if self.conn == None:
			self.conn = psycopg2.connect(dbname=SQL_conn_info.dbname, user=SQL_conn_info.user, 
				password=SQL_conn_info.passwd, host=SQL_conn_info.host, port=SQL_conn_info.port)
			self.last_commit = time.time()

	def __init_database(self):
		'''
		check if the database has been set up correctly. Will generate a new overview table
		for all the measurements in case it is empty
		'''
		cur = self.conn.cursor()
		cur.execute(query_generator.generate_overview_of_measurements_table())
		self.commit(True)
		cur.close()

	def register_measurement(self, ds):
		'''
		register a dataset in the database. Also sets up the buffers.
		'''
		cur = self.conn.cursor()
		
		#####################################################
		# add a new entry in the measurements overiew table #
		#####################################################
		cur.execute(query_generator.insert_new_measurement_in_overview_table())
		cur.execute(query_generator.get_last_meas_in_overview_table())
		measurement_id = cur.fetchone()[0]
		
		ds.run_id = measurement_id
		ds.running = True
		ds.table_name = str(measurement_id) + "_" + ds.exp_name[:20]

		cur.execute(query_generator.fill_meas_info_in_overview_table(
			measurement_id,ds.table_name,
			start_time=time.time(), metadata=ds.metadata, snapshot=ds.snapshot))

		#################################################
		# make table for storage of the getters/setters #
		#################################################
		cur.execute(query_generator.make_new_data_table(ds.table_name))




		# done!
		self.commit(True)
		cur.close()

	def fetch_dataset(run_id):
		pass


	def commit(self, force = False):
		'''
		commit non-timecritical updates to the database (e.g. updates of measurements) (update rate 200ms).

		Args:
			force (bool) : enforce the database to update anyway.
		'''
		current_time = time.time() 
		if current_time - self.last_commit > 0.2 or force==True:
			self.conn.commit()
			self.last_commit=current_time

if __name__ == '__main__':
	from core_tools.data.SQL.connector import set_up_data_storage

	set_up_data_storage('localhost', 5432, 'stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

	test = SQL_database_manager()
