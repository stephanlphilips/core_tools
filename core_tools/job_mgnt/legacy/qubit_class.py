class my_qubits(object):
	"""docstring for my_qubits"""
	def __init__(self):
		return

	def get_qubit_names(self):
		return ["Qb_1", "Qb_2", "Qb_3", "Qb_4", "Qb_5"]

	def get_interconnected_qubits(self):
		# Format tuple[(qubit1 qubit2),(qubit2, qubit3)]
		return [("Qb_1", "Qb_2"),("Qb_2", "Qb_3"),("Qb_3", "Qb_4"),("Qb_4", "Qb_5")]

	def get_qubits_next_to_reservoir(self):
		pass

	def get_gate_of_qubit(self, name, type="awg"):
		pass

	def get_gate_inbetween_qubits(self, name_QB1, name_QB2, type="awg"):
		# resorvoir is considered a big qubit
		pass
