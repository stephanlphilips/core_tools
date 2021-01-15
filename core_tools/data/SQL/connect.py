'''
definition of storage locations and initializer for storage.
'''

class SQL_descriptor(object):
	def __init__(self, required=False):
		self.val = None
	
	def __set__(self, obj, val):
		self.val = val

	def __get__(self, obj, objtype):
		if self.val is None:
			raise ConnectionError('No sample information provided\n\n** Please check the docs (set up section). \n\n')
		return self.val

class sample_info:
	project = SQL_descriptor(True)
	set_up = SQL_descriptor(True)
	sample = SQL_descriptor(True)

	def __init__(self, project, set_up, sample):
		sample_info.project = project
		sample_info.set_up = set_up
		sample_info.sample = sample


class conn_info_descriptor:
	def __set_name__(self, owner, name):
		setattr(owner,'__'+name, None)
		self.name = '__' + name
		self.owner = owner

	def __set__(self, obj, val):
		setattr(self.owner, self.name, val)

	def __get__(self, obj, objtype):
		if getattr(self.owner, self.name) is None:
			if objtype is SQL_conn_info_local:
				val =  getattr(SQL_conn_info_remote, self.name)
			elif objtype is SQL_conn_info_remote:
				val =  getattr(SQL_conn_info_local, self.name)
			
			if val is None:
				raise ConnectionError('Nor a localcal server/remote server, please check the set up section of the dataset documentation.')
			
			return val

		return objtype.__dict__[self.name]


'''
if one of the two connection object is not configured it will automatically fall back to the other one.
'''
class SQL_conn_info_local:
	host = conn_info_descriptor()
	port = conn_info_descriptor()
	user = conn_info_descriptor()
	passwd = conn_info_descriptor()
	dbname = conn_info_descriptor()

	def __init__(self, host, port, user, passwd, dbname):
		self.host = host
		self.port = port
		self.user = user
		self.passwd = passwd
		self.dbname = dbname

class SQL_conn_info_remote:
	host = conn_info_descriptor()
	port = conn_info_descriptor()
	user = conn_info_descriptor()
	passwd = conn_info_descriptor()
	dbname = conn_info_descriptor()

	def __init__(self, host, port, user, passwd, dbname):
		self.host = host
		self.port = port
		self.user = user
		self.passwd = passwd
		self.dbname = dbname


def set_up_local_storage(user, passwd, dbname, project, set_up, sample):
	'''
	Set up the specification for the datastorage needed to store/retrieve measurements.
	
	Args:
		user (str) : name of the user to connect with
		passwd (str) : password of the user
		dbname (str) : database to connect with (e.g. 'vandersypen_data')

		project (str) : project for which the data will be saved
		set_up (str) : set up at which the data has been measured
		sample (str) : sample name 
	'''
	SQL_conn_info_local('localhost', 5432, user, passwd, dbname)
	sample_info(project, set_up, sample)

def set_up_remote_storage(host, port, user, passwd, dbname, project, set_up, sample):
	'''
	Set up the specification for the datastorage needed to store/retrieve measurements.
	
	Args:
		host (str) : host that is used for storage, e.g. "localhost" for local or "spin_data.tudelft.nl" for global storage
		port (int) : port number to connect through, the default it 5432
		user (str) : name of the user to connect with
		passwd (str) : password of the user
		dbname (str) : database to connect with (e.g. 'vandersypen_data')

		project (str) : project for which the data will be saved
		set_up (str) : set up at which the data has been measured
		sample (str) : sample name 
	'''
	SQL_conn_info_remote(host, port, user, passwd, dbname)
	sample_info(project, set_up, sample)

def set_up_local_and_remote_storage(host, port, 
									user_local, passwd_local, dbname_local,
									user_remote, passwd_remote, dbname_remote,
									project, set_up, sample):
	'''
	Set up the specification for the datastorage needed to store/retrieve measurements.
	
	Args:
		host (str) : host that is used for storage, e.g. "localhost" for local or "spin_data.tudelft.nl" for global storage
		port (int) : port number to connect through, the default it 5432
		
		user_local (str) : [local server] name of the user to connect with
		passwd_local (str) : [local server] password of the user
		dbname_local (str) : [local server] database to connect with (e.g. 'vandersypen_data')
		
		user_remote (str) : [remote server] name of the user to connect with
		passwd_remote (str) : [remote server] password of the user
		dbname_remote (str) : [remote server] database to connect with (e.g. 'vandersypen_data')

		project (str) : project for which the data will be saved
		set_up (str) : set up at which the data has been measured
		sample (str) : sample name 
	'''
	SQL_conn_info_local('localhost', 5432, user_local, passwd_local, dbname_local)
	SQL_conn_info_remote(host, port, user_remote, passwd_remote, dbname_remote)
	sample_info(project, set_up, sample)