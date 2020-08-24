"""
define a function that loads the HVI file that will be used thoughout the experiments
"""
import keysightSD1
import core_tools.HVI.AWG_parallel_test_no_dig as ct

HVI_ID = "HVI_single_shot_no_dig.HVI"


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
	error = HVI.open(ct.__file__[:-11] + "single_shot_alike.HVI")
	print(error)

	error = HVI.assignHardwareWithUserNameAndSlot("Module 0",1,2)
	print('chassis assignment',error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 1",1,3)
	print('chassis assignment',error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 2",1,4)
	print('chassis assignment',error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 3",1,5)
	print('chassis assignment',error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 4",1,7)
	print('chassis assignment',error)

	error = HVI.compile()
	print(error)
	error = HVI.load()
	print(error)
	# error = HVI.load()
	# print(error)
	

	error = HVI.start()
	print(error)

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
	length = int(playback_time/10 + 200) # extra delay, seems to be needef or the digitizer.

	for awgname, awg in AWGs.items():
		err = awg.awg.writeRegisterByNumber(2, int(nrep))
		err = awg.awg.writeRegisterByNumber(3, int(length))
		
	# start sequence
	err = AWGs['AWG1'].awg.writeRegisterByNumber(1, 0)
	err = AWGs['AWG1'].awg.writeRegisterByNumber(0,int(1))
