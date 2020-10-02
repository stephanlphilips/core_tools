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
		statement += "metadata JSON);"
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
			statement += "UPDATE measurements_overview SET exp_data_location = '{}' WHERE ID = {};".format(measurement_table_name, meas_id)
		if start_time is not None:
			statement += "UPDATE measurements_overview SET start_time = to_timestamp('{}') WHERE ID = {};".format(start_time, meas_id)
		if stop_time is not None:
			statement += "UPDATE measurements_overview SET stop_time = to_timestamp('{}') WHERE ID = {};".format(stop_time, meas_id)
		if metadata is not None:
			statement += "UPDATE measurements_overview SET metadata = '{}' WHERE ID = {};".format(metadata, meas_id)
		if snapshot is not None:
			statement += "UPDATE measurements_overview SET snapshot = '{}' WHERE ID = {};".format(snapshot, meas_id)

		return statement

	@staticmethod
	def make_new_data_table(name):
		statement = "CREATE TABLE {} ( ".format(name )
		statement += "id INT NOT NULL, "
		statement += "param_id BIGINT, "
		statement += "nth_set INT, "
		statement += "param_id_m_param BIGINT, "
		statement += "setpoint BOOL, "
		statement += "setpoint_local BOOL, "
		statement += "name_gobal varchar(1024), "
		statement += "name varchar(1024) NOT NULL,"
		statement += "label varchar(1024) NOT NULL,"
		statement += "unit varchar(1024) NOT NULL,"
		statement += "depencies varchar(1024), "
		statement += "shape jsonb, "
		statement += "size INT, "
		statement += "oid INT );"
		return statement

	def insert_measurement_spec_in_meas_table(measurement_table, data_item):
		statement = "INSERT INTO {} "
		statement += "(param_id nth_set, param_id_m_param, setpoint, setpoint_local, name_gobal, name, label, unit, depencies, shape, size,oid) VALUES ('"
		statement += str(SQL_conn_info.set_up) + "', '"
		statement += str(SQL_conn_info.project) + "', '"
		statement += str(SQL_conn_info.sample) + "', '"
		statement += exp_name + "');"
		return statement
