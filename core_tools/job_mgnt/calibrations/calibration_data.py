import sqlite3
import time

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
        self.current_line = None

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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,\
                    start_time DOUBLE not NULL,\
                    end_time DOUBLE,\
                    success BOOLEAN not NULL)".format(self.table_name)
        self.__exec_command(generate_table)

        # Get current columns in the data base:
        db_paramters = self.cal_object.set_vals.get_db_column_names() + self.cal_object.get_vals.get_db_column_names()
        db_column_info = self.__query_db("PRAGMA table_info('%s')"%self.table_name)
        db_column_names= [db_column_name[1].lower() for db_column_name in db_column_info]
        column_to_add = [param_name for param_name in db_paramters if param_name.lower() not in db_column_names]

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

    def __start_data_entry(self):
        '''
        start new line in the table where data can be saved.
        '''
        cmd = 'INSERT INTO {} (start_time, success) values ({}, TRUE)'.format(self.table_name, time.time())
        self.__exec_command(cmd)
        self.current_line = self.__query_db('SELECT id from {} order by ROWID DESC limit 1'.format(self.table_name))[0][0]

    def write(self, parameter, value):
        ''' 
        Write data to the table
        
        Args:
            parameter (qc.Paramter/str) : parameter to be written
            value (float) : value to write. 
        '''
        if self.current_line is None:
            self.__start_data_entry()

        cmd = 'UPDATE {}\
                SET {} = {} \
                WHERE id = {};'. format(self.table_name, str(parameter), value, self.current_line)

        self.__exec_command(cmd)

    def finish_data_entry(self, status):
        '''
        finish the current entry. Report status of the calibration
        
        Args:
            status (bool) : True = success, False = fail
        '''
        self.write('end_time', time.time())
        self.write('success', status)
        self.current_line = None

    def empty(self):
        '''
        checks if the current db is empty
        '''
        pass

    def query(self):
        # --> make into object.
        pass

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

    d = data_mgr(test_cal(), 'my_test_db')
    # d.write('frequency', 1e6)
    # d.write('frequency', 1e9) # overwrite a value ..
    # d.write('amplitude', 0.1)
    # d.finish_data_entry(True)

    # d.write('frequency', 1e6)
    # d.write('omega_qubit_1', 1.23e2)
    # d.write('amplitude', 0.201)
    # d.finish_data_entry(False)
    
