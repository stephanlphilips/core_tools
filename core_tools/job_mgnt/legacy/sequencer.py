import time



class active_element(object):
	"""docstring for active_element"""
	def __init__(self, arg):
		super(active_element, self).__init__()
		self.arg = arg
	
	def add_libraries(self, lib):
		self.lib = lib

	def upload_data(self):
		raise NotImplementedError()

	def add_gate(self, segement):
		raise NotImplementedError()

	def construct_sequence(self):
		raise NotImplementedError()

	def start(self):
		time.wait(1)

	def pause(self):
		return
		
	def resume(self):
		return