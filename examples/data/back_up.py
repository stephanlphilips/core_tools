from core_tools.data.SQL.connector import set_up_local_and_remote_storage
from core_tools.data.SQL.SQL_synchronization_manager import sync_agent

##############################################
# only in case of remote and local server!!! #
##############################################

set_up_local_and_remote_storage('ipaddr_rem_server', 5432,
	'local_usernam', 'local_passwd', 'local_dbname',
	'remote_usernam', 'remote_passwd', 'remote_dbname',
	'project_name', 'set_up_name', 'sample_name')

db = sync_agent()