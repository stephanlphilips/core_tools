from core_tools.data.gui.data_browser_models.result_table_data_class import m_result_overview 
from core_tools.data.SQL.SQL_database_mgr import SQL_database_manager

import datetime

class query_for_samples():
	@staticmethod
	def get_set_ups(project = None, sample = None):
		'''
		get all the set ups for a selected project/sample (None is no selection)

		Args:
			project (str) : project to select from
			sample (str) : sample to select from
		'''
		return query_for_samples.get_x_given_yz('set_up', ('project', project), ('sample', sample))

	@staticmethod
	def get_projects(set_up = None, sample = None):
		'''
		get all the set ups for a selected project/sample (None is no selection)

		Args:
			set_up (str) : set_up to select from
			sample (str) : sample to select from
		'''
		return query_for_samples.get_x_given_yz('project', ('set_up', set_up), ('sample', sample))

	@staticmethod
	def get_samples(set_up = None, project = None):
		'''
		get all the set ups for a selected project/sample (None is no selection)

		Args:
			set_up (str) : set_up to select from
			project (str) : project to select from
		'''
		return query_for_samples.get_x_given_yz('sample', ('project', project), ('set_up', set_up))

	@staticmethod
	def get_x_given_yz(to_get, condition_x, condition_y):
		
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
		statement = "SELECT id, uuid, exp_name, start_time, project, set_up, sample, keywords FROM global_measurement_overview "
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

		return m_result_overview(res)

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

if __name__ == '__main__':
	
	from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage

	set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
	# s = query_for_samples.get_set_ups(project=None, sample=None)
	# print(s)
	# s = query_for_samples.get_projects(set_up=None, sample=None)
	# print(s)
	# s = query_for_samples.get_samples(set_up=None, project=None)
	# print(s)
	# s = query_for_samples.get_samples(set_up='6dot', project=None)
	# print(s)
	# import datetime
	# from datetime import date
	# my_date = date.fromisoformat('2020-10-05')
	# print()
	# current_date = datetime.datetime.now()
	# print(current_date - datetime.timedelta(hours=current_date.hour, minutes=current_date.minute,
 #    seconds=current_date.second, microseconds=current_date.microsecond) )
	# test_date = datetime.datetime.now()- datetime.timedelta(20)
	# a = query_for_measurement_results.get_results_for_date(test_date, sample=None, set_up=None, project='Intel Project', limit=1000)
	# print(a[0])
	# print(len(a))

	# a = query_for_measurement_results.get_all_dates_with_meaurements(sample=None, set_up=None, project='Intel Project')
	# print(a)

	# a = query_for_measurement_results.search_query(None, None, 'a', None, None, 'Intel Project', None, None)
	# print(a)
	# print(len(a))

	a = query_for_measurement_results.detect_new_meaurements()
	print(a)