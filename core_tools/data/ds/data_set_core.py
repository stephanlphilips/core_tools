from core_tools.data.ds.data_set_DataMgr import m_param_origanizer, dataset_data_description
from core_tools.data.SQL.SQL_dataset_creator import SQL_dataset_creator

import datetime
import string
import time

class data_set_desciptor(object):
    def __init__(self, variable, is_time=False, is_JSON=False):
        self.var = variable
        self.is_time = is_time
        self.is_JSON = is_JSON

    def __get__(self, obj, objtype):
        value = getattr(getattr(obj,"_data_set__data_set_raw"), self.var)
        if self.is_time:
            return datetime.datetime.fromtimestamp(value)

        return value

class data_set:
    completed = data_set_desciptor('completed')

    dbname = data_set_desciptor('dbname')
    table_name = data_set_desciptor('SQL_table_name')
    name = data_set_desciptor('exp_name')

    exp_id = data_set_desciptor('exp_id')
    exp_uuid = data_set_desciptor('exp_uuid')
    exp_name = data_set_desciptor('exp_name')

    project = data_set_desciptor('project')
    set_up = data_set_desciptor('set_up')
    sample_name = data_set_desciptor('sample')

    metadata = data_set_desciptor('metadata')
    snapshot = data_set_desciptor('snapshot')
    keywords = data_set_desciptor('keywords')

    run_timestamp = data_set_desciptor('UNIX_start_time', is_time=True)
    run_timestamp_raw = data_set_desciptor('UNIX_start_time')
    completed_timestamp = data_set_desciptor('UNIX_stop_time', is_time=True)
    completed_timestamp_raw = data_set_desciptor('UNIX_stop_time')

    def __init__(self, ds_raw):
        self.id = None
        self.__data_set_raw = ds_raw
        self.__repr_attr_overview = []
        self.__init_properties(m_param_origanizer(ds_raw.measurement_parameters_raw))
        self.last_commit = time.time()

    def __len__(self):
        return len(self.__repr_attr_overview)

    def __getitem__(self, i):
        if isinstance(i, str):
            return self(i)

        return self.__repr_attr_overview[i]

    def __init_properties(self, data_set_content):
        '''
        populates the dataset with the measured parameter in the raw dataset

        Args:
            data_set_content (m_param_origanizer) : m_param_raw raw objects in their mamagement object
        '''
        m_id = data_set_content.get_m_param_id()

        for i in range(len(m_id)): #this is not pretty.
            n_sets = len(data_set_content[m_id[i]])
            repr_attr_overview = []
            for j in range(n_sets):
                ds_descript = dataset_data_description('', data_set_content.get(m_id[i],  j), data_set_content)

                name = 'm' + str(i+1) + "_" + str(j+1)
                setattr(self, name, ds_descript)

                if j == 0:
                    setattr(self, 'm' + str(i+1), ds_descript)

                if j == 0 and n_sets==1: #consistent printing
                    repr_attr_overview += [('m' + str(i+1), ds_descript)]
                    ds_descript.name = 'm' + str(i+1)
                else:
                    repr_attr_overview += [(name, ds_descript)]
                    ds_descript.name = name

            self.__repr_attr_overview += [repr_attr_overview]

    def __call__(self, label_variable):
        '''
        extract a meaurement by its label
        '''
        for minstr in self.__repr_attr_overview:
            for var_meas in minstr:
                if var_meas[1].label == label_variable or var_meas[1].name == label_variable:
                    return var_meas[1]

        raise ValueError(f'Unable to find \'{label_variable}\' in ds with id :{self.exp_id}')

    def add_result(self, input_data):
        '''
        Add results to the dataset

        Args:
            input_data (dict<int, list<np.ndarray>>) : dict with as key the id of the measured parameter and the data that is measured.
        '''
        for m_param in self.__data_set_raw.measurement_parameters:
            if m_param.id_info in input_data.keys():
                m_param.write_data(input_data)

        self.__write_to_db()

    def mark_completed(self):
        '''
        mark dataset complete. Stop updating the database and allow garbage collector to release memory.
        '''
        self.__data_set_raw.completed = True
        self.__write_to_db(True)
        SQL_ds_creator = SQL_dataset_creator()
        SQL_ds_creator.finish_measurement(self.__data_set_raw)

    def sync(self):
        '''
        Updates dataset in case only part of the points were downloaded.
        '''
        if self.completed == False:
            SQL_ds_creator = SQL_dataset_creator()
            self.completed = SQL_ds_creator.is_completed(self.exp_uuid)
            self.__data_set_raw.sync_buffers()

    def __write_to_db(self, force = False):
        '''
        update values every 200ms to the database.

        Args:
            force (bool) : enforce the update
        '''
        current_time = time.time()
        if current_time - self.last_commit > 0.2 or force==True:
            self.last_commit=current_time

            self.__data_set_raw.sync_buffers()
            SQL_ds_creator = SQL_dataset_creator()
            SQL_ds_creator.update_write_cursors(self.__data_set_raw)

    def __repr__(self):
        output_print = "DataSet :: {}\n\nid = {}\nuuid = {}\n\n".format(self.name, self.exp_id, self.exp_uuid)
        output_print += "| idn             | label           | unit     | size                     |\n"
        output_print += "---------------------------------------------------------------------------\n"
        for i in self.__repr_attr_overview:
            for j in i:
                output_print += j[1].__repr__()
                output_print += "\n"

        output_print += "set_up : {}\n".format(self.set_up)
        output_print += "project : {}\n".format(self.project)
        output_print += "sample_name : {}\n".format(self.sample_name)
        return output_print