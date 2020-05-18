from pulse_lib.base_pulse import pulselib
from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib_quad_dot,return_pulse_lib_nodar_sample, return_pulse_lib_virt_gate_exp
import qcodes as qc

import qcodes.instrument_drivers.Keysight.SD_common.SD_AWG as keysight_awg
import qcodes.instrument_drivers.Keysight.SD_common.SD_DIG as keysight_dig

def start_pulse_lib(sample = "quad", hardware = None):
	station = qc.Station.default
	if sample == 'quad':
		pulse = return_pulse_lib_quad_dot(hardware, station.AWG1, station.AWG2, station.AWG3, station.AWG4)
		virtual_gate_set_1 = None
		IQ_stuff = None
		pulse.cpp_uploader.resegment_memory()
		# dirty since pulse is atm no qcodes instrument ..
		station.pulse = pulse
	elif sample == 'DEMO18':
		pulse = return_pulse_lib_nodar_sample(hardware, station.AWG1, station.AWG2, station.AWG3, station.AWG4)
		virtual_gate_set_1 = None
		IQ_stuff = None
		pulse.cpp_uploader.resegment_memory()
		# dirty since pulse is atm no qcodes instrument ..
		station.pulse = pulse
	else:
		pulse = return_pulse_lib_quad_dot(hardware)
		IQ_stuff = None
		virtual_gate_set_1 = None

	
	return pulse, virtual_gate_set_1, IQ_stuff

def resegment_pulselib():
	station = qc.Station.default
	station.pulse.cpp_uploader.resegment_memory()