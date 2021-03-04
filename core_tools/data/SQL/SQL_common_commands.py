from psycopg2.extras import RealDictCursor
from psycopg2 import sql

from core_tools.data.SQL.SQL_utility import sql_name_formatter, sql_value_formatter, name_value_formatter

def execute_statement(conn, statement, placeholders = []):
	cursor = conn.cursor()
	cursor.execute(statement, placeholders)
	cursor.close()

	return ((), )

def execute_query(conn, query, dict_cursor=False, placeholders = []):
	if dict_cursor == False:
		cursor = conn.cursor()
	else:
		cursor = conn.cursor(cursor_factory=RealDictCursor)
	
	cursor.execute(query, placeholders)

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
		order_by (tuple, str) : order results (e.g. ('uuid',  'DESC')
		limit (int) : limit the amount of results
		dict_cursor (bool) : return result as an ordered dict
	'''
	var_names_SQL = sql_name_formatter(var_names)

	query = sql.SQL("select {0} from {1} ").format(
				sql.SQL(', ').join(var_names_SQL),
				sql.SQL(table_name))
	# SQL.Identifier does not work with underscore names for tables?

	if where is not None:
		query += sql.SQL("WHERE {0} = {1} ").format(sql.Identifier(where[0]), sql.Literal(where[1]))
	if order_by is not None:
		query += sql.SQL("ORDER BY {0} {1} ").format(sql.Identifier(order_by[0]), sql.SQL(order_by[1]))
	if limit is not None:
		query += sql.SQL("LIMIT {0} ").format(sql.SQL(str(int(limit))))

	return execute_query(conn, query, dict_cursor)

def insert_row_in_table(conn, table_name, var_names, var_values, returning=None, custom_statement=''):
	'''
	insert a row in a table

	Args:
		conn (psycopg2.connect) : connection object from psycopg2 librabry
		table_name (str) : name of the table to update
		var_names (tuple<str>) : variable names of the table
		var_values (tuple<str>) : values corresponding to the variable names
		returning (tuple<str>) : name of a variables you want returned
	'''
	var_values_SQL, placeholders = sql_value_formatter(var_values)
	var_names_SQL = sql_name_formatter(var_names)

	statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ").format(sql.SQL(table_name),
			sql.SQL(', ').join(var_names_SQL),
			sql.SQL(', ').join(var_values_SQL))

	if returning is None:
		return execute_statement(conn, statement + sql.SQL(custom_statement), placeholders)
	else:
		statement += sql.SQL(" RETURNING {} ").format(sql.SQL(", ").join([sql.Identifier(i) for i in returning]))
		return execute_query(conn, statement + sql.SQL(custom_statement), placeholders=placeholders)


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

	statement = sql.SQL("UPDATE {} SET ").format(sql.SQL(table_name))

	names_values = name_value_formatter(var_names, var_values)
	if len(names_values) == 0:
		return ""
	
	var_names_SQL = sql_name_formatter(var_names)
	var_values_SQL, placeholders = sql_value_formatter(var_values)

	statement += sql.SQL(', ').join(sql.SQL("{} = {} ").format(i,j) for i,j in zip(var_names_SQL, var_values_SQL))

	if condition is not None:
		statement += sql.SQL("WHERE {0} = {1} ").format(sql.Identifier(condition[0]), sql.Literal(condition[1]))

	return execute_statement(conn, statement, placeholders=placeholders)

def alter_table(conn, table_name, colums, dtypes):
	'''
	add columns to a table

	Args:
		conn (psycopg2.connect) : connection object from psycopg2 librabry
		table_name (str) : name of the table to update
		colums (tuple<str>) : names of the columns
		dtypes (tuple<str>) : type of the column's
	'''
	statement = sql.SQL("ALTER TABLE {} ADD COLUMN ").format(sql.SQL(table_name))
	for i,j in zip(colums, dtypes):
		print(i,j)
	statement += sql.SQL(" , ADD COLUMN ").join(sql.SQL(" {0} {1} ").format(sql.Identifier(i), sql.SQL(j)) for i, j in zip(colums, dtypes))

	return execute_statement(conn, statement)