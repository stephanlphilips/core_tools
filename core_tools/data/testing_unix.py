import psycopg2
import numpy as np
conn = psycopg2.connect("dbname=test user=stephan")
cur = conn.cursor()

conn.commit()

from core_tools.data.SQL.connector import sample_info
from core_tools.data.SQL.connector import set_up_data_storage


set_up_data_storage('localhost', 5432, 'stephan', 'magicc', 'test', 'project', 'set_up', 'sample')


def insert_new_measurement_in_overview_table(exp_name):
		statement = "INSERT INTO measurements_overview "
		statement += "(set_up, project, sample, exp_name) VALUES ('"
		statement += str(sample_info.set_up) + "', '"
		statement += str(sample_info.project) + "', '"
		statement += str(sample_info.sample) + "', '"
		statement += exp_name + "');"
		return statement

def get_last_meas_id_in_overview_table():
		return "SELECT MAX(id) FROM measurements_overview;" 

stmt = get_last_meas_id_in_overview_table()
cur.execute(stmt)
print(cur.fetchone()[0])
conn.commit()
