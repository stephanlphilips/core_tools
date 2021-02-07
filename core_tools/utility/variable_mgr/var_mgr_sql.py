from core_tools.data.SQL.connect import sample_info
from psycopg2.extras import RealDictCursor, DictCursor
from psycopg2.errors import UndefinedColumn
import datetime, time

def to_postgres_time(my_date_time):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000",my_date_time.timetuple())

class var_sql_queries:
    @staticmethod
    def init_table(conn):
        cur = conn.cursor()
        statement = statement = "CREATE TABLE if not EXISTS {} (".format(
            var_sql_queries.gen_table_overview_name())
        statement += "name text NOT NULL UNIQUE,"
        statement += "unit text NOT NULL,"
        statement += "step FLOAT8 NOT NULL,"
        statement += "category text NOT NULL );"
        cur.execute(statement)

        statement = "CREATE TABLE if not EXISTS {} (id SERIAL, insert_time TIMESTAMP );".format(
            var_sql_queries.gen_table_content_name())
        cur.execute(statement)
        cur.close()
        conn.commit()

    @staticmethod
    def add_variable(conn, name, unit, category, step, value=0):
        # this will be the line where we set the value
        vals, last_update_id = var_sql_queries.update_val(conn, name=None, value=None)
        cur = conn.cursor()
        statement = "SELECT name from {} where name='{}'".format(
            var_sql_queries.gen_table_overview_name(), name)
        cur.execute(statement)
        res = cur.fetchall()

        if len(res) == 0:
            statement_1 = "INSERT INTO {} (name, unit, category, step) VALUES ('{}', '{}', '{}', '{}');".format(
                var_sql_queries.gen_table_overview_name(), name, unit, category, step)
            statement_2 = "ALTER TABLE {} ADD COLUMN {} FLOAT8 ;".format(
                var_sql_queries.gen_table_content_name(), name)

            cur.execute(statement_1)
            cur.execute(statement_2)

            # update value
            statement = "UPDATE {} set {} = {} where id = {} ;".format(
                var_sql_queries.gen_table_content_name(), name, value, last_update_id)
            cur.execute(statement)
            cur.close()
            conn.commit()
        else: 
            print('Variable {} already present, skipping.'.format(name))

    def get_all_specs(conn):
        cur = conn.cursor(cursor_factory=RealDictCursor)
        statement ="SELECT * FROM {};".format(
            var_sql_queries.gen_table_overview_name())
        cur.execute(statement)
        res = cur.fetchall()
        cur.close()

        return res

    def get_all_values(conn):
        cur = conn.cursor(cursor_factory=RealDictCursor)
        statement ="SELECT * FROM {} ORDER BY id DESC LIMIT 1;".format(
            var_sql_queries.gen_table_content_name())
        cur.execute(statement)
        res = cur.fetchone()
        cur.close()

        if res is None:
            return {}
        return res

    def update_val(conn, name , value):
        cur = conn.cursor()

        all_vals = var_sql_queries.get_all_values(conn)
        if name is not None:
            all_vals[name.lower()] = value
        if all_vals is None:
            all_vals = dict()

        all_vals.pop('id', None)
        all_vals['insert_time'] = to_postgres_time(datetime.datetime.now())

        statement = "INSERT INTO {} {} VALUES {} RETURNING id;".format(
            var_sql_queries.gen_table_content_name(),
            str(tuple(all_vals.keys())).replace('\'', " ").replace(',)', " )"),
            str(tuple(all_vals.values())).replace(',)', " )"))
        cur.execute(statement)
        my_id = cur.fetchone()[0]
        cur.close()
        conn.commit()
        return all_vals, my_id

    def remove_variable(conn, variable_name):

        try:
            cur = conn.cursor()

            statement_1 = "DELETE FROM {} WHERE name = '{}' ;".format(var_sql_queries.gen_table_overview_name(), variable_name)
            statement_2 = "ALTER TABLE {} DROP COLUMN {} ;".format(var_sql_queries.gen_table_content_name(), variable_name)

            cur.execute(statement_1)
            cur.execute(statement_2)
            cur.close()
            conn.commit()
        except UndefinedColumn:
            print('Nothing to remove. {} is not present in the database?'.format(variable_name))

    @staticmethod
    def gen_table_overview_name():
        return ('_'+sample_info.project+'_'+sample_info.set_up+'_'+sample_info.sample + "__variables_overview").replace(" ", "_").replace('-', '_')

    @staticmethod
    def gen_table_content_name():
        return ('_'+sample_info.project+'_'+sample_info.set_up+'_'+sample_info.sample + "__variables_content").replace(" ", "_").replace('-', '_')

if __name__ == '__main__':
    from core_tools.data.SQL.connector import set_up_local_storage, set_up_remote_storage
    from core_tools.utility.variable_mgr.var_mgr import variable_mgr
    set_up_local_storage('stephan', 'magicc', 'test', 'project', 'set_up', 'sample')

    conn = variable_mgr().conn_local
    var_sql_queries.init_table(conn)

    # var_sql_queries.add_variable(conn, "SD1_P_on", "mV", "SD voltages", 0.1)
    # var_sql_queries.add_variable(conn, "SD1_P_on", "mV", "SD voltages", 0.1)
    # var_sql_queries.update_val(conn, "name", 12)
    print(var_sql_queries.get_all_specs(conn))
    # var_sql_queries.remove_variable(conn, "SD1_P_on")