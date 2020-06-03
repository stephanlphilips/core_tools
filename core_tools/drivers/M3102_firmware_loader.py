"""
Standard firmware files for the digitizer of the V2 setup.

CLEAN : normal image, revert to the normal AWG.
AVG : special image with MAV and interator. A custom qcodes driver needs to be used for that.
"""
M3102A_CLEAN = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/clean_4_41.sbp"
M3102A_AVG = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/averaging_firmware_1_41.sbp"

from core_tools.drivers.M3102A import MODES

def firmware_loader(dig, file):
	"""
	load a custom firmware image on board of the digitizer

	Args:
		dig <SD_dig (qcodes instrument) : digitzer object
		file (string) : location where to find the new firmware
	"""
	err = dig.SD_AIN.FPGAload(file)
	if file == M3102A_CLEAN:
		dig.set_aquisition_mode(MODES.NORMAL)
	else:
		dig.set_aquisition_mode(MODES.AVERAGE)


	if err == 0 :
		print("Succesful upload of the firmware")
	else:
		print("upload failed, error code {} (see keysight manual for instructions)".format(err))

if __name__ == '__main__':
	firmware_loader(dig, M3102A_CLEAN)