import qcodes as qc
from functools import partial
import numpy as np
import copy

class gates(qc.Instrument):
	"""
	gates class, generate qcodes parameters for the real gates and the virtual gates
	It also manages the virtual gate matrix. 
	"""
	def __init__(self, name ,hardware, dac_sources):
		'''
		gates object 
		args:
			name (str) : name of the instrument
			hardware (class) : class describing the instrument (standard qtt issue, see example below to generate a gate set).
			dac_sources (list<virtual_dac>) : list with the dacs
		'''
		super(gates, self).__init__(name)
		self.hardware = hardware
		self.dac_sources = dac_sources
		
		self._gv = dict()
		# self._vgv = dict()

		# add gates:
		for gate_name, dac_location in hardware.dac_gate_map.items():
			self.add_parameter(gate_name, set_cmd = partial(self._set_voltage,  gate_name), get_cmd=partial(self._get_voltage,  gate_name), unit = "mV")
		
		# make virtual gates:
		for virt_gate_set in self.hardware.virtual_gates:
			for gate_name in virt_gate_set.virtual_gate_names:
				self.add_parameter(gate_name, set_cmd = partial(self._set_voltage_virt, gate_name, virt_gate_set),
					get_cmd=partial(self._get_voltage_virt, gate_name, virt_gate_set), unit = "mV")

	@property
	def virtual_gate_matrix_inv(self):
		# property as can be the normal matrix can be changed externally.
		self._virtual_gate_matrix_inv = np.linalg.inv(self.virtual_gate_matrix)

		return self._virtual_gate_matrix_inv
	
	def _set_voltage(self, gate_name, voltage):
		'''
		set a voltage to the dac
		Args:
			voltage (double) : voltage to set	
			gate_name (str) : name of the gate to set 
		'''
		dac_location = self.hardware.dac_gate_map[gate_name]
		if gate_name in self.hardware.boundaries.keys():
			min_voltage, max_voltage = self.hardware.boundaries[gate_name]
			if voltage < min_voltage or voltage > max_voltage:
				raise ValueError("Voltage boundaries violated, trying to set gate {} to {}mV. \nThe limit is set to {} to {} mV.\nThe limit can be changed by updating the hardware class".format(gate_name, voltage, min_voltage, max_voltage))

		getattr(self.dac_sources[dac_location[0]], 'dac{}'.format(int(dac_location[1])) )(voltage)

	def _get_voltage(self, gate_name):
		'''
		get a voltage to the dac
		Args:
			gate_name (str) : name of the gate to set 
		'''
		dac_location = self.hardware.dac_gate_map[gate_name]
		return getattr(self.dac_sources[dac_location[0]], 'dac{}'.format(int(dac_location[1])) )()

	def _set_voltage_virt(self, gate_name, virt_gate_obj, voltage):
		'''
		set a voltage to the virtual dac
		Args: 
			voltage (double) : voltage to set
			name : name of the real gate (that corresponds the certain virtual gate)
		'''
		current_voltages_formatted = np.zeros([len(virt_gate_obj)])
		current_voltages = list(self.gv.values())
		names = list(self.gv.keys())

		for i in range(len(virt_gate_obj)):
			current_voltages_formatted[i] = current_voltages[names.index(virt_gate_obj.real_gate_names[i])]

		voltage_key = virt_gate_obj.virtual_gate_names.index(gate_name)
		virtual_voltages =  np.matmul(virt_gate_obj.virtual_gate_matrix,current_voltages_formatted)
		virtual_voltages[voltage_key] = voltage
		new_voltages = np.matmul(np.linalg.inv(virt_gate_obj.virtual_gate_matrix), virtual_voltages)

		i = 0
		for gate_name in virt_gate_obj.real_gate_names: 
			if new_voltages[i] != current_voltages_formatted[i]:
				self._set_voltage(gate_name,new_voltages[i]) 
			i+=1

	def _get_voltage_virt(self, gate_name, virt_gate_obj):
		'''
		get a voltage to the virtual dac
		Args:
			name : name of the real gate (that corresponds the certain virtual gate)
		'''

		current_voltages_formatted = np.zeros([len(virt_gate_obj)])
		current_voltages = list(self.gv.values())
		names = list(self.gv.keys())

		for i in range(len(virt_gate_obj)):
			current_voltages_formatted[i] = current_voltages[names.index(virt_gate_obj.real_gate_names[i])]

		voltage_key = virt_gate_obj.virtual_gate_names.index(gate_name)
		virtual_voltages =  np.matmul(virt_gate_obj.virtual_gate_matrix,current_voltages_formatted)

		return virtual_voltages[voltage_key]


	def set_all_zero(self):
		'''
		set all dacs in the gate set to 0. Is ramped down 1 per 1
		'''
		print("In progress ..")
		for gate_name, dac_location in self.hardware.dac_gate_map.items():
			self._set_voltage(gate_name, 0)
		print("All gates set to 0!")

	def update_virtual_gate_entry(self, virtual_gate_set, gate_name, gate_names_CC, values):
		'''
		update a row in the virtual gate matrix

		Args:
			virtual_gate_set (str) : name of the virtual gate matrix you want to update as defined in the hardware class.
			gate_name (str) : name of the row where changes need to occur (e.g. 'P1')
			gate_names_CC (list<str>) : list with the names of the gates that need to be updated.
			values (np.ndarray) : array with the new values.
		'''
		idx = self.hardware.virtual_gates.index(virtual_gate_set)
		virtual_gate_item = self.hardware.virtual_gates[idx]

		i = virtual_gate_item.real_gate_names.index(gate_name)
		j = np.empty([len(gate_names_CC)], dtype=np.int)
		for k in range(len(gate_names_CC)):
			j[k] = virtual_gate_item.real_gate_names.index(gate_names_CC[k])

		np.asarray(virtual_gate_item.virtual_gate_matrix)[i,j] = np.asarray(values)

		self.hardware.sync_data()

	@property
	def gv(self):
		'''
		get a dict with all the gate value of dacs (real values).
		Return:
			real_voltages (dict<str, double>): dict with gate name as key and the corresponding voltage as value
		'''
		for gate_name, my_dac_location in self.hardware.dac_gate_map.items():
			self._gv[gate_name] = self._get_voltage(gate_name)

		return copy.copy(self._gv)

	@gv.setter
	def gv(self, my_gv):
		'''
		setter for voltages
		'''
		names = list(my_gv.keys())
		voltages = list(my_gv.values())

		for i in range(len(names)):
			self._set_voltage(names[i], voltages[i])


if __name__ == '__main__':
	from V2_software.drivers.virtual_gates.examples.hardware_example import hardware_example 
	from V2_software.drivers.virtual_gates.instrument_drivers.virtual_dac import virtual_dac

	my_dac_1 = virtual_dac("dac_a", "virtual")
	my_dac_2 = virtual_dac("dac_b", "virtual")
	my_dac_3 = virtual_dac("dac_c", "virtual")
	my_dac_4 = virtual_dac("dac_d", "virtual")

	hw =  hardware_example("hw")
	my_gates = gates("my_gates", hw, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])
	# print(my_gates.vgv)
	print(my_gates.vB0())
	my_gates.vB0(1200)
	my_gates.vB0(1800)
	gv = my_gates.gv
	print(my_gates.vB0())
	my_gates.set_all_zero()
	my_gates.gv = gv
	print(my_gates.vB0())
	print(np.array(my_gates.hardware.virtual_gates['general'].virtual_gate_matrix))

	# my_gates.update_virtual_gate_entry("general", "B0", ["B0", "B1", "B2",], [1,0.8,0.3])
	print(np.array(my_gates.hardware.virtual_gates['general'].virtual_gate_matrix))
	print(my_dac_1)