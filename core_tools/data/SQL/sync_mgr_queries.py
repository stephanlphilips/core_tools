from core_tools.data.SQL.SQL_commands import write_query_generator
from core_tools.data.SQL.connector import SQL_conn_info_remote
from psycopg2.extras import RealDictCursor, DictCursor,Json
import time, datetime, json
import numpy as np

def to_postgres_time(my_date_time):
	return time.strftime("%a, %d %b %Y %H:%M:%S +0000",my_date_time.timetuple())


class sync_mgr_query:
	@staticmethod
	def check_meas_4_upload(sync_agent):
		'''
		returns:
			meaurments <list<long>> : list of uuid's that need to be uploaded
		'''

		statement = "SELECT uuid FROM global_measurement_overview where synchronized=False;"

		cur = sync_agent.conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()

		return list(sum(res, ()))

	def cpy_meas_info_to_remote_meas_table(sync_agent, uuid):
		'''
		update/copy record in the remote global_measurement_overview

		Returns:
			exp_data_location (str) : name of the table that is supposed to hold the measurement data
		'''
		statement = "SELECT uuid FROM global_measurement_overview where uuid={};".format(uuid)
		cur_rem = sync_agent.conn_remote.cursor()
		cur_rem.execute(statement)
		meas_present = len(cur_rem.fetchall())

		statement = ("SELECT "+
			"uuid, exp_name, set_up, project, sample, creasted_by, start_time, " + 
			"stop_time, exp_data_location,snapshot, metadata, tags, completed, data_size " + 
			" FROM global_measurement_overview where uuid={};".format(uuid))

		cur_loc = sync_agent.conn_local.cursor(cursor_factory=RealDictCursor)
		cur_loc.execute(statement)
		res = cur_loc.fetchall()[0]
		res['start_time'] = to_postgres_time(res['start_time'])
		if res['stop_time'] is not None:
			res['stop_time'] = to_postgres_time(res['stop_time'])

		res['snapshot'] = str(Json(res['snapshot'])).replace('\'', '')

		cur_loc.close()
		if meas_present == False:
			statement = ("INSERT INTO global_measurement_overview " + 
			"(uuid, exp_name, set_up, project, sample, creasted_by, start_time, " + 
			"stop_time, exp_data_location,snapshot, metadata, tags, completed, data_size) " + 
			" VALUES {} RETURNING exp_data_location;".format(str(tuple(res.values()))))
			statement = statement.replace('None', 'null')
		else:
			statement = "UPDATE global_measurement_overview SET "
			for key, value in res.items():
				statement += " {} = '{}' ,".format(key, str(value)) if isinstance(value, str) else  " {} = {} ,".format(key, str(value))
			statement = statement [:-1]
			statement += "where uuid = {} RETURNING exp_data_location;".format(uuid)
			statement = statement.replace("'null'", 'null').replace('None', 'null')

		cur_rem.execute(statement)
		meas_table_name = cur_rem.fetchone()[0]
		
		# add also measurement in the sample info overiew table:
		statement = write_query_generator.write_data_overview_tables(res['set_up'], res['project'], res['sample'])
		cur_rem.execute(statement)
		cur_rem.close()
		sync_agent.conn_remote.commit()

		return meas_table_name

	def generate_meaurement_data_table(sync_agent, meas_table_name):
		'''
		generate the measurement data table if if does not exists
		'''
		stmt = write_query_generator.make_new_data_table(meas_table_name)
		cur_rem = sync_agent.conn_remote.cursor()
		cur_rem.execute(stmt)
		cur_rem.close()
		sync_agent.conn_remote.commit()

	def fill_and_sync_measurement_table(sync_agent, meas_table_name):
		cur_rem = sync_agent.conn_remote.cursor(cursor_factory=RealDictCursor)
		cur_loc = sync_agent.conn_local.cursor(cursor_factory=RealDictCursor)


		statement_n_rows = "SELECT COUNT(*) FROM {} ;".format(meas_table_name)

		cur_rem.execute(statement_n_rows)
		res_rem = cur_rem.fetchone()['count']
		cur_loc.execute(statement_n_rows)
		res_loc = cur_loc.fetchone()['count']

		# check includes also a neglect of the full table
		if res_rem != res_loc:
			# drop
			statement_get_rid_of_table = "DROP TABLE IF EXISTS {} ; ".format(meas_table_name)
			cur_rem.execute(statement_get_rid_of_table)
			
			# create
			cur_rem.execute(write_query_generator.make_new_data_table(meas_table_name))
			
			# copy table
			statement_data_to_insert = ("SELECT * FROM {} ORDER by id;".format(meas_table_name))

			cur_loc.execute(statement_data_to_insert)
			res_loc = cur_loc.fetchall()

			for result in res_loc:
				lobject = sync_agent.conn_remote.lobject(0,'w')
				result['oid'] = lobject.oid
				result['write_cursor'] = 0
				result['depencies'] = json.dumps(result['depencies'])
				result['shape'] = json.dumps(result['shape'])


				statement_insert_row = "INSERT INTO {} {} VALUES {} ;".format(meas_table_name, 
					str(tuple(result.keys())).replace("'", ""), str(tuple(result.values())))
				statement_insert_row = statement_insert_row.replace('None', 'null')
				cur_rem.execute(statement_insert_row)
				sync_agent.conn_remote.commit()
				lobject.close()

		# write data from a to b
		statement_write_status = "SELECT write_cursor, total_size, oid FROM {} ORDER by id;".format(meas_table_name)

		cur_rem.execute(statement_write_status)
		res_rem = cur_rem.fetchall()
		cur_loc.execute(statement_write_status)
		res_loc = cur_loc.fetchall()
		
		for i in range(len(res_loc)):
			r_cursor = res_rem[i]['write_cursor']
			l_cursor = res_loc[i]['write_cursor']
			r_oid = res_rem[i]['oid']
			l_oid = res_loc[i]['oid']
			l_lobject = sync_agent.conn_local.lobject(l_oid,'rb')
			r_lobject = sync_agent.conn_remote.lobject(r_oid,'wb')
			# read in data in a buffer
			l_lobject.seek(r_cursor*8)
			mybuffer = np.frombuffer(l_lobject.read(l_cursor*8-r_cursor*8))
			# push data to the server
			r_lobject.seek(r_cursor*8)
			r_lobject.write(mybuffer.tobytes())
			r_lobject.close()
			l_lobject.close()

			# update the server until where the data is written
			stmnt = "UPDATE {} set write_cursor={} where oid={} ;".format(meas_table_name, 
				l_cursor, r_oid)
			cur_rem.execute(stmnt)
			completed = []

		sync_agent.conn_remote.commit()

		cur_rem.close()
		cur_loc.close()

	@staticmethod
	def check_if_sync_done(sync_agent, uuid, meas_table_name):
		cur_rem = sync_agent.conn_remote.cursor(cursor_factory=RealDictCursor)
		cur_loc = sync_agent.conn_local.cursor(cursor_factory=RealDictCursor)

		# check if the measurement is marked as completed.
		
		statement = "SELECT completed FROM global_measurement_overview where uuid={}".format(uuid)
		cur_loc.execute(statement)
		res_loc = cur_loc.fetchone()
		done = True

		if res_loc['completed'] == True:
			# check if all the entries are fully copied.
			statement_write_status = "SELECT write_cursor, total_size, oid FROM {} ;".format(meas_table_name)

			cur_rem.execute(statement_write_status)
			res_rem = cur_rem.fetchall()

			cur_loc.execute(statement_write_status)
			res_loc = cur_loc.fetchall()

			for row_l, row in zip(res_loc, res_rem):
				if row_l['write_cursor'] != row['write_cursor']:
					done = False
				else:
					stmnt = "UPDATE {} set synchronized = True, sync_location = '{}' where oid={} ;".format(meas_table_name, 
							str(sync_agent.SQL_conn_info_remote.dbname) + "@" + str(sync_agent.SQL_conn_info_remote.host), row['oid'])
					cur_loc.execute(stmnt)
		
			if done == True:
				stmnt = "UPDATE global_measurement_overview set synchronized = True, sync_location = '{}' where uuid={} ;".format( 
								str(sync_agent.SQL_conn_info_remote.dbname) + "@" + str(sync_agent.SQL_conn_info_remote.host), uuid)
				cur_loc.execute(stmnt)
				print('sync of dataset with uuid {} --> done.'.format(uuid))

		sync_agent.conn_remote.commit()
		sync_agent.conn_local.commit()
		cur_rem.close()
		cur_loc.close()

	@staticmethod
	def mark_incomplete_completed(sync_agent, uuid_list):
		if len(uuid_list) >= 2:
			cur_loc = sync_agent.conn_local.cursor()

			uuid_s_completed = tuple(uuid_list[:-1])
			for uuid in uuid_s_completed:
				statement = "UPDATE global_measurement_overview set completed = TRUE where uuid = {} ;".format(uuid)
				cur_loc.execute(statement)

			sync_agent.conn_local.commit()
			cur_loc.close()

	@staticmethod
	def mark_all_for_resync(sync_agent):
		cur_loc = sync_agent.conn_local.cursor()
		statement = "UPDATE global_measurement_overview set synchronized = FALSE ;"
		cur_loc.execute(statement)
		sync_agent.conn_local.commit()
		cur_loc.close()

if __name__ == '__main__':
	from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
	from core_tools.data.SQL.SQL_synchronization_manager import sync_agent
	set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
		'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')

	s = sync_agent()
	# s.re_sync_all()
	s.run()
	

	# t = sync_agent()
	# t.conn_remote

	# m = sync_mgr_query.check_meas_4_upload()

	# for m_id in m:
	# 	try:
	# 		table = sync_mgr_query.cpy_meas_info_to_remote_meas_table(m_id)
	# 		sync_mgr_query.generate_meaurement_data_table(table)
	# 		sync_mgr_query.fill_and_sync_measurement_table(table)
	# 		sync_mgr_query.check_if_sync_done(m_id, table)
	# 	except:
	# 		pass
	# 		# check if connected