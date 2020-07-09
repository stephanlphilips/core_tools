import sqlite3

class data_mgr():
    def __init__(self, cls_object, db_location):
        '''
        Args:
            cls_object (object) : calibration object
            db_location (str) : location of the database

        '''
        self.filename_db = db_location + '.sqlite'
        self.cal_object = cls_object
        self.table_name = cls_object.__class__.__name__
        
        self.__update_table()
    
    def __connect(self):
        db = sqlite3.connect(self.filename_db)
        cursor = db.cursor()
        return db, cursor

    def __exec_command(self,cmd):
        '''
        Execute command in the database.
        
        Args :
            cmd (str) : command you want to execute in the database.
        '''
        db, cursor = self.__connect()
        cursor.execute(cmd)
        db.commit()
        db.close()

    def __query_db(self, cmd):
        '''
        Aks for values in the database/execute command in the database.

        Args:
            cmd (str) : command you want to execute in the database.

        Returns : 
            mydata (list<tuple>) : raw container with the data of your query
        '''
        db, cursor = self.__connect()
        cursor.execute(cmd)        
        mydata = cursor.fetchall()
        db.commit()
        db.close()
        return mydata

    def __update_table(self):
        '''
        function that will construct if not already there the database where the data will be saved. 
        Note that is is no problem running this when no update is strictly needed (e.g. when you start up the module)
        NOTE: that existing fields will not be updated. Use stash_table to rename it and create a new one if you want to do that.
        '''
        generate_table =  "CREATE TABLE IF NOT EXISTS {} (\
                    id data_type PRIMARY KEY,\
                    meas_time TEXT not NULL)".format(self.table_name)
        self.__exec_command(generate_table)

        # Get current columns in the data base:
        db_paramters = self.cal_object.set_vals.get_db_column_names() + self.cal_object.get_vals.get_db_column_names()
        db_column_info = self.__query_db("PRAGMA table_info('%s')"%self.table_name)
        db_column_names= [db_column_name[1].lower() for db_column_name in db_column_info]
        
        column_to_add = [param_name for param_name in db_paramters if param_name[0].lower() not in db_column_names]

        for param in column_to_add:
            self.__exec_command("ALTER TABLE {} ADD COLUMN {} {}".format(self.table_name, param, 'DOUBLE'))

    def stash_table(self):
        '''
        e.g. when you make a new sample.
        save to self.table_name.date
        heck if the table has the right entries.
        '''
        time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
        self.__exec_command("ALTER TABLE %s RENAME TO %s"%(self.table_name, self.table_name + '_' + time))

    def delete_table(self):
        '''
        Delete the current table.
        '''
        self.__exec_command("DROP TABLE %s"% self.table_name)

    def get_all_parameter_names(self):
        '''
        Get all the parameters that are currently in use. Note that SQLite is case insensitive.
        '''
        db, cursor = self.__connect()
        cursor.execute("PRAGMA table_info('%s')"%self.table_name)
        db_column_info = cursor.fetchall()
        db_column_names= [i[1].lower() for i in db_column_info]
        db.close()
        return db_column_names

    def save_calib_results(self, data_tuple):
        '''
        saves the data_tuple to database, if you give a variable that not exist, this will will be discarded
        TODO tell when people feed garbage.
        Args:
            data_tuple list<tuple<str, any>: input data for one row [(var_name, value)]
        '''
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

    def get_parameter_latest(self, params, side_condition=None):
        '''
        returns array with wanted params, if no params given, all parameters of the last calibration will be returned
        params = string or array of strings containing the wanted parameter. 
        side_condition = tuple of values that should be set to a certain value (e.g)
        return format:
        list of dictionaries with field name, data and unit
        Returns:
            Format of param input, return None if not found.
        '''
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

if __name__ == '__main__':

    class value_mgr():
        def __init__(self, *args):
            self.vals = tuple(args)

        def get_db_column_names(self):
            return self.vals 

    class test_cal():
        def __init__(self):
            self.set_vals = value_mgr('frequency', 'amplitude')
            self.get_vals = value_mgr('omega_qubit_1')

    d = data_mgr(test_cal(), 'test/my_test_db')
    print(d.get_all_parameter_names())