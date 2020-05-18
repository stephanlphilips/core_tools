from V2_software.drivers.M3102A.M3102A import SD_DIG, MODES, DATA_MODE
from V2_software.drivers.M3102A.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
import qcodes as qc

def autoconfig_digitizer(firmware = M3102A_AVG):
	station = qc.Station.default
	#dig = SD_DIG(name ="M3102A_digitizer_", chassis = 0, slot = 6)
	if firmware is not None:
		firmware_loader(station.dig, firmware)

	#set digitzer to use software triggering and return 1 point per channel --> average the full trace.
	t_measure = 1e4 #1ms (unit ns)
	cycles = 1 # just measure once.

	station.dig.set_digitizer_software(t_measure, cycles, data_mode=DATA_MODE.AVERAGE_TIME_AND_CYCLES, channels = [1,2])

	station.dig.daq_flush(1)
	station.dig.daq_flush(2)
	station.dig.daq_flush(3)
	station.dig.daq_flush(4)
	
	print("testing digitzer :: ")
	print(station.dig.measure())