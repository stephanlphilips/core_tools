from core_tools.data.SQL.connector import SQL_conn_info_local, set_up_remote_storage, sample_info, set_up_local_storage
from core_tools.data.ds.data_set import load_by_id, load_by_uuid


# set_up_local_storage('stephan', 'magicc', 'test', "6dot", "XLD", "6D3S - SQ20-20-5-18-4")

set_up_remote_storage('131.180.205.81', 5432, 'stephan_test', 'magicc', 'spin_data_test', "6dot", "XLD", "6D3S - SQ20-20-5-18-4")
ds = load_by_uuid(1604569867541234729)

print(ds)
print(ds.m1()[:,50])
print(ds.m1.x.full()[:,50])
print(ds.m1.y.full()[:,50])