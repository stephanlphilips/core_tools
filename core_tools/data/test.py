import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="test",
    user="stephan",
    password="magicc")

# write_tests for measurements

def clear(conn):
	'''
	clear all data from the database
	'''
	cmd = 'create table data_saver_test (id int, npt_tot int, n_written int, data largeobjec)'


def create(conn):
	pass

def save_measurements(conn, size):
	'''
	save a empty dataset to the server with size size.
	''' 
	pass


def load_measurement(conn, id):
	pass

