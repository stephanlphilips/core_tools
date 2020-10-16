import numpy as np


class buffer_reference:
	'''
	object in case a user want to take a copy of the reader/writer
	'''
	def __init__(self, data):
		self.buffer = data
		self.buffer_lambda = buffer_reference.__empty_lambda

	@property
	def data(self):
		return self.buffer_lambda(self.buffer)

	@staticmethod
	def __empty_lambda(data):
		return data

	@staticmethod
	def averaging_lambda(dim):
		def avg_lambda(data):
			return np.average(data, axis=dim)
		return avg_lambda

	@staticmethod
	def slice_lambda(args):
		def slice_lambda(data):
			return data[tuple(args)]
		return slice_lambda

	@staticmethod
	def reshaper(shape):
		def reshape(data):
			return data.reshape(shape)
		return reshape

class buffer_writer(buffer_reference):
	def __init__(self, SQL_conn, input_buffer):
		self.conn = SQL_conn
		self.buffer = input_buffer.ravel()
		self.buffer_lambda = buffer_reference.reshaper(input_buffer.shape)

		self.lobject = self.conn.lobject(0,'w')
		self.oid = self.lobject.oid
		self.cursor = 0
		self.cursor_db = 0
		self.blocks_written = 0

	def write(self, data):
		'''
		write n points to the buffer (no upload yet)
		
		Args:
			data (np.ndarray, ndim=1, dtype=double) : data to write
		'''
		self.buffer[self.cursor:self.cursor+data.size] = data
		self.cursor += data.size

	def sync(self):
		try:
			if self.cursor - self.cursor_db != 0:
				self.__load_blocks(self.cursor - self.cursor_db)
				self.lobject.write((self.buffer[self.cursor_db:self.cursor]).tobytes())
				self.cursor_db += self.cursor - self.cursor_db
		except:
			self.lobject = self.conn.lobject(self.oid, 'w')
			self.lobject.seek(self.cursor_db*8)
			self.sync()

	def close(self):
		self.lobject.close()

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
				scratch_data = np.full([self.buffer.size - self.blocks_written], np.nan)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size
			else:
				scratch_data = np.full([125000], np.nan)
				self.lobject.write(scratch_data.tobytes())
				self.blocks_written += scratch_data.size

			# reset writing position
			self.lobject.seek(self.cursor*8)

class buffer_reader(buffer_reference):
	def __init__(self, SQL_conn, oid, shape):
		'''
		'''
		self.conn = SQL_conn
		self.buffer = np.full(shape, np.nan).ravel()
		self.buffer_lambda = buffer_reference.reshaper(shape)
		self.oid = oid

		self.lobject = self.conn.lobject(oid,'rb')
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

