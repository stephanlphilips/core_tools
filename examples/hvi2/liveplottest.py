import time
import logging
import os
from PyQt5 import QtCore
from pprint import pprint

import qcodes
#import qcodes.logger as logger
#from qcodes.logger import start_all_logging

from qcodes_contrib_drivers.drivers.Keysight.M3202A import M3202A

from core_tools.GUI.keysight_videomaps.liveplotting import liveplotting

from core_tools.drivers.M3102A import SD_DIG
from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log, get_fpga_image_path
from keysight_fpga.sd1.sd1_utils import check_error
from keysight_fpga.sd1.dig_iq import load_iq_image
from core_tools.HVI2.hvi2_schedules import Hvi2Schedules

from pulse_lib.base_pulse import pulselib

from PyQt5.QtCore import QTimer

#start_all_logging()
#logger.get_file_handler().setLevel(logging.DEBUG)

try:
    for awg in awgs:
        awg.close()
    dig.close()
    schedule.close()
except: pass
try:
    qcodes.Instrument.close_all()
except: pass


def load_default_awg_image(awg):
    bitstream = os.path.join(get_fpga_image_path(awg.awg), 'default_M3202A_ch_clk_k41_BSP_04_00_95.k7z')
    check_error(awg.load_fpga_image(bitstream), f'loading dig bitstream: {bitstream}')

def load_awg_image(awg):
    bitstream = os.path.join(get_fpga_image_path(awg.awg), 'awg_enhanced.k7z')
    check_error(awg.load_fpga_image(bitstream), f'loading dig bitstream: {bitstream}')



def return_pulse_lib_quad_dot(*args):
    """
    return pulse library object

    Args:
        hardware : hardware class (if not present, put None)
        *args : AWG instances you want to add (qcodes AWG object)
    """
    pulse = pulselib()

    # add to pulse_lib
    for i in range(len(args)):
        pulse.add_awgs('AWG{}'.format(i+1),args[i])

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'AWG{i+1}.{ch}',f'AWG{i+1}', ch)

    pulse.finish_init()
    return pulse

class UpdateTimer(QtCore.QObject):

    def start(self, plotting):
        self.count = 0
        self.timer = QTimer(plotting)
        self.timer.timeout.connect(self.change_plot)
        self.timer.start(9000)
        plotting.destroyed.connect(self.stop_timer)

    def stop_timer(self):
        logging.info('Stop timer')
        self.timer.stop()

    def change_plot(self):
        self.count += 1
        logging.info(f'start #{self.count}')
        v = (plotting._2D_V1_swing.value() + 1)
        if v > 1100:
            v = 100

        plotting._2D_V1_swing.setValue(v)
        start = time.monotonic()
        plotting.update_plot_settings_2D()
        logging.info(f'restart duration {time.monotonic()- start:5.2f} s')


dig = SD_DIG("dig", 1, 6)
awg_slots = [3] # [3,4]
awgs = []
for i,slot in enumerate(awg_slots):
    awg = M3202A(f"AWG{i}", 1, slot)
    awgs.append(awg)

for awg in awgs:
    load_awg_image(awg)
#    load_default_awg_image(awg)
    print_fpga_info(awg.awg)

station = qcodes.Station()
station_name = 'Test'

for awg in awgs:
    station.add_component(awg)

station.add_component(dig)

dig_mode = 1
load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)
dig.set_acquisition_mode(dig_mode)


logging.info('init pulse lib')
# load the AWG library
pulse = return_pulse_lib_quad_dot(*awgs)

logging.info('create hvi2 schedule')
print('create schedule')
schedules = Hvi2Schedules(pulse, dig)
schedule = schedules.get_video_mode(dig_mode)
schedule.load()

print('start gui')

logging.info('open plotting')
plotting = liveplotting(pulse, dig, "Keysight", hw_schedule=schedule)
plotting._2D_gate2_name.setCurrentIndex(1)
plotting._2D_t_meas.setValue(1)
plotting._2D_V1_swing.setValue(100)
plotting._2D_npt.setValue(80)

#pprint(plotting.metadata)

#updateTimer = UpdateTimer()
#updateTimer.start(plotting)
#plotting._2D_start_stop()

#%%

# station.close_all_registered_instruments()

#from V2_software.LivePlotting.data_getter.scan_generator_Virtual import fake_digitizer
#
#dig = fake_digitizer("fake_digitizer")
#pulse = return_pulse_lib_quad_dot(None)
#
#V2_liveplotting(pulse, dig)
