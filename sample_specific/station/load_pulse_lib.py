from pulse_lib.base_pulse import pulselib
from pulse_lib.virtual_channel_constructors import IQ_channel_constructor, virtual_gates_constructor

import numpy as np

def return_pulse_lib(hardware = None, *args):
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
    pulse.define_channel('B0','AWG1', 1)
    pulse.define_channel('P1','AWG1', 2)
    pulse.define_channel('B1','AWG1', 3)
    pulse.define_channel('P2','AWG1', 4)
    pulse.define_channel('B2','AWG2', 1)
    pulse.define_channel('P3','AWG2', 2)
    pulse.define_channel('B3','AWG2', 3)
    pulse.define_marker('M1','AWG2', 4)
    pulse.define_channel('I_pos','AWG3',1)
    pulse.define_channel('I_neg','AWG3',2)
    pulse.define_channel('Q_pos','AWG3', 3)
    pulse.define_channel('Q_neg','AWG3', 4)


    # format : channel name with delay in ns (can be posive/negative)
    # pulse.add_channel_delay('I_MW',-60)
    # pulse.add_channel_delay('Q_MW',-60)
    # pulse.add_channel_delay('M1',-110)
    # pulse.add_channel_delay('M2',-25)

    # add limits on voltages for DC channel compenstation (if no limit is specified, no compensation is performed).
    pulse.add_channel_compenstation_limit('B0', (-1500, 1500))
    pulse.add_channel_compenstation_limit('B1', (-1500, 1500))
    pulse.add_channel_compenstation_limit('B2', (-1500, 1500))
    pulse.add_channel_compenstation_limit('B3', (-1500, 1500))
    pulse.add_channel_compenstation_limit('P1', (-1500, 1500))
    pulse.add_channel_compenstation_limit('P2', (-1500, 1500))
    pulse.add_channel_compenstation_limit('P3', (-1500, 1500))

    IQ_chan_set_1 = IQ_channel_constructor(pulse)
    # set right association of the real channels with I/Q output.
    IQ_chan_set_1.add_IQ_chan("I_pos", "I",  image = "+")
    IQ_chan_set_1.add_IQ_chan("I_neg", "I",  image = "-")
    IQ_chan_set_1.add_IQ_chan("Q_pos", "Q",  image = "+")
    IQ_chan_set_1.add_IQ_chan("Q_neg", "Q",  image = "-")
    IQ_chan_set_1.add_marker("M1", 0, 2000)
    IQ_chan_set_1.set_LO(1e9)
    IQ_chan_set_1.add_virtual_IQ_channel('qubit1_MW')
    IQ_chan_set_1.add_virtual_IQ_channel('qubit2_MW')
    IQ_chan_set_1.add_virtual_IQ_channel('qubit3_MW')
    IQ_chan_set_1.add_virtual_IQ_channel('qubit4_MW')
   


    if hardware is not None:
        pulse.load_hardware(hardware)
    pulse.finish_init()
    return pulse


if __name__ == '__main__':
    pulse = return_pulse_lib()
