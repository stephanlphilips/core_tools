import numpy as np

class buffer_writer:
	def __init__(self, SQL_conn, input_buffer):
		self.conn = SQL_conn
		self.buffer = input_buffer

		self.lobject = conn.lobject(0,'wb')
		self.cursor = 0
		self.blocks_written = 0

	def write(n):
		'''
		write n points to the large object file
		
		Args:
			n (int) : number of floats to be written
		'''
		self.__load_blocks(n)
		self.lobject.write(self.buffer[self.cursor:self.cursor+n])
		self.cursor += n

	def __load_blocks(n):
		'''
		load empty blocks in the buffer to prevent defragmentation
		'''
		if self.cursor + n > self.blocks_written:
			self.lobject.seek(self.blocks_written)

			if self.input_buffer.size - self.blocks_written <125000:
				scratch_data = np.empty([self.input_buffer.size - self.blocks_written]).fill(np.NaN)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size
			else:
				scratch_data = np.empty([125000]).fill(np.NaN)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size

			# reset writing position
			self.lobject.seek(self.cursor)


class buffer_reader:
	def __init__(self, SQL_conn, oid, shape):
		self.conn = SQL_conn
		self.buffer = np.empty(shape).fill(np.NaN)

		self.lobject = conn.lobject(oid,'rb')
		self.update_buffer()

	def update_buffer(start=0, stop=None):
		'''
		update the buffer (for datasets that are still being written)

		Args:
			start (int) : start position to update
			stop (int) : update until (default, end of the data)
		'''
		self.lobject.seek(start)
		if stop is not None:
			binary_data = self.lobject.read(stop)
		else:
			binary_data = self.lobject.read()

		data = np.frombuffer(binary_data)
		self.buffer.flat[start:start+data.size] = data