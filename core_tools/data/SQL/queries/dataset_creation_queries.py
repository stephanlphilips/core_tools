from core_tools.data.SQL.SQL_common_commands import execute_statement, execute_query
from core_tools.data.SQL.SQL_common_commands import select_elements_in_table, insert_row_in_table, update_table

from core_tools.data.SQL.SQL_utility import text, generate_uuid, N_to_n
from core_tools.data.SQL.connect import SQL_conn_info_local, sample_info

import psycopg2, json

class sample_info_queries:
	'''
	small table that holds a overview of which samples have been measured on the current system. 
	'''
	table_name = 'sample_info_overview'
	
	@staticmethod
	def generate_table(conn):
		statement = "CREATE TABLE if not EXISTS {} (".format(sample_info_queries.table_name)
		statement += "sample_info_hash text NOT NULL UNIQUE,"
		statement += "set_up text NOT NULL,"
		statement += "project text NOT NULL,"
		statement += "sample text NOT NULL );"

		execute_statement(conn, statement)

	@staticmethod
	def add_sample(conn):
		sample, set_up, project = sample_info.sample, sample_info.set_up, sample_info.project
		var_names = ('sample_info_hash', 'sample', 'set_up', 'project')
		var_values = (set_up+project+sample, sample, set_up, project)
		insert_row_in_table(conn, sample_info_queries.table_name, var_names, var_values,
			custom_statement='ON CONFLICT DO NOTHING')

class measurement_overview_queries:
	'''
	large-ish table that holds all the inforamtion of what measurements are done. 

	The raw data is saved in other tables (-> data_table_queries)
	'''
	table_name="global_measurement_overview"

	@staticmethod
	def generate_table(conn):
		statement = "CREATE TABLE if not EXISTS {} (".format(measurement_overview_queries.table_name)
		statement += "id SERIAL,"
		statement += "uuid BIGINT NOT NULL unique,"
		
		statement += "exp_name text NOT NULL,"
		statement += "set_up text NOT NULL,"
		statement += "project text NOT NULL,"
		statement += "sample text NOT NULL,"
		statement += "creasted_by text NOT NULL,"
		
		statement += "start_time TIMESTAMP, "
		statement += "stop_time TIMESTAMP, "
		
		statement += "exp_data_location text,"
		statement += "snapshot BYTEA, "
		statement += "metadata BYTEA,"
		statement += "keywords JSONB, "
		statement += "starred BOOL DEFAULT False, "
		
		statement += "completed BOOL DEFAULT False, "
		statement += "data_size int,"
		statement += "data_cleared BOOL DEFAULT False, "

		statement += "data_synchronized BOOL DEFAULT False,"
		statement += "table_synchronized BOOL DEFAULT False,"
		statement += "sync_location text); "
		
		statement += "CREATE INDEX IF NOT EXISTS uuid_indexed ON {} USING BTREE (uuid) ;".format(measurement_overview_queries.table_name)
		statement += "CREATE INDEX IF NOT EXISTS starred_indexed ON {} USING BTREE (starred) ;".format(measurement_overview_queries.table_name)
		statement += "CREATE INDEX IF NOT EXISTS date_day_index ON {} USING BTREE (project, set_up, sample) ;".format(measurement_overview_queries.table_name)
		
		statement += "CREATE INDEX IF NOT EXISTS data_synced_index ON {} USING BTREE (data_synchronized);".format(measurement_overview_queries.table_name)
		statement += "CREATE INDEX IF NOT EXISTS table_synced_index ON {} USING BTREE (table_synchronized);".format(measurement_overview_queries.table_name)

		execute_statement(conn, statement)

	@staticmethod
	def new_measurement(conn, exp_name):
		'''
		insert new measurement in the measurement table

		Args:
			exp_name (str) : name of the experiment to be executed

		Returns:
			id, uuid, SQL_datatable : id and uuid of the new measurement and the tablename for raw data storage
		'''
		uuid = generate_uuid()
		var_names = ('uuid', 'set_up', 'project', 'sample', 'creasted_by', 'exp_name')
		var_values = (uuid, str(sample_info.set_up),  str(sample_info.project),
			str(sample_info.sample) , SQL_conn_info_local.user, exp_name)
		
		returning = ('id', 'uuid')
		query_outcome = insert_row_in_table(conn, measurement_overview_queries.table_name, var_names, var_values, returning)

		SQL_datatable = ("_" + sample_info.set_up + "_" +sample_info.project + "_" +sample_info.sample +"_" + str(query_outcome[0][1])).replace(" ", "_").replace('-', '_')
		return query_outcome[0][0], query_outcome[0][1], SQL_datatable

	def update_measurement(conn, meas_uuid, meas_table_name=None, start_time=None, stop_time=None,
			metadata=None, snapshot=None, keywords= None, data_size=None, data_synchronized=False, completed=False):
		'''
		fill in the addional data in a record of the measurements overview table.

		Args:
			meas_uuid (int) : record that needs to be updated
			meas_table_name (str) : name of the table that contains the raw measurement data
			start_time (long) : time in unix seconds since the epoch
			stop_time (long) : time in unix seconds since the epoch
			metadata (dict) : json string to be saved in the database
			snapshot (dict) : snapshot of the exprimental set up
			keywords (list) : keywords describing the measurement
			completed (bool) : tell that the measurement is completed.
		'''
		var_names = ['exp_data_location','metadata', 'snapshot', 'keywords', 'data_size', 'data_synchronized', 'completed']
		var_values = [meas_table_name, psycopg2.Binary(str(json.dumps(metadata)).encode('ascii')),
			psycopg2.Binary(str(json.dumps(snapshot)).encode('ascii')), psycopg2.extras.Json(keywords),
			data_size, str(data_synchronized), str(completed) ]

		if start_time is not None:
			var_names += ['start_time']
			var_values += [psycopg2.sql.SQL("TO_TIMESTAMP({})").format(psycopg2.sql.Literal(start_time))]
		if stop_time is not None:
			var_names += ['stop_time']
			var_values += [psycopg2.sql.SQL("TO_TIMESTAMP({})").format(psycopg2.sql.Literal(stop_time))]

		condition = ('uuid', meas_uuid)
		update_table(conn, measurement_overview_queries.table_name, var_names, var_values, condition)

	@staticmethod
	def is_completed(conn, uuid):
		completed =  execute_query(conn, 
			"SELECT completed FROM {} where uuid = {};".format(measurement_overview_queries.table_name, uuid))
		return completed[0][0]

class data_table_queries:
	'''
	these tables contain the raw data of every measurement parameter.
	'''
	@staticmethod
	def generate_table(conn, table_name):
		statement = "CREATE TABLE if not EXISTS {} ( ".format(table_name )
		statement += "id serial primary key, "
		statement += "param_id BIGINT, "
		statement += "nth_set INT, "
		statement += "nth_dim INT, "
		statement += "param_id_m_param BIGINT, "
		statement += "setpoint BOOL, "
		statement += "setpoint_local BOOL, "
		statement += "name_gobal text, "
		statement += "name text NOT NULL,"
		statement += "label text NOT NULL,"
		statement += "unit text NOT NULL,"
		statement += "depencies jsonb, "
		statement += "shape jsonb, "
		statement += "write_cursor INT, "
		statement += "total_size INT, "
		statement += "oid INT, "
		statement += "synchronized BOOL DEFAULT False,"
		statement += "sync_location text);"
		execute_statement(conn, statement)
		
	@staticmethod
	def insert_measurement_spec_in_meas_table(conn, table_name, data_item):
		'''
		instert all the info of the set and get parameters in the measurement table.

		Args:
			measurement_table (str) : name of the measurement table
			data_item (m_param_raw) : raw format of the measurement parameter
		'''
		var_names = ("param_id", "nth_set", "nth_dim", "param_id_m_param",
			"setpoint", "setpoint_local", "name_gobal", "name", 
			"label", "unit", "depencies", "shape", 
			"write_cursor", "total_size", "oid")

		var_values = (data_item.param_id, data_item.nth_set, data_item.nth_dim, 
			data_item.param_id_m_param, data_item.setpoint, data_item.setpoint_local, 
			data_item.name_gobal, data_item.name, data_item.label, 
			data_item.unit, psycopg2.extras.Json(data_item.dependency), psycopg2.extras.Json(data_item.shape),
			0, data_item.size, data_item.oid)
		
		insert_row_in_table(conn, table_name, var_names, var_values)

	@staticmethod
	def update_cursors_in_meas_tab(conn, table_name, data_items):
		statement = ""
		for i in range(len(data_items)):
			statement += "UPDATE {} SET write_cursor = {} WHERE id = {}; ".format(table_name, data_items[i].data_buffer.cursor, i+1)

		execute_statement(conn, statement)