from core_tools.utility.digitizer_param_conversions import IQ_to_scalar, down_sampler,data_reshaper, Elzerman_param, get_phase_compentation_IQ_signal

from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Keysight import construct_1D_scan_fast
from core_tools.HVI.single_shot_exp.HVI_single_shot import load_HVI, set_and_compile_HVI, excute_HVI, HVI_ID
from core_tools.sweeps.sweeps_old.pulse_lib_sweep import spin_qubit_exp
from core_tools.utility.mk_digitizer_param import get_digitizer_param
from core_tools.utility.dig_utility import autoconfig_digitizer
from core_tools.drivers.M3102_firmware_loader import M3102A_CLEAN, M3102A_AVG
from core_tools.drivers.M3102A import DATA_MODE
from core_tools.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG

import qcodes as qc

def measure_optimal_phase_IQ_sigal(SD = 'vSD2_P'):
    '''
    Measure the phase rotation that is needed to rotate the sigal of the SD into the I line of the IQ plane
    
    Args:
        SD (str) : gates name to sweep (sigal generator)
    Returns : 
        phase (double) : phase rotation in the IQ plane
    '''
    station = qc.Station.default
    #make scan around SD to make phase estimation
    param = construct_1D_scan_fast(SD, 10, 400, 50000, False, station.pulse, station.dig, [1,2], 100e6)
    return get_phase_compentation_IQ_signal(param)

def run_readout_exp(name, segment, t_meas, n_rep, show_raw_traces, threshold, blib_down, phase):
    '''
    autoconfig utility for runing a readout experiment

    Args:
        name (str) : name of the measurement to be run
        segment (segment_container) : segment to be played on the AWG
        t_meas (double) : measurement time to set to the digitizer (will be removed when digitzer updates)
        n_rep (double) : number times a experiment needs to be repeated
        n_qubit (int) : number of qubit to be measured
        show_raw_traces (bool) : show raw traces
        threshold (double) : threadhold for the detection
        blib_down (bool) : direction of the blib (if true, downward blib expected).
        phase (double) : phase rotation in the IQ plane for SD
    Returns:
        data (qCoDeS dataset) : returns the dataset of the measured data.
    '''

    station = qc.Station.default

    data_mode = DATA_MODE.FULL
    if n_rep == 1:
        data_mode = DATA_MODE.AVERAGE_CYCLES
    
    dig_param = get_digitizer_param(station.dig, t_meas, n_rep, data_mode)
    IQ_meas_param = IQ_to_scalar(dig_param, phase)
    down_sampled_seq = down_sampler(IQ_meas_param, 0.3e6, None)
    elzerman_det = Elzerman_param(down_sampled_seq, threshold, blib_down)
    
    if not isinstance(segment, list):
        segment = [segment]
    
    my_seq = station.pulse.mk_sequence(segment)
    
    settings = dict()
    settings['averaging'] = False

    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI, digitizer = station.dig, **settings)
    my_seq.n_rep = n_rep
    my_seq.neutralise = True

    if show_raw_traces == True:
        my_exp = spin_qubit_exp(name, my_seq, down_sampled_seq)
    else:
        my_exp = spin_qubit_exp(name, my_seq, Elzerman_param)
    data = my_exp.run()

    return data



def run_PSB_exp(name, segment, t_meas, n_rep, raw_traces, phase):
    '''
    autoconfig utility for runing a readout experiment with PSB
    (will use fpga averaging when possible)

    Args:
        name (str) : name of the measurement to be run
        segment (segment_container) : segment to be played on the AWG
        t_meas (double) : measurement time to set to the digitizer (will be removed when digitzer updates)
        n_rep (double) : number times a experiment needs to be repeated
        raw_traces (bool) : show raw traces
        phase (double) : phase rotation in the IQ plane for SD
    Returns:
        data (qCoDeS dataset) : returns the dataset of the measured data.
    '''
    station = qc.Station.default
    
    if raw_traces == False:
        autoconfig_digitizer(station.dig, M3102A_AVG, 'average')
        data_mode = DATA_MODE.AVERAGE_TIME_AND_CYCLES
        if n_rep == 1:
            data_mode = DATA_MODE.AVERAGE_CYCLES
        station.dig.set_data_handling_mode(data_mode)
    else:
        autoconfig_digitizer(station.dig, M3102A_CLEAN, 'normal')
        data_mode = DATA_MODE.FULL
        station.dig.set_data_handling_mode(data_mode)
        
    

    dig_param = get_digitizer_param(station.dig, t_meas, n_rep, data_mode)
    IQ_meas_param = IQ_to_scalar(dig_param, phase)
    
    if raw_traces == True:
        down_sampled_seq = down_sampler(IQ_meas_param, 5e6)

    my_seq = station.pulse.mk_sequence(segment)
    
    settings = dict()
    settings['averaging'] = True
    if raw_traces == True:
        settings['averaging'] = False


    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI, digitizer = station.dig, **settings)
    my_seq.n_rep = n_rep
    my_seq.neutralise = True

    if raw_traces == True:
        my_exp = spin_qubit_exp(name, my_seq, down_sampled_seq)
    else:
        my_exp = spin_qubit_exp(name, my_seq, IQ_meas_param)
    data = my_exp.run()

    station.pulse.uploader.release_memory()

    autoconfig_digitizer(station.dig, M3102A_AVG, 'average')

    return data



