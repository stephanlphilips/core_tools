from core_tools.data.SQL.SQL_utility import text

from core_tools.data.SQL.SQL_common_commands import execute_statement, execute_query
from core_tools.data.SQL.SQL_common_commands import select_elements_in_table, insert_row_in_table, update_table
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

import datetime 

class alter_dataset:
	@staticmethod
	def update_name(uuid, name):
		conn = SQL_database_manager().conn_local
		update_table(conn, 'global_measurement_overview', ('exp_name', 'table_synchronized'), (text(name), False), condition = 'uuid = {}'.format(uuid))
		conn.commit()
	@staticmethod
	def star_measurement(uuid, state):
		conn = SQL_database_manager().conn_local
		update_table(conn, 'global_measurement_overview', ('starred', 'table_synchronized'), (state, False), condition = 'uuid = {}'.format(uuid))
		conn.commit()
class query_for_samples():
	@staticmethod
	def get_projects(set_up = None, sample = None):
		# get all projects for a selected set-up/sample (None is no selection)
		return query_for_samples.__get_x_given_yz('project', ('set_up', set_up), ('sample', sample))
	
	@staticmethod
	def get_set_ups(project = None, sample = None):
		#get all set ups for a selected project/sample (None is no selection)
		return query_for_samples.__get_x_given_yz('set_up', ('project', project), ('sample', sample))

	@staticmethod
	def get_samples(set_up = None, project = None):
		# get all samples for a selected project/set-up (None is no selection)
		return query_for_samples.__get_x_given_yz('sample', ('project', project), ('set_up', set_up))
	
	@staticmethod
	def __get_x_given_yz(to_get, condition_x, condition_y):
		
		statement = "SELECT DISTINCT {} from sample_info_overview ".format(to_get)

		if condition_x[1] is not None and condition_y[1] is not None:
			statement += "WHERE {} = '{}' and {} = '{}';".format(*condition_x, *condition_y)
		elif condition_x[1] is not None:
			statement += "WHERE {} = '{}' ;".format(*condition_x)
		elif condition_y[1] is not None:
			statement += "WHERE {} = '{}' ;".format(*condition_y)
		else:
			statement += ";"

		cur = SQL_database_manager().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		result = set(sum(res, () ))
		cur.close()

		cur = SQL_database_manager().conn_remote.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		result |= set(sum(res, () ))
		cur.close()
		return list(result)

class query_for_measurement_results:
	def get_results_for_date(date, sample, set_up, project):
		statement = "SELECT id, uuid, exp_name, start_time, project, set_up, sample, starred, keywords FROM global_measurement_overview "
		statement += "WHERE start_time >= '{}' and start_time < '{} '".format(date, date+ datetime.timedelta(1))
		if sample is not None:
			statement += " and sample =  '{}' ".format(sample)
		if set_up is not None:
			statement += " and set_up = '{}' ".format(set_up)
		if project is not None:
			statement += " and project = '{}' ".format(project)
		statement += " ;"

		
		cur = SQL_database_manager().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()

		return res

	def get_all_dates_with_meaurements(project, set_up, sample):
		statement = "SELECT DISTINCT date_trunc('day', start_time) FROM global_measurement_overview "
		statement += "where 1=1 "
		if sample is not None:
			statement += " and sample =  '{}' ".format(sample)
		if set_up is not None:
			statement += " and set_up = '{}' ".format(set_up)
		if project is not None:
			statement += " and project = '{}' ".format(project)
		statement += ';'

		cur = SQL_database_manager().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()
		
		res = list(sum(res, ()))
		res.sort(reverse=True)
		
		return res

	def search_query(exp_id, uuid, words, start_date, stop_date, project, set_up, sample):
		statement = "SELECT id, uuid, exp_name, start_time, project, set_up, sample, keywords FROM global_measurement_overview "
		statement += "WHERE 1=1 "
		if exp_id is not None:
			statement += " and id = '{}' ".format(exp_id)
		if uuid is not None:
			statement += " and uuid = '{}' ".format(uuid)
		if start_date is not None:
			statement += " and start_time = '{}' ".format(start_date)
		if stop_date is not None:
			statement += " and start_time = '{}' ".format(stop_date)
		if sample is not None:
			statement += " and sample =  '{}' ".format(sample)
		if set_up is not None:
			statement += " and set_up = '{}' ".format(set_up)
		if project is not None:
			statement += " and project = '{}' ".format(project)
		if words != "":
			statement += " and exp_name like '%{}%' ".format(words)
		statement += " ;"

		
		cur = SQL_database_manager().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()

		return m_result_overview(res)

	def detect_new_meaurements(n_records=0):
		statement = "SELECT count(*) from global_measurement_overview;"
		cur = SQL_database_manager().conn_local.cursor()
		cur.execute(statement)
		res = cur.fetchall()
		cur.close()

		update = False
		if res[0][0] != n_records:
			update =True
			n_records = res[0][0]

		return update, n_records
