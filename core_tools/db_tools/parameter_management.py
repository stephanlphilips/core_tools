'''
classes that automate the saving an collection of data of a parameter on the database
'''
from qcodes import Parameter, Instrument
from dataclasses import dataclass
from core_tools.db_tools.db_help_funtions import checkTableExists, getColumnNames
import logging

@dataclass
class db_field:
    name : Parameter
    field_type : str
    value : any = None

def define_table(cursor, table_name, fields):
    '''
    define a paramter in the db, if does not exist, field are the field that are expected to be present.
    
    Args:
        cursor () : db cursor
        table_name (str) : name of the table to write to the db (e.g. the insturment names which generaters the paramters)
        fields (list<db_field>) : field to write
    '''
    # check if instrument present / create db if needed
    if not checkTableExists(cursor, table_name):
        cursor.execute("CREATE TABLE %s (snapshot_id INT AUTO_INCREMENT PRIMARY KEY,)", (table_name, ))
        logging.info('generated a new table in db, {}'.format(table_name))




    # for every field, check if the column exists
    pass

def remove_table(cursor, param):
    '''
    removes a table out of the db (if needed)
    '''
    pass
def write_to_db(cursor, param, fields):
    '''
    perform a write if fuekd in the db
    '''
    pass
def get_snapshot_names(cursor, param, contains, N = 10):
    '''
    get names of snapshots
    '''
    pass
def get_data(cursor, parameter, snapshot_id=-1):
    '''
    get data by primary key, if -1, get latest entry
    '''
    pass





if __name__ == '__main__':
    from qcodes.tests.instrument_mocks import DummyInstrument
    import mysql.connector

    dac = DummyInstrument('dac', gates=['ch1', 'ch2'])
    # print(dac.print_readable_snapshot())
    
    db = mysql.connector.connect(user='stephan', password='magicc',
                                  host='51.89.64.39',
                                  database='qcodes_test')

    ## creating an instance of 'cursor' class which is used to execute the 'SQL' statements in 'Python'
    cursor = db.cursor()
    cursor.execute("USE testing")
    print(checkTableExists(cursor, 'table_prim_key'))
    print(getColumnNames(cursor, 'table_prim_key'))
    db.close()