'''
parameter class for calibration object. Similar to qcodes paramters, but with some extra quirks.
'''

class CalibrationParameter():
	def __init__(self, name, label=None, unit='a.u.'):
		self.name = name
		self.label = label if label is not None else name
		self.unit = unit
		self.query =  None

	def add_queryclass(self, my_query):
		self.query = my_query

	def sort(self, order='DESC'):
		'''
		sort the data in the query small first (ASC)/big first (DESC)
		''' 
		self.query.order_by = self.name +  ' ' +  order

	def get(self):
		'''
		tell to the db that you are interested in fetching this parameter
		'''
		self.query.columns_to_fetch += [self.name]

	def __lt__(self, other):
		self.get()
		self.query.where += '{} < {}'.format(self.name, str(other))

	def __le__(self, other):
		self.get()
		self.query.where += '{} <= {}'.format(self.name, str(other))

	def __eq__(self, other):
		self.get()
		if other is not None:
			self.query.where += '{} = {}'.format(self.name, str(other))
		else:
			self.query.where += '{} IS NULL'.format(self.name)

	def __ne__(self, other):
		self.get()
		if other is not None:
			self.query.where += '{} != {}'.format(self.name, str(other))
		else:
			self.query.where += '{} IS NOT NULL'.format(self.name)
	def __ge__(self, other):
		self.get()
		self.query.where += '{} >= {}'.format(self.name, str(other))

	def __gt__(self, other):
		self.get()
		self.query.where += '{} > {}'.format(self.name, str(other))

	def __repr__(self):
		return self.name

if __name__ == '__main__':
	t = CalibrationParameter('testparam')
