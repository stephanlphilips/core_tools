import numpy as np

class buffer_writer:
	def __init__(self, SQL_conn, input_buffer):
		self.conn = SQL_conn
		self.buffer = input_buffer

		self.lobject = conn.lobject(0,'w')
		self.oid = self.lobject.oid
		self.cursor = 0
		self.blocks_written = 0

	def write(self, n):
		'''
		write n points to the large object file
		
		Args:
			n (int) : number of floats to be written
		'''
		try:
			self.__load_blocks(n)
			self.lobject.write((self.buffer[self.cursor:self.cursor+n]).tobytes())
			self.cursor += n
		except:
			self.lobject = conn.lobject(self.oid, 'w')
			self.lobject.seek(self.cursor*8)
			self.write(n)


	def __load_blocks(self, n):
		'''
		load empty blocks in the buffer to prevent defragmentation.

		Args:
			n (int) : number of writes to be performed
		'''
		if self.cursor + n > self.blocks_written:
			self.lobject.seek(self.blocks_written)

			if n > 1e6/8:
				pass #write is large than the number of blocks reserved -> skip.
			elif self.buffer.size - self.blocks_written <1e6/8:
				scratch_data = np.empty([self.buffer.size - self.blocks_written])
				scratch_data.fill(np.NaN)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size
			else:
				scratch_data = np.empty([125000])
				scratch_data.fill(np.NaN)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size

			# reset writing position
			self.lobject.seek(self.cursor*8)


class buffer_reader:
	def __init__(self, SQL_conn, oid, shape):
		'''
		'''
		self.conn = SQL_conn
		self.buffer = np.empty(shape)
		self.buffer.fill(np.NaN)
		self.oid = oid

		self.lobject = conn.lobject(oid,'rb')
		self.update_buffer()

	def update_buffer(self, start=0, stop=None):
		'''
		update the buffer (for datasets that are still being written)

		Args:
			start (int) : start position to update
			stop (int) : update until (default, end of the data)
		'''
		try:
			self.lobject.seek(start*8)
		except:
			self.lobject = conn.lobject(self.oid, 'rb')
			self.update_buffer(start, stop)
		if stop is not None:
			binary_data = self.lobject.read(stop*8)
		else:
			binary_data = self.lobject.read()

		data = np.frombuffer(binary_data)
		self.buffer.flat[start:start+data.size] = data

if __name__ == '__main__':
	import psycopg2
	import numpy as np
	conn = psycopg2.connect("dbname=test user=stephan")
	import time
	test_data = np.linspace(0, 80,1000000)
	print(test_data[:])

	bw = buffer_writer(conn, test_data)

	t = time.time()
	
	for i in range(0,8):
		bw.write(10000)
		if i%4==0:
			conn.commit()
	
	t1 = time.time()

	print(t1-t)
	conn.commit()
	print(bw.oid)

	oid = bw.oid
	read_buffer = buffer_reader(conn, oid, (80000,))
	conn.commit()
	read_buffer.update_buffer(800,1200)
	print(read_buffer.buffer)
