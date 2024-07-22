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
                # self.__load_blocks(self.cursor - self.cursor_db)
                self.lobject.write((self.buffer[self.cursor_db:self.cursor]).tobytes())
                self.cursor_db += self.cursor - self.cursor_db
        except:
            # NOTE: After a commit the lobject is not valid anymore and must be created again.
            #       The overhead for this is very small.
            self.lobject = self.conn.lobject(self.oid, 'w')
            self.lobject.seek(self.cursor_db*8)
            self.sync()

    def close(self):
        self.lobject.close()


class buffer_reader(buffer_reference):
    def __init__(self, SQL_conn, oid, shape):
        self.conn = SQL_conn
        self.buffer = np.full(shape, np.nan).ravel()
        self.buffer_lambda = buffer_reference.reshaper(shape)
        self.oid = oid

        self.lobject = self.conn.lobject(oid,'rb')
        self.cursor = 0
        self.sync()

    def sync(self):
        '''
        update the buffer (for datasets that are still being written)
        '''
        self.lobject = self.conn.lobject(self.oid, 'rb')
        self.lobject.seek(self.cursor*8)
        binary_data = self.lobject.read()
        data = np.frombuffer(binary_data)

        self.buffer[self.cursor:self.cursor+data.size] = data
        self.cursor = self.cursor+data.size

    def close(self):
        self.lobject.close()
