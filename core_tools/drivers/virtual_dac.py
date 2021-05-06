import qcodes as qc
from functools import partial
import numpy as np

class virtual_dac(qc.Instrument):
	"""docstring for virtual_dac"""
	def __init__(self, name, my_type, **kwargs):
		'''
		Args:
			name (str) : name of the instrument
			type (str) : type of the parent (virtual, IVVI or SPI)
			**kwargs : keyword arguments, copy the arguments for the real driver
		'''
		super(virtual_dac, self).__init__(name)
		self.type = my_type
		self.kwargs = kwargs
		self.virtual_instrument_initialized = False

		self.my_voltages = np.zeros([16])
		n_dacs = 16
		self._gv = dict()
		for i in range(n_dacs):
			self.add_parameter('dac{}'.format(i + 1),
								   label='DAC {}'.format(i + 1),
								   get_cmd=partial(self._get_dac, i),
								   set_cmd=partial(self._set_dac, i),
								   unit="mV")

	def _set_dac(self, number, voltage):
		'''
		set voltage to the dac
		Args:
			number (int) : number of the dac to set
			voltage (int) : voltage the needs to be set
		'''
		self.my_voltages[number] = voltage
		
	def _get_dac(self, number):
		return self.my_voltages[number]
		# self.connected_instance.send(number)
		# return self.connected_instance.get()
		