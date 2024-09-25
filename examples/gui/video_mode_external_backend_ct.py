from core_tools.GUI.keysight_videomaps import liveplotting
from scan_generator_Keysight_shuttling import ShuttlingScanGeneratorKeysight, ShuttlingSequence

from pulse_lib.tests.configurations.test_configuration import context

pulse = context.init_pulselib(n_gates=6, n_sensors=2, virtual_gates=True)


defaults = {
    'gen': {
        'n_columns': 2,
        },
    }

v_setpoints = {}
v_setpoints["read"] = {
    "P1": -20.0
    }

v_setpoints["scan"] = {
    }

for step in range(4):
    v_setpoints[f"dot{step+1}"] = {
        f"P{step+1}": 10.0,
        }

sequence = [
    "dot1", "dot2", "dot3", "dot4",
    "scan",
    "dot4", "dot3", "dot2", "dot1",
    "read",
    ]

shuttling_sequence = ShuttlingSequence(
        v_setpoints,
        sequence=sequence,
        t_shuttle_step=100,
        scan_point="scan",
        t_scan=200,
        read_point="read",
        t_resolution=100)

scan_generator = ShuttlingScanGeneratorKeysight(pulse, shuttling_sequence)
# scan_generator.plot_first = True

# Start the liveplotting
plotting = liveplotting.liveplotting(
        pulse,
        scan_generator=scan_generator,
        )
