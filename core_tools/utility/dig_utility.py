from core_tools.drivers.M3102A import SD_DIG, MODES, DATA_MODE
from core_tools.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG


MODES = MODES

def autoconfig_digitizer(digitizer, firmware, mode):
    firmware_loader(digitizer, firmware, mode)
    #set digitzer to use software triggering and return 1 point per channel --> average the full trace.
    t_measure = 1e6 #1us (unit ns)
    cycles = 1 # just measure once.
    digitizer.set_digitizer_software(t_measure, cycles, data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES, 
                                  channels = [1,2,3,4], fourchannel = True)


    digitizer.daq_flush(1)
    digitizer.daq_flush(2)
    digitizer.daq_flush(3)
    digitizer.daq_flush(4)

    print("testing digitizer:",digitizer.measure())

def autoconfig_dig_v2(digitzer, average):
    '''
    Args:
        digitzer (Insturment) : qcodes instrement representing the digitizer
        average (bool) : average yes/No ..
    '''
    if average == True:
        if digitzer.mode == MODES.NORMAL:
            firmware_loader(digitzer, M3102A_AVG, MODES.AVERAGE)
    else:
        if digitzer.mode == MODES.AVERAGE:
            firmware_loader(digitzer, M3102A_CLEAN, MODES.NORMAL)
    
    digitzer.set_digitizer_software(1e6, 1, data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES, 
                                  channels = [1,2,3,4], fourchannel = True)


def test_digitizer_hvi2(digitizer:SD_DIG, requested_mode: MODES):
    '''
    Args:
        digitizer: M3102A digitizer
        requested_mode: requested acquisition mode after test
    '''
    digitizer.set_acquisition_mode(MODES.NORMAL)
    digitizer.set_digitizer_software(1e6, 1, data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES,
                                     channels = [1,2,3,4])
    digitizer.daq_flush_multiple(0b1111)
    v_str = ','.join([f'{v:7.3f}' for v in digitizer.measure()])
    print(f"testing digitizer: {v_str} mV")

    digitizer.set_acquisition_mode(requested_mode)
