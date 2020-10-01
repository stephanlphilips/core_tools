import psycopg2
import numpy as np
conn = psycopg2.connect("dbname=test user=stephan")
cur = conn.cursor()


cur.execute("SELECT * FROM pg_largeobject;")

res = cur.fetchall()
print(res)
# conn.commit()


def make_new_lobject(conn):
	o = conn.lobject(0,'wb')
	print("new_file_id = {}".format(o.oid))
	return o, o.oid

def open_lobject(conn, oid):
	o = conn.lobject(oid,'wb')
	return o, o.oid

def write_numpy_array(conn, o, data_array):
	char_data = data_array.tobytes()
	o.seek(0)
	o.write(char_data)
	conn.commit()

def load_numpy_array(conn, oid):
	o = conn.lobject(oid,'wb')
	binary_data = o.read()
	data = np.frombuffer(binary_data)
	return data


string = 'this is a random sentence that I just storred in a text file in the the database...'

data = np.linspace(0,50,500).reshape(10,50)

# o, oid = make_new_lobject(conn)
o, oid = open_lobject(conn, 16411)
write_numpy_array(conn, o, data)
new_data = load_numpy_array(conn, o.oid)
print(new_data.reshape(10,50))
# o = conn.lobject(16409, 'wb')
# print(o.oid)
# print(o.mode)
# print(o.tell())
# print(o.seek(160))
# o.write(string)
# print(o.tell())
# print(o.seek(0))
# print(o.read())

# o.close()
# conn.commit()