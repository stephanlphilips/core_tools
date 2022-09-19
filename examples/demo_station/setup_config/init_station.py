import qcodes as qcodes
import os

import setup_config

from setup_config.setup_hardware import setup_hardware
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import fake_digitizer

def init_station():

    # load config file with the instrument settings
    station = qcodes.Station(config_file = os.path.dirname(setup_config.__file__) + '\\instruments.yaml')

    station.load_instrument('D5a1')
    station.load_instrument('D5a2')
    station.load_instrument('D5a3')
#    station.load_instrument('D5a1', spi_rack=None)
#    station.load_instrument('D5a2', spi_rack=None)
#    station.load_instrument('D5a3', spi_rack=None)

    hw = setup_hardware()
    station.add_component(hw)
    station.load_instrument(
            'gates', hardware = hw,
            dac_sources = [station.D5a1, station.D5a2, station.D5a3])


    # load the digitizer
#   station.load_instrument('digitizer_keys')
    dig = fake_digitizer('digitizer_keys')
    station.add_component(dig)

    station.load_instrument('AWG1')
    station.load_instrument('AWG2')
    station.load_instrument('AWG3')
    station.load_instrument('AWG4')
    station.load_instrument('AWG5')
    station.load_instrument('AWG6')
    station.load_instrument('AWG7')
    station.load_instrument('AWG8')

    return station
