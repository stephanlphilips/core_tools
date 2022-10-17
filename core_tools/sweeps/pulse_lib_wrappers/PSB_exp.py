
from core_tools.drivers.M3102A import MODES, OPERATION_MODES
from core_tools.HVI2.schedule_manager import ScheduleMgr

import qcodes as qc
from pulse_lib.segments.utility.measurement_converter import measurement_converter
from pulse_lib.keysight.qs_uploader import QsUploader


def add_schedule_to_lambda(schedule):
    def new_lamdba(seq):
        seq.set_hw_schedule(schedule)
    return new_lamdba

def run_qubit_exp(exp_name, sequence, mode = 'normal'):
    '''
    Args:
        exp_name (str) : name of the experiment
        sequence (sequence_builder) : sequence builder
    '''
    station = qc.Station.default

    my_seq = sequence.forge()
    my_seq.neutralise = True
    my_seq.n_rep = sequence.n_rep

    md = my_seq.measurements_description

    n_acq = md.acquisition_count
    station.dig.set_operating_mode(OPERATION_MODES.HVI_TRG)
    station.dig.set_acquisition_mode(MODES.IQ_INPUT_SHIFTED_I_OUT)

    active_channels = []

    if not QsUploader.use_digitizer_sequencers:
        print(f'QsUploader.use_digitizer_sequencers set to {QsUploader.use_digitizer_sequencers}')
    for channel_name in md.acquisitions:
        dig_channel = station.pulse.digitizer_channels[channel_name]

        for ch in dig_channel.channel_numbers:
            if n_acq[channel_name] > 0:
                station.dig.set_channel_properties(ch, V_range=1.0)
                station.dig.set_daq_settings(ch, my_seq.n_rep*n_acq[channel_name], 30)
                active_channels.append(ch)

    station.dig.set_active_channels(active_channels)

    starting_lambda = add_schedule_to_lambda(ScheduleMgr().single_shot())
    my_seq.starting_lambda = starting_lambda
    mc = measurement_converter(md, my_seq.n_rep)

    if mode == 'normal':
        dig_param = mc.less_results()
    else:
        dig_param = mc.state_tomography_results()

    dig_param.setUpParam(mc, station.dig)
    my_seq.m_param = dig_param

    return my_seq, dig_param, exp_name


