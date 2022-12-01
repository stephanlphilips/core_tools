
from core_tools.drivers.hardware.hardware import hardware

def setup_hardware():
    hw = hardware()
    hw.dac_gate_map = {
                    'LB1': (0,1),
                    'LB2': (0,2),
                    'LB3': (0,3),
                    'LB4': (0,4),
                    'LB5': (0,5),
                    'LB6': (0,6),
                    'LB7': (0,7),
                    'LB8': (0,8),
                    'UB1': (0,9),
                    'UB2': (0,10),
                    'UB3': (0,11),
                    'UB4': (0,12),
                    'UB5': (0,13),
                    'UB6': (0,14),
                    'UB7': (0,15),
                    'UB8': (0,16),
                    'NW_P': (1,1),
                    'NW_BL': (1,2),
                    'NW_BR': (1,3),
                    'NE_P': (1,4),
                    'NE_BL': (1,5),
                    'NE_BR': (1,6),
                    'SW_P': (1,7),
                    'SW_BL': (1,8),
                    'SW_BR': (1,9),
                    'SE_P': (1,10),
                    'SE_BL': (1,11),
                    'SE_BR': (1,12),
                    'P1': (1,13),
                    'P2': (1,14),
                    'P3': (1,15),
                    'P4': (1,16),
                    'P5': (2,1),
                    'P6': (2,2),
                    'P7': (2,3),
                    'NW_CO': (2,4),
                    'NE_CO': (2,5),
                    'SW_CO': (2,6),
                    'SE_CO': (2,7),
                    'Vsd1': (2,8),
                    'Vsd2': (2,9),
                    'Vsd3': (2,10),
                    'Vsd4': (2,11),
                    'zNA_2_12': (2,12),
                    'zNA_2_13': (2,13),
                    'zNA_2_14': (2,14),
                    'zNA_2_15': (2,15),
                    'zNA_2_16': (2,16),
                    }

    gate_boundaries = dict({})
    for gate in hw.dac_gate_map.keys():
        if 'SRC' in gate or 'SNK' in gate:
            gate_boundaries[gate] = (-50, 2000)
        else:
            gate_boundaries[gate] = (-1900, 1000)

    for i in range(1,5):
        gate_boundaries[f'Vsd{i}'] = (-500, 500)

    hw.boundaries = gate_boundaries

    all_gates = [kg for kg in hw.dac_gate_map.keys() if 'zNA' not in kg and 'Vsd' not in kg]

    hw.virtual_gates.add('vgates', all_gates, normalization=True)

    sensor_gates = ['SE_P', 'NW_P', 'NE_P', 'SW_P']
    hw.virtual_gates.add('sensors', sensor_gates, virtual_gates=('all_sens', 'zzzSens2', 'zzzSens3', 'zzzSens4'))

    hw.virtual_gates.add('dets12', ['vP1', 'vP2'],
                         virtual_gates=('e12', 'U12'),
                         matrix=[
                                 [+1.0, -1.0],
                                 [+0.5, +0.5],
                                 ]
                         )

    hw.virtual_gates.add('dets67', ['P5', 'P6', 'P7', 'SE_P'], virtual_gates=('e67', 'U67', 'zd67_P7', 'zd67_SE_P'))
    hw.virtual_gates.add('coupling_6b7', ['P6', 'P7', 'UB4', 'LB7', 'SE_P'], virtual_gates=('zP6', 'zP7', 't_6b7', 'j_6b7', 'zSE_P'))
#    hw.virtual_gates.add('coupling_6b7', ['P6', 'P7', 'UB3', 'UB4', 'LB7', 'SE_P'], virtual_gates=('zP6', 'zP7', 'xxx', 't_6b7', 'j_6b7', 'zSE_P'))

    hw.virtual_gates.add('coupling_6t7', ['P6', 'P7', 'UB5', 'LB7', 'SE_P'], virtual_gates=('zzP6', 'zzP7', 't_6t7', 'j_6t7', 'zzSE_P'))
    #hw.virtual_gates.add('dets34', ['P4', 'P5', 'P6', 'P3', 'SW_P'], virtual_gates=('e45', 'U45', 'vvvvP6', 'vvP3', 'vvSW_P'))
    # hw.virtual_gates.add('P567', ['P5', 'P6', 'P7', 'SE_P'], virtual_gates=('x_ax', 'y_ax', 'zzzz', 'zzSE_P'))
    hw.awg2dac_ratios.add(hw.virtual_gates.vgates.gates)

    return hw
