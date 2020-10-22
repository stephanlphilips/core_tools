from core_tools.data.ds.data_set_raw import data_set_raw, m_param_raw
from core_tools.data.SQL.buffer_writer import buffer_reader
from core_tools.data.SQL.connector import sample_info
from uuid import getnode as get_mac

import time
import json

def generate_uuid():
	ms_time = int(time.time()*1000)*1000000
	return ms_time + get_mac()%99999999

class write_query_generator:
	@staticmethod
	def generate_data_overview_tables():
		'''
		small table that holds a overview of which samples have been measured on the current system. 
		Table use : for syncing data.
		'''
		table_name = 'sample_info_overview'

		statement = "CREATE TABLE if not EXISTS {} (".format(table_name)
		statement += "sample_info_hash text NOT NULL UNIQUE,"
		statement += "set_up text NOT NULL,"
		statement += "project text NOT NULL,"
		statement += "sample text NOT NULL );"

		return statement

	@staticmethod
	def write_data_overview_tables(set_up, project, sample):
		hash_string = set_up+project+sample

		statement = "INSERT INTO sample_info_overview (sample_info_hash,set_up,project,sample) "
		statement += "VALUES ( '{}', '{}', '{}', '{}') ".format(hash_string, set_up, project, sample)
		statement += "ON CONFLICT DO NOTHING;"
		
		return statement

	@staticmethod
	def generate_measurement_table(table_name="global_measurement_overview"):
		statement = "CREATE TABLE if not EXISTS {} (".format(table_name)
		statement += "id SERIAL,"
		statement += "uuid BIGINT NOT NULL unique,"
		
		statement += "exp_name text NOT NULL,"
		statement += "set_up text NOT NULL,"
		statement += "project text NOT NULL,"
		statement += "sample text NOT NULL,"
		statement += "creasted_by text NOT NULL,"
		
		statement += "start_time TIMESTAMP,"
		statement += "stop_time TIMESTAMP,"
		
		statement += "exp_data_location text,"
		statement += "snapshot JSON,"
		statement += "metadata JSON, "
		statement += "tags JSONB, "
		
		statement += "completed BOOL DEFAULT False,"
		statement += "data_size int,"
		statement += "data_cleared BOOL DEFAULT False, "

		statement += "synchronized BOOL DEFAULT False,"
		statement += "sync_location text); "
		
		statement += "CREATE INDEX IF NOT EXISTS uuid_indexed ON {} USING BTREE (uuid) ;".format(table_name)
		statement += "CREATE INDEX IF NOT EXISTS pro_set_sample_index ON {} USING GIN(to_tsvector('english',project), to_tsvector('english',set_up), to_tsvector('english',sample)) ;".format(table_name)
		statement += "CREATE INDEX IF NOT EXISTS pro_set_sample_search_tag_index ON {} USING GIN (to_tsvector('english',project), to_tsvector('english',set_up), to_tsvector('english',sample), tags, to_tsvector('english',exp_name));".format(table_name)
		statement += "CREATE INDEX IF NOT EXISTS search_tag_index ON {} USING GIN (tags, to_tsvector('english',exp_name));".format(table_name)
		statement += "CREATE INDEX IF NOT EXISTS synced_index ON {} USING BTREE (synchronized);".format(table_name)
		statement += "CREATE INDEX IF NOT EXISTS data_size_index ON {} USING BTREE (data_size);".format(table_name)

		return statement

	@staticmethod
	def insert_new_measurement_in_measurement_table(exp_name, dbuser):
		'''
		insert new measurement in the measurement table

		Args:
			exp_name (str) : name of the experiment to be executed
			dbuser (str) : name of the user creating the measurement
		Not used atm:	
			table_name (str) : name of the table where to insert
			uuid (int64) : integer that represent a unique fingerprint of the current experiment 
		'''
		table_name="global_measurement_overview"
		uuid =  generate_uuid()

		statement = "INSERT INTO {} ".format(table_name)
		statement += "(uuid, set_up, project, sample, creasted_by, exp_name) VALUES ('"
		statement += str(uuid) + "' , '"
		statement += str(sample_info.set_up) + "', '"
		statement += str(sample_info.project) + "', '"
		statement += str(sample_info.sample) + "', '"
		statement += dbuser + "', '"
		statement += exp_name + "');"
		return statement

	@staticmethod
	def get_last_meas_id_in_measurement_table(table_name="global_measurement_overview"):
		return "SELECT id, uuid FROM {} ORDER BY uuid DESC LIMIT 1;".format(table_name)

	def fill_meas_info_in_measurement_table(meas_uuid, measurement_table_name=None, start_time=None, stop_time=None, metadata=None, snapshot=None, tags= None, completed=None):
		'''
		fill in the addional data in a record of the measurements overview table.

		Args:
			meas_uuid (int) : record that needs to be updated
			measurement_table_name (str) : name of the table that contains the raw measurement data
			start_time (long) : time in unix seconds since the epoch
			stop_time (long) : time in unix seconds since the epoch
			metadata (JSON) : json string to be saved in the database
			snapshot (JSON) : snapshot of the exprimental set up
			tags (JSON) : list of tags that accompuarby the measurment if any
			completed (bool) : tell that the measurement is completed.
		
		Not used atm:	
			table_name (str) : name of the table where to insert
		'''
		table_name="global_measurement_overview"
		statement = ""

		if measurement_table_name is not None:
			statement += "UPDATE {} SET exp_data_location = '{}' WHERE uuid = {};".format(table_name, measurement_table_name, meas_uuid)
		if start_time is not None:
			statement += "UPDATE {} SET start_time = to_timestamp('{}') WHERE uuid = {};".format(table_name, start_time, meas_uuid)
		if stop_time is not None:
			statement += "UPDATE {} SET stop_time = to_timestamp('{}') WHERE uuid = {};".format(table_name, stop_time, meas_uuid)
		if metadata is not None:
			statement += "UPDATE {} SET metadata = '{}' WHERE uuid = {};".format(table_name, metadata, meas_uuid)
		if snapshot is not None:
			statement += "UPDATE {} SET snapshot = '{}' WHERE uuid = {};".format(table_name, snapshot, meas_uuid)
		if tags is not None:
			statement += "UPDATE {} SET tags = '{}' WHERE uuid = {};".format(table_name, tags, meas_uuid)
		if completed is not None:
			statement += "UPDATE {} SET completed = '{}' WHERE uuid = {};".format(table_name, completed, meas_uuid)

		return statement

	def fill_technical_infomation_in_measurement_table(meas_uuid, data_size=None, data_cleared=None, synchronized=None, sync_location=None):
		'''
		fill in technical details about the measurement

		Args:
			table_name (str) : name of the table where to fill in these things
			meas_uuid (int64) : unique identifier of the measurement
			data_size (int) : number of bytes that are stored for this measurement
			data_cleared (bool) : if the data of this measurement has been cleared to spare space (--> moved to the server)
			synchronized (bool) : tells if this measurement has been synchronized to the server.
			sync_location (str) : string to what server the data has been stored (user@schema@host)
		
		Not used atm:	
			table_name (str) : name of the table where to insert
		'''
		table_name="global_measurement_overview"
		statement = ""

		if data_size is not None:
			statement += "UPDATE {} SET data_size = '{}' WHERE uuid = {};".format(table_name, data_size, meas_uuid)
		if data_cleared is not None:
			statement += "UPDATE {} SET data_cleared = '{}' WHERE uuid = {};".format(table_name, data_cleared, meas_uuid)
		if synchronized is not None:
			statement += "UPDATE {} SET synchronized = '{}' WHERE uuid = {};".format(table_name, synchronized, meas_uuid)
		if sync_location is not None:
			statement += "UPDATE {} SET sync_location = '{}' WHERE uuid = {};".format(table_name, sync_location, meas_uuid)
		
		return statement


	@staticmethod
	def make_new_data_table(name):
		statement = "CREATE TABLE {} ( ".format(name )
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
		statement += "(param_id, nth_set, nth_dim, param_id_m_param, setpoint, setpoint_local, name_gobal, name, label, unit, depencies, shape, write_cursor, total_size, oid) "
		statement += "VALUES ( {} , {} , {} , {},{} , {} , '{}' , '{}' , '{}' , '{}' , '{}' , '{}' , {} , {} , {} );". format(
			data_item.param_id, data_item.nth_set, data_item.nth_dim, data_item.param_id_m_param, 
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

# get data local
class data_fetch_queries:
	table_name = "global_measurement_overview"

	@staticmethod
	def check_if_exp_uuid_exists(cursor, exp_uuid):
		statement = "SELECT uuid FROM {} WHERE uuid = {};".format(data_fetch_queries.table_name, exp_uuid);

		return data_fetch_queries.__check_exist(cursor, statement)

	@staticmethod
	def check_if_exp_id_exists(cursor, exp_id):
		statement = "SELECT id FROM {} WHERE id = {};".format(data_fetch_queries.table_name, exp_id);

		return data_fetch_queries.__check_exist(cursor, statement)

	@staticmethod
	def check_if_meas_table_exists(cursor, meas_table_name):
		statement = "SELECT to_regclass('{}');".format(meas_table_name);
		
		return data_fetch_queries.__check_exist(cursor, statement)

	@staticmethod
	def convert_id_to_uuid(cursor, exp_id):
		statement = "SELECT id, uuid FROM {} WHERE id = {};".format(data_fetch_queries.table_name, exp_id);

		cursor.execute(statement)
		
		return_data = cursor.fetchall()
		if len(return_data) != 0 and len(return_data[0]) == 2:
			return return_data[0][1]
		else:
			raise ValueError('uuid for exp_id {} does not exist.'.format(exp_id))

	@staticmethod
	def is_running(cursor, exp_uuid):
		statement = (	"SELECT completed " + 
						"FROM {} ".format(data_fetch_queries.table_name) +
						"WHERE uuid = {};".format(exp_uuid)
					)

		cursor.execute(statement)
		data = cursor.fetchone()
		return data[0]

	@staticmethod
	def get_dataset_raw(conn, exp_uuid):
		statement = (	"SELECT id, uuid, exp_name, set_up, project, sample, " +
						"start_time, stop_time, exp_data_location, snapshot, " +
						"metadata, tags, completed " + 
						"FROM {} ".format(data_fetch_queries.table_name) +
						"WHERE uuid = {};".format(exp_uuid)
					)
		cursor = conn.cursor()
		cursor.execute(statement)
		data = cursor.fetchone()

		ds = data_set_raw(exp_id=data[0], exp_uuid=data[1], exp_name=data[2], 
			set_up = data[3], project = data[4], sample = data[5], 
			UNIX_start_time=data[6].timestamp(), UNIX_stop_time=data[7].timestamp(), 
			SQL_datatable=data[8],snapshot=data[9], metadata=data[10],
			tags=data[11], completed=data[12],)
		
		ds.measurement_parameters_raw = data_fetch_queries.__get_dataset_raw_dataclasses(conn, cursor, ds.SQL_datatable)
		cursor.close()

		return ds


	@staticmethod		
	def __get_dataset_raw_dataclasses(conn, cursor, meas_table_name):
		statement =	(	"SELECT param_id, nth_set, nth_dim, param_id_m_param, " +
						"setpoint, setpoint_local, name_gobal, name, label, " +
						"unit, depencies, shape, total_size, oid " +
						"from {};".format(meas_table_name))

		cursor.execute(statement)
		data_raw = []
		for row in cursor.fetchall():
			raw_data_row = m_param_raw(*row)
			raw_data_row.data_buffer = buffer_reader(conn, raw_data_row.oid, raw_data_row.shape)
			data_raw.append(raw_data_row)

		return data_raw

	@staticmethod
	def __check_exist(cursor, statement):
		cursor.execute(statement)

		return_data = cursor.fetchall()
		if len(return_data) == 0 or return_data[0][0] is None:
			return False
		return True

if __name__ == '__main__':
	from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
	import psycopg2

	set_up_local_storage('stephan', 'magicc', 'test', '6dot', 'XLD2', 'SQblabla12')

	conn_local = psycopg2.connect(dbname=SQL_conn_info_local.dbname, user=SQL_conn_info_local.user, 
					password=SQL_conn_info_local.passwd, host=SQL_conn_info_local.host, port=SQL_conn_info_local.port)

	cur = conn_local.cursor()
	# cur.execute(write_query_generator.generate_data_overview_tables())
	# cur.execute(write_query_generator.write_data_overview_tables(sample_info.project, sample_info.set_up, sample_info.sample))
	# conn_local.commit()
	# cur.close()

	# name1 = '_'+sample_info.project+'_'+sample_info.set_up+'_'+sample_info.sample
	# name2 = 'global_measurement_overview'

	# cur = conn_local.cursor()
	# cur.execute(write_query_generator.generate_measurement_table())
	# # cur.execute(write_query_generator.generate_measurement_table(name2))
	# exp_name = 'test'
	# uuid = generate_uuid()
	# # cur.execute(write_query_generator.insert_new_measurement_in_measurement_table(exp_name, SQL_conn_info_local.user))
	# # # cur.execute(write_query_generator.insert_new_measurement_in_measurement_table(name2, exp_name, uuid, SQL_conn_info_local.user))

	# cur.execute(write_query_generator.get_last_meas_id_in_measurement_table())
	
	# # print( cur.fetchone())
	# local_id, uuid = cur.fetchone()
	# print(local_id, uuid)
	# # table_name = name2
	# meas_uuid = uuid
	# measurement_table_name="_" + sample_info.set_up + "_" +sample_info.project + "_" +sample_info.sample +"_" + str(uuid)
	# start_time=time.time()
	# stop_time=time.time()
	# metadata=json.dumps(['test', "test", 'more tests'])
	# snapshot=json.dumps(['blah', "blah", 'more blah'])
	# search_kw = json.dumps(['vP1', "vP2", 'Idc'])
	# tags= json.dumps(['calibration'])
	# completed=True

	# cur.execute(write_query_generator.fill_meas_info_in_measurement_table(meas_uuid, start_time=start_time))
	# # cur.execute(write_query_generator.fill_meas_info_in_measurement_table(table_name, meas_uuid, stop_time=stop_time))
	# # cur.execute(write_query_generator.fill_meas_info_in_measurement_table(table_name, meas_uuid, metadata=metadata))
	# # cur.execute(write_query_generator.fill_meas_info_in_measurement_table(table_name, meas_uuid, tags=tags))
	# # cur.execute(write_query_generator.fill_meas_info_in_measurement_table(table_name, meas_uuid, search_kw=search_kw))
	# cur.execute(write_query_generator.fill_meas_info_in_measurement_table(meas_uuid, measurement_table_name=measurement_table_name))
	# cur.execute(write_query_generator.fill_meas_info_in_measurement_table(meas_uuid, completed=completed))
	# cur.execute(write_query_generator.fill_meas_info_in_measurement_table(meas_uuid, snapshot=snapshot))

	# data_size=12000
	# data_cleared=False
	# synchronized=True
	# sync_location='vandersypen@vanvliet.qutech.tudelft.nl'
	# cur.execute(write_query_generator.fill_technical_infomation_in_measurement_table(meas_uuid, data_size, data_cleared, synchronized, sync_location))


	statement = data_fetch_queries.check_if_exp_uuid_exists(cur, 1603364967262642671)
	statement = data_fetch_queries.check_if_meas_table_exists(cur, "global_measurement_overview1")
	statement = data_fetch_queries.is_running(cur, 1603386306086642671)
	print(statement)
	statement = data_fetch_queries.get_dataset_raw(conn_local, 1603386306086642671)

	from core_tools.data.ds.data_set import data_set

	ds = data_set(statement)
	print(ds)
	print(statement)
	# cur.execute(statement)
	# cur.execute(statement)

	# print(cur.fetchall())
	# print(cur.fetchall())
	# conn_local.commit()
	# cur.close()