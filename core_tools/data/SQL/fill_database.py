import random
import string
import time
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
from datetime import datetime

def get_random_string():
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(20))
    return result_str


def generate_random_times(n_exp):
	t1 = time.time()
	t0 = t1 - 9.154e6

	times_range = [random.uniform(t0, t1), random.uniform(t0, t1)]
	times_range.sort()

	times = []
	for i in range(n_exp):
		times += [random.uniform(times_range[0], times_range[1])]
	times.sort()

	return times

# code to be used for testing and benchamaring performance.

# populate database with ~800k items
projects_set_up_pairs = [[['Intel Project', 'dipstick'], ['Intel Project', 'F006'], ['Intel Project', 'V1'],],
						 [['Quantum sim', 'dipstick'], ['Quantum sim', 'V2'],],
						 [['Hybrid', 'VTI'], ['Hybrid', 'dipstick'], ['Hybrid', 'V3'],],
						 [['Horsridge', 'XLD2']],
						 [['6dot', 'dipstick'], ['6dot', 'XLD']],
						 [['2x2', 'dipstick'], ['2x2', 'V1'], ['2x2', 'V2']]
						]



print(projects_set_up_pairs)
n = 0
import psycopg2
from core_tools.data.SQL.SQL_commands import write_query_generator
from core_tools.data.SQL.SQL_database_mgr import SQL_database_manager

set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample_name')
SQL_database_manager()


conn_local = psycopg2.connect(dbname=SQL_conn_info_local.dbname, user=SQL_conn_info_local.user, 
					password=SQL_conn_info_local.passwd, host=SQL_conn_info_local.host, port=SQL_conn_info_local.port)
cur = conn_local.cursor()
for p_s_multi in projects_set_up_pairs:

	n_samples = random.randint(10, 40)
	for n_samples in range(n_samples):
		sample_name = 'SQ' + str(random.randint(10000000, 100000000))
		for project, set_up in p_s_multi:
			set_up_local_storage('stephan', 'magicc', 'test', project, set_up, sample_name)
			
			n_measurements = random.randint(100, 3000)
			times = generate_random_times(n_measurements)
			t1 = time.time()
			for i in range(n_measurements):
				n += 1
				name = get_random_string()
		
				cur.execute(write_query_generator.write_data_overview_tables(sample_info.set_up, sample_info.project, sample_info.sample))
				cur.execute(write_query_generator.insert_new_measurement_in_measurement_table(name, SQL_conn_info_local.user))

				cur.execute(write_query_generator.get_last_meas_id_in_measurement_table())
				exp_id, exp_uuid = cur.fetchone()
				
				exp_id = exp_id
				exp_uuid = exp_uuid
				running = True
				SQL_datatable = "_" + sample_info.set_up + "_" +sample_info.project + "_" +sample_info.sample +"_" + str(exp_uuid)

				# todo -- add tags to the measurements
				cur.execute(write_query_generator.fill_meas_info_in_measurement_table(
					exp_uuid,SQL_datatable,
					times[i]))
				time.sleep(0.001)
			
			conn_local.commit()
			t2 = time.time()
			print(project, set_up, sample_name, 'time per line {}'.format((t2-t1)/n_measurements))
cur.close()

print(n)

# print(random.randint(10, 100))