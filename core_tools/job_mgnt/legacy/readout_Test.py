import threading as th
import logging
import time
import inspect

identifier = "default"

class default(th.Thread):
	"""docstring for ClassName"""
	def __init__(self):
		self.active = 0
	
	def run(self):
		logging.debug('running')
		return

	def pause(self):
		if self.active == 1:
			self.active = 0

	def start_meas(self):
		logging.debug('Meas_Started')
		self.active = 1;

	def get_id(self):
		return 'my_id'

	def do_calib(self):
		if self.active == 0:
			self.active = 1
			return True

	def calibrate(self):
		print('calibrating something')
		time.sleep(0.4)


