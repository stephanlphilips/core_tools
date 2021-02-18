from psycopg2.extras import RealDictCursor, Json
from psycopg2 import sql
import psycopg2
from uuid import getnode as get_mac
import time
import re

def to_postgres_time(my_date_time):
	return time.strftime("%a, %d %b %Y %H:%M:%S +0000",my_date_time.timetuple())

def text(my_input):
	return "\'{}\'".format(str(my_input))

def generate_uuid():
	ms_time = int(time.time()*1000)*1000000
	return ms_time + get_mac()%99999999

def N_to_n(arg):
	''' convert None to null '''
	if arg is None:
		return 'null'
	else:
		return arg

def format_SQL_value(var_value):
	if isinstance(var_value, (sql.SQL, sql.Composed, sql.Literal)):
		return var_value, []
	else:
		return sql.Placeholder(), [var_value]

def sql_name_formatter(var_names):
	var_names_SQL = []
	
	for i in var_names:
		if i == '*':
			var_names_SQL.append(sql.SQL(i))
		elif isinstance(i, sql.SQL):
			var_names_SQL.append(i)
		else:
			var_names_SQL.append(sql.Identifier(i))

	return var_names_SQL

def sql_value_formatter(var_values):
	var_values_SQL = []
	placeholders = []

	for i in var_values:
		val,placeholder = format_SQL_value(i)
		var_values_SQL  += [val]
		placeholders += placeholder
	
	return var_values_SQL, placeholders

class name_value_formatter():
	def __init__(self, var_names, var_values):
		self.placeholders = []
		self.var_names = []
		self.var_values = []

		for i,j in zip(var_names, var_values):
			if is_empty(j):
				continue

			self.var_names += [sql.Identifier(i)]
			val,placeholder = format_SQL_value(j)
			self.var_values  += [val]
			self.placeholders += placeholder

	@property
	def var_name_pairs(self):
		return [(i,j) for i,j in zip(self.var_names, self.var_values)]

	def __len__(self):
		return len(self.var_names)

def is_empty(data):
	if data is None: 
		return True
	if data == "\'None\'":
		return True
	if data == "to_timestamp('null')":
		return True
	if str(data) == "'null'":
		return True
	if str(data) == "'null'::bytea":
		return True
	return False
