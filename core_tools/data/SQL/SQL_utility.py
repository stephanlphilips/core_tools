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

def clean_name_value_pair(names, values):
	'''
	removes empty entries from name value pairs (SQL does not like this)
	'''
	names = list(names)
	values = list(values)

	for i in reversed(range(len(values))):
		if values[i] == None or values[i] == 'null':
			values.pop(i)
			names.pop(i)
			continue
		values[i] = str(values[i])

	return tuple(names), tuple(values)

def format_tuple_SQL(my_tuple):
	'''
	performs some reguglar expersions to nicely convert the tuple in a nice SQL string.
	(for now only timestamp correction)
	'''
	str_tuple = str(my_tuple)
	my_str = re.sub(r"\"to_timestamp\((.{2,30})\)\"", r"to_timestamp(\1)", str_tuple)
	return my_str.replace(", \"'", ", '").replace("(\"'", "('").replace("'\", ", "', ").replace("'\")", "\')")

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
