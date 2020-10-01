'''
definition of storage locations and initializer for storage.
'''

class SQL_descriptor(object):
	def __init__(self, descr):
		self.val = descr
	
	def __set__(self, obj, val):
		self.val = val

	def __get__(self, obj, objtype):
		if self.val is None:
			raise ConnectionError('SQL server connection not initialized\n\n\
please run the folowing code:\n\n\
from core_tools.data.SQL.connector import set_up_data_storage \n\
set_up_data_storage(mydataserver.tudelft.nl, 5432, username, passwd, "5 dot spin qubit QC", "XLD" ,"the_one_to_rule_them_all")\n\n')
		return self.val

class sample_info:
	project = SQL_descriptor(None)
	set_up = SQL_descriptor(None)
	sample = SQL_descriptor(None)

	def __init__(self, project, set_up, sample):
		sample_info.project = project
		sample_info.set_up = set_up
		sample_info.sample = sample

class SQL_conn_info:
	host = SQL_descriptor(None)
	port = SQL_descriptor(None)
	user = SQL_descriptor(None)
	passwd = SQL_descriptor(None)
	dbname = SQL_descriptor(None)

	def __init__(self, host, port, user, passwd, dbname):
		SQL_conn_info.host = host
		SQL_conn_info.port = port
		SQL_conn_info.user = user
		SQL_conn_info.passwd = passwd
		SQL_conn_info.dbname = dbname


def set_up_data_storage(host, port, user, passwd, dbname, project, set_up, sample):
	'''
	Set up the specification for the datastorage needed to store/retrieve measurements.
	
	Args:
		host (str) : host that is used for storage, e.g. "localhost" for local or "spin_data.tudelft.nl" for global storage
		port (int) : port number to connect through, the default it 5421
		user (str) : name of the user to connect with
		passwd (str) : password of the user
		dbname (str) : database to connect with (e.g. 'vandersypen_data')

		project (str) : project for which the data will be saved
		set_up (str) : set up at which the data has been measured
		sample (str) : sample name 
	'''
	SQL_conn_info(host, port, user, passwd, dbname)
	sample_info(project, set_up, sample)

