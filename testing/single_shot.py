from core_tools.sweeps.pulse_lib_sweep import spin_qubit_exp, dummy_multi_parameter
from pulse_templates.elzerman_pulses.basic_elzerman_pulse import elzerman_basic
from pulse_templates.oper.operators import jump, wait

from pulse_templates.utility.plotting import plot_seg

measurment_parameter = dummy_multi_parameter("digitzer_1", label="qubit_1 (spin up)", unit="%")


#%%
import pulse_lib.segments.utility.looping as lp

seg = pulse.mk_segment()

gates = ('B2',)
t_init = lp.linspace(5000, 10000)
t_ramp = 500
t_load = 1000
t_read = 5000

p_0 = (-20,)
p_1 = (1,)
p_2 = (-1,)
p_3 = (10,)
p_4 = (50,)

elzerman_basic(seg, gates, t_init, t_ramp, t_load, t_read, p_0, p_1, p_2, p_3, p_4)

seg2 = pulse.mk_segment()
seg2.B2 += 50
jump(seg2, gates, 5000, (0,), (50,))
jump(seg2, gates, 5000, (50,), (50,))
jump(seg2, gates, 5000, (50,), (-50,))
jump(seg2, gates, 5000, (0,), (50,))

from core_tools.HVI.single_shot_exp.HVI_single_shot import HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI

sequence = pulse.mk_sequence([seg2, seg])
sequence.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
sequence.nrep = 1000
sequence.sample_rate=1e9

#%%

for i in range(50):
    sequence.upload([i])
    sequence.play([i])
