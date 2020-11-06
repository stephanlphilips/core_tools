from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
from core_tools.data.gui.data_browser import data_browser

##################################################
# uncomment the option that is applicable to you #
##################################################

# in case you are only using a local server.
# set_up_local_storage('local_usernam', 'local_passwd', 
# 	'local_dbname', 'project_name', 'set_up_name', 'sample_name')

# in case you are only the remote server.
# set_up_remote_storage('ipaddr_rem_server', 5432, 
# 	'remote_usernam', 'remote_passwd', 'remote_dbname', 
# 	'project_name', 'set_up_name', 'sample_name')

# in case you are using both a local and remote server.
# set_up_local_and_remote_storage('ipaddr_rem_server', 5432,
# 	'local_usernam', 'local_passwd', 'local_dbname',
# 	'remote_usernam', 'remote_passwd', 'remote_dbname',
# 	'project_name', 'set_up_name', 'sample_name')

db = data_browser()