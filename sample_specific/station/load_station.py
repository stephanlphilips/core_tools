
from sample_specific.station import init_station
from sample_specific.station.load_pulse_lib import return_pulse_lib

station = init_station()
pulse = return_pulse_lib(station.hardware, station.AWG1, station.AWG2, station.AWG3)
