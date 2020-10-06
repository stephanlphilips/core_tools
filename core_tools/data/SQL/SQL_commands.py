from core_tools.data.SQL.connector import sample_info
import json

class query_generator:
	@staticmethod
	def generate_overview_of_measurements_table():
		statement = "CREATE TABLE if not EXISTS measurements_overview ("
		statement += "id SERIAL,"
		statement += "set_up varchar(1024) NOT NULL,"
		statement += "project varchar(1024) NOT NULL,"
		statement += "sample varchar(1024) NOT NULL,"
		statement += "start_time TIMESTAMP,"
		statement += "stop_time TIMESTAMP,"
		statement += "exp_name varchar(1024) NOT NULL,"
		statement += "exp_data_location varchar(1024),"
		statement += "snapshot JSON,"
		statement += "metadata JSON, "
		statement += "search_keywords JSON, "
		statement += "completed BOOL DEFAULT False);"
		return statement

	@staticmethod
	def insert_new_measurement_in_overview_table(exp_name):
		statement = "INSERT INTO measurements_overview "
		statement += "(set_up, project, sample, exp_name) VALUES ('"
		statement += str(sample_info.set_up) + "', '"
		statement += str(sample_info.project) + "', '"
		statement += str(sample_info.sample) + "', '"
		statement += exp_name + "');"
		return statement

	@staticmethod
	def get_last_meas_id_in_overview_table():
		return "SELECT MAX(id) FROM measurements_overview;"

	def fill_meas_info_in_overview_table(meas_id, measurement_table_name=None, start_time=None, stop_time=None, metadata=None, snapshot=None, search_kw = None, completed=None):
		'''
		fill in the addional data in a record of the measurements overview table.

		Args:
			meas_id (int) : record that needs to be updated
			measurement_table_name (str) : name of the table that contains the raw measurement data
			start_time (long) : time in unix seconds since the epoch
			stop_time (long) : time in unix seconds since the epoch
			metadata (JSON) : json string to be saved in the database
			snapshot (JSON) : snapshot of the exprimental set up
			search_kw (JSON) : keywords that can be used to search in the array (list of keywords)
			completed (bool) : tell that the measurement is completed.
		'''
		statement = ""

		if measurement_table_name is not None:
			statement += "UPDATE measurements_overview SET exp_data_location = '{}' WHERE ID = {};".format(measurement_table_name, meas_id)
		if start_time is not None:
			statement += "UPDATE measurements_overview SET start_time = to_timestamp('{}') WHERE ID = {};".format(start_time, meas_id)
		if stop_time is not None:
			statement += "UPDATE measurements_overview SET stop_time = to_timestamp('{}') WHERE ID = {};".format(stop_time, meas_id)
		if metadata is not None:
			statement += "UPDATE measurements_overview SET metadata = '{}' WHERE ID = {};".format(metadata, meas_id)
		if snapshot is not None:
			statement += "UPDATE measurements_overview SET snapshot = '{}' WHERE ID = {};".format(snapshot, meas_id)
		if search_kw is not None:
			statement += "UPDATE measurements_overview SET search_keywords = '{}' WHERE ID = {};".format(search_kw, meas_id)


		return statement

	@staticmethod
	def make_new_data_table(name):
		statement = "CREATE TABLE {} ( ".format(name )
		statement += "id serial primary key, "
		statement += "param_id BIGINT, "
		statement += "nth_set INT, "
		statement += "param_id_m_param BIGINT, "
		statement += "setpoint BOOL, "
		statement += "setpoint_local BOOL, "
		statement += "name_gobal varchar(1024), "
		statement += "name varchar(1024) NOT NULL,"
		statement += "label varchar(1024) NOT NULL,"
		statement += "unit varchar(1024) NOT NULL,"
		statement += "depencies jsonb, "
		statement += "shape jsonb, "
		statement += "write_cursor INT, "
		statement += "total_size INT, "
		statement += "oid INT );"
		
		return statement

	@staticmethod
	def insert_measurement_spec_in_meas_table(measurement_table, data_item):
		'''
		instert all the info of the set and get parameters in the measurement table.

		Args:
			measurement_table (str) : name of the measurement table
			data_item (m_param_raw) : raw format of the measurement parameter
		'''
		statement = "INSERT INTO {} ".format(measurement_table)
		statement += "(param_id, nth_set, param_id_m_param, setpoint, setpoint_local, name_gobal, name, label, unit, depencies, shape, write_cursor, total_size, oid) "
		statement += "VALUES ( {} , {} , {} , {} , {} , '{}' , '{}' , '{}' , '{}' , '{}' , '{}' , {} , {} , {} );". format(
			data_item.param_id, data_item.nth_set, data_item.param_id_m_param, 
			data_item.setpoint, data_item.setpoint_local, data_item.name_gobal, 
			data_item.name, data_item.label, data_item.unit, 
			json.dumps(data_item.dependency), json.dumps(data_item.shape),
			0, data_item.size, data_item.oid)
		
		return statement

	@staticmethod
	def update_cursors_in_meas_tab(measurement_table, data_items):
		statement = ""
		for i in range(len(data_items)):
			statement += "UPDATE {} SET write_cursor = {} WHERE id = {}; ".format(measurement_table, data_items[i].data_buffer.cursor, i+1)

		return statement