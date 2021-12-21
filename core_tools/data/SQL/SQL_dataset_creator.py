from core_tools.data.SQL.queries.dataset_creation_queries import sample_info_queries, measurement_overview_queries, data_table_queries
from core_tools.data.SQL.queries.dataset_loading_queries import load_ds_queries
from core_tools.data.SQL.queries.dataset_sync_queries import sync_mgr_queries

from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

import time

class SQL_dataset_creator(object):
    def __init__(self):
        self.conn = SQL_database_manager().conn_local

    def register_measurement(self, ds):
        '''
        Args:
            ds (data_set_raw) : raw dataset
        '''
        #####################################################
        # add a new entry in the measurements overiew table #
        #####################################################
        sample_info_queries.add_sample(self.conn)
        ds.exp_id, ds.exp_uuid, ds.SQL_datatable = measurement_overview_queries.new_measurement(self.conn, ds.exp_name)
        ds.running = True
        ds.UNIX_start_time = time.time()

        print('\nStarting measurement with id : {}\n'.format(ds.exp_id))

        measurement_overview_queries.update_measurement(self.conn, ds.exp_uuid, ds.SQL_datatable,
            start_time=ds.UNIX_start_time, metadata=ds.metadata, snapshot=ds.snapshot, keywords=ds.generate_keywords())

        #################################################
        # make table for storage of the getters/setters #
        #################################################
        data_table_queries.generate_table(self.conn, ds.SQL_datatable)

        for m_param in ds.measurement_parameters_raw:
            data_table_queries.insert_measurement_spec_in_meas_table(self.conn, ds.SQL_datatable, m_param)

        self.conn.commit()

    def update_write_cursors(self, ds):
        '''
        update the write_cursors to the current position and commit the cached (measured) data.

        Args:
            ds (dataset_raw)
        '''
        data_table_queries.update_cursors_in_meas_tab(self.conn, ds.SQL_datatable, ds.measurement_parameters_raw)
        measurement_overview_queries.update_measurement(self.conn, ds.exp_uuid, data_synchronized=False)
        self.conn.commit()

    def is_completed(self, exp_uuid):
        '''
        checks if the current measurement is still running

        Args:
            exp_uuid (int) : uuid of the experiment to check
        '''
        return measurement_overview_queries.is_completed(self.conn, exp_uuid)

    def finish_measurement(self, ds):
        '''

        register the mesaurement as finished in the database.

        Args:
            ds (dataset_raw)
        '''
        ds.UNIX_stop_time = time.time()

        data_table_queries.update_cursors_in_meas_tab(self.conn, ds.SQL_datatable, ds.measurement_parameters_raw)
        measurement_overview_queries.update_measurement(self.conn, ds.exp_uuid,
            stop_time=ds.UNIX_stop_time, completed=True, data_size=ds.size(), data_synchronized=False)

        self.conn.commit()

        # close the connection with the buffer to the database
        for data_item in ds.measurement_parameters_raw:
            data_item.data_buffer.close()

    def fetch_raw_dataset_by_Id(self, exp_id):
        '''
        assuming here used want to get a local id

        Args:
            exp_id (int) : id of the measurment you want to get
        '''
        if load_ds_queries.check_id(self.conn, exp_id) == False:
            raise ValueError("The id {}, does not exist in this database.".format(exp_id))

        uuid = load_ds_queries.id_to_uuid(self.conn, exp_id)

        return self.fetch_raw_dataset_by_UUID(uuid)

    def fetch_raw_dataset_by_UUID(self, exp_uuid, sync2local=False):
        '''
        Try to find a measurement with the corresponding uuid

        Args:
            exp_uuid (int) : uuid of the measurment you want to get
            sync2local (bool): sync measurement to local database
        '''
        sync = False
        if load_ds_queries.check_uuid(self.conn, exp_uuid):
            conn = self.conn
        elif load_ds_queries.check_uuid(SQL_database_manager().conn_remote, exp_uuid):
            conn = SQL_database_manager().conn_remote
            sync = sync2local
        else:
            raise ValueError("the uuid {}, does not exist in the local/remote database.".format(exp_uuid))

        ds_raw = load_ds_queries.get_dataset_raw(conn, exp_uuid)
        if sync:
            conn_mgr = SQL_database_manager()
            sync_mgr_queries.sync_raw_data(conn_mgr, exp_uuid, to_local=True)
            sync_mgr_queries.sync_table(conn_mgr, exp_uuid, to_local=True)

        return ds_raw

if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project', 'test_set_up', 'test_sample')
    # set_up_local_and_remote_storage('131.180.205.81', 5432, 'stephan', 'magicc', 'test',
    #     'stephan_test', 'magicc', 'spin_data_test', 'test_project', 'test_set_up', 'test_sample')
    ds_creator = SQL_dataset_creator()

    ds_creator.fetch_raw_dataset_by_Id(71)