from core_tools.utility.digitizer_param_conversions import IQ_to_scalar, down_sampler,data_reshaper, PSB_param, get_phase_compentation_IQ_signal

from core_tools.utility.mk_digitizer_param import get_digitizer_param
from core_tools.utility.dig_utility import autoconfig_dig_v2, MODES
from core_tools.drivers.M3102A import DATA_MODE
from core_tools.sweeps.sweep_utility import check_OD_scan
from core_tools.HVI2.schedule_manager import ScheduleMgr

from core_tools.utility.qubit_param_gen.digitizer_parameter import get_digitizer_qubit_param
import qcodes as qc


def add_schedule_to_lambda(lambda_func, schedule):
    def new_lamdba(seq):
        seq.set_hw_schedule(schedule)
        lambda_func()
    return new_lamdba

def run_PSB_exp(name, segment, t_meas, n_rep, n_qubit ,raw_traces ,phase, channels=[1,2,3,4], order=1, threshold=None):
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
    dig_param, starting_lambda = get_digitizer_param(station.dig, t_meas, n_rep*n_qubit, channels, raw_traces)
    
    starting_lambda = add_schedule_to_lambda(starting_lambda, ScheduleMgr().single_shot(n_qubit))

    IQ_meas_param = IQ_to_scalar(dig_param, phase)
    if n_qubit > 1:
        reshaped_signal = data_reshaper(n_qubit, IQ_meas_param)
        PSB_out = PSB_param(reshaped_signal, order, threshold)
    else:
        PSB_out = PSB_param(IQ_meas_param, order, threshold)
    
    
    if not isinstance(segment, list):
        segment = [segment]
    
    my_seq = station.pulse.mk_sequence(segment)

    my_seq.n_rep = n_rep
    my_seq.neutralise = True

    my_seq.starting_lambda = starting_lambda
    # my_seq.starting_lambda(my_seq)

    if raw_traces == True:
        return check_OD_scan(my_seq, reshaped_signal) + (name, )
    else:
        return check_OD_scan(my_seq, PSB_out) + (name, )

def run_qubit_exp(exp_name, sequence, measurement_mgr):
    '''
    Args:
        exp_name (str) : name of the experiment
        sequence (list<segment>) : list of segments to play back
        measurement_mgr (measurement_manager) : manager that describes what needs to be measured
    '''
    station = qc.Station.default
    dig_param, starting_lambda = get_digitizer_qubit_param(station.dig, measurement_mgr)
    
    starting_lambda = add_schedule_to_lambda(starting_lambda, ScheduleMgr().single_shot(measurement_mgr.n_readouts))

    if not isinstance(sequence, list):
        sequence = [sequence]
    
    my_seq = station.pulse.mk_sequence(sequence)

    my_seq.n_rep = measurement_mgr.n_rep
    my_seq.neutralise = True

    my_seq.starting_lambda = starting_lambda
    my_seq.starting_lambda(my_seq)


    return check_OD_scan(my_seq, dig_param) + (exp_name, )
