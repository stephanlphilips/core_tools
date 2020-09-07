from data_storage_class cimport data_item, data_set_raw, measurement_overview_set, upload_mgr


class data_class:
	def __init__(self):
		self.id = None
		self.snapshot = None

		cdef data_set_raw __data_set_raw  = data_set_raw()
		self.__property_managment_list = []

	def __init_properties(self):
		# make easy_access_properties x,y,z, z1,z2, y2, ...
		pass

	def __generate_data_variables(self):
		pass

	def assign_raw_data_set(self, ds):
		pass


cdef class data_storage_manager:
	cdef upload_mgr *upload_manager

	def __cinit__(self, server_address, user_name, password, db_name):
		'''
		initializer the storage manager. Connect to the server

		Args:
			server_address (str) : adress of the server (e.g. "localhost" for a local database)
			username (str) : login credential to the database
			password (str) : password to log in to the database
			db_name (str) : name of the database where the experimental data is contained in
		'''
		self.upload_manager = new upload_mgr(server_address, user_name, password, db_name)

	def __dealloc__(self):
		del self.upload_manager

	def register_measurement(self, set_up, project, sample, exp_name):
		'''
		announce that a measurement will be made to the database.

		Args:
			set_up (str) : set up name
			project (str) : project running on this set up
			sample (str) : sample name
			exp_name (str) : name of the experiment
		'''

		# generate dataclass


		# make c representation of the dataclass

		# assign id.

		pass

	def start_upload_job(self, ds):
		'''
		will upload the measurement in a contingeous way to the server until is is completed.
		Args:
			ds (data_set) : will upload the measurement in DS until it flagged complete.
		'''

		pass

	def get_dataset(self, exp_run_id):
		'''
		get the dataset of a measrurement.

		Args:
			exp_run_id (int) : id of the dataset to get

		Returns:
			ds (data_set) : returned dataset
		'''
		pass
