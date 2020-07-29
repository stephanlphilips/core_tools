from projects.keysight_measurement.M3102A import SD_DIG, MODES, DATA_MODE
from core_tools.drivers.M3102_firmware_loader import firmware_loader

def autoconfig_digitizer(digitizer, firmware = None, av_mode = None):
    if firmware is not None:
        if av_mode is None:
            raise ValueError('Please specify average mode (normal or average) when specifying firmware')
        firmware_loader(digitizer, firmware, av_mode)

    #set digitzer to use software triggering and return 1 point per channel --> average the full trace.
    t_measure = 1e6 #1us (unit ns)
    cycles = 1 # just measure once.
    digitizer.set_digitizer_software(t_measure, cycles, data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES, 
                                  channels = [1,2], fourchannel = True)

    digitizer.daq_flush(1)
    digitizer.daq_flush(2)
    digitizer.daq_flush(3)
    digitizer.daq_flush(4)

    print("testing digitizer:",digitizer.measure())