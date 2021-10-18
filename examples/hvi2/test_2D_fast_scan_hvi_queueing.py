import logging
import time

import numpy as np
import matplotlib.pyplot as pt


from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log
from keysight_fpga.sd1.dig_iq import load_iq_image

from keysight_fpga.qcodes.M3202A_fpga import M3202A_fpga
from core_tools.drivers.M3102A import SD_DIG, MODES

from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader
from core_tools.HVI2.hvi2_video_mode import Hvi2VideoMode
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Keysight import construct_2D_scan_fast
from pulse_lib.base_pulse import pulselib
from pulse_lib.virtual_channel_constructors import virtual_gates_constructor

import qcodes

import qcodes.logger as logger
from qcodes.logger import start_all_logging

start_all_logging()
logger.get_file_handler().setLevel(logging.DEBUG)

# close objects still active since previous run (IPython)
try:
    oldLoader.close_all()
except: pass
oldLoader = Hvi2ScheduleLoader

try:
    qcodes.Instrument.close_all()
except: pass


def create_pulse_lib(awgs):
    pulse = pulselib(backend='M3202A')

    channels = []
    # add to pulse_lib
    for i, awg in enumerate(awgs):
        pulse.add_awgs(awg.name, awg)

        # define channels
        for ch in range(1,5):
            channel_name = f'{awg.name}_{ch}'
            pulse.define_channel(channel_name, awg.name, ch)
            channels.append(channel_name)

    n_ch = len(channels)

    # set a virtual gate matrix
    virtual_gate_set_1 = virtual_gates_constructor(pulse)
    virtual_gate_set_1.add_real_gates(*channels)
    virtual_gate_set_1.add_virtual_gates(*[f'vP{i+1}' for i in range(n_ch)])

    # copy data of AWG1 to all other AWG
    inv_matrix = np.zeros((n_ch,)*2)
    for i in range(4):
        inv_matrix[i::4,i] = 1.0
    for i in range(4, n_ch):
        inv_matrix[i,i] = 1.0
    virtual_gate_set_1.add_virtual_gate_matrix(np.linalg.inv(inv_matrix))

    pulse.finish_init()
    return pulse



awg_slots = [3,7]
dig_slot = 5
dig_channels = [1,2,3,4]
full_scale = 2.0

dig_mode = 1
t_measure = 180 #20
lo_f = 0e6
acquisition_delay_ns = 0 #160


awgs = []
for i, slot in enumerate(awg_slots):
    awg = M3202A_fpga(f'AWG{slot}', 1, slot)
    awgs.append(awg)
    awg.set_hvi_queue_control(True)

dig = SD_DIG('DIG1', 1, dig_slot)
load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)
dig.set_acquisition_mode(dig_mode)


## add to pulse lib.
p = create_pulse_lib(awgs)

for ch in dig_channels:
    dig.set_lo(ch, lo_f, 0, input_channel=ch)


## create 2D scan
gate1, swing1, n_pt1 = 'vP1', 500, 8
gate2, swing2, n_pt2 = 'vP2', 500, 15
biasT_corr=True

dig_param = construct_2D_scan_fast(
        gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_measure, biasT_corr, p,
        dig, dig_channels, 500e6,
        acquisition_delay_ns=acquisition_delay_ns,
        dig_vmax=full_scale,
        pulse_gates={'vP3':200},
        line_margin=1,
        )


config_fpga_debug_log(dig.SD_AIN,
                      enable_mask=0xC000_0000,
                      )


## run
start = time.perf_counter()
data = dig_param()
duration = time.perf_counter() - start
print(f'duration {duration*1000:5.1f} ms')


print_fpga_log(dig.SD_AIN)
for awg in awgs:
    print(f'AWG: {awg.name}')
    print_fpga_log(awg.awg, clock200=True)



dig_data = [None]*4
index = 0
for ch in dig_channels:
    c = ch-1
    dig_data[c] = data[index].flatten()
    index += 1
    print(f'ch{ch}: {len(dig_data[c])}')

### plots
#colors = ['k', 'b','r', 'c', 'y']
#colors = ['k', 'tab:blue', 'k', 'yellow', 'tomato']
colors = ['k', 'tab:blue', 'tab:orange', 'tab:green', 'tab:red']


# plot direct data
if dig_mode == 0:
    pt.figure(5)
    pt.clf()
    for ch in dig_channels:
        pt.figure(ch)
        c = ch-1
        t = (np.arange(len(dig_data[c])) + 0.5) * 2
        pt.plot(t, dig_data[c])
        pt.figure(5)
        pt.plot(t, dig_data[c], '-', ms=4, label=f'ch{ch}', color=colors[ch])
        pt.legend()

if dig_mode == 1:
    pt.figure(5)
    pt.clf()
    # plot averages
    for ch in dig_channels:
        c = ch-1
        t = (np.arange(len(dig_data[c])) + 0.5) * t_measure
        pt.figure(ch)
        pt.plot(t, dig_data[c], '-')
    #    pt.ylim(-0.8, 0.8)
#        pt.legend()
        pt.figure(5)
        pt.plot(t, dig_data[c], '-', ms=4, color=colors[ch], label=f'ch{ch}')
        pt.legend()
    #    pt.ylim(-0.8, 0.8)


if dig_mode in [2,3]:
    ## plot IQ
    for ch in dig_channels:
        c = ch-1
        t = (np.arange(len(dig_data[c])) + 0.5) * t_measure
        pt.figure(20)
        pt.plot(t, dig_data[c].real, label=f'ch{ch} I')
        pt.legend()

        pt.figure(10+ch)
        pt.plot(t, dig_data[c].real, label=f'ch{ch} I')
        if dig_mode == 2:
            pt.plot(t, dig_data[c].imag, label=f'ch{ch} Q')
            pt.legend()
            pt.figure(30+ch)
            pt.plot(t, dig_data[c].imag, label=f'ch{ch} Q')
            pt.legend()

        pt.figure(7)
        pt.plot(t, np.abs(dig_data[c]), label=f'ch{ch}')
        pt.legend()
        pt.figure(8)
        pt.plot(t, np.angle(dig_data[c], deg=True), label=f'ch{ch}')
        pt.legend()

dig_param.stop()

for awg in awgs:
    awg.close()
dig.close()

