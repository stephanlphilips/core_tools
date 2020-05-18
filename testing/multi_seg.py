# -*- coding: utf-8 -*-
"""
Created on Fri May 15 13:59:26 2020

@author: LocalAdmin
"""


from pulse_templates.utility.plotting import plot_seg
from pulse_templates.demo_pulse_lib.virtual_awg import get_demo_lib
from pulse_templates.utility.oper import add_block, add_ramp
from pulse_templates.utility.plotting import plot_seg

from pulse_templates.coherent_control.single_qubit_gates.standard_set import single_qubit_std_set
from pulse_templates.coherent_control.single_qubit_gates.single_qubit_gates import single_qubit_gate_spec
from pulse_templates.elzerman_pulses.basic_elzerman_pulse import elzerman_read


INIT = pulse.mk_segment()
MANIP = pulse.mk_segment()
READ = pulse.mk_segment()

# assume 1QD -- elzerman init
t_init = 50e3
gates = ('B2',)
p_0 = (200, )

add_block(INIT, t_init, gates, p_0)
#done.

# add single qubit gates in manip

# add default dc levels
MANIP.B2 += 50

# define a set 
xpi2 = single_qubit_gate_spec('qubit1_MW', 1.1e8, 100, 120, padding=2, AM_mod='cosine')
xpi = single_qubit_gate_spec('qubit1_MW', 1.1e8, 200, 120, padding=2)

ss_set = single_qubit_std_set()
ss_set.X = xpi2
ss_set.X2 = xpi

ss_set.X.add(MANIP)
ss_set.X.add(MANIP)
ss_set.Y.add(MANIP)


# assume 1QD -- elzerman read -- simplified
t_read = 50e3
gates = ('B2',)
p_readout = (-100, )

elzerman_read(READ, gates, t_read, p_readout)
#done.


from core_tools.HVI.single_shot_exp.HVI_single_shot import HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI

sequence = pulse.mk_sequence([MANIP, INIT, READ])
sequence.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
sequence.nrep = 1000
sequence.sample_rate=1e9

#%%

for i in range(1):
    print(i)
    sequence.upload([i])
    sequence.play([i])
