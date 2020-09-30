'''
database manager ::

This class is reponsible for:
	* establishing the connection witht the databae
	* queries of measurement that are present in the database
	* loading of measurements from the database (e.g. load a dataset)
	* saving measurements.
		* the raw data is saved in a different calls in raw_data_mgr.py

Note that can only be one measurement manager per python session.
'''
import psycopg2
from core_tools.data.SQL.connector import SQL_descriptor, sample_info
import time
import json

class query_generator:
	@staticmethod
	def generate_overview_of_measurements_table():
		statement = "CREATE TABLE if not EXISTS measurements_overview ("+
			"id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,"+
			"set_up varchar(1024) NOT NULL,"+
			"project varchar(1024) NOT NULL,"+
			"sample varchar(1024) NOT NULL,"+
			"start_time TIMESTAMP,"+
			"stop_time TIMESTAMP,"+
			"exp_name varchar(1024) NOT NULL,"+
			"exp_data_location varchar(1024),"+
			"snapshot JSON,"+
			"metadata JSON);"
		return statement

	@staticmethod
	def insert_new_measurement_in_overview_table(exp_name):
		statement = "INSERT INTO measurements_overview "+ 
		"(set_up, project, sample, exp_name) VALUES ('" + 
			str(SQL_descriptor.set_up) + "', '" + 
			str(SQL_descriptor.project) + "', '" + 
			str(SQL_descriptor.sample) + "', '" + 
			exp_name + "');"
		return statement

	@staticmethod
	def get_last_meas_id_in_overview_table():
		return "SELECT MAX(id) FROM measurements_overview;"

	def fill_meas_info_in_overview_table(meas_id, measurement_table_name=None, start_time=None, stop_time=None, metadata=None, snapshot=None):
		'''
		fill in the addional data in a record of the measurements overview table.

		Args:
			meas_id (int) : record that needs to be updated
			measurement_table_name (str) : name of the table that contains the raw measurement data
			start_time (long) : time in unix seconds since the epoch
			stop_time (long) : time in unix seconds since the epoch
			metadata (JSON) : json string to be saved in the database
			snapshot (JSON) : snapshot of the exprimental set up
		'''
		statement = ""

		if measurement_table_name is not None:
			statement += "UPDATE measurements_overview SET exp_data_location = {} WHERE meas_id = {};".format(measurement_table_name, meas_id)
		if start_time is not None:
			statement += "UPDATE measurements_overview SET start_time = {} WHERE meas_id = {};".format(start_time, meas_id)
		if stop_time is not None:
			statement += "UPDATE measurements_overview SET stop_time = {} WHERE meas_id = {};".format(stop_time, meas_id)
		if metadata is not None:
			statement += "UPDATE measurements_overview SET snapshot = {} WHERE meas_id = {};".format(metadata, meas_id)
		if snapshot is not None:
			statement += "UPDATE measurements_overview SET metadata = {} WHERE meas_id = {};".format(snapshot, meas_id)

		return statement

	@staticmethod
	def make_new_data_table(name):
		statement= "CREATE TABLE {} ( ".format(name ) +
			"id INT NOT NULL, " +
			"param_id BIGINT, " +
			"nth_set INT, " +
			"param_id_m_param BIGINT, " +
			"setpoint BOOL, " +
			"setpoint_local BOOL, " +
			"name_gobal varchar(1024), " +
			"name varchar(1024) NOT NULL," +
			"label varchar(1024) NOT NULL," +
			"unit varchar(1024) NOT NULL," +
			"depencies varchar(1024), " +
			"shape jsonb, " +
			"size INT, " +
			"oid INT );" +
		return statement

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
			self.conn = psycopg2.connect(dbname=SQL_descriptor.dbname, user=SQL_descriptor.user, 
				password=SQL_descriptor.passwd, host=SQL_descriptor.host, port=SQL_descriptor.port)
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