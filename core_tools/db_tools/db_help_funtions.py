from dataclasses import dataclass

@dataclass
class column_prop:
    field_name : str
    data_type : str
    null : str
    key : str
    default : str
    extra : str
    privileges : str = None
    comment : str = None

    __eq__(self, other):
        if isinstance(other, string):
            if self.field_name==other:
                return True
        raise ValueError("comparison not type {} not supported.".format(type(other)))



def checkTableExists(cursor, table_name):
    '''
    check is a table exists in the db (expected to be selected before)

    Args:
        cursor ():
        table_name (str) : name of the table to check
    '''
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", (table_name, ))
    
    if cursor.fetchone()[0]:
        return True

    return False

def getColumnNames(cursor, table_name):
    '''
    get call the column names out of the db

    Args:
        cursor ():
        table_name (str) : name of the table to check
    '''
    cursor.execute("SHOW COLUMNS FROM {}".format(table_name))
    return cursor.fetchall()