import threading as th
import logging
import time
identifier = "default"

class default(th.Thread):
	"""docstring for ClassName"""
	# def __init__(self):
	# 	active = 0
	
	def run(self):
		logging.debug('running')
		self.active = 0
		self.calibration_pending = False
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
		# Checks if calibration needs to be done
		return False

	def calibrate(self, force=False, called_by_dep=False):
		# Checks if still needed.

		# executes calibration
		time.wait(1)
		return True
