from typing import Union
import numpy as np


class SampleLayoutField():
	# formatter for a single field of the sample layout class
	def __init__(self, std_field_name = '', input_names = tuple()):
		'''
		Args:
			std_field_name (str) : standard name to append before the input name
			input_names (tuple<str>) : input names
		'''
		self.variable_names = list()
		self.std_field_name = '_' if std_field_name == '' else  "_" + std_field_name + '_'
		self += input_names		

	def __add__(self, other):
		if isinstance(other, Union[str, int, float].__args__):
			return self + [other]

		if isinstance(other, Union[list, tuple, np.ndarray, range].__args__):
			for var in other:
				self.variable_names += [self.std_field_name + str(var)]
			return self
		raise ValueError('type not recognized?')

	def __radd__(self, other):
		if isinstance(other, str):
			return_var = tuple()
			for var in self.variable_names:
				return_var += (other + var,)
			return return_var

		raise ValueError('type for adding not recognized. Only strings are supported') 

class MyExampleSampleLayout():
	def __init__(self):
		self.qubits = SampleLayoutField('qubits')
		self.qubit_pairs = SampleLayoutField()
		self.res_barrier = SampleLayoutField()
		self.n = SampleLayoutField()
		self.SD = SampleLayoutField('SD')

		self.qubits += range(1,6)
		self.qubit_pairs += (12,23,34,45)
		self.res_barrier += (1,2)
		self.n += range(1,6)
		self.SD += range(1,3)

if __name__ == '__main__':
	# example usage of layout class
	SL = MyExampleSampleLayout()

	print('FREQ' + SL.qubits)
	print('J' + SL.qubit_pairs)
	print('SD' + SL.SD)
	print('tc_res' + SL.res_barrier)
