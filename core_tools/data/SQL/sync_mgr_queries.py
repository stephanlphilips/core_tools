from core_tools.data.SQL.SQL_commands import write_query_generator

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

	def fill_measurement_table(meas_table_name):
		cur_rem = sync_agent().conn_remote.cursor()
		cur_loc = sync_agent().conn_local.cursor()


		statement_n_rows = "SELECT COUNT(*) FROM global_measurement_overview ;".format(uuid)

		cur_rem.execute(statement_n_rows)
		res_rem = cur_rem.fetchone()
		cur_loc.execute(statement_n_rows)
		cur_loc = cur_loc.fetchone()

		# check includes also a neglect of the full table
		if res_rem[0] != res_loc[0]:
