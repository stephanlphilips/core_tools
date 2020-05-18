# -*- coding: utf-8 -*-
"""
Created on Tue May 12 17:01:25 2020

@author: LocalAdmin
"""


from core_tools.sweeps.pulse_lib_sweep import spin_qubit_exp, dummy_multi_parameter
from pulse_templates.coherent_control.single_qubit_gates import single_qubit_gate_simple, single_qubit_gate_spec
from pulse_templates.oper.operators import jump, wait
from pulse_templates.utility.plotting import plot_seg
import numpy as np

def T2_ramsey(seg, pi2_pulse, t_wait, f_bg_oscillations):
    '''
    perform T2* measurement on the qubit

    Args:
        seg (segment_container) : segment container
        pi2_pulse (single_qubit_gate_spec) : parameter describing pi/2 pulse
        t_wait (double) : time to wait
        f_bg_oscillations (double) : freq at which the the qubit needs to oscilate 
    '''
    padding = 1
    single_qubit_gate_simple(seg, pi2_pulse, padding)
    getattr(seg, pi2_pulse.qubit_name).wait(t_wait) #substract padding
    getattr(seg, pi2_pulse.qubit_name).add_global_phase(t_wait*1e-9*f_bg_oscillations*np.pi*2)
    getattr(seg, pi2_pulse.qubit_name).reset_time()
    single_qubit_gate_simple(seg, pi2_pulse, padding)

def T2_CPMG_t_tot(seg, pi2_pulse, pi_pulse, t_wait, N_rep,f_bg_oscillations):
    '''
    perform CPMG given tot total waiting time

    Args:
        seg (segment_container) : segment container
        pi2_pulse (single_qubit_gate_spec) : parameter describing pi/2 pulse (X type)
        pi_pulse (single_qubit_gate_spec) : parameter describing pi pulse (X type)
        t_wait (double) : total time waited in the pulse
        N_rep (double) : amount of X gates you want to do
        f_bg_oscillations (double) : freq at which the the qubit needs to oscilate 
    
    TODO : problems is T_wait and N are loop objects? PULSE lib add support for multipying two param.
    '''
    padding = 1
    single_qubit_gate_simple(seg, pi2_pulse, padding)
    for i in range(N_rep):
        getattr(seg, pi2_pulse.qubit_name).wait(t_wait/N_rep) #substract padding
        getattr(seg, pi2_pulse.qubit_name).reset_time()

        single_qubit_gate_simple(seg, pi_pulse, padding)
        
        getattr(seg, pi2_pulse.qubit_name).wait(t_wait/N_rep)
        getattr(seg, pi2_pulse.qubit_name).reset_time()

    getattr(seg, pi2_pulse.qubit_name).add_global_phase(t_wait*1e-9*f_bg_oscillations*np.pi*2)
    getattr(seg, pi2_pulse.qubit_name).reset_time()
    single_qubit_gate_simple(seg, pi2_pulse, padding)

def T2_CPMG_t_single(seg, pi2_pulse, pi_pulse, t_wait, N_rep, f_bg_oscillations):
    '''
    perform CPMG given tot total waiting time

    Args:
        seg (segment_container) : segment container
        pi2_pulse (single_qubit_gate_spec) : parameter describing pi/2 pulse (X type)
        pi_pulse (single_qubit_gate_spec) : parameter describing pi pulse (X type)
        t_wait (double) : time to wait
        N_rep (double) : amount of X gates you want to do
        f_bg_oscillations (double) : freq at which the the qubit needs to oscilate 
    
    TODO : problems is T_wait and N are loop objects? PULSE lib add support for multipying two param.
    '''
    T2_CPMG_t_tot(seg, pi2_pulse, pi_pulse, t_wait*N_rep, N_rep, f_bg_oscillations)

def T2_hahn(seg, pi2_pulse, pi_pulse, t_wait, f_bg_oscillations):
    '''
    perform hahn echo

    Args:
        seg (segment_container) : segment container
        pi2_pulse (single_qubit_gate_spec) : parameter describing pi/2 pulse (X type)
        pi_pulse (single_qubit_gate_spec) : parameter describing pi pulse (X type)
        t_wait (double) : time to wait
        f_bg_oscillations (double) : freq at which the the qubit needs to oscilate 
    '''
    T2_CPMG_t_tot(seg, pi2_pulse, pi_pulse, t_wait, 1, f_bg_oscillations)

import pulse_lib.segments.utility.looping as lp

measurment_parameter = dummy_multi_parameter("digitzer_1", label="qubit_1 (spin up)", unit="%")

# todo put in hardware file
pulse.IQ_channels[0].virtual_channel_map[0].reference_frequency = 1.01e9



pi2_rot = single_qubit_gate_spec('qubit1_MW', 1.1e9, 50, 100, 0, AM_mod='blackman')
pi_rot = single_qubit_gate_spec('qubit1_MW', 1.1e9, 100, 150, 0, AM_mod='blackman')

seg = pulse.mk_segment()
T2_ramsey(seg, pi2_rot, lp.linspace(100,1000), 10e6)
plot_seg(seg)

seg = pulse.mk_segment()
T2_hahn(seg, pi2_rot,pi_rot, lp.linspace(100,1000, axis=0), 10e6)
plot_seg(seg)

seg = pulse.mk_segment()
T2_CPMG_t_tot(seg, pi2_rot,pi_rot, 5000, 20, 10e6)
plot_seg(seg)