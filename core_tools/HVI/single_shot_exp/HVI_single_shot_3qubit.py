"""
define a function that loads the HVI file that will be used thoughout the experiments
"""
import keysightSD1
import core_tools.HVI.single_shot_exp as ct

HVI_ID_3 = "HVI_single_shot_3qubit.HVI"


def load_HVI_3(AWGs, channel_map, *args,**kwargs):
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
	error = HVI.open(ct.__file__[:-11] + "HVI_single_shot_3qubit.HVI")
	print(error)

	error = HVI.assignHardwareWithUserNameAndSlot("Module 0",1,2)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 1",1,3)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 2",1,4)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 3",1,5)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 4",1,6)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 5",1,7)
	print(error)
	error = HVI.assignHardwareWithUserNameAndSlot("Module 6",1,8)
	print(error)

	error = HVI.compile()
	print(error)
	error = HVI.load()
	print(error)
	error = HVI.load()
	print(error)
	

	error = HVI.start()
	print(error)

	return HVI


"""
define a function that applies the settings to a HVI file and then compiles it before the experiment.
"""

def set_and_compile_HVI_3(HVI, playback_time, n_rep, *args, **kwargs):
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

def excute_HVI_3(HVI, AWGs, channel_map, playback_time, n_rep, *args, **kwargs):
	"""
	load HVI code.
	Args:
		AWGS (dict <str, QCoDeS Intrument>) : key is AWGname, value awg object. 
		channel_map (dict <str, (tuple <str, int>)) : key is channelname, value is AWGname, channel number
		playback_time (int) : #ns to play the sequence (assuming every point is one ns)
		n_rep (int) : number of repertitions. This is the number of reperititons that you set in the pulselub object.
	"""

	nrep = int(n_rep)
	length = int(playback_time/10 + 200) # extra delay, seems to be needed or the digitizer.

	for awgname, awg in AWGs.items():
		err = awg.awg.writeRegisterByNumber(2, int(nrep))
		err = awg.awg.writeRegisterByNumber(3, int(length))

	dig = kwargs['digitizer'] 
	dig_wait_1 = kwargs['dig_wait_1']
	dig_wait_2 = kwargs['dig_wait_2']
	dig_wait_3 = kwargs['dig_wait_3']


	delay_1 = int(dig_wait_1/10)
	delay_2 = int(dig_wait_2/10)
	delay_3 = int(dig_wait_3/10)

	if delay_2-delay_1 < 200 :
		raise ValueError('triggers 1 and 2 are too close, at least 2 us distance is needed.')
	if delay_3-delay_2 < 200 :
		raise ValueError('triggers 2 and 3 are too close, at least 2 us distance is needed.')	

	time_shift = int(50/10)
	err = dig.SD_AIN.writeRegisterByNumber(2, int(nrep))
	err = dig.SD_AIN.writeRegisterByNumber(3, int(delay_1 + 43))
	err = dig.SD_AIN.writeRegisterByNumber(4, int(delay_2-delay_1-4))
	err = dig.SD_AIN.writeRegisterByNumber(5, int(delay_3-delay_2-4))
	err = dig.SD_AIN.writeRegisterByNumber(6, int(length-delay_3+45))

	if 'averaging' in kwargs:
		dig.set_meas_time(kwargs['t_measure'], fourchannel=True)
		dig.set_MAV_filter(16,1, fourchannel=True)
	# start sequence
	err = AWGs['AWG1'].awg.writeRegisterByNumber(1, 0)
	err = AWGs['AWG1'].awg.writeRegisterByNumber(0,int(1))
