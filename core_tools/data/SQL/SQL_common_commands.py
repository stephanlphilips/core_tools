from psycopg2.extras import RealDictCursor
from core_tools.data.SQL.SQL_utility import clean_name_value_pair, format_tuple_SQL, is_empty

def execute_statement(conn, statement):
	cursor = conn.cursor()
	cursor.execute(statement)
	cursor.close()

	return ((), )


def execute_query(conn, query, dict_cursor=False):
	if dict_cursor == False:
		cursor = conn.cursor()
	else:
		cursor = conn.cursor(cursor_factory=RealDictCursor)
	
	cursor.execute(query)
	return_values =cursor.fetchall()
	cursor.close()
	
	return return_values

def select_elements_in_table(conn, table_name, var_names, where=None, order_by = None, limit=None, dict_cursor=True):
	'''
	execute a query on a table

	Args:
		conn (psycopg2.connect) : connection object from psycopg2 librabry
		table_name (str) : name of the table to update
		var_names (tuple<str>) : variable names of the table
		where (str) : selection critere (e.g. 'id = 5')
		order_by (str) : order results (e.g. 'uuid DESC')
		limit (int) : limit the amount of results
		dict_cursor (bool) : return result as an ordered dict
	'''
	query = "SELECT {} from {} ".format(str(var_names), table_name)
	if where is not None:
		query += "WHERE {} ".format(where)
	if order_by is not None:
		query += "ORDER BY {} ".format(order_by)
	if limit is not None:
		query += "LIMIT {} ".format(int(limit))

	query += ";"

	return execute_query(conn, query, dict_cursor)

def insert_row_in_table(conn, table_name, var_names, var_values, returning=None, custom_statement=''):
	'''
	insert a row in a table

	Args:
		conn (psycopg2.connect) : connection object from psycopg2 librabry
		table_name (str) : name of the table to update
		var_names (tuple<str>) : variable names of the table
		var_values (tuple<str>) : values corresponding to the variable names
		returning (str) : name of a variablle you want returned
	'''
	var_names, var_values = clean_name_value_pair(var_names, var_values)
	statement = "INSERT INTO {} {} VALUES {} ".format(table_name, str(var_names).replace('\'', ''), format_tuple_SQL(var_values))

	if returning is None:
		return execute_statement(conn, statement + custom_statement + ";")
	else:
		statement += " RETURNING {} ".format(returning)
		return execute_query(conn, statement + custom_statement +";")


def update_table(conn, table_name, var_names, var_values, condition=None):
	'''
	generate statement for updating an existing stable

	Args:
		conn (psycopg2.connect) : connection object from psycopg2 librabry
		table_name (str) : name of the table to update
		var_names (tuple<str>) : variable names of the table
		var_values (tuple<str>) : values corresponding to the variable names
		condition (str) : condition for the update (e.g. 'id = 5')
	'''
	if len(var_names) == 0:
		return ""

	statement = "UPDATE {} SET ".format(table_name)

	for i,j in zip(var_names, var_values):
		if is_empty(j):
			continue
		statement +=  "{} = {} ,".format(i,j)

	statement = statement[:-1]

	if condition is not None:
		statement += " WHERE {} ".format(condition)

	return execute_statement(conn, statement + ";")