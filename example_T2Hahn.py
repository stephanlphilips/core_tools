from pulse_templates.utility.plotting import plot_seg
from pulse_templates.demo_pulse_lib.virtual_awg import get_demo_lib
from pulse_templates.utility.oper import add_block, add_ramp
from pulse_templates.utility.plotting import plot_seg

from pulse_templates.coherent_control.single_qubit_gates.standard_set import single_qubit_std_set
from pulse_templates.coherent_control.single_qubit_gates.single_qubit_gates import single_qubit_gate_spec
from pulse_templates.elzerman_pulses.basic_elzerman_pulse import elzerman_read
from pulse_templates.coherent_control.single_qubit_gates.T2_meas import T2_hahn

from pulse_lib.segments.utility.looping import linspace

pulse = get_demo_lib('quad')

INIT = pulse.mk_segment()
MANIP = pulse.mk_segment()
READ = pulse.mk_segment()

# assume 1QD -- elzerman init
t_init = 50e3
gates = ('vP4',)
p_0 = (0, )

add_block(INIT, t_init, gates, p_0)



# T2 hahn
MANIP.vP4 += 20
xpi2 = single_qubit_gate_spec('qubit4_MW', 1.1e8, 1000, MW_power=120, padding=2) #X
xpi = single_qubit_gate_spec('qubit4_MW', 1.1e8, 2000, MW_power=120, padding=2) #X2

ss_set = single_qubit_std_set()
ss_set.X = xpi2
ss_set.X2 = xpi

times = linspace(100, 1e5, 100, axis=0, name='time', unit='ns')

T2_hahn(MANIP, ss_set, times, 1e6)

#
p_read = (0, )
t_read = 100e3

elzerman_read(READ, gates, t_read, p_read, disable_trigger=False)

# run exp()
run_exp([INIT, MANIP, READ], nrep = 100, ..)
