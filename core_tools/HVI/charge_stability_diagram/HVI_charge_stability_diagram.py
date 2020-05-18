"""
define a function that loads the HVI file that will be used thoughout the experiments
"""
import warnings

try:
    import keysightSD1
except:
    warnings.warn("\nAttemting to use a file that needs Keysight AWG libraries. Please install if you need them.\n")

import V2_software.HVI_files.charge_stability_diagram as ct
import time

HVI_ID = "HVI_charge_stability_diagram.HVI"

def load_HVI(AWGs, channel_map, *args,**kwargs):
	"""
	load a HVI file on the AWG.
	Args:
		AWGS (dict <str, QCoDeS Intrument>) : key is AWGname, value awg object. 
		channel_map (dict <str, (tuple <str, int>)) : key is channelname, value is AWGname, channel number
	Returns:
		HVI (SD_HVI) : keyisight HVI object.	
	"""

	for channel, channel_loc in channel_map.items():
		# 6 is the magic number of the arbitary waveform shape.
		AWGs[channel_loc[0]].awg_stop(channel_loc[1])
		AWGs[channel_loc[0]].set_channel_wave_shape(keysightSD1.SD_Waveshapes.AOU_AWG,channel_loc[1])
		AWGs[channel_loc[0]].awg_queue_config(channel_loc[1], 1)

			
	HVI = keysightSD1.SD_HVI()
	a = HVI.open(ct.__file__[:-11] + "HVI_charge_stability_diagram.HVI")

	error = HVI.assignHardwareWithUserNameAndSlot("Module 0",0,2)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 1",0,3)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 2",0,4)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 3",0,5)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 4",0,6)
	
	HVI.compile()
	HVI.load()

	return HVI


"""
define a function that applies the settings to a HVI file and then compiles it before the experiment.
"""

def set_and_compile_HVI(HVI, playback_time, n_rep, *args, **kwargs):
	"""
	Function that set values to the currently loaded HVI script and then performs a compile step.
	Args:
		HVI (SD_HVI) : HVI object that is already loaded in the memory. Will be loaded by default.
		playback_time (int) : #ns to play the sequence (assuming every point is one ns)
		n_rep (int) : number of repertitions. This is the number of reperititons that you set in the pulselub object.
	Returns:
		None
	"""
	# No need ... We will overwrite the registers instead of a re-compile for updated speed :-)
	pass

"""
Function to load the HVI on the AWG. This will be the last function that is executed in the play function.

This function is optional, if not defined, there will be just two calls,
	HVI.load()
	HVI.start()
So only define if you want to set custom settings just before the experiment starts. Note that you can access most settings via HVI itselves, so it is better to do it via there.
"""

def excute_HVI(HVI, AWGs, channel_map, playback_time, n_rep, *args, **kwargs):
	"""
	load HVI code.
	Args:
		AWGS (dict <str, QCoDeS Intrument>) : key is AWGname, value awg object. 
		channel_map (dict <str, (tuple <str, int>)) : key is channelname, value is AWGname, channel number
		playback_time (int) : #ns to play the sequence (assuming every point is one ns)
		n_rep (int) : number of repertitions. This is the number of reperititons that you set in the pulselub object.
	"""

	nrep = int(n_rep)
	step = 1

	length = int(playback_time/10 + 20)

	for awgname, awg in AWGs.items():
		awg.writeRegisterByNumber(3, int(length))

	dig = kwargs['digitizer'] 
	t_single_point = kwargs['t_measure']
	npt = kwargs['number_of_points']

	t_single_point_formatted = int((t_single_point)/10) # divide by 10 since 100MHz clock (160 ns HVI overhead)

	dig.writeRegisterByNumber(2, npt)
	dig.writeRegisterByNumber(3, t_single_point_formatted)
	
	if 'averaging' in kwargs:
		dig.set_meas_time(kwargs['t_measure'])
		dig.set_MAV_filter(16,1)

	HVI.start()


if __name__ == '__main__':
	
	"""
	Let's now set these setting to the AWG, for this peculiar experiment.
	"""
	from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib

	import V2_software.drivers.M3102A as M3102A
	from V2_software.drivers.M3102A.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
	from qcodes.instrument_drivers.Keysight.SD_common.SD_AWG import SD_AWG


	dig = M3102A.SD_DIG("digitizer1", chassis = 0, slot = 7)
	firmware_loader(dig, M3102A_AVG)

	AWG1 = SD_AWG("AWG1", chassis = 0, slot = 2, channels=4, triggers=8)
	AWG2 = SD_AWG("AWG2", chassis = 0, slot = 3, channels=4, triggers=8)
	AWG3 = SD_AWG("AWG3", chassis = 0, slot = 4, channels=4, triggers=8)
	AWG4 = SD_AWG("AWG4", chassis = 0, slot = 5, channels=4, triggers=8)

	pulse, _, _ = return_pulse_lib(AWG1, AWG2, AWG3, AWG4)

	test  = pulse.mk_segment()
	test.P1 += 100
	test.P1.wait(1e6)

	my_seq = pulse.mk_sequence([test])

	# set number of repetitions (default is 1000)
	my_seq.n_rep = 1000
	my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)

	# my_seq.upload([0])
	# my_seq.start([0])
	# # start upload after start.
	# my_seq.upload(0)
	# # upload is released shortly after called (~5ms, upload is without any gil.)

