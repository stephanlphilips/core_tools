from core_tools.data.name_validation import validate_data_identifier_value
from core_tools.data.SQL.connect import sample_info
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager
from core_tools.data.SQL.queries.dataset_creation_queries import sample_info_queries
from core_tools.startup.db_connection import is_connected

def set_sample_info(project=None, setup=None, sample=None):
    if project is None:
        project = sample_info.project
    else:
        validate_data_identifier_value(project)
    if setup is None:
        setup = sample_info.set_up
    else:
        validate_data_identifier_value(setup)
    if sample is None:
        sample = sample_info.sample
    else:
        validate_data_identifier_value(sample)
    sample_info(project, setup, sample)
    if is_connected():
        db_mgr = SQL_database_manager()
        if not db_mgr.SQL_conn_info_local.readonly:
            conn_local = db_mgr.conn_local
            sample_info_queries.add_sample(conn_local)
