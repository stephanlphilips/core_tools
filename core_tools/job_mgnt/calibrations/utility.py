from typing import Union
import numpy as np

from qcodes import Parameter

class param_mngr(list):
	'''
	mangagment class for parameters, allows for easy extending of multiple param if needed.
	'''
	def __init__(self,name, unit='a.u.'):
		super().__init__()

		param = Parameter(name, label=name, unit=unit)
		self.base_param = param
		self.append(param)

	def __add__(self, other):
		if isinstance(other, SampleLayoutField):
			for i in other:
				if self[0] == self.base_param:
					self.pop(0)
				name = self.base_param.name + i
				self += [Parameter(name, label=name, unit=self.base_param.unit)]
		else:
			raise ValueError('please add up the type SampleLayoutField')

		return self

class SampleLayoutField(list):
	# formatter for a single field of the sample layout class
	def __init__(self, std_field_name = '', input_names = list()):
		'''
		Args:
			std_field_name (str) : standard name to append before the input name
			input_names (list<str>) : input names
		'''
		super().__init__(input_names)
		self.std_field_name = '_' if std_field_name == '' else  "_" + std_field_name + '_'	

	def __add__(self, other):
		if isinstance(other, Union[str, int, float].__args__):
			return self + [other]

		if isinstance(other, Union[list, tuple, np.ndarray, range].__args__):
			for var in other:
				self.append(self.std_field_name + str(var))
			return self
		raise ValueError('type not recognized?')

	def __iadd__(self, other):
		return self.__add__(other)

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

	# use in combination with param manager to easily generate paramter object.
	FREQ = param_mngr('FREQ', 'Hz') + SL.qubits
	for f in FREQ:
		print(f)
