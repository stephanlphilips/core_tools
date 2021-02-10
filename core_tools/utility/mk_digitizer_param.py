from qcodes import MultiParameter
import numpy as np
from core_tools.drivers.M3102A import MODES, DATA_MODE

import matplotlib.pyplot as plt

def reduce_parameter_descriptor_by_2(description, name_add=None):
    '''
    Convert multiparameter argumanets by a factor two (e.g. channel 1 + channel 2 => pair 1 ;  channel 3 + channel 4 => pair 2)
    
    Args:
        description (tuple<any>) : descriptor of a multiparamter e.g. names, labels, ..
        name_add (str) : name to add to the combined names (if provided)
    '''
    new_description = list()

    for i in range(int(len(description)/2)):
        if isinstance(description[i],str):
            if name_add is not None:
                comb_name = description[int(i*2)] + description[int(i*2+1)] + name_add
                new_description.append(comb_name)
            else:
                new_description.append(description[int(i*2)])

        elif isinstance(description[i], tuple):
            new_description.append(description[int(i*2)])

    return tuple(new_description)

class _digitzer_measurement_param(MultiParameter):
        def __init__(self, digitizer, t_measure, n_rep, sample_rate, data_mode, channels):
            super().__init__(name=digitizer.name, names = digitizer.measure.names, shapes = digitizer.measure.shapes,
                            labels = digitizer.measure.labels, units = digitizer.measure.units,
                            setpoints = digitizer.measure.setpoints, setpoint_names=digitizer.measure.setpoint_names,
                            setpoint_labels=digitizer.measure.setpoint_labels, setpoint_units=digitizer.measure.setpoint_units,
                            docstring='automatically generated parameter of a digitizer')
            self.dig = digitizer
            self.measure = self.dig.measure
            self.t_measure = t_measure
            self.n_rep = n_rep
            self.sample_rate =sample_rate
            self.data_mode = data_mode
            self.channels = channels

        def get_raw(self):
            data = self.dig.measure()
            # reinit for the next sequence.
            self.dig.set_digitizer_HVI(self.t_measure, self.n_rep, sample_rate = self.sample_rate, data_mode = self.data_mode, channels = self.channels)

            return data

def get_digitizer_param(digitizer, t_measure, n_rep, channels = [1,2], raw=False):
    """
    make a parameter for the digitizer
    
    Args:
        digitizer (Instrument) : qcodes digitizer object
        t_measure (float) : time to measure (ns)
        n_rep (int) : number of times you are retaking the same experiment.
        data_mode (int) : mode of handling data. see data mode in V2_software.drivers.M3102A
        channels (list) : list of channels you want to measure.

    Note that you should regenerate the parameter each time before starting a new measurement/loop. This should be cleaned up later a bit by doing some more stuff in HVI.
    """
    sample_rate = 500e6
    data_mode = None
    
    data_mode = DATA_MODE.AVERAGE_TIME
    if raw == True:
        data_mode = DATA_MODE.FULL

    if raw == True:
        digitizer.set_acquisition_mode(MODES.AVERAGE)
        digitizer.set_digitizer_HVI(t_measure, n_rep, downsampled_rate = 2e6, data_mode = DATA_MODE.FULL, channels =  channels, Vmax=0.5)
        print( digitizer.measure.setpoints)
        print( digitizer.measure.setpoint_names)
    else:
        data_mode = DATA_MODE.AVERAGE_TIME
        digitizer.set_acquisition_mode(MODES.AVERAGE)
        digitizer.set_digitizer_HVI(t_measure, n_rep, data_mode = DATA_MODE.AVERAGE_TIME, channels = channels, Vmax=0.5)

    def starting_lambda():
        if raw == True:
            digitizer.set_acquisition_mode(MODES.AVERAGE)
            digitizer.set_digitizer_HVI(t_measure, n_rep, downsampled_rate = 2e6, data_mode = DATA_MODE.FULL, channels =  channels, Vmax=0.5)
        else:
            data_mode = DATA_MODE.AVERAGE_TIME
            digitizer.set_acquisition_mode(MODES.AVERAGE)
            digitizer.set_digitizer_HVI(t_measure, n_rep, data_mode = DATA_MODE.AVERAGE_TIME, channels = channels, Vmax=0.5)

    return _digitzer_measurement_param(digitizer, t_measure, n_rep, sample_rate, data_mode, channels), starting_lambda

class _digitzer_post_selection_param(MultiParameter):
        def __init__(self, digitzer_measurement_param, n_corr_points, wanted_reference_value):
            shapes = list(digitzer_measurement_param.shapes)

            for i in range(len(shapes)):
                shape = list(shapes[i])
                shape[0] = int(shape[0]/(n_corr_points*2))
                shapes[i] = tuple(shape)
            shapes = tuple(shapes)

            setpoints = list(digitzer_measurement_param.setpoints)
            for i in range(len(setpoints)):
                my_setpoint = list(setpoints[i])
                my_setpoint[0] = my_setpoint[0][0:int(len(my_setpoint[0])/n_corr_points/2)]
                setpoints[i] = tuple(my_setpoint)
            setpoints = tuple(setpoints)

            super().__init__(name=digitzer_measurement_param.name, names = digitzer_measurement_param.names, shapes = shapes,
                            labels = digitzer_measurement_param.labels, units = digitzer_measurement_param.units,
                            setpoints = setpoints, setpoint_names=digitzer_measurement_param.setpoint_names,
                            setpoint_labels=digitzer_measurement_param.setpoint_labels, setpoint_units=digitzer_measurement_param.setpoint_units,
                            docstring='automatically generated parameter of a digitizer')

            self.digitzer_measurement_param = digitzer_measurement_param
            self.dig = self.digitzer_measurement_param.dig
            self.n_corr_points = n_corr_points
            self.wanted_reference_value = wanted_reference_value

        def get_raw(self):
            data_all = self.digitzer_measurement_param.get()

            my_data = []

            for n in range(len(self.shapes)):

                SD_level = np.empty((self.n_corr_points,))
                # 0 -> n
                data_orignal = data_all[0]
                data_out = np.empty(self.shapes[0])
                n_cycles = self.shapes[0][0]
                
                for i in range(n_cycles):
                    # if time steps present
                    if data_orignal.ndim == 2:
                        data_orignal_reshaped = data_orignal.reshape(n_cycles, self.n_corr_points, 2, self.shapes[0][1] )
                        SD_level = np.average(data_orignal_reshaped[i,:, 1, :], axis=1)
                        SD_level_ref = np.copy(SD_level)
                        SD_level -= self.wanted_reference_value
                        SD_level = np.abs(SD_level)
                        location = np.where(SD_level == np.min(SD_level))

                        _extra_offset = self.wanted_reference_value - SD_level_ref[location[0]]

                        data_out[i] = data_orignal_reshaped[i, location[0], 0, :] + _extra_offset
                    else:
                        data_orignal_reshaped = data_orignal.reshape(n_cycles, self.n_corr_points, 2)
                        SD_level = data_orignal_reshaped[i,:, 1]
                        SD_level_ref = np.copy(data_orignal_reshaped[i,:, 1])

                        SD_level -= self.wanted_reference_value
                        SD_level = np.abs(SD_level)
                        location = np.where(SD_level == np.min(SD_level))
                        
                        _extra_offset = self.wanted_reference_value - SD_level_ref[location[0]]

                        if n == 0:
                            data_out[i] = data_orignal_reshaped[i, location[0], 0] + _extra_offset
                        if n == 1:
                            data_out[i] = location[0]
                            # data_out[i] = data_orignal_reshaped[i, location[0], 0]
                my_data.append(data_out)

            return my_data
        
        
  
        

def post_process_SD_correction_data(digitizer_param, n_corr_points, wanted_reference_value, ):
    '''
    function that handles the post processing of the digitizer data

    Args:
        digitizer_param (MultiParameter) : paramter where the digitizer is set to collect the neseceryy data.
        n_corr_points (int) : number of points set for the correction
        wanted_reference_value (float) : wanted voltage of the sensing dot in the reference measurement
    
    Returns:
        digitizer_data (MultiParameter) : parameter witht the corrected amplitudes
    '''
    if digitizer_param.dig.data_mode is DATA_MODE.AVERAGE_CYCLES or digitizer_param.dig.data_mode is DATA_MODE.AVERAGE_TIME_AND_CYCLES:
        raise ValueError("digitzer is not set to the right mode. Please don't AVERAGE the cycles.")

    return _digitzer_post_selection_param(digitizer_param, n_corr_points, wanted_reference_value)






class _digitzer_IQ_to_scalar(MultiParameter):
        def __init__(self, digitzer_measurement_param, T, off):
            '''
            Args:
                digitzer_measurement_param (MultiParameter) : parameter function with valid shape and setpoints (and getter)
                T (tuple <np.ndarray>) : set of rotation matrices
                offset (tuple < float> ) : set of offset for the different IQ channels
            '''
            # assume IQ data comes in pairs (e.g. channel 1 + channel 2 => pair 1 ;  channel 3 + channel 4 => pair 2)

            names = reduce_parameter_descriptor_by_2(digitzer_measurement_param.names, "_IQ_scalar")
            shapes = reduce_parameter_descriptor_by_2(digitzer_measurement_param.shapes)
            labels = reduce_parameter_descriptor_by_2(digitzer_measurement_param.labels)
            units = reduce_parameter_descriptor_by_2(digitzer_measurement_param.units)
            setpoints = reduce_parameter_descriptor_by_2(digitzer_measurement_param.setpoints)
            setpoint_names = reduce_parameter_descriptor_by_2(digitzer_measurement_param.setpoint_names)
            setpoint_labels = reduce_parameter_descriptor_by_2(digitzer_measurement_param.setpoint_labels)
            setpoint_units = reduce_parameter_descriptor_by_2(digitzer_measurement_param.setpoint_units)

            super().__init__(name=digitzer_measurement_param.name, names = names, shapes = shapes,
                            labels = labels, units = units,
                            setpoints =setpoints, setpoint_names=setpoint_names,
                            setpoint_labels=setpoint_labels, setpoint_units=setpoint_units,
                            docstring='automatically generated parameter of a digitizer')
            self.digitzer_measurement_param = digitzer_measurement_param
            self.dig = self.digitzer_measurement_param.dig
            self.T = T
            self.off = off

        def get_raw(self):
            data_orignal = self.digitzer_measurement_param.get()
            data_out = list()
            
            for n in range(int(len(self.shapes)/2)+1):
                
                my_data = np.asarray([data_orignal[int(n*2)].flatten(), data_orignal[int(n*2 + 1)].flatten()])
                OptiData = np.empty([data_orignal[int(n*2)].size])

                #very inefficient ...
                for i in range(0, data_orignal[int(n*2)].size):
                    OptiData[i] = np.matmul(my_data[:,i], self.T)[0][0]

                OptiData = OptiData.reshape(data_orignal[int(n*2)].shape)
                data_out.append(OptiData)

            return tuple(data_out)


def convert_to_scalar_data(digitzer_param, T, off):
    '''
    function that returns converts the IQ parameter to a Scalar parameter, in order to get the highest sensitive parameter.

    Args:
        digitzer_param (MultiParameter) : parameter where the digitizer is set to collect the necessary data.
        T (np.ndarray[ndim = 2, dtype = np.double]) : rotation matrix in the IQ plane (or tuples off, in case of 2 IQ channels at the same time)
        off (float) : offset in the IQ plane (or tuples off, in case of 2 IQ channels at the same time)
    
    Return:
        digitizer_data (MultiParameter) : parameter with data corrected to a scalar one.
    '''
    if not isinstance(T, tuple):
        T = (T, )

    if not isinstance(off, tuple):
        off = (off, )

    return _digitzer_IQ_to_scalar(digitzer_param, T, off)


class _digitzer_flatten(MultiParameter):
        def __init__(self, digitzer_measurement_param):
            '''
            Args:
                digitzer_measurement_param (MultiParameter) : parameter function with valid shape and setpoints (and getter)
                T (tuple <np.ndarray>) : set of rotation matrices
                offset (tuple < float> ) : set of offset for the different IQ channels
            '''
            # assume IQ data comes in pairs (e.g. channel 1 + channel 2 => pair 1 ;  channel 3 + channel 4 => pair 2)

            names = digitzer_measurement_param.names
            labels = digitzer_measurement_param.labels
            units = digitzer_measurement_param.units

            shapes = tuple()
            setpoints = tuple()
            setpoint_names = tuple()
            setpoint_labels = tuple()
            setpoint_units = tuple()

            for i in digitzer_measurement_param.shapes:
                shapes += ( (),)
                setpoints += ( (),)
                setpoint_names += ( (),)
                setpoint_labels += ( (),)
                setpoint_units += ( (),)

            super().__init__(name=digitzer_measurement_param.name, names = names, shapes = shapes,
                            labels = labels, units = units,
                            setpoints =setpoints, setpoint_names=setpoint_names,
                            setpoint_labels=setpoint_labels, setpoint_units=setpoint_units,
                            docstring='automatically generated parameter of a digitizer')
            self.digitzer_measurement_param = digitzer_measurement_param
            self.dig = self.digitzer_measurement_param.dig

        def get_raw(self):
            data_orignal = self.digitzer_measurement_param.get()
            
            data_out = [0]*len(self.shapes)
            for i in range(len(data_out)):
                data_out[i] = np.average(data_orignal[i])

            return tuple(data_out)

def flatten_data(digitzer_param,):
    '''
    flattens out input data.

    Args:
        digitzer_param (MultiParameter) : parameter where the digitizer is set to collect the necessary data.
        
    Return:
        digitizer_data (MultiParameter) : parameter that is fully averaged.
    '''
    return _digitzer_flatten(digitzer_param)


class _add_phase_amp_to_IQ_data(MultiParameter):
    def __init__(self, digitzer_measurement_param):
        names = digitzer_measurement_param.names + ("Amplitude (mV)", "phase (rad)")
        labels = digitzer_measurement_param.labels +  ("Amplitude", "phase")
        units = digitzer_measurement_param.units +  ("mV", "rad")

        shapes = digitzer_measurement_param.shapes + digitzer_measurement_param.shapes 
        setpoints = digitzer_measurement_param.setpoints + digitzer_measurement_param.setpoints
        setpoint_names = digitzer_measurement_param.setpoint_names + digitzer_measurement_param.setpoint_names
        setpoint_labels = digitzer_measurement_param.setpoint_labels + digitzer_measurement_param.setpoint_labels
        setpoint_units = digitzer_measurement_param.setpoint_units + digitzer_measurement_param.setpoint_units

        super().__init__(name=digitzer_measurement_param.name, names = names, shapes = shapes,
                            labels = labels, units = units,
                            setpoints =setpoints, setpoint_names=setpoint_names,
                            setpoint_labels=setpoint_labels, setpoint_units=setpoint_units,
                            docstring='automatically generated parameter of a digitizer')
        self.digitzer_measurement_param = digitzer_measurement_param

    def get_raw(self):
        data_orignal = self.digitzer_measurement_param.get()
        
        new_data = []
        # I data
        new_data.append(data_orignal[0])
        # I data
        new_data.append(data_orignal[1])
        # amp data
        new_data.append(np.abs(data_orignal[0] + data_orignal[1]*1j))
        # phase data
        new_data.append(np.angle(data_orignal[0] + data_orignal[1]*1j))

        return tuple(new_data)


def get_phase_amp_to_IQ_data(digitzer_param):
    return _add_phase_amp_to_IQ_data(digitzer_param)

if __name__ == '__main__':
    from V2_software.drivers.M3102A.M3102A import SD_DIG, MODES, DATA_MODE

    digitizer1 = SD_DIG("digitizer1", chassis = 0, slot = 6)

    # clear all ram (normally not needed, but just to sure)
    digitizer1.daq_flush(1)
    digitizer1.daq_flush(2)
    digitizer1.daq_flush(3)
    digitizer1.daq_flush(4)

    t_measure =1e3
    cycles = 1

    digitizer1.set_aquisition_mode(MODES.AVERAGE)
    # set up the digitzer, software triggering used, measure channel 1 and 2
    digitizer1.set_digitizer_software(t_measure, cycles, data_mode=DATA_MODE.AVERAGE_TIME_AND_CYCLES, channels = [1,2])
    
    # show some multiparameter properties
    # # measure the parameter
    meas = digitizer1.measure

    p = get_phase_amp_to_IQ_data(meas)
    print(p.shapes)
    print(p.setpoint_units)
    print(p.setpoints)
    print(p.get())