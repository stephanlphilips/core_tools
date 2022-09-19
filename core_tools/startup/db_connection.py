from core_tools.data.SQL.connect import (
        SQL_conn_info_local,
        SQL_conn_info_remote,
        )
from core_tools.data.SQL.queries.dataset_gui_queries import query_for_samples

from .config import get_configuration

_connected = False

def connect_local_db(readonly=False):
    _config_local_db(readonly)
    _connect()

def connect_remote_db(readonly=False):
    _config_remote_db(readonly)
    _connect()

def connect_local_and_remote_db(readonly=False):
    _config_local_db(readonly)
    _config_remote_db(readonly)
    _connect()

def is_connected():
    return _connected

def _config_remote_db(readonly):
    cfg = get_configuration()
    user = cfg['remote_database.user']
    passwd = cfg['remote_database.password']
    dbname = cfg['remote_database.database']
    address = cfg['remote_database.address']
    host,port = address.split(':')
    SQL_conn_info_remote(host, int(port),
                         user, passwd, dbname,
                         readonly)

def _config_local_db(readonly):
    cfg = get_configuration()
    user = cfg['local_database.user']
    passwd = cfg['local_database.password']
    dbname = cfg['local_database.database']
    SQL_conn_info_local('localhost', 5432,
                        user, passwd, dbname,
                        readonly)

def _connect():
    global _connected
    try:
        # Querying automatically tries to connect to both connections.
        query_for_samples.get_projects()
        _connected = True
    except:
        raise