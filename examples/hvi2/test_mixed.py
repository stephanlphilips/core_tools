import logging
import os
import time

import numpy as np
import matplotlib.pyplot as pt

from keysight_fpga.sd1.fpga_utils import \
    print_fpga_info, config_fpga_debug_log, print_fpga_log, get_fpga_image_path, fpga_list_registers
from keysight_fpga.sd1.sd1_utils import check_error
from keysight_fpga.sd1.dig_iq import load_iq_image

from qcodes_contrib_drivers.drivers.Keysight.M3202A import M3202A
from core_tools.drivers.M3102A import SD_DIG
from pulse_lib.base_pulse import pulselib

from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader

import qcodes

#import qcodes.logger as logger
#from qcodes.logger import start_all_logging

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

    pulse.finish_init()
    return pulse

def load_default_awg_image(awg):
    bitstream = os.path.join(get_fpga_image_path(awg.awg), 'default_M3202A_ch_clk_k41_BSP_04_00_95.k7z')
    check_error(awg.load_fpga_image(bitstream), f'loading dig bitstream: {bitstream}')

def load_awg_image(awg):
    bitstream = os.path.join(get_fpga_image_path(awg.awg), 'awg_enhanced.k7z')
    check_error(awg.load_fpga_image(bitstream), f'loading dig bitstream: {bitstream}')

def scan2D_keysight(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, pulse_lib, biasT_corr=False):

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

def create_ss_seq(p, dig_mode):
    t_wave = 10000
    t_pulse = 8000
    pulse_duration = 100

    ## create waveforms
    seg = p.mk_segment()
    for awg in awgs:
        for ch in [1,2,3,4]:
            channel = getattr(seg, f'{awg.name}_{ch}')
            channel.wait(t_wave)
            channel.add_block(t_pulse, t_pulse+pulse_duration, 600)

    seg.add_HVI_marker('dig_trigger_1', t_off=t_pulse-t_measure//4)

    ## create sequencer
    seq = p.mk_sequence([seg])
    seq.set_hw_schedule(Hvi2ScheduleLoader(p, "SingleShot", dig))
    seq.n_rep = n_rep
    return seq

def create_ssr_seq(p, dig_mode):
    t_wave = 10000
    t_pulse_1 = 3000
    t_pulse_2 = 9000
    pulse_duration = 100

    ## create waveforms
    seg = p.mk_segment()
    for awg in awgs:
        for ch in [1,2,3,4]:
            channel = getattr(seg, f'{awg.name}_{ch}')
            channel.wait(t_wave)
            channel.add_block(t_pulse_1, t_pulse_1+pulse_duration, 800)
            channel.add_block(t_pulse_2, t_pulse_2+pulse_duration, 500)

    seg.add_HVI_marker('dig_trigger_1', t_off=t_pulse_1-t_measure//4)
    seg.add_HVI_marker('dig_trigger_2', t_off=t_pulse_2-t_pulse_1)

    ## create sequencer
    seq = p.mk_sequence([seg])
    seq.set_hw_schedule(Hvi2ScheduleLoader(p, "SingleShot", dig))
    seq.n_rep = n_rep
    return seq

def create_vidmod_seq(p, dig_mode):

    ## create sequencer
    gate1, swing1, n_pt1 = 'AWG3_1', 500, 50
    gate2, swing2, n_pt2 = 'AWG3_2', 500, 50
    t_step = t_measure
    seq = scan2D_keysight(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, p)
    seq.set_hw_schedule(Hvi2ScheduleLoader(p, "VideoMode", dig))
    seq.n_rep = 1
    return seq


awg_slots = [3]
dig_slot = 6
dig_channels = [1,2,3,4]
full_scale = 2.0

dig_mode = 1
t_measure = 200
t_average = 10
p2decim = 0
lo_f = 20e6

n_rep = 1000

awgs = []
for i, slot in enumerate(awg_slots):
    awg = M3202A(f'AWG{slot}', 1, slot)
    awgs.append(awg)


dig = SD_DIG('DIG1', 1, dig_slot)
load_iq_image(dig.SD_AIN)
print_fpga_info(dig.SD_AIN)
dig.set_acquisition_mode(dig_mode)

for awg in awgs:
    load_awg_image(awg)
#    load_default_awg_image(awg)
    print_fpga_info(awg.awg)
#    fpga_list_registers(awg.awg)

#config_fpga_debug_log(dig.SD_AIN,
#                      #change_mask = 0x9F00_8585,
#                      enable_mask=0xC000_0000,
##                      enable_mask=0xC038_0505,
##                      capture_start_mask=0x8800_4141, capture_duration=1
#                      )


## add to pulse lib.
p = create_pulse_lib(awgs)
## create schedule


for q in range(3000):
    s = (q+2) % 3
    n_points = 0
    if s == 0:
        sequencer = create_ss_seq(p, dig_mode)
        n_points = n_rep

    elif s == 1:
        sequencer = create_ssr_seq(p, dig_mode)
        n_points = 2 * n_rep

    elif s == 2:
        sequencer = create_vidmod_seq(p, dig_mode)
        n_pt1, n_pt2 = 20, 20
        n_points = 1 * n_pt1 * n_pt2


    for ch in dig_channels:
        dig.set_lo(ch, lo_f, 0, input_channel=ch)
    dig.set_digitizer_HVI(t_measure, n_points, channels=dig_channels,
                          downsampled_rate=1e9/t_average,
                          power2decimation=p2decim, Vmax=full_scale)

    # dummy for schedule switch or compile/load
    sequencer.upload(index=[0])
    sequencer.play(index=[0])
    data = dig.measure.get_data()
    ## run
    N = 10
    start = time.perf_counter()
    for i in range(N):
        sequencer.upload(index=[0])
        sequencer.play(index=[0])
        data = dig.measure.get_data()

    if N > 0:
        duration = time.perf_counter() - start
        print(f'duration {duration*1000/N:5.1f} ms')


Hvi2ScheduleLoader.close_all()
for awg in awgs:
    awg.close()
dig.close()

