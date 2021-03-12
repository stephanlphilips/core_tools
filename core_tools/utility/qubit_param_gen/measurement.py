from dataclasses import dataclass, field
import numpy as np

@dataclass
class setpoint_mgnt:
	names : tuple = field(default_factory=lambda: tuple())
	labels : tuple = field(default_factory=lambda: tuple())
	units : tuple = field(default_factory=lambda: tuple())
	shapes : tuple = field(default_factory=lambda: tuple())
	setpoints : tuple = field(default_factory=lambda: tuple())
	setpoint_shapes : tuple = field(default_factory=lambda: tuple())
	setpoint_names : tuple = field(default_factory=lambda: tuple())
	setpoint_labels : tuple = field(default_factory=lambda: tuple())
	setpoint_units : tuple = field(default_factory=lambda: tuple())

	def add_channels(self, *suffixes):
		s = setpoint_mgnt()
		for suffix in suffixes:
			s.names += self.names[0]+'_'+suffix
			s.labels += self.labels[0]+'_'+suffix
			s.units += self.units[0]
			s.shapes += self.shapes[0]
			s.setpoints += self.setpoints[0]
			s.setpoint_shapes += self.setpoint_shapes[0]
			s.setpoint_names += self.setpoint_names[0]+'_'+suffix
			s.setpoint_labels += self.setpoint_labels[0]+'_'+suffix
			s.setpoint_units += self.setpoint_units[0]
		
		return s

	def __add__(self, other):
		added = setpoint_mgnt()
		added.names = self.names + other.names
		added.labels = self.labels + other.labels
		added.units = self.units + other.units
		added.shapes = self.shapes + other.shapes
		added.setpoints = self.setpoints + (other.setpoints, )
		added.setpoint_shapes = self.setpoint_shapes + (other.setpoint_shapes, )
		added.setpoint_names = self.setpoint_names + (other.setpoint_names, )
		added.setpoint_labels = self.setpoint_labels + (other.setpoint_labels, )
		added.setpoint_units = self.setpoint_units + (other.setpoint_units, )
		return added

@dataclass
class measurement:
	name : str
	chan   : tuple
	threshold : float   = None
	accept : int        = -1
	phase : float  		= None
	flip : str			= None
	_0_on_high : bool   = True
	__nth_readout : int = 0
	
	def __post_init__(self):
		if self.threshold is None and self.accept != -1:
			raise ValueError('Cannot accept data without threshold.')

		if self.threshold is not None and self.phase is None:
			raise ValueError('Cannot threshold without phase correcting data (put 0 to select I channel).')
		if len(self.chan) != 2:
			raise ValueError(f'Please provice the I and Q channel, now provided {self.chan}')
	
	def set_nth_read(self, n):
		self.__nth_readout = n

	def format_raw(self, raw, n_readouts):
		data_I = np.asarray(raw[self.chan[0]-1])
		data_I = data_I.reshape([int(data_I.size/n_readouts), n_readouts])[:, self.__nth_readout]
		data_Q = np.asarray(raw[self.chan[1]-1])
		data_Q = data_Q.reshape([int(data_Q.size/n_readouts), n_readouts])[:, self.__nth_readout]
		
		if self.phase is not None:
			data_complex = (data_I + 1j*data_Q)*np.exp(1j*self.phase)
			return (data_complex.real, )
		
		return (data_I, data_Q)

	def get_selection(self, raw, n_readouts):
		raw_measurement = self.format_raw(raw, n_readouts)[0]
		out = np.ones(raw_measurement.shape, dtype=np.bool)

		if self.threshold is None:
			return (np.invert(out), len(out))

		if self._0_on_high == False:
			selection = np.where(raw_measurement < self.threshold)[0]
		else:
			selection = np.where(raw_measurement > self.threshold)[0]
		
		out[selection] = 0

		return (out, len(selection))

	def get_meas(self, raw, indexes, qubit_outcomes, n_readouts):
		sel, n_selected = self.get_selection(raw, n_readouts)
		meas_points = sel[indexes]

		if self.threshold is None:
			return (self.format_raw(raw)[0], np.average(self.format_raw(raw)))

		if self.flip is not None:
			if self.flip not in qubit_outcomes.keys():
				raise ValueError(f'flipping on {self.flip} is not present in any of the measurement names? Please check your naming')
			meas_points = np.bitwise_xor(meas_points, np.invert(qubit_outcomes[self.flip]))
		if len(indexes) == 0:
			return (meas_points, 0 ,)
		
		return (meas_points, len(np.where(meas_points == True)[0])/len(indexes) ,)

	def get_setpoints_raw(self, n_rep):
		s = setpoint_mgnt()
		s.names  = (f'RAW_{self.name}'.replace(' ', '_'),)
		s.labels = (f'{self.name} raw data',)
		s.units  = ('mV',)
		s.shapes = ((n_rep,),)
		s.setpoints = (tuple(np.arange(n_rep)),)
		s.setpoint_shapes = ((n_rep,),)
		s.setpoint_names =  (f'measurement_trigger_{self.__nth_readout}_ch{self.chan[0]}_ch{self.chan[1]}',)
		s.setpoint_labels = (f'measurement trigger {self.__nth_readout} ch{self.chan[0]} and ch{self.chan[1]}',)
		s.setpoint_units =  ('#',)

		if self.phase is None:
			return s.add_channels(f'ch{self.chan[0]}', f'ch{self.chan[1]}')
		else:
			return s

	def get_setpoints(self):
		s = setpoint_mgnt()

		if self.accept == -1:
			s.names  = (f'{self.name}'.replace(' ', '_'),)
			s.labels = (f'{self.name}',)
			s.units  = ('%',)
			s.shapes = ((),)
		else:
			s.names  = (f'RAW_selection_{self.name}'.replace(' ', '_'),)
			s.labels = (f'{self.name} selection',)
			s.units  = ('#',)
			s.shapes = ((),)

		return s

class measurement_manager():
	def __init__(self):
		self.measurements = []
		self.n_rep = 500
		self.n_readouts = 0

	def add(self, *measurements):
		'''
		Add measurement for the current trigger.
		'''
		for meas in measurements:
			meas.set_nth_read(self.n_readouts)
			self.measurements += [meas]
		self.n_readouts = self.n_readouts + 1

	def set_repetitions(self, rep):
		self.n_rep = rep

	@property
	def state_selectors(self):
		state_selectors = []

		for meas in self.measurements:
			if meas.accept != -1:
				state_selectors.append(meas)

		return state_selectors

	@property
	def measurement_outcomes(self):
		meas_outcomes = []

		for meas in self.measurements:
			if meas.accept == -1:
				meas_outcomes.append(meas)

		return meas_outcomes
	
	def format_data(self, data):
		# check if input shape is as expected
		# if data[0].shape != (self.n_rep, 4):
		# 	raise ValueError(f'number of readout ({data.shape}) not the same of the expected({(self.n_rep, self.n_readouts)})?')

		state_selectors = self.state_selectors
		meas_outcomes   = self.measurement_outcomes 

		data_out = []
		# 1) pull out raw data
		for meas_op in state_selectors + meas_outcomes:
			data_out += meas_op.format_raw(data, self.n_readouts)

		# 2) select on qubit basis
		selector = np.ones((self.n_rep,), dtype=np.bool)
		for sel in state_selectors:
			raw_selection, n_selected = sel.get_selection(data, self.n_readouts)
			data_out += [n_selected]
			
			if sel.accept == 0:
				selector = np.bitwise_and(np.invert(raw_selection), selector)
			else:
				selector = np.bitwise_and(raw_selection, selector)

		idx = np.where(selector == True)[0]

		# 3) global selection
		if len(state_selectors) > 1:
			data_out += [len(idx)]

		# 4) qubit outcomes
		qubit_outcomes = dict()
		for meas_op in meas_outcomes:
			data_raw, spin_up_fraction = meas_op.get_meas(data, indexes = idx, qubit_outcomes=qubit_outcomes, n_readouts=self.n_readouts)
			data_out += (spin_up_fraction, )
			qubit_outcomes[meas_op.name] = data_raw

		return data_out

	def generate_setpoints_information(self):
		s = setpoint_mgnt()

		state_selectors = self.state_selectors
		meas_outcomes   = self.measurement_outcomes 

		for selector in state_selectors:
			s += selector.get_setpoints_raw(self.n_rep)

		for meas_op in meas_outcomes:
			s += meas_op.get_setpoints_raw(self.n_rep)

		for selector in state_selectors:
			s += selector.get_setpoints()

		if len(state_selectors) > 1:
			s_tot = setpoint_mgnt()
			s_tot.names  = ('total_states_selected',)
			s_tot.labels = ('total states selected',)
			s_tot.units  = ('#',)
			s_tot.shapes = ((),)
			s += s_tot

		for meas_op in meas_outcomes:
			s += meas_op.get_setpoints()

		return s

if __name__ == '__main__':
	m1=measurement('PSB_12_init', [1,2], accept=0, threshold=0.5, phase=0.3)
	m2=measurement('PSB_12_read', [1,2], threshold=0.5, phase=0.3)

	test_data = np.random.random([50,3,4])
	d = m1.format_raw(test_data)
	# print(d)
	idx = np.arange(25)
	# d = m1.get_meas(test_data, indexes=idx)
	d = m1.get_selection(test_data)
	# print(d)

	s1= m1.get_setpoints()
	s2= m1.get_setpoints_raw(50)
	s = setpoint_mgnt()
	# print(s+s2+s1)

	m_mngr = measurement_manager()
	m_mngr.add(m1)
	m_mngr.add(m2)
	m_mngr.set_repetitions(50)

	print(m_mngr.generate_setpoints_information())