from core_tools.data.SQL.connect import sample_info
from core_tools.data.SQL.SQL_common_commands import insert_row_in_table, update_table, select_elements_in_table, execute_statement, alter_table
from psycopg2.extras import RealDictCursor, DictCursor
from psycopg2.errors import UndefinedColumn
from psycopg2 import sql

import datetime, time

def to_postgres_time(my_date_time):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000",my_date_time.timetuple())

class var_sql_queries:
    @staticmethod
    def init_table(conn):
        statement = statement = "CREATE TABLE if not EXISTS {} (".format(
            var_sql_queries.gen_table_overview_name())
        statement += "name text NOT NULL UNIQUE,"
        statement += "unit text NOT NULL,"
        statement += "step FLOAT8 NOT NULL,"
        statement += "category text NOT NULL );"
        execute_statement(conn, statement)

        statement = "CREATE TABLE if not EXISTS {} (id SERIAL, insert_time TIMESTAMP );".format(
            var_sql_queries.gen_table_content_name())
        execute_statement(conn, statement)

        conn.commit()

    @staticmethod
    def add_variable(conn, name, unit, category, step, value=0):
        # this will be the line where we set the value
        vals, last_update_id = var_sql_queries.update_val(conn, name=None, value=None)
        res = select_elements_in_table(conn, var_sql_queries.gen_table_overview_name(), ('name', ), where=('name', name))

        if len(res) == 0:
            insert_row_in_table(conn,  var_sql_queries.gen_table_overview_name(),  ('name', 'unit', 'category', 'step'), (name, unit, category, step))
            alter_table(conn, var_sql_queries.gen_table_content_name(), (name, ), ('FLOAT8',))

            update_table(conn, var_sql_queries.gen_table_content_name(), (name,), (value,), condition=('id', last_update_id))
            conn.commit()

        else: 
            print('Variable {} already present, skipping.'.format(name))

    def get_all_specs(conn):
        return select_elements_in_table(conn, var_sql_queries.gen_table_overview_name(), ('*', ), dict_cursor=RealDictCursor)

    def get_all_values(conn):
        res = select_elements_in_table(conn, var_sql_queries.gen_table_content_name(), ('*',), 
            order_by=('id','DESC'), limit=100, dict_cursor=RealDictCursor)

        if len(res) == 0:
            return {}
        return res[0]

    def update_val(conn, name , value):
        all_vals = var_sql_queries.get_all_values(conn)
        if name is not None:
            all_vals[name] = value
        if all_vals is None:
            all_vals = dict()

        all_vals.pop('id', None)
        all_vals['insert_time'] = to_postgres_time(datetime.datetime.now())

        my_id = insert_row_in_table(conn, var_sql_queries.gen_table_content_name(), tuple(all_vals.keys()), tuple(all_vals.values()), returning=('id', ))[0]
        conn.commit()

        return all_vals, my_id

    def remove_variable(conn, variable_name):


        try:
            statement_1 = sql.SQL("DELETE FROM {} WHERE {} = {} ").format(sql.SQL(var_sql_queries.gen_table_overview_name()), sql.Identifier('name'),sql.Literal(variable_name))
            statement_2 = sql.SQL("ALTER TABLE {} DROP COLUMN {}").format(sql.SQL(var_sql_queries.gen_table_content_name()), sql.Identifier(variable_name))
            execute_statement(conn, statement_2)
            conn.commit()
            execute_statement(conn, statement_1)
            
        except UndefinedColumn:
            print('Nothing to remove. {} is not present in the database?'.format(variable_name))

    @staticmethod
    def gen_table_overview_name():
        return ('_'+sample_info.project+'_'+sample_info.set_up+'_'+sample_info.sample + "__variables_overview").replace(" ", "_").replace('-', '_')

    @staticmethod
    def gen_table_content_name():
        return ('_'+sample_info.project+'_'+sample_info.set_up+'_'+sample_info.sample + "__variables_content").replace(" ", "_").replace('-', '_')

if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage
    from core_tools.utility.variable_mgr.var_mgr import variable_mgr
    set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample')
    set_up_local_storage("xld_user", "XLDspin001", "vandersypen_data", "6dot", "XLD", "testing")

    conn = variable_mgr().conn_local
    var_sql_queries.init_table(conn)

    # var_sql_queries.add_variable(conn, "SD1_P_on3execute_statement(conn, statement_1)", "mV", "SD voltages", 0.1)
    # var_sql_queries.add_variable(conn, "SD1_P_on", "mV", "SD voltages", 0.1)
    var_sql_queries.update_val(conn, "SD1_P_on", 12)
    print(var_sql_queries.get_all_values(conn))
    print(var_sql_queries.get_all_specs(conn))
    # var_sql_queries.remove_variable(conn, "sd1_p_on")

