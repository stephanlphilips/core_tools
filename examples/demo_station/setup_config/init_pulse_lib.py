from pulse_lib.base_pulse import pulselib
from pulse_lib.virtual_channel_constructors import IQ_channel_constructor


def init_pulse_lib(hardware = None, *args):
    """
    return pulse library object

    Args:
        hardware : hardware class (if not present, put None)
        *args : AWG instances you want to add (qcodes AWG object)
    """
    pulse = pulselib(backend='M3202A')

    # add to pulse_lib
    for i in range(len(args)):
        pulse.add_awgs('AWG{}'.format(i+1),args[i])

    # define channels
    pulse.define_channel('NW_P','AWG1', 1)
    pulse.define_channel('NE_P','AWG1', 2)
    pulse.define_channel('SW_P','AWG1', 3)
    pulse.define_channel('SE_P','AWG1', 4)
    pulse.define_channel('UB1','AWG3', 1)
    pulse.define_channel('LB1','AWG3', 2)
    pulse.define_channel('P1','AWG3', 3)
    pulse.define_channel('P2','AWG3', 4)
    pulse.define_channel('P7','AWG4', 1)
    pulse.define_channel('P4','AWG4', 2)
    pulse.define_channel('P5','AWG4', 4)
    pulse.define_channel('P6','AWG4', 3)
    pulse.define_channel('LB7','AWG5', 1)
    pulse.define_channel('UB4','AWG5', 2)
    pulse.define_channel('UB5','AWG5', 3)
    pulse.define_channel('LB8','AWG5', 4)
    pulse.define_channel('UB6','AWG6', 4)
    pulse.define_channel('UB3','AWG6', 3)
    pulse.define_channel('UB2','AWG6', 2)
    pulse.define_channel('P3','AWG6', 1)
    pulse.define_channel('LB6','AWG7', 4)
    pulse.define_channel('LB5','AWG7', 3)
    pulse.define_channel('LB4','AWG7', 2)
    pulse.define_channel('LB3','AWG7', 1)
    pulse.define_channel('LB2','AWG8', 4)
    pulse.define_channel('UB7','AWG8', 3)
    pulse.define_channel('UB8','AWG8', 2)
    pulse.define_channel('test','AWG8', 1)
    pulse.define_channel('MW_I', 'AWG2', 3)
    pulse.define_channel('MW_Q', 'AWG2', 4)
    # pulse.define_marker('RFmarker','AWG4', 3)
    # pulse.define_channel('SCOPE','AWG4', 4)

    # format : channel name with delay in ns (can be posive/negative)
    # pulse.add_channel_delay('I_MW',-60)
    # pulse.add_channel_delay('Q_MW',-60)
    # pulse.add_channel_delay('M1',-110)
    #pulse.define_marker('M1', 'AWG2', 2, setup_ns=50, hold_ns=50)  #setting pulse modulation block, 50ns before and after pulse
    #pulse.define_marker('M1', 'AWG1', 0, setup_ns=60, hold_ns=60)
    # pulse.add_channel_delay('M2',-25)

    # add limits on voltages for DC channel compenstation (if no limit is specified, no compensation is performed).
    # max_c = 20
    max_c = 100
    for ch in pulse.awg_channels:
        att = pulse.awg_channels[ch].attenuation
        pulse.add_channel_compensation_limit(ch, (-max_c/att, max_c/att))


    # set right association of the real channels with I/Q output.
    # IQ_chan_set_1 = IQ_channel_constructor(pulse)
    # IQ_chan_set_1.add_IQ_chan("MW_I", "I")
    # IQ_chan_set_1.add_IQ_chan("MW_Q", "Q")
    # # IQ_chan_set_1.add_marker("M1", 10, 10)
    # IQ_chan_set_1.set_LO(2e9)
    # IQ_chan_set_1.add_virtual_IQ_channel("MW_q6_1")
    # IQ_chan_set_1.add_virtual_IQ_channel("MW_q7")
####

    IQ_chan_set_1 = IQ_channel_constructor(pulse)
    IQ_chan_set_1.add_IQ_chan("MW_I", "I")
    IQ_chan_set_1.add_IQ_chan("MW_Q", "Q")
    #IQ_chan_set_1.add_marker("M1")
    #f = station.sig_gen.frequency.get()
    IQ_chan_set_1.set_LO(2e9)
    IQ_chan_set_1.add_virtual_IQ_channel("MW_q7") ## plunger 1
####

    if hardware is not None:
        pulse.load_hardware(hardware)

    pulse.finish_init()

    return pulse
