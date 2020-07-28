M3102A_CLEAN = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/clean_4_41.sbp"
M3102A_AVG = "C:/V2_code/FPGA_Bitstreams/Digitizer_FW1.41/averaging_firmware_1_41.sbp"
# from core_tools.drivers.M3102A import MODES

from projects.keysight_measurement.M3102A import MODES

def firmware_loader(dig, file, av_mode):
    """
    load a custom firmware image on board of the digitizer

    Args:
        dig <SD_dig (qcodes instrument) : digitzer object
        file (string) : location where to find the new firmware
    """
    err = dig.SD_AIN.FPGAload(file)
    if av_mode == 'normal':
        dig.set_aquisition_mode(MODES.NORMAL)
    elif av_mode == 'average':
        dig.set_aquisition_mode(MODES.AVERAGE)
    else:
        raise ValueError("Average mode must be normal or average")

    if err == 0 :
        print("Succesful upload of the firmware")
    else:
        print("upload failed, error code {} (see keysight manual for instructions)".format(err))