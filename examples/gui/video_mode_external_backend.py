from core_tools.GUI.keysight_videomaps import liveplotting
from core_tools.GUI.keysight_videomaps.data_saver.qcodes import QCodesDataSaver
from core_tools.GUI.qt_util import qt_init

from pulse_lib.base_pulse import pulselib
from scan_generator_Keysight_shuttling import ShuttlingScanGeneratorKeysight, ShuttlingSequence

def create_pulse_lib(awg_channels, dig_channels):
    pulse = pulselib()

    # Note: Video Mode retrieves channel names from pulse-lib.
    for num, ch_name in enumerate(awg_channels):
        pulse.define_channel(ch_name, "AWG_X", num)

    for num, ch_name in enumerate(dig_channels):
        pulse.define_digitizer_channel(ch_name, "Digitizer", num)

    # do not initialize backend
    # pulse.finish_init()
    return pulse





if __name__ == '__main__':

    pulse = create_pulse_lib(
        [f"P{i}" for i in range(1, 9)],
        [f"SD{i}" for i in range(1, 3)],
        )

    defaults = {
        'gen': {
            'n_columns': 2,
            'bias_T_RC': 5, # bias-T RC time [ms] only used for warnings in GUI.
            },
        }

    # Initialize Qt5 if running in IPython console
    qt_init()

    # Using the qcodes datasaver since that can be used without establishing the connection to the database.
    # Remove this line to use the default datasaver.
    liveplotting.set_data_saver(QCodesDataSaver())


    v_setpoints = {}
    v_setpoints["read"] = {
        "P8": 10.0
        }

    for step in range(4):
        v_setpoints[f"dot{step+1}"] = {
            f"P{step+1}": 10.0,
            }

    v_setpoints["scan"] = {
        "P2": 20.0
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

    scan_generator = ShuttlingScanGeneratorKeysight(shuttling_sequence)
    # scan_generator.plot_first = True

    # Start the liveplotting
    plotting = liveplotting.liveplotting(
            pulse,
            scan_generator=scan_generator,
            cust_defaults=defaults,
            )
