from core_tools.utility.digitizer_param_conversions import IQ_to_scalar, down_sampler,data_reshaper, PSB_param, get_phase_compentation_IQ_signal


from core_tools.HVI.single_shot_exp.HVI_single_shot import load_HVI, set_and_compile_HVI, excute_HVI, HVI_ID
from core_tools.HVI.single_shot_exp.HVI_single_shot_1qubit import load_HVI_1, set_and_compile_HVI_1, excute_HVI_1, HVI_ID_1
from core_tools.HVI.single_shot_exp.HVI_single_shot_2qubit import load_HVI_2, set_and_compile_HVI_2, excute_HVI_2, HVI_ID_2
from core_tools.HVI.single_shot_exp.HVI_single_shot_3qubit import load_HVI_3, set_and_compile_HVI_3, excute_HVI_3, HVI_ID_3

from core_tools.utility.mk_digitizer_param import get_digitizer_param
from core_tools.utility.dig_utility import autoconfig_dig_v2, MODES
from core_tools.drivers.M3102A import DATA_MODE
from core_tools.sweeps.sweep_utility import check_OD_scan


import qcodes as qc


def run_PSB_exp(name, segment, t_meas, n_rep, n_qubit ,raw_traces ,phase, threshold=None):
    '''
    autoconfig utility for runing a readout experiment

    Args:
        name (str) : name of the measurement to be run
        segment (segment_container) : segment to be played on the AWG
        t_meas (double) : measurement time to set to the digitizer (will be removed when digitzer updates)
        n_rep (double) : number times a experiment needs to be repeated
        n_qubit (int) : number of qubit to be measured
        raw_traces (bool) : show raw traces
        phase (double) : phase rotation in the IQ plane for SD
    Returns:
        sequence (sequence) : pulselib sequence
        minstr (MultiParameter) : parameter to be measured
    '''

    station = qc.Station.default

    if raw_traces == False:
        autoconfig_dig_v2(station.dig, MODES.AVERAGE)
        data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES
        if n_rep == 1:
            data_mode = DATA_MODE.AVERAGE_CYCLES
        if n_qubit > 1:
            data_mode = DATA_MODE.AVERAGE_TIME
        station.dig.set_data_handling_mode(data_mode)
    else:
        autoconfig_dig_v2(station.dig, MODES.NORMAL)
        data_mode = DATA_MODE.FULL
        station.dig.set_data_handling_mode(data_mode)
    
    dig_param = get_digitizer_param(station.dig, t_meas, n_rep*n_qubit, data_mode)
    IQ_meas_param = IQ_to_scalar(dig_param, phase)
    if n_qubit > 1:
        reshaped_signal = data_reshaper(n_qubit, IQ_meas_param)
        PSB_out = PSB_param(reshaped_signal, threshold)
    else:
        PSB_out = PSB_param(IQ_meas_param, threshold)
    
    
    if raw_traces == True:
        down_sampled_seq = down_sampler(PSB_out, 1e6)
    
    if not isinstance(segment, list):
        segment = [segment]
    
    my_seq = station.pulse.mk_sequence(segment)
    
    settings = dict()
    settings['averaging'] = True
    if raw_traces == True:
        settings['averaging'] = False

    if n_qubit == 1:
        print('1 qubit detected')
        my_seq.add_HVI(HVI_ID_1, load_HVI_1, set_and_compile_HVI_1, excute_HVI_1, digitizer = station.dig, **settings)
    elif n_qubit == 2:
        print('2 qubits detected')
        my_seq.add_HVI(HVI_ID_2, load_HVI_2, set_and_compile_HVI_2, excute_HVI_2, digitizer = station.dig, **settings)
    elif n_qubit == 3:
        print('3 qubits detected')
        my_seq.add_HVI(HVI_ID_3, load_HVI_3, set_and_compile_HVI_3, excute_HVI_3, digitizer = station.dig, **settings)
    else:
        raise ValueError('No more than 3 qubit supported at the moment :/')

    my_seq.n_rep = n_rep
    my_seq.neutralise = True

    station.pulse.uploader.release_memory()

    if raw_traces == True:
        return check_OD_scan(my_seq, down_sampled_seq)
    else:
        return check_OD_scan(my_seq, PSB_out)
