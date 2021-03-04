import logging
import time

import numpy as np
import matplotlib.pyplot as pt


from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log
from keysight_fpga.sd1.dig_iq import load_iq_image

from keysight_fpga.qcodes.M3202A_fpga import M3202A_fpga
from core_tools.drivers.M3102A import SD_DIG, MODES

from core_tools.HVI2.hvi2_schedules import Hvi2Schedules
from pulse_lib.base_pulse import pulselib

import qcodes

import qcodes.logger as logger
from qcodes.logger import start_all_logging

start_all_logging()
logger.get_file_handler().setLevel(logging.DEBUG)

# close objects still active since previous run (IPython)
try:
    for awg in awgs:
        awg.close()
    dig.close()
    schedule.close()
except: pass
try:
    qcodes.Instrument.close_all()
except: pass


def create_pulse_lib(awgs):
    pulse = pulselib(backend='M3202A')

    # add to pulse_lib
    for i, awg in enumerate(awgs):
        pulse.add_awgs(awg.name, awg)

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'{awg.name}_{ch}', awg.name, ch)

    pulse.finish_init()
    return pulse


def scan2D_keysight(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, pulse_lib, dig_mode, biasT_corr=False):

    segment  = pulse_lib.mk_segment()

    segment.add_HVI_variable("t_measure", int(t_step))
    segment.add_HVI_variable("number_of_points", int(n_pt1*n_pt2))
    segment.add_HVI_variable("averaging", True)

    sweep_channel = getattr(segment, gate1)
    step_channel = getattr(segment, gate2)

    # set up timing for the scan
    # 2us needed to re-arm digitizer
    # 100ns HVI waiting time
    # [SdS] Why is the value below 120 ns?
    if dig_mode == MODES.NORMAL:
        step_eff = 1800 + t_step
    else:
        step_eff = 50 + t_step

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    # set point voltages
    voltages1_sp = np.linspace(-vp1,vp1,n_pt1)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)

    if biasT_corr == True:
        voltages2 = np.zeros(n_pt2)
        voltages2[::2] = voltages2_sp[:len(voltages2[::2])]
        voltages2[1::2] = voltages2_sp[-len(voltages2[1::2]):][::-1]
    else:
        voltages2 = voltages2_sp

    sweep_channel.add_ramp_ss(0, step_eff*n_pt1, -vp1, vp1)
    sweep_channel.repeat(n_pt1)

    for voltage in voltages2:
        step_channel.add_block(0, step_eff*n_pt1, voltage)
        step_channel.reset_time()

    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([segment])
    my_seq.sample_rate = sample_rate

    return my_seq



awg_slots = [3,7]
dig_slot = 6
dig_channels = [1,2,3,4]
full_scale = 2.0


dig_mode = 1
t_measure = 250
t_average = t_measure
p2decim = 0
lo_f = 20e6

n_rep = 1

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

schedules = Hvi2Schedules(p, dig)

## create schedule
schedule = schedules.get_video_mode(dig_mode, hvi_queue_control=True)

schedule.load()

## create sequencer
gate1, swing1, n_pt1 = 'AWG3_1', 500, 16
gate2, swing2, n_pt2 = 'AWG3_2', 500, 12
t_step = t_measure
sequencer = scan2D_keysight(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, p, dig_mode)
sequencer.set_hw_schedule(schedule)
sequencer.n_rep = n_rep

for ch in dig_channels:
    dig.set_lo(ch, lo_f, 0, input_channel=ch)
dig.set_digitizer_HVI(t_measure, n_rep*n_pt1*n_pt2,
                      channels=dig_channels,
                      downsampled_rate=1e9/t_average, power2decimation=p2decim, Vmax=full_scale)


config_fpga_debug_log(dig.SD_AIN,
                      enable_mask=0xC000_0000,
                      )

#time.sleep(1)

## run
N = 1
start = time.perf_counter()
for i in range(N):
    sequencer.upload(index=[0])
    sequencer.play(index=[0])
    time.sleep(1.0)

    data = dig.measure.get_data()
duration = time.perf_counter() - start
print(f'duration {duration*1000/N:5.1f} ms')

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
        pt.plot(t, dig_data[c], '-', ms=4, label=f'direct 500 MSa/a', color=colors[ch])

if dig_mode == 1:
    pt.figure(5)
    pt.clf()
    # plot averages
    for ch in dig_channels:
        c = ch-1
        t = (np.arange(len(dig_data[c])) + 0.5) * t_average
        pt.figure(ch)
        pt.plot(t, dig_data[c], '-', label=f'p2d={p2decim}, {1000/t_average:5.1f} MSa/s')
    #    pt.ylim(-0.8, 0.8)
        pt.legend()
        pt.figure(5)
        pt.plot(t, dig_data[c], '-', ms=4, color=colors[ch],
                label=f'p2d={p2decim}, {1000/t_average:5.1f} MSa/s')
        pt.legend()
    #    pt.ylim(-0.8, 0.8)


if dig_mode in [2,3]:
    ## plot IQ
    for ch in dig_channels:
        c = ch-1
        t = (np.arange(len(dig_data[c])) + 0.5) * t_average
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
        pt.plot(t, np.abs(dig_data[c]),
                label=f'ch{ch} p2d={p2decim}, {1000/t_average:5.1f} MSa/s')
        pt.legend()
        pt.figure(8)
        pt.plot(t, np.angle(dig_data[c], deg=True),
                label=f'ch{ch} p2d={p2decim}, {1000/t_average:5.1f} MSa/s')
        pt.legend()

schedule.close()
for awg in awgs:
    awg.close()
dig.close()

