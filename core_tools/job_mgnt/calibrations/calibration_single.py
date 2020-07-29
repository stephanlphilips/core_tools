from calibration_data import data_mgr
import qcodes as qc


class CalibrationError(Exception):
	pass

class dep_mgr():
	dep = tuple()

def calibration_wrapper(cls, function):
	def run_function(*args, **kwargs):
		try:
			function(args, kwargs)
			if cls._N_rep > cls._n:
				run_function(args, kwargs)
		except:
			raise CalibrationError

		cls._N_rep = 0
		cls._n = 0

	return run_function

class calibration_generic():
	FAIL = 0
	SUCCES = 1
	station = qc.Station.default
	
	def __new__(self):
		self.update_interval = 0 # 0 for do not update
		self.auto_update = False # automatically rerun the last calibration after the update intercal exceeded
		self.prioritize = True # first calibration or first measurement
		self.dependencies = dep_mgr()
		self.data_mgr = data_mgr(self, 'todo')
		
		# iteration variables
		self._N_rep = 0
		self._n = 0

		return self

	def get_data(self, parameters ,set_vals = dict()):
		self.data_mgr.get(set_vals)

	def save_data(self, set_vals):
		self.data_mgr.set()

	def reiterate(self, N=1):
		'''
		call this function in to reiterature the same calibration N times.
		'''
		self._N_rep = N+1
		self._n = 0

class ExampleCal(calibration_generic):
	def __init__(self):
		self.dependencies += my_cals.readout_of_dot_1
		self.dependencies += (my_cals.readout_of_dot_2, my_cals.tc_res)

		self.setters = ...
		self.getters = ...

if __name__ == '__main__':
	test = ExampleCal()
	print(test)
	print(test.update_interval)