import threading as th
import time, logging, importlib, os, time
import inspect
import os
import sqlite3
from datetime import datetime

class CalibrationMaster():
    # Parent class for all the calibration classes.
    def __init__(self):
        # init values: set in such a way they will not result in a function call.

        # zero means infinity 
        self.update_time_interval = 0 # sec
        self.number_of_meas_run_before_update = 0
        self.run_before_exp = False
        self.execute_during_exp = False
        self.execure_during_idle = False

        self.libraries = None
        self.my_qubit = None
        self.calibration_params = []
        self.table_name = self.__class__.__name__
        self.table_name_unit = self.__class__.__name__ + '_units'

        self.   = []
        
        # database object 
        self.my_database = None
    
    def __connect(self):
        # Get path where the database is saved.
        module_location = inspect.getmodule(self).__file__
        filename_db = os.path.splitext(module_location)[0] + '.sqlite'
        # connect to your database
        db = sqlite3.connect(filename_db)
        cursor = db.cursor()
        return db, cursor

    def __exec_command(self,cmd):
        # Execute command in the database.
        # INPUT ::
        #   cmd (str) :: command you want to execute in the database.
        # returns :: None
        db, cursor = self.__connect()
        cursor.execute(cmd)
        db.commit()
        db.close()

    def __query_db(self, cmd):
        # Aks for values in the database.
        # Execute command in the database.
        # INPUT ::
        #   cmd (str) :: command you want to execute in the database.
        # returns :: 
        #   [(,),] :: raw container with the data of your query
        db, cursor = self.__connect()
        cursor.execute(cmd)        
        mydata = cursor.fetchall()
        db.commit()
        db.close()
        return mydata

    def update_table(self):
        # function that will construct if not already there the database where the data will be saved. 
        # Note that is is no problem running this when no update is strictly needed (e.g. when you start up the module)
        # NOTE: that existing fields will not be updated. Use stash_table to rename it and create a new one if you want to do that.

        # Get data that needs to be saved.
        base_colomns = [('Time_human_readable','TEXT', 'a.u.')]
        all_colls = base_colomns + self.calibration_params

        # Connect to the database.
        db, cursor = self.__connect()

        # Check if table exists of data
        cursor.execute("select count(*) from sqlite_master where type='table' and name='%s'"% self.table_name)
        exists = True if cursor.fetchall()[0][0]==1 else False

        if not exists:
            cursor.execute('CREATE TABLE %s (time DOUBLE PRIMARY KEY)' %self.table_name)
            cursor.execute('CREATE TABLE %s (varname TEXT, unit TEXT)' %(self.table_name + '_units'))
            cursor.execute("INSERT INTO %s VALUES ('%s', '%s')" % (self.table_name + '_units', 'time', 's'))

        # Get current columns in the data base:
        cursor.execute("PRAGMA table_info('%s')"%self.table_name)
        db_colomn_info = cursor.fetchall()
        db_colomn_names= [i[1].lower() for i in db_colomn_info]
        # Check if all the wanted coloms are there (suppose users made up their mind about the datype they want to use...)

        columms_to_add = [i for i in all_colls if i[0].lower() not in db_colomn_names]

        # Add missing colomn to table
        for i in columms_to_add:
            cursor.execute("ALTER TABLE %s ADD COLUMN '%s' %s" % (self.table_name, i[0], i[1]))
            cursor.execute("INSERT INTO %s VALUES ('%s', '%s')" % (self.table_name + '_units', i[0], i[2]))

        # commit changes
        db.commit()
        # Close conn
        db.close()

    def stash_table(self):
        # e.g. when you make a new sample.
        # save to self.table_name.date
        # Check if the table has the right entries.
        time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
        db, cursor = self.__connect()
        cursor.execute("ALTER TABLE %s RENAME TO %s"%(self.table_name, self.table_name + '_' + time))
        cursor.execute("ALTER TABLE %s RENAME TO %s"%(self.table_name+ '_units', self.table_name + '_units' + '_' + time))
        db.commit()
        db.close()

    def delete_table(self):
        # Delete the current table.
        db, cursor = self.__connect()
        cursor.execute("DROP TABLE %s"% self.table_name)
        cursor.execute("DROP TABLE %s"% (self.table_name + '_units'))
        db.commit()
        db.close()

    def get_all_parameter_names(self):
        # Get all the parameters that are currently in use. Note that SQLite is case insensitive.
        db, cursor = self.__connect()
        cursor.execute("PRAGMA table_info('%s')"%self.table_name)
        db_colomn_info = cursor.fetchall()
        db_colomn_names= [i[1].lower() for i in db_colomn_info]
        db.close()
        return db_colomn_names

    def save_calib_results(self, data_tuple):
        # saves the data_tuple to database, if you give a variable that not exist, this will will be discarded
        # TODO tell when people feed garbage.
        # data_tuple :: format :: [(var_name, value)]
        # returns :: None.
        if type(data_tuple) != type(list()):
            data_tuple = [data_tuple]

        fields =  self.get_all_parameter_names()

        to_upload = []
        for i in fields:
            var_found = False
            if i == 'time':
                to_upload.append(time.time())
                continue
            if i == 'time_human_readable':
                to_upload.append(datetime.now().strftime("'%Y/%m/%d-%H:%M:%S'"))
                continue
            for j in data_tuple:
                if i == j[0].lower():
                    to_upload.append(j[1])
                    var_found = True
                    break

            if var_found==False:
                to_upload.append('null')

        cmd = 'INSERT INTO %s VALUES ('%self.table_name
        for i in to_upload:
            cmd += str(i) + ','
        cmd = cmd[:-1]
        cmd += ')'

        self.__exec_command(cmd)

    def do_calib(self, num_exp_run = 0, starting_exp=False):
        # Function to ask weather to do or not to do a calibration, opt input number_of_exp_run
        # Returns 
        #       True/False

        latest_query = self.__query_db('SELECT time FROM %s ORDER BY time DESC LIMIT 1'%self.table_name)
        if len(latest_query) == 0:
            latest_query = 0 # this is 1970
        else:
            latest_query = latest_query[0][0]

        if starting_exp == True and run_before_exp==True:
            return True

        if (num_exp_run > self.number_of_meas_run_before_update)and self.number_of_meas_run_before_update!=0:
            return True

        if time.time() - latest_query > self.update_time_interval:
            if num_exp_run > 1 and self.execute_during_exp == True:
                return True
            if num_exp_run ==0 and self.execure_during_idle== True:
                return True

        return False

    def calibrate(self, libraries, **kwargs):
        # Share libraries loaded in the job manager.
        # You should write this function yourself.
        self.libraries = libraries
        raise NotImplementedError()

    def make_qubit_dep_param(self, name, type, unit="a.u."):
        # construction function for properties that depend on one qubit.
        qubit_names = self.my_qubit.get_qubit_names()
        return [(name+'_'+i, type, unit) for i in qubit_names]

    def make_inter_qubit_param(self, name, type, unit="a.u."):
        # Generate names with qubit a,b where the order of a and b does not matter
        connected_qubits = self.my_qubit.get_interconnected_qubits()
        return [(name+'_'+i[0] + '_' + i[1], type, unit) for i in connected_qubits]

    def make_inter_qubit_param_directional(self, name, type, unit='a.u.'):
        # generate names with qubit a,b, where the order of a and b does matter.
        connected_qubits = self.my_qubit.get_interconnected_qubits()
        return [(name+'_'+i[0] + '_' + i[1], type) + (name+'_'+i[1] + '_' + i[0], type, unit) for i in connected_qubits] 

    def get_unit(self, param_name):
        # get unit of a parameter.
        # parameter_name: string or list of strings where the name is a variable of the class
        # return: format similar to input.
        try:
            if type(param_name) == str:
                return self.__query_db("SELECT unit FROM %s WHERE UPPER(varname)=UPPER('%s')"%(self.table_name_unit,param_name))[0][0]
            if type(param_name) == list:
                return [self.__query_db("SELECT unit FROM %s WHERE UPPER(varname)=UPPER('%s')"%(self.table_name_unit,i))[0][0]
                            for i in param_name]
        except:
            print('parameter name invalid ...')
            return None

    def get_parameter_latest(self, params=[], side_condition=[]):
        # returns array with wanted params, if no params given, all parameters of the last calibration will be returned
        # params = string or array of strings containing the wanted parameter. 
        # side_condition = tuple of values that should be set to a certain value (e.g)
        # return format:
        # list of dictionaries with field name, data and unit
        # Returns:
        #          Format of param input, return None if not found.

        input_is_str= False
        # safe typing
        if type(params) != list:
            params = [params]
            input_is_str = True


        # Construction of query
        cmd = 'SELECT MAX(time), '
        # param to select
        for i in params:
            cmd += i + ','
        cmd = cmd[:-1] + ' FROM %s '%self.table_name
        cmd += 'WHERE '
        for i in params:
            cmd += '%s IS NOT NULL AND '%i
        if len(side_condition) != 0:
            for i in side_condition:
                if str(i[1]).lower() == 'null':
                    cmd += '%s IS %s and '%(i[0], i[1])
                else:
                    cmd += '%s = %s and '%(i[0], i[1])

        cmd = cmd[:-4]

        if input_is_str:
            return self.__query_db(cmd)[0][1:][0]
        else:
            return list(self.__query_db(cmd)[0][1:])

    def plot_param_history(self,param):
        raise NotImplementedError()
