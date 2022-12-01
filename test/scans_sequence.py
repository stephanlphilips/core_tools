import core_tools as ct
from core_tools.sweeps.scans import Scan, sweep, Function, Break
from qcodes import ManualParameter
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

from setup_config.init_pulse_lib import init_pulse_lib
from setup_config.init_station import init_station
from util.multi_param import MyDigitizerParam
import pulse_lib.segments.utility.looping as lp
from pulse_lib.tests.hw_schedule_mock import HardwareScheduleMock

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = init_station()

pulse = init_pulse_lib(
    station.hardware,
    (station[f'AWG{i+1}'] for i in range(8))
    )

#%%
x = ManualParameter('x', initial_value=0)
y = ManualParameter('y', initial_value=9)

t = ElapsedTimeParameter('t')

t_measure = 200
m_param = MyDigitizerParam(t_measure, n_rep=None)

#%%
amplitude = lp.linspace(0, 20, 11, axis=0, name='amplitude')
#t_pulse = lp.linspace(100, 200, 6, axis=1, name='t_pulse')
t_pulse = 2000
seg = pulse.mk_segment()
seg.P1.add_block(0, t_pulse, amplitude)
sequence = pulse.mk_sequence([seg])
sequence.set_hw_schedule(HardwareScheduleMock())


#%%

ds1 = Scan(
        sweep(x, -20, 20, 3, delay=0.01),
        t,
        sequence,
        m_param,
        name='test_scan_sequence',
        silent=True,
        ).run()



#%%
from core_tools.sweeps.sweeps import do0D

#ds2 = do0D(sequence, t, m_param, name='do0D-sequence', silent=True).run()
