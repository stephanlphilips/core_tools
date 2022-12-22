
from core_tools.startup.db_connection import connect_local_and_remote_db
from core_tools.startup.sample_info import set_sample_info
from core_tools.startup.app_wrapper import run_app
from core_tools.data.SQL.SQL_connection_mgr import SQL_sync_manager


def sync_init():
    set_sample_info('Any', 'Any', 'Any')
    connect_local_and_remote_db()
    print('Starting DB sync')


def sync_main():
    SQL_sync_manager().run()


if __name__ == '__main__':
    run_app('db_sync', sync_init, sync_main)
