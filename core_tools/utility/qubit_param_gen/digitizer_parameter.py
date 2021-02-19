from qcodes import MultiParameter
import numpy as np
from core_tools.drivers.M3102A import MODES, DATA_MODE

class _digitzer_qubit_param(MultiParameter):
        def __init__(self, digitizer, measurement_mgr):
            self.measurement_mgr = measurement_mgr
            param_prop = measurement_mgr.generate_setpoints_information()
            super().__init__(name=digitizer.name, names = param_prop.names, shapes = param_prop.shapes,
                            labels = param_prop.labels, units = param_prop.units,
                            setpoints = param_prop.setpoints, setpoint_names=param_prop.setpoint_names,
                            setpoint_labels=param_prop.setpoint_labels, setpoint_units=param_prop.setpoint_units)
            self.dig = digitizer

        def get_raw(self):
            data = self.dig.measure()
            return measurement_mgr.format_data(data)

def get_digitizer_qubit_param(digitizer, measurement_mgr):
    """
    make a parameter for the digitizer
    
    Args:
        digitizer (Instrument) : qcodes digitizer object
        measurement_mgr (measurement_manager) : manager for qubit measurements

    Note that you should regenerate the parameter each time before starting a new measurement/loop. This should be cleaned up later a bit by doing some more stuff in HVI.
    """
    def starting_lambda():
            digitizer.set_acquisition_mode(MODES.AVERAGE)
            digitizer.set_digitizer_HVI(measurement_mgr.t_measure, measurement_mgr.n_rep, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2,3,4], Vmax=0.5)

    return _digitzer_qubit_param(digitizer, measurement_mgr), starting_lambda


