import qcodes as qc
import sample_specific.station as XLD_SiQubit
import os

def init_station():
    '''
    Initialise the V2 station.
    '''

    # load config file with the instrument settings
    station = qc.Station(config_file = os.path.dirname(XLD_SiQubit.__file__) + '\\instruments.yaml')

    station.load_instrument('hardware')
    station.load_instrument('AWG1')
    station.load_instrument('AWG2')
    station.load_instrument('AWG3')
    

    return station


def set_dac_range(my_range='2v bi'):
    '''
    DO not run this when a sample is connected!
    '''
    # quicky make sure that the dacs are in the wanted range
    station = qc.station.Station.default
    dacs = [station.dac_a, station.dac_b, station.dac_c]

    for dac in dacs:
        for dac_i in range(dac._number_dacs):
           if dac._get_span(dac_i) != my_range:
               dac._set_span(dac_i, my_range)