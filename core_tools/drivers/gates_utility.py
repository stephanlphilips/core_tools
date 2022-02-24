from core_tools.data.ds.data_set import load_by_id

import qcodes as qc

def load_gate_voltages_from_ds(ds_id, gates_name='gates', hardware_name='hardware',
                               force=False):
    '''
    load gate voltages from an existing dataset.

    Args:
        ds_id (int) : id of the dataset to load
        gates_name (str) : name of gates instrument in the snapshot present in the dataset
        harware_name (str) : name of the hardware in the snapshot
        force (bool) : if True overwrite without asking, else ask confirmation before changing voltage
    '''
    load_gate_voltages_from_snapshot(load_by_id(ds_id).snapshot,
                                     gates_name=gates_name,
                                     hardware_name=hardware_name,
                                     force=force)


def load_gate_voltages_from_snapshot(snapshot, gates_name='gates', hardware_name='hardware',
                                     force=False):
    '''
    load gate voltages from an existing dataset.

    Args:
        snapshot (str) : json string with snapshot
        gates_name (str) : name of gates instrument in the snapshot
        harware_name (str) : name of the hardware in the snapshot
        force (bool) : if True overwrite without asking, else ask confirmation before changing voltage
    '''
    gates_obj = qc.Station.default.components['gates']
    instruments = snapshot['station']['instruments']

    try:
        gate_params = instruments[gates_name]['parameters']
    except:
        raise ValueError(f'no gate parameter {gates_name} found in snapshot')

    try:
        vgates = ['IDN']
        for key, val in instruments[hardware_name]['virtual_gates'].items():
            vgates += val['virtual_gate_names']
    except:
        raise ValueError('cannot detect virtual gates, not restoring voltages')

    for key, val in gate_params.items():
        if key not in vgates:
            voltage = float(val['value'])
            gate_param = gates_obj[key]
            current_voltage = gate_param()
            diff = voltage - current_voltage
            abs_diff = abs(diff)
            if abs_diff > 2:
                if force or confirm(f'setting {key} to {voltage:.1f} mV (diff: {diff:.1f} mV), are you sure?'):
                    gate_param(voltage)
            else:
                gate_param(voltage)


def confirm(prompt_text):
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = "_"
    while answer not in ["", "y", "n"]:
        answer = input(prompt_text + ' [y]/n').lower()
    return answer == "y" or answer == ''

