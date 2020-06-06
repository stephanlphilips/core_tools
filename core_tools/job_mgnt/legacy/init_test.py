import sqlite3
import threading as t
import logging
import time
from job_manager import CalibrationMaster
import qubit_class

identifier = "init_default"

class init_default(CalibrationMaster):
	def __init__(self, my_qubit, my_libraries ):
		CalibrationMaster.__init__(self)
		self.my_qubit = my_qubit
		self.active = 0
		self.update_time_interval = 10000
		self.execure_during_idle = True
		self.execute_during_exp = True
		self.number_of_meas_run_before_update = 200
		# self.stash_table()
		self.calibration_params += self.make_qubit_dep_param('f_rabi_TARGET', 'DOUBLE', 'Hz')
		self.calibration_params += self.make_qubit_dep_param('f_rabi_POWER', 'DOUBLE', 'Hz')

		# self.dependencies = [(name_module, parameter=opt,qubit_s=opt, parameter_arugments=opt)]
		# self.load_data()
		self.save_calib_results([('f_rabi_target_qb_1',1e-7),('f_rabi_power_qb_1',3.4e3)])
		self.save_calib_results([('f_rabi_target_qb_2',1e-7),('f_rabi_power_qb_2',3.7e3),('f_rabi_target_qb_1',1e-7),('f_rabi_power_qb_1',3.4e3)])
		self.save_calib_results([('f_rabi_target_qb_4',1e-7),('f_rabi_power_qb_4',3.7e3),('f_rabi_target_qb_1',1e-7),('f_rabi_power_qb_1',3.4e3)])
		self.save_calib_results([('f_rabi_target_qb_4',1e-7),('f_rabi_power_qb_4',3.7e3),('f_rabi_target_qb_5',1e-7),('f_rabi_power_qb_5',3.4e3)])

	def get_awg_sequence(self):
		raise NotImplementedError()

	def construct_awg_sequence(self):
		raise NotImplementedError()

	def calibrate(self, param_nam[], param_value=[]):
		pass

	def get_value(self,  ):
		return [(1, 'unit')]

 

a = init_default(qubit_class.my_qubits(), None)
# print(a.get_unit('time'))
# print(a.get_parameter_latest(['time', 'f_rabi_power_qb_1', ' f_rabi_power_qb_2'],[('f_rabi_power_qb_4', 'NULL'),('f_rabi_power_qb_1', 3.1e3)]))
# # a.get_awg_sequence()
# print(a.do_calib(num_exp_run=210))
