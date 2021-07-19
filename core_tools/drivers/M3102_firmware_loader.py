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
        dig.set_acquisition_mode(MODES.NORMAL)
    elif av_mode == 'average':
        dig.set_acquisition_mode(MODES.AVERAGE)
    else:
        raise ValueError("Average mode must be normal or average")

    if err == 0 :
        print("Succesful upload of the firmware")
    else:
        print("upload failed, error code {} (see keysight manual for instructions)".format(err))