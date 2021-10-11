import time
import logging
import numpy as np
from PyQt5 import QtCore
from functools import partial
import qcodes

from core_tools.GUI.keysight_videomaps.liveplotting import liveplotting

from keysight_fpga.qcodes.M3202A_fpga import M3202A_fpga
from core_tools.drivers.M3102A import SD_DIG
from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log
from keysight_fpga.sd1.dig_iq import load_iq_image
from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader
from core_tools.drivers.keysight_rfgen import keysight_rfgen

from pulse_lib.base_pulse import pulselib

#start_all_logging()
#logger.get_file_handler().setLevel(logging.DEBUG)

try:
    oldLoader.close_all()
except: pass
oldLoader = Hvi2ScheduleLoader

try:
    qcodes.Instrument.close_all()
except: pass


def create_pulse_lib(awgs):
    """
    return pulse library object

    Args:
        hardware : hardware class (if not present, put None)
        *args : AWG instances you want to add (qcodes AWG object)
    """
    pulse = pulselib()

    # add to pulse_lib
    for i, awg in enumerate(awgs):

        pulse.add_awgs(awg.name, awg)

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'{awg.name}.{ch}', awg.name, ch)

    pulse.finish_init()
    return pulse


awg_slots = [3,7]
dig_slot = 5
dig_mode = 2

f1 = 190e6
f2 = 110e6
IF = 0
amp1 = 600
amp2 = 200

# lo-key: AWG, AWG channel, amplitude, frequency, enable
awg_channel_los = {
    'lo1_0': ('AWG1', 1, amp1, f1, True),
    'lo1_1': ('AWG1', 1, amp2, f2, True),
    'lo3_0': ('AWG2', 3, amp1, f1, True),
    'lo3_1': ('AWG2', 3, amp2, f2, True),
    }

# lo-key, DAQ channel, hw input channel, intermediate frequency, IF band (+/-1), phase
dig_channel_los = {
    ('lo1_0', 1, 1, IF, +1, 0.0),
    ('lo1_1', 2, 1, IF, +1, 0.0),
    ('lo3_0', 3, 3, IF, +1, 0.0),
    ('lo3_1', 4, 3, IF, +1, 0.0),
    }

station = qcodes.Station()

awgs = []
for i,slot in enumerate(awg_slots):
    awg = M3202A_fpga(f"AWG{i+1}", 1, slot)
    awgs.append(awg)
    awg.set_digital_filter_mode(0)
    station.add_component(awg)

dig = SD_DIG("dig", 1, 5)
station.add_component(dig)

load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)
dig.set_acquisition_mode(dig_mode)


logging.info('init pulse lib')
# load the AWG library
pulse = create_pulse_lib(awgs)

rf_gen = keysight_rfgen('keysight_rfgen', awg_channel_los, pulse.awg_devices,
                        station.dig, dig_channel_los)
station.add_component(rf_gen)

print('start gui')

logging.info('open plotting')
channel_map = {
        'ch1_I':(1, np.real),
        'ch1_Q':(1, np.imag),
        'ch1_Amp':(1, np.abs),
        'ch1_Phase':(1, partial(np.angle, deg=True)),
        'ch2_Amp':(2, np.abs),
        'ch2_Phase':(2, np.angle),
    }
plotting = liveplotting(pulse, dig, "Keysight", channel_map=channel_map)
plotting._2D_gate2_name.setCurrentIndex(1)
plotting._2D_t_meas.setValue(1)
plotting._2D_V1_swing.setValue(100)
plotting._2D_npt.setValue(80)

