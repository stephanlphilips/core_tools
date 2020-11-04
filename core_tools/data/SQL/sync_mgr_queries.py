from core_tools.data.SQL.SQL_commands import write_query_generator
from core_tools.data.SQL.connector import SQL_conn_info_remote
class sync_mgr_query:
	@staticmethod
	def check_meas_4_upload():
		'''
		returns:
			meaurments <list<long>> : list of uuid's that need to be uploaded
		'''

		statement = "SELECT uuid FROM global_measurement_overview where synchronized=False;"

		cur = sync_agent().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()

		return list(res)

	def cpy_meas_info_to_remote_meas_table(uuid):
		'''
		update/copy record in the remote global_measurement_overview

		Returns:
			exp_data_location (str) : name of the table that is supposed to hold the measurement data
		'''
		statement = "SELECT uuid FROM global_measurement_overview where uuid={};".format(uuid)
		cur_rem = sync_agent().conn_remote.cursor()
		cur_rem.execute(statement)
		meas_present = len(cur_rem.fetchall())

		statement = "SELECT * FROM global_measurement_overview where uuid={};".format(uuid)
		cur_loc = sync_agent().conn_local.cursor()
		cur_loc.execute(statement)
		res = cur_loc.fetchall()
		cur_loc.close()

		if meas_present == False:
			statement = "INSERT INTO global_measurement_overview (*) {} RETURNING exp_data_location;".format(str(res[0]))
		else:
			statement  = "UPDATE global_measurement_overview SET (*) {} where uuid = {} RETURNING exp_data_location;"..format(str(res[0]), uuid)

		cur_rem.execute(statement)
		res = cur_rem.fetchall()
		cur_rem.close()

		return res[0]

	def generate_meaurement_data_table(meas_table_name):
		'''
		generate the measurement data table if if does not exists
		'''
		stmt = write_query_generator.make_new_data_table(meas_table_name)
		cur_rem = sync_agent().conn_remote.cursor()
		cur_rem.execute(stmt)
		cur_rem.close()

	def fill_and_sync_measurement_table(meas_table_name):
		cur_rem = sync_agent().conn_remote.cursor()
		cur_loc = sync_agent().conn_local.cursor()


		statement_n_rows = "SELECT COUNT(*) FROM {} ;".format(uuid, meas_table_name)

		cur_rem.execute(statement_n_rows)
		res_rem = cur_rem.fetchone()
		cur_loc.execute(statement_n_rows)
		res_loc = cur_loc.fetchone()

		# check includes also a neglect of the full table
		if res_rem[0] != res_loc[0]:
			# drop
			statement_get_rid_of_table = "DROP TABLE IF EXISTS {} ; ".format(meas_table_name)
			cur_rem.execute(statement_get_rid_of_table)
			
			# create
			cur_rem.execute(write_query_generator.make_new_data_table(meas_table_name))
			
			# copy table
			statement_data_to_insert = "SELECT id, param_id, nth_set, nth_dim, param_id_m_param, setpoint, setpoint_local, name_gobal, name, label, unit, depencies, shape, total_size FROM {} ;".format(meas_table_name)

			cur_loc.execute(statement_data_to_insert)
			res_loc = cur_loc.fetchall()

			for i in res_loc:
				lobject = sync_agent().conn_remote.lobject(0,'w')
				oid = lobject.oid
				cursor = 0

				statement_insert_row = "INSERT INTO {} (id, param_id, nth_set, nth_dim, param_id_m_param, setpoint, setpoint_local, name_gobal, name, label, unit, depencies, shape, total_size, write_cursor, oid) {} ;".format(meas_table_name, *i, write_cursor, oid)
				cur_rem.execute(statement_n_rows)
				sync_agent().conn_remote.commit()
				lobject.close()

		# write data from a to b
		statement_write_status = "SELECT write_cursor, total_size, oid FROM {} ;".format(uuid, meas_table_name)

		cur_rem.execute(statement_write_status)
		res_rem = cur_rem.fetchone()
		cur_loc.execute(statement_write_status)
		cur_loc = cur_loc.fetchone()

		
		for i in res_local:
			write_cursor = i[0]
			total_size = i[1]
			oid = i[2]

			if write_cursor == total_size:
				stmnt = "UPDATE {} set (synchronized, sync_location) True, {} where oid={} ;".format(meas_table_name, 
					str(SQL_conn_info_remote.dbname) + "@" + str(SQL_conn_info_remote.host), oid)
				cur_rem.execute(stmnt)

		cur_rem.close()
		cur_loc.close()