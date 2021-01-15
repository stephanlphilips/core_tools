'''
update the database version for the dataset

to_update:
* add starring column
* generate keywords automatically
* snapshot and metadata are converted to the type bytea (more appropriate type)
'''
from psycopg2.extras import RealDictCursor, DictCursor,Json
import json, time
from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
import psycopg2
from core_tools.data.SQL.misc.old.SQL_commands import write_query_generator, data_fetch_queries


def to_postgres_time(my_date_time):
	return time.strftime("%a, %d %b %Y %H:%M:%S +0000",my_date_time.timetuple())

def load_old_table(conn_local):
	statement = 'SELECT * from global_measurement_overview;'

	cur = conn_local.cursor(cursor_factory=RealDictCursor)
	cur.execute(statement)
	res = cur.fetchall()
	cur.close()

	return res

def generate_kws(conn_local, uuid):
	statement = 'SELECT exp_data_location from global_measurement_overview WHERE uuid = {};'.format(uuid)	
	
	cur = conn_local.cursor()
	cur.execute(statement)
	meas_table_name = cur.fetchone()[0]
	cur.close()

	statement =  'SELECT label from {} where setpoint = True or setpoint_local = True;'.format(meas_table_name)

	cur = conn_local.cursor()
	cur.execute(statement)
	res = cur.fetchall()
	cur.close()

	set_param = []
	for i in res:
		set_param += i

	statement =  'SELECT label from {} where setpoint = FALSE and setpoint_local = FALSE;'.format(meas_table_name)

	cur = conn_local.cursor()
	cur.execute(statement)
	res = cur.fetchall()
	cur.close()

	get_param = []
	for i in res:
		get_param += i

	# make unique:
	set_param = set(set_param)
	get_param = set(get_param)
	
	return list(set_param) + list(get_param)

def convert_old_table_to_new_tables(conn_local):
	temp_table =  'global_measurement_overview_tmp'
	
	statement = write_query_generator.generate_measurement_table(temp_table)
	cur = conn_local.cursor()
	cur.execute(statement)
	print('new table made')
	conn_local.commit()

	entries_old_table = load_old_table(conn_local)

	for entry in entries_old_table:
		print('copy - ing id {}'.format(entry['id']))
		entry = dict(entry)
		kws = generate_kws(conn_local, entry['uuid'])
		entry['keywords'] = str(Json(kws)).replace('\'', '')
		del entry['tags']
		del entry['sync_location']
		del entry['synchronized']
		del entry['data_cleared']
		del entry['id']

		entry['start_time'] = to_postgres_time(entry['start_time'])
		if entry['stop_time'] is not None:
			entry['stop_time'] = to_postgres_time(entry['stop_time'])

		entry['snapshot'] = json.dumps(entry['snapshot'])
		entry['metadata'] = json.dumps(entry['metadata'])

		statement = "INSERT INTO {} {}  VALUES {}".format(temp_table, str(tuple(entry.keys())).replace('\'', ''), tuple(entry.values()))

		cur.execute(statement.replace("'null'", 'null').replace('None', 'null'))
	conn_local.commit()


def drop_and_move(conn_local):
	cur = conn_local.cursor()
	statement = 'DROP TABLE global_measurement_overview;'
	cur.execute(statement)
	conn_local.commit()
	print('table dropped')

	statement = 'ALTER TABLE global_measurement_overview_tmp RENAME TO global_measurement_overview;'
	cur.execute(statement)
	conn_local.commit()
	print('table altered')

from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage, set_up_remote_storage

set_up_remote_storage('131.180.205.81', 5432, 'xld_measurement_pc', 'XLDspin001', 'spin_data', "6dot", "XLD", "6D3S - SQ20-20-5-18-4")
set_up_remote_storage('131.180.205.81', 5432, 'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')
print('attemping connections')
conn_local = psycopg2.connect(dbname=SQL_conn_info_local.dbname, user=SQL_conn_info_local.user, 
				password=SQL_conn_info_local.passwd, host=SQL_conn_info_local.host, port=SQL_conn_info_local.port)
print('connected')
# convert_old_table_to_new_tables(conn_local)

drop_and_move(conn_local)