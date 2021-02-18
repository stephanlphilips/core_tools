from core_tools.data.SQL.connect import set_up_local_and_remote_storage
from core_tools.data.SQL.SQL_connection_mgr import SQL_sync_manager

##############################################
# only in case of remote and local server!!! #
##############################################

set_up_local_and_remote_storage('ipaddr_rem_server', 5432,
	'local_usernam', 'local_passwd', 'local_dbname',
	'remote_usernam', 'remote_passwd', 'remote_dbname',
	'project_name', 'set_up_name', 'sample_name')

set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
        'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')

db = SQL_sync_manager()
db.run()