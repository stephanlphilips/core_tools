from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info
from core_tools.data.SQL.SQL_commands import write_query_generator, data_fetch_queries

import psycopg2
import time
import json

class SQL_database_init:
	conn_local = None
	last_commit = 0

	__instance = None

	def __new__(cls):
		if SQL_database_manager.__instance is None:
			SQL_database_manager.__instance = object.__new__(cls)
		return SQL_database_manager.__instance

	def __init__(self):
		if self.conn_local is None:		
			self.conn_local = psycopg2.connect(dbname=SQL_conn_info_local.dbname, user=SQL_conn_info_local.user, 
				password=SQL_conn_info_local.passwd, host=SQL_conn_info_local.host, port=SQL_conn_info_local.port)
			self.conn_remote = psycopg2.connect(dbname=SQL_conn_info_remote.dbname, user=SQL_conn_info_remote.user, 
				password=SQL_conn_info_remote.passwd, host=SQL_conn_info_remote.host, port=SQL_conn_info_remote.port)

			self.__init_database()
			self.last_commit = time.time()

	def __init_database(self):
		'''
		check if the database has been set up correctly. Will generate a new overview table
		for all the measurements in case it is empty
		'''
		cur = self.conn_local.cursor()
		cur.execute(write_query_generator.generate_data_overview_tables())
		cur.execute(write_query_generator.generate_measurement_table())
		self.conn_local.commit()
		cur.close()

class SQL_database_manager(SQL_database_init):
	def register_measurement(self, ds):
		'''
		register a dataset in the database. Also sets up the buffers.

		Args:
			ds (data_set_raw) : raw dataset
		'''
		cur = self.conn_local.cursor()
		
		#####################################################
		# add a new entry in the measurements overiew table #
		#####################################################
		cur.execute(write_query_generator.write_data_overview_tables(sample_info.set_up, sample_info.project, sample_info.sample))
		cur.execute(write_query_generator.insert_new_measurement_in_measurement_table(ds.exp_name, SQL_conn_info_local.user))

		cur.execute(write_query_generator.get_last_meas_id_in_measurement_table())
		exp_id, exp_uuid = cur.fetchone()
		
		ds.exp_id = exp_id
		ds.exp_uuid = exp_uuid
		ds.running = True
		ds.SQL_datatable = "_" + sample_info.set_up + "_" +sample_info.project + "_" +sample_info.sample +"_" + str(exp_uuid)
		ds.SQL_datatable = ds.SQL_datatable.replace(" ", "_").replace('-', '_')
		# todo -- add tags to the measurements

		cur.execute(write_query_generator.fill_meas_info_in_measurement_table(
			ds.exp_uuid,ds.SQL_datatable,
			start_time=time.time(), metadata=ds.metadata, snapshot=ds.snapshot))

		#################################################
		# make table for storage of the getters/setters #
		#################################################
		cur.execute(write_query_generator.make_new_data_table(ds.SQL_datatable))

		for m_param in ds.measurement_parameters_raw:
			cur.execute(write_query_generator.insert_measurement_spec_in_meas_table(ds.SQL_datatable, m_param))

		self.conn_local.commit()
		cur.close()

	def update_write_cursors(self, ds):
		'''
		update the write_cursors to the current position and commit the cached (measured) data.

		Args:
			ds (dataset_raw)
		'''
		self.conn_local.commit()

		cur = self.conn_local.cursor()
		cur.execute(write_query_generator.update_cursors_in_meas_tab(ds.SQL_datatable, ds.measurement_parameters_raw))
		self.conn_local.commit()

	def is_completed(self, exp_uuid):
		'''
		checks if the current measurement is still running

		Args:
			exp_uuid (int) : uuid of the experiment to check
		'''
		cur = self.conn_local.cursor()
		cur.execute(write_query_generator.check_completed_measurement_table(exp_uuid))
		completed = cur.fetchone()[0]
		cur.close()
		
		return completed

	def finish_measurement(self, ds):
		'''
		
		register the mesaurement as finished in the database.

		Args:
			ds (dataset_raw)
		'''
		cur = self.conn_local.cursor()
		cur.execute(write_query_generator.update_cursors_in_meas_tab(ds.SQL_datatable, ds.measurement_parameters_raw))
		cur.execute(write_query_generator.fill_meas_info_in_measurement_table(
			ds.exp_uuid,ds.SQL_datatable,
			stop_time=time.time(), completed=True))

		cur.execute(write_query_generator.fill_technical_infomation_in_measurement_table(ds.exp_uuid,data_size=ds.size(), data_cleared=False, synchronized=False))
		self.conn_local.commit()
		cur.close()

		# close the connection with the buffer to the database
		for data_item in ds.measurement_parameters_raw:
			data_item.data_buffer.close()

	def fetch_raw_dataset_by_Id(self, exp_id):
		'''
		assuming here used want to get a local id

		Args:
			exp_id (int) : id of the measurment you want to get
		'''
		cur = self.conn_local.cursor()

		if data_fetch_queries.check_if_exp_id_exists(cur, exp_id) == False:
			raise ValueError("the id {}, does not exist in the database {} on {}.".format(exp_id, SQL_conn_info_local.dbname, SQL_conn_info_local.user))
		uuid = data_fetch_queries.convert_id_to_uuid(cur, exp_id)
		
		return self.fetch_raw_dataset_by_UUID(uuid)

	def fetch_raw_dataset_by_UUID(self, exp_uuid):
		'''
		Try to find a measurement with the corresponding uuid

		Args:
			exp_uuid (int) : uuid of the measurment you want to get
		'''
		conn = None

		if data_fetch_queries.check_if_exp_uuid_exists(self.conn_local.cursor(), exp_uuid) == True:
			conn = self.conn_local
		elif data_fetch_queries.check_if_exp_uuid_exists(self.conn_remote.cursor(), exp_uuid):
			conn = self.conn_remote
		else:
			raise ValueError("the uuid {}, does not exist in the local/remote database.".format(exp_uuid))

		ds_raw = data_fetch_queries.get_dataset_raw(conn, exp_uuid)

		return ds_raw
		

if __name__ == '__main__':
	from core_tools.data.SQL.connector import set_up_local_storage

	set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

	test = SQL_database_manager()

	t1 = test.fetch_raw_dataset_by_Id(47)
	t2 = test.fetch_raw_dataset_by_UUID(1603652809326642671)
	print(t1)