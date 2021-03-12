import time

import numpy as np
import matplotlib.pyplot as pt

from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log, get_fpga_image_path, fpga_list_registers
from keysight_fpga.sd1.sd1_utils import check_error
from keysight_fpga.sd1.dig_iq import load_iq_image

from keysight_fpga.qcodes.M3202A_fpga import M3202A_fpga
from core_tools.drivers.M3102A import SD_DIG, MODES
from pulse_lib.base_pulse import pulselib

from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader

import qcodes

import qcodes.logger as logger
from qcodes.logger import start_all_logging

#start_all_logging()
#logger.get_console_handler().setLevel(logging.WARN)
#logger.get_file_handler().setLevel(logging.DEBUG)

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

    # add to pulse_lib
    for i, awg in enumerate(awgs):
        pulse.add_awgs(awg.name, awg)

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'{awg.name}_{ch}', awg.name, ch)
            pulse.add_channel_delay(f'{awg.name}_{ch}', 5*ch)

    pulse.finish_init()
    return pulse


awg_slots = [3,7]
dig_slot = 6
dig_channels = [1,2,3,4]
full_scale = 2.0

t_wave = 20_000
t_pulse = 15_000
pulse_duration = 100

dig_mode = MODES.NORMAL #AVERAGE
t_measure = 10_000
t_average = 10
p2decim = 0
lo_f = 20e6

n_rep = 1

awgs = []
for i, slot in enumerate(awg_slots):
    awg = M3202A_fpga(f'AWG{slot}', 1, slot, waveform_size_limit=1e7)
    awgs.append(awg)
    awg.set_hvi_queue_control(True)
    awg.set_digital_filter_mode(0)


dig = SD_DIG('DIG1', 1, dig_slot)
load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)
dig.set_acquisition_mode(dig_mode)


## add to pulse lib.
p = create_pulse_lib(awgs)

schedule = Hvi2ScheduleLoader(p, "SingleShot", dig)

## create waveforms
seg = p.mk_segment()
for awg in awgs:
    for ch in [1,2,3,4]:
        channel = getattr(seg, f'{awg.name}_{ch}')
        channel.wait(t_wave)
        channel.add_block(t_pulse, t_pulse+pulse_duration, 800)
        channel.add_ramp_ss(t_wave-100, t_wave, 100, 100*ch)

seg.add_HVI_marker('dig_trigger_1', t_off=t_pulse-100)

seg2 = p.mk_segment()
for awg in awgs:
    for ch in [1,2,3,4]:
        channel = getattr(seg2, f'{awg.name}_{ch}')
        channel.wait(t_wave)
        channel.add_ramp_ss(0, 100, 100*ch, 200*ch-100)
        channel.add_block(100, 100+pulse_duration, 500)
seg2.sample_rate = 1e8

## create sequencer
sequencer = p.mk_sequence([seg,seg2])
sequencer.set_hw_schedule(schedule)
sequencer.n_rep = n_rep

#for ch in dig_channels:
#    dig.set_lo(ch, lo_f, 0, input_channel=ch)


config_fpga_debug_log(dig.SD_AIN,
                      change_mask = 0x8F00_0000,
                      enable_mask=0xC000_0000,
#                      enable_mask=0xC038_0505,
#                      capture_start_mask=0x8800_4141, capture_duration=1
                      )

dig.set_digitizer_HVI(t_measure, n_rep, channels=dig_channels,
                      downsampled_rate=1e9/t_average,
                      power2decimation=p2decim, Vmax=full_scale)
sequencer.upload(index=[0])
sequencer.play(index=[0])
data = dig.measure.get_data()

#dig.set_digitizer_HVI(t_measure, n_rep, channels=dig_channels,
#                      downsampled_rate=1e9/t_average, power2decimation=p2decim, Vmax=full_scale)


## run
N = 0
start = time.perf_counter()
for i in range(N):
    dig.set_digitizer_HVI(t_measure, n_rep, channels=dig_channels,
                          downsampled_rate=1e9/t_average,
                          power2decimation=p2decim, Vmax=full_scale)
    sequencer.upload(index=[0])
    sequencer.play(index=[0])
    data = dig.measure.get_data()

if N > 0:
    duration = time.perf_counter() - start
    print(f'duration {duration*1000/N:5.1f} ms')

#print_fpga_log(dig.SD_AIN)
for awg in awgs:
    print(f'AWG: {awg.name}')
    print_fpga_log(awg.awg, clock200=True)


dig_data = [None]*4
for ch in dig_channels:
    c = ch-1
    dig_data[c] = data[c].flatten()
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
        pt.plot(t, dig_data[c], '-', label=f'p2d={p2decim}, {1000/t_average} MSa/s')
    #    pt.ylim(-0.8, 0.8)
        pt.legend()
        pt.figure(5)
        pt.plot(t, dig_data[c], '-', ms=4, color=colors[ch],
                label=f'p2d={p2decim}, {1000/t_average} MSa/s')
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
                label=f'ch{ch} p2d={p2decim}, {1000/t_average} MSa/s')
        pt.legend()
        pt.figure(8)
        pt.plot(t, np.angle(dig_data[c], deg=True),
                label=f'ch{ch} p2d={p2decim}, {1000/t_average} MSa/s')
        pt.legend()


schedule.close()
for awg in awgs:
    awg.close()
dig.close()

