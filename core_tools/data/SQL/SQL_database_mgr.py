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
		self.conn.commit()
		cur.close()

	def register_measurement(self, ds):
		'''
		register a dataset in the database. Also sets up the buffers.

		Args:
			ds (data_set_raw) : raw dataset
		'''
		cur = self.conn.cursor()
		
		#####################################################
		# add a new entry in the measurements overiew table #
		#####################################################
		cur.execute(query_generator.insert_new_measurement_in_overview_table(ds.exp_name))
		cur.execute(query_generator.get_last_meas_id_in_overview_table())
		measurement_id = cur.fetchone()[0]
		
		ds.run_id = measurement_id
		ds.running = True
		ds.SQL_datatable = "_" + sample_info.set_up + "_" +sample_info.project + "_" +sample_info.sample +"_" + str(measurement_id)

		cur.execute(query_generator.fill_meas_info_in_overview_table(
			measurement_id,ds.SQL_datatable,
			start_time=time.time(), metadata=ds.metadata, snapshot=ds.snapshot))

		#################################################
		# make table for storage of the getters/setters #
		#################################################
		cur.execute(query_generator.make_new_data_table(ds.SQL_datatable))

		for m_param in ds.measurement_parameters_raw:
			cur.execute(query_generator.insert_measurement_spec_in_meas_table(ds.SQL_datatable, m_param))

		self.conn.commit()
		cur.close()

	def update_write_cursors(self, ds):
		'''
		update the write_cursors to the current position and commit the cached (measured) data.

		Args:
			ds (dataset_raw)
		'''
		self.conn.commit()

		cur = self.conn.cursor()
		cur.execute(query_generator.update_cursors_in_meas_tab(ds.SQL_datatable, ds.measurement_parameters_raw))
		self.conn.commit()

	def finish_measurement(self, ds):
		'''
		
		register the mesaurement as finished in the database.

		Args:
			ds (dataset_raw)
		'''
		cur = self.conn.cursor()
		cur.execute(query_generator.update_cursors_in_meas_tab(ds.SQL_datatable, ds.measurement_parameters_raw))
		cur.execute(query_generator.fill_meas_info_in_overview_table(
			ds.run_id,ds.SQL_datatable,
			stop_time=time.time(), completed=True))
		self.conn.commit()
		cur.close()

		# close the connection with the buffer to the database
		for data_item in ds.measurement_parameters_raw:
			data_item.data_buffer.close()

	def fetch_dataset_by_Id(run_id):
		pass


	def fetch_dataset_by_TrueId(run_id):
		pass
		

if __name__ == '__main__':
	from core_tools.data.SQL.connector import set_up_data_storage

	set_up_data_storage('localhost', 5432, 'stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

	test = SQL_database_manager()
