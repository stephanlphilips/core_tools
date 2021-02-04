import logging
import time

import numpy as np
import matplotlib.pyplot as pt

from keysight_fpga.sd1.fpga_utils import print_fpga_info, config_fpga_debug_log, print_fpga_log
from keysight_fpga.sd1.dig_iq import load_iq_image

from keysight_fpga.qcodes.M3202A_fpga import M3202A_fpga
from core_tools.drivers.M3102A import SD_DIG, OPERATION_MODES
from pulse_lib.base_pulse import pulselib

from core_tools.HVI2.hvi2_schedules import Hvi2Schedules

import qcodes


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


awg_slots = [3]
dig_slot = 6
full_scale = 2.0

t_wave = 10000
t_pulse = [3000, 7500, 9000]
pulse_amplitude = [800, 500, 600]
pulse_duration = 100

awg_los = [('AWG3',1,0), ('AWG3',1,1), ('AWG3',3,0), ('AWG3',3,1)]
awg_lo_amps = [600, 200]
awg_lo_freq = [60e6, 190e6]

dig_channel_modes = {1:1, 2:2, 3:2}
t_measure = 1000
t_average = 10
p2decim = 0
lo_f = [0, 0, 60e6, 190e6, 0]

n_rep = 2
n_triggers = 3

lo_0 = awg_los[0]
lo_1 = awg_los[1]
lo_2 = awg_los[2]
lo_3 = awg_los[3]
enabled_los = [
        [lo_0, lo_1, lo_2, lo_3],
        [lo_0, lo_2],
        [lo_1, lo_3],
        ]


awgs = []
for i, slot in enumerate(awg_slots):
    awg = M3202A_fpga(f'AWG{slot}', 1, slot)
    awg.set_digital_filter_mode(0)
    awgs.append(awg)

dig = SD_DIG('DIG1', 1, dig_slot)
load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)

dig.set_operating_mode(OPERATION_MODES.HVI_TRG)

for awg in awgs:
    for awg_name, channel, lo in awg_los:
        if awg_name == awg.name:
            awg.config_lo(channel, lo, False, awg_lo_freq[lo], awg_lo_amps[lo])
            awg.set_lo_mode(channel, True)


for ch, mode in dig_channel_modes.items():
    dig.set_lo(ch, lo_f[ch], 0, input_channel=1)

for ch, mode in dig_channel_modes.items():
    dig.set_channel_acquisition_mode(ch, mode)
    dig.set_channel_properties(ch, full_scale)


## add to pulse lib.
p = create_pulse_lib(awgs)
## create schedule
schedules = Hvi2Schedules(p, dig)
schedule = schedules.get_single_shot(dig_channel_modes={'DIG1':dig_channel_modes},
                                     n_triggers=n_triggers,
                                     awg_channel_los=awg_los,
                                     enabled_los=enabled_los,
                                     switch_los=True
                                     )
schedule.load()

## create waveforms
seg = p.mk_segment()
for awg in awgs:
    for ch in [1,2,3,4]:
        channel = getattr(seg, f'{awg.name}_{ch}')
        channel.wait(t_wave)
        for t,amp in zip(t_pulse, pulse_amplitude):
            channel.add_block(t, t+pulse_duration, amp)

for i,t in enumerate(t_pulse):
    seg.add_HVI_marker(f'dig_trigger_{i+1}', t_off=t-t_measure//4)
    seg.add_HVI_marker(f'awg_los_on_{i+1}', t_off=t)
    seg.add_HVI_marker(f'awg_los_off_{i+1}', t_off=t+pulse_duration+100*i)

## create sequencer
sequencer = p.mk_sequence([seg])
sequencer.set_hw_schedule(schedule)
sequencer.n_rep = n_rep

config_fpga_debug_log(dig.SD_AIN,
                      #change_mask = 0x9F00_8585,
                      enable_mask=0xC000_0000,
#                      enable_mask=0xC038_0505,
#                      capture_start_mask=0x8800_4141, capture_duration=1
                      )

for ch, mode in dig_channel_modes.items():
    dig.set_daq_settings(ch, n_rep*n_triggers, t_measure, downsampled_rate=1e9/t_average, power2decimation=p2decim)

sequencer.upload(index=[0])
sequencer.play(index=[0])
data = dig.measure.get_data()

## run
N = 1
start = time.perf_counter()
for i in range(N):
    sequencer.upload(index=[0])
    sequencer.play(index=[0])
    data = dig.measure.get_data()

if N > 0:
    duration = time.perf_counter() - start
    print(f'duration {duration*1000/N:5.1f} ms')

print_fpga_log(dig.SD_AIN)
for awg in awgs:
    print(f'AWG: {awg.name}')
    print_fpga_log(awg.awg, clock200=True)


dig_data = [None]*4
for ch in dig_channel_modes:
    c = ch-1
    dig_data[c] = data[c].flatten()
    print(f'ch{ch}: {len(dig_data[c])}')

### plots
#colors = ['k', 'b','r', 'c', 'y']
#colors = ['k', 'tab:blue', 'k', 'yellow', 'tomato']
colors = ['k', 'tab:blue', 'tab:orange', 'tab:green', 'tab:red']



# plot direct data
if 0 in dig_channel_modes.values():
    pt.figure(5)
    pt.clf()
    for ch, mode in dig_channel_modes.items():
        if mode == 0:
            pt.figure(ch)
            c = ch-1
            t = (np.arange(len(dig_data[c])) + 0.5) * 2
            pt.plot(t, dig_data[c])
            pt.figure(5)
            pt.plot(t, dig_data[c], '-', ms=4, label=f'direct 500 MSa/a', color=colors[ch])

if 1 in dig_channel_modes.values():
    pt.figure(6)
    pt.clf()
    # plot averages
    for ch, mode in dig_channel_modes.items():
        if mode == 1:
            c = ch-1
            t = (np.arange(len(dig_data[c])) + 0.5) * t_average
            pt.figure(ch)
            pt.plot(t, dig_data[c], '-', label=f'p2d={p2decim}, {1000/t_average} MSa/s')
        #    pt.ylim(-0.8, 0.8)
            pt.legend()
            pt.figure(6)
            pt.plot(t, dig_data[c], '-', ms=4, color=colors[ch],
                    label=f'p2d={p2decim}, {1000/t_average} MSa/s')
            pt.legend()
        #    pt.ylim(-0.8, 0.8)


if 2 in dig_channel_modes.values() or 3 in dig_channel_modes.values():
    ## plot IQ
    for ch, mode in dig_channel_modes.items():
        if mode in [2,3]:
            c = ch-1
            t = (np.arange(len(dig_data[c])) + 0.5) * t_average
            pt.figure(20)
            pt.plot(t, dig_data[c].real, label=f'ch{ch} I')
            pt.legend()

            pt.figure(10+ch)
            pt.plot(t, dig_data[c].real, label=f'ch{ch} I')
            if mode == 2:
                pt.plot(t, dig_data[c].imag, label=f'ch{ch} Q')
                pt.legend()
                pt.figure(30)
                pt.plot(t, dig_data[c].imag, label=f'ch{ch} Q')
                pt.legend()

                pt.figure(9)
                phase = np.angle(dig_data[c], deg=True)
                jitter = (phase - np.average(phase))/360/lo_f[ch] * 1e12
                pt.plot(t, jitter, label=f'ch{ch}')
                pt.title('Jitter')

            pt.figure(7)
            pt.plot(t, np.abs(dig_data[c]),
                    label=f'ch{ch} p2d={p2decim}, {1000/t_average} MSa/s')
            pt.legend()
            pt.title('Amplitude')
            pt.figure(8)
            pt.plot(t, np.angle(dig_data[c], deg=True),
                    label=f'ch{ch} p2d={p2decim}, {1000/t_average} MSa/s')
            pt.legend()
            pt.title('Phase')

schedule.close()
for awg in awgs:
    awg.close()
dig.close()

