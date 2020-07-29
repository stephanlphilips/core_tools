from core_tools.job_mgnt.calibrations.calibration_single import calibration_generic, CalibrationError
from core_tools.job_mgnt.calibrations.utility import param_mngr

from core_tools.GUI.keysight_videomaps.data.scan_generator_Virtual import construct_1D_scan_fast

SD_gates = {'SD_1':'SD1_P', 'SD_2':'SD2_P', 'SD_2':'SD2_P'}

class SD_cal(calibration_generic):
	def __init__(self):
		self.update_interval = 30
		self.auto_update = True

		self.getter = param_mngr('SD', unit='mV') + SL.SD

	def calibrate(self):
		for param in getter:
			SD_gate = SD_gates[param.name]

			# construct global cal_mgmt --> enable RF readout at dot 1
			CAL_MGRG.rf_readout(['dot_1'], enable=True)

			scan_obj = construct_1D_scan_fast(SD_gate, swing=5, n_pt=100, t_step=5, biasT_corr=10, pulse_lib, digitizer)
			fit_voltage = fit_SD(scan_obj)

			if abs(fit_voltage) < 2:
				SD_gate_dc = self.station.gates.getattr()
				SD_gate_dc.(SD_gate_dc.get + fit_voltage)

				self.save_data(param, SD_gate_dc(), state=self.SUCCESS)
			else:
				self.save_data(param, state=self.FAIL)
				raise CalibrationError('finding most sensitive spot of SD failed.')

		# repeat 3 times to move toward (in case there is a slight mismatch between DC/AC conversion)
		self.reiterate(3)