from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info
from core_tools.data.SQL.SQL_database_mgr import SQL_database_manager
from core_tools.utility.variable_mgr.var_mgr_sql import var_sql_queries
import psycopg2

class variable_descriptor:
    def __init__(self, name, unit, category, value=0, skip_init=False):
        self.name = name
        self.unit = unit
        self.category = category

        if skip_init == False:
            var_sql_queries.add_variable(variable_mgr().conn_local, name , unit, category, value)
    
    def __get__(self, obj, objtype=None):
        return obj.vars[self.name]

    def __set__(self, obj, value):
        all_vals, last_id = var_sql_queries.update_val(variable_mgr().conn_local, self.name, value)
        obj.vars = dict(all_vals)

class variable_mgr():
    __instance = None
    conn_local = None

    def __new__(cls):
        if variable_mgr.__instance is None:
            variable_mgr.__instance = object.__new__(cls)
        return variable_mgr.__instance

    def __init__(self):
        # fetch the connection from the database object, no need to connect multiple times.
        if self.conn_local is None:
            self.conn_local = SQL_database_manager().conn_local
            
            self.vars = dict()
            self.__load_variables()

    def __load_variables(self):
        var_sql_queries.init_table(self.conn_local)
        all_specs = var_sql_queries.get_all_specs(self.conn_local)
        for item in all_specs: 
            self.add_variable(item['category'], item['name'], item['unit'], skip_init=True)
        self.vars = dict(var_sql_queries.get_all_values(self.conn_local))

    def show(self):
        pass
        
    def add_variable(self, category, name ,unit, value=0, skip_init=False):
        my_desc = variable_descriptor(name, unit, category, value, skip_init)

        setattr(self, name, my_desc)

    def remove_variable(self, name):
        raise NotImplementedError
    
    def __getattribute__(self, name): #little hack to make make the descriptors work.
        attr = super().__getattribute__(name)
        if hasattr(attr, '__get__'):
            return attr.__get__(self, attr)
        return attr

    def __setattr__(self, name, value): #little hack to make make the descriptors work.
        try:
            attr = super().__getattribute__(name)
            return attr.__set__(self, value)
        except AttributeError:
            return super().__setattr__(name, value)

if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

    t = variable_mgr()

    print(t.vars)
    print(t.name)
    print(t.name1)
    t.name1 = 12
    print(t.name1)
    t.name = 10