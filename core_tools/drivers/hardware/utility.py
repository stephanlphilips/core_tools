from core_tools.data.ds.data_set import load_by_id

import numpy as np
import qcodes as qc

def load_virtual_gate_matrix_from_ds(ds_id, hardware_name='hardware'):
    '''
    load virtual gate matrix from a existing dataset.

    Args:
        ds_id (int) : id of the dataset to load
        hardware_name (str) : name of hardware in the snapshot present in the dataset
    '''
    load_virtual_gate_matrix_from_snapshot(load_by_id(ds_id).snapshot, hardware_name)

def load_virtual_gate_matrix_from_snapshot(snapshot, hardware_name='hardware', no_norm=True):
    '''
    load virtual gate matrix from a existing datasset.

    Args:
        snapshot (dict) : snapshot of the station (loaded JSON)
        hardware_name (str) : name of hardware in the snapshot present in the dataset
    '''
    virtual_gates = snapshot['station']['instruments'][hardware_name]['virtual_gates']
    
    print('Loading  virtual gates matrices from dataset:')

    for key, value in virtual_gates.items():
        if no_norm:
            try:
                matrix = value['virtual_gate_matrix_no_norm']
            except:
                print('no old style matrix found, trying new style')
                matrix = value['virtual_gate_matrix']
        else:
            matrix = value['virtual_gate_matrix']

        mat = np.array(eval(matrix))

        hw = qc.Station.default.hardware
        hw.virtual_gates.add(key, value['real_gate_names'], value['virtual_gate_names'], mat)
        
        print(f'\tfound virtual gate matrix named ::\t{key} ({mat.shape[0]}x{mat.shape[1]})')

def load_AWG_to_dac_conversion_from_ds(ds_id, hardware_name='hardware'):
    '''
    load AWG to dac conversion from a exisisting dataset.

    Args:
        ds_id (int) : id of the dataset to load
        harware_name (str) : name of the hardware in the dataset its snapshot
    '''
    load_AWG_to_dac_conversion_from_snapshot(load_by_id(ds_id).snapshot, hardware_name)

def load_AWG_to_dac_conversion_from_snapshot(snapshot, hardware_name='hardware'):
    hardware_info = snapshot['station']['instruments'][hardware_name]
    if 'AWG_to_DAC' in hardware_info.keys():
        AWG_to_DAC = hardware_info['AWG_to_DAC']
    elif 'awg2dac_ratios' in hardware_info.keys():
        AWG_to_DAC = hardware_info['awg2dac_ratios']
    else:
        raise ValueError('AWG to DAC conversion not found!')

    hw = qc.Station.default.hardware
    hw.awg2dac_ratios.add(AWG_to_DAC.keys())

    for gate, value in AWG_to_DAC.items():
        hw.awg2dac_ratios[gate] = value
    print('AWG to dac conversions loaded!')



if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')
    from core_tools.drivers.hardware.hardware import hardware
    from core_tools.drivers.virtual_dac import virtual_dac
    from core_tools.drivers.gates import gates
    import qcodes as qc

    my_dac_1 = virtual_dac("dac_a", "virtual")
    my_dac_2 = virtual_dac("dac_b", "virtual")
    my_dac_3 = virtual_dac("dac_c", "virtual")
    my_dac_4 = virtual_dac("dac_d", "virtual")

    hw =  hardware()
    # hw.RF_source_names = []
    hw.dac_gate_map = {
        'B0': (0, 1), 'P1': (0, 2), 
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6), 
        'B3': (0, 7), 'P4': (0, 8), 
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13), 'S6' : (0,14,),
        'SD1_P': (1, 1), 'SD2_P': (1, 2), 
        'SD1_B1': (1, 3), 'SD2_B1': (1, 4),
        'SD1_B2': (1, 5), 'SD2_B2': (1, 6),}

    hw.boundaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    hw.awg2dac_ratios.add(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'S6', 'SD1_P', 'SD2_P'])
    hw.virtual_gates.add('test', ['B0', 'P1', 'B1', 'P2', 'B2', 'P3', 'B3', 'P4', 'B4', 'P5', 'B5', 'P6', 'B6', 'S6', 'SD1_P', 'SD2_P'])
    
    my_gates = gates("gates", hw, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])
    station=qc.Station(my_gates, hw)
    from core_tools.sweeps.sweeps import do1D
    from qcodes.tests.instrument_mocks import DummyInstrument
    import random

    instr = DummyInstrument('instr', gates=['measure'])
    instr.measure.get =  lambda: random.randint(0, 100)
    station.add_component(instr)

    # do1D(station.gates.B0, 0, 20, 50, 0.1, instr.measure).run()
    
    # load_AWG_to_dac_conversion_from_ds(18, 'hardware')