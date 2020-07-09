from core_tools.job_mgnt.calibrations.calibration_single import calibration_generic, CalibrationError
from core_tools.job_mgnt.calibrations.utility import param_mngr

from core_tools.GUI.keysight_videomaps.data.scan_generator_Virtual import construct_1D_scan_fast

SD_gates = {'SD_1':'SD1_P', 'SD_2':'SD2_P', 'SD_2':'SD2_P'}

class SD_cal(calibration_generic):
	@dataclass
	class SD_data:
		v_peak : float
		v_off : float
		sigma : float
		amp : float
		_units = {'v_peak'='mV', 'v_off' = 'mV', 'sigma' = 'mV', 'amp' = 'mV'}

	def __init__(self):
		self.update_interval = 30
		self.auto_update = True

		self.getter = param_mngr('transition_line_lock_P', unit='mV') + SL.dots + SD_data

	def calibrate(self, param):
		pass
