from core_tools.data.SQL.connector import set_up_local_storage,\
	set_up_remote_storage, set_up_local_and_remote_storage

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


# when you want to do sweeps
from core_tools.sweeps.sweeps import do0D, do1D, do2D

ds = do2D(param, start, stop, n_points, delay).run()

# see what is in the dataset
print(ds)

# inspecting data (extract arrays, labels, units):
x_data, y_data, z_data = ds.m1.x(), ds.m1.y(), ds.m1()
x_label, y_label, z_label = ds.m1.x.label, ds.m1.y.label, ds.m1.label
x_unit, y_unit, z_unit = ds.m1.x.unit, ds.m1.y.unit, ds.m1.unit

# when you want to plot a dataset
from core_tools.data.gui.plot_mgr import data_plotter
plot = data_plotter(ds)

# load a dataset by id or uuid
from core_tools.data.ds.data_set import load_by_id, load_by_uuid

ds = load_by_id(101)
