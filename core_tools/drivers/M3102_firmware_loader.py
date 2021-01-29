M3102A_CLEAN = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/clean_4_41.sbp"
M3102A_AVG = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/averaging_firmware_1_41.sbp"

from projects.keysight_measurement.M3102A import MODES, is_sd1_3x

def firmware_loader(dig, file, mode):
    """
    load a custom firmware image on board of the digitizer

    Args:
        dig <SD_dig (qcodes instrument) : digitzer object
        mode (int) : mode of the digitizer
    """
    if is_sd1_3x:
        raise Exception('firmware_loader cannot be used with SD1 3.x.')

    err = dig.SD_AIN.FPGAload(file)
    if err == 0 :
        print("Succesful upload of the firmware")
    else:
        print("upload failed, error code {} (see keysight manual for instructions)".format(err))

    if mode == MODES.NORMAL:
        dig.set_aquisition_mode(MODES.NORMAL)
    else:
        dig.set_aquisition_mode(MODES.AVERAGE)