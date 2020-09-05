SET_UP = None
PROJECT = None
SAMPLE = None

DB_LOCATION = None
USERNAME = None
PASSWD = None

def set_data_saver_info(set_up, project, sample, db_location, username, passwd):
	SET_UP = set_up
	PROJECT = project
	SAMPLE = sample
	DB_LOCATION = db_location
	USERNAME = username
	PASSWD = passwd

	# here -- test connection to db -- throw error if there is problem.