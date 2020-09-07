from core_tools.job_mgnt.calibrations.data.calibration_parameter import CalibrationParameter
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List
import numpy as np
import sqlite3
import time


def return_std_paramters():
    parameters = list()
    parameters.append(CalibrationParameter('id', unit='#'))
    parameters.append(CalibrationParameter('start_time', label='start time', unit='s'))
    parameters.append(CalibrationParameter('end_time', label='end time', unit='s'))
    parameters.append(CalibrationParameter('success', unit='boolean'))

    return parameters


class sqlite_where_mgr():
    def __init__(self):
        self.commands = list()

    def __add__(self, other):
        self.commands += [other]
        return self

    def __len__(self):
        return len(self.commands)

    def get_cmd(self):
        cmd = ''
        for my_cmd in self.commands:
            cmd += my_cmd + ' AND '

        return cmd[:-5]

@dataclass
class my_query:
    where : sqlite_where_mgr = sqlite_where_mgr()
    columns_to_fetch : List = field(default_factory=list)
    order_by : str = 'end_time DESC'
    limit : int = 50

    def reset(self):
        '''
        resets the query back to default setings
        '''
        self.where = sqlite_where_mgr()
        self.order_by = 'end_time DESC'
        self.columns_to_fetch = list()
        self.limit = 50

    def generate_query(self, table_name):
        column_names = ''
        column_names_set = list(set(self.columns_to_fetch))
        for column in column_names_set:
            column_names += column + ', '
        column_names = column_names[:-2]

        if len(column_names) == 0:
            raise ValueError('query failed, no column selected.')

        cmd = 'SELECT {} FROM {}\n'.format(column_names,table_name)

        if len(self.where) > 0:
            cmd += 'WHERE {} \n'.format(self.where.get_cmd())
        
        cmd += 'ORDER BY {}\nLIMIT {};'.format(self.order_by,self.limit)

        return cmd, column_names_set

class querier():
    '''
    class that can be used to make SQL queries for parameters.
    '''
    def __init__(self, data_mgr, cal_object):
        self.data_mgr = data_mgr
        self.my_query =  my_query()

        db_paramters = return_std_paramters()
        db_paramters += cal_object.set_vals.get_param() + cal_object.get_vals.get_param()

        for param in db_paramters:
            param.add_queryclass(self.my_query)
            setattr(self, param.name, param)

        self.query = my_query()

    def n_results(self, n):
        '''
        Specify the number of results
        
        Args:
            n (int) : number of results to fetch, default is 50
        '''
        self.my_query.limit = n

    def get(self):
        cmd, variables = self.my_query.generate_query(self.data_mgr.table_name)
        data = self.data_mgr._query_db(cmd)

        return data_obj(self,variables, data)

class my_write:
    '''
    descriptor for a write object
    '''
    def __init__(self, name, data_mgr):
        self.name = name
        self.data_mgr = data_mgr
        self.value = None
    def __get__(self, obj, objtype):
        return self.value

    def __set__(self, obj, value):
        self.value = value
        self.data_mgr._write(self.name, value)

class writer():
    '''
    class to prefrom a write to the database
    '''
    def __init__(self, data_mgr, cal_object):
        self.data_mgr = data_mgr

        db_paramters = return_std_paramters()
        db_paramters += cal_object.set_vals.get_param() + cal_object.get_vals.get_param()

        for param in db_paramters:
            setattr(self, param.name, my_write(param.name, self.data_mgr))

        self.query = my_query()

    def commit(self, success =  True):
        '''
        commit a write to the database
        '''
        self.data_mgr.finish_data_entry(success)


class data_obj():
    '''
    data object that generated at the end of a query, to easily access the data
    '''
    def __init__(self, query_obj, variables, query_result):
        self.variables = dict()

        for variable_idx in range(len(variables)):
            variable = variables[variable_idx]
            self.variables[variable] = getattr(query_obj, variable)
            
            data = np.zeros([len(query_result)])
            for i in range(data.size):
                data[i] = query_result[i][variable_idx]
            setattr(self, variable, data)

    def __repr__(self):
        representation = 'Data present in this object :: \n\n'
        for variable in self.variables.keys():
            representation += '\t{}\n'.format(variable)

        return representation

    def plot(self, A, B):
        '''
        plot two variables in the data object. 

        Args:
            A (str) : name of the variable on the X axis
            B (str) : name of the variable on the Y axis
        '''
        data_a = getattr(self, A)
        plot_info_a = self.variables[A]
        data_b = getattr(self, B)
        plot_info_b = self.variables[B]

        plt.plot(data_a, data_b)
        plt.show()