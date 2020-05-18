from qcodes import MultiParameter
from V2_software.HVI_files.charge_stability_diagram.HVI_charge_stability_diagram import load_HVI, set_and_compile_HVI, excute_HVI, HVI_ID
from V2_software.drivers.M3102A.M3102A import DATA_MODE, MODES
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from V2_software.Modulated_scans.DEMOD_tests import generate_dig_data_set

class DEMOD_methods:
    BOX_CAR = 0
    HANN = 1
    COSINE = 2

def demodulate_data(data, sampling_rate, frequencies):
    '''
    function that will demodulate the measured data and returns the phase and amplitude of the measured signal.
        data: numpy 1D array of input data (IQ data imaginary).
        sampling_rate: rate at which the given data is samples
        frequencies: frequencies around which to expect a modulation
    '''

    # init data sets for the demodulated data.
    amplitudes = [0]*len(frequencies)
    phases = [0]*len(frequencies)

    window =  signal.hann(data.size)
    times = np.linspace(0,data.size/sampling_rate, data.size)

    # perform the demodulation
    for i in range(len(frequencies)):
        freq_carrier = frequencies[i]

        sin_carrier = np.sin(freq_carrier*2*np.pi*times)
        cos_carrier = np.cos(freq_carrier*2*np.pi*times)

        demod_signal = np.average(sin_carrier*data*window) +1j*np.average(cos_carrier*data*window)
        
        # phases
        phases[i] = np.angle(demod_signal)
        # amp
        amplitudes[i] = np.abs(demod_signal)*4

    # return data
    return amplitudes, phases

def process_data_single_set(data, freq, sample_rate):
    '''
    demulate all the IQ data in the full data object
    Args:
        data (np.ndarray) : data set of a single channal
        freq (list<double>) : list of the frequencies that need to be demodulated
        sample_rate (double) : sample rate of the digitizer

    returns:
        output_data (list<np.ndarray>) : arrays of the demodulated data (sorting as, data_set_1_f1_amp, data_set_1_f1_phase, data_set_1_f2_amp, ...)
    '''
    output_data = np.zeros([len(freq)*2, data.shape[0]]) #AMP and phase returned per freq

    for cycle_number in range(data.shape[0]):
        amps, phases = demodulate_data(data[cycle_number], sample_rate, freq)

        for i in range(len(freq)):
            output_data[i*2][cycle_number] = amps[i]
            output_data[i*2 + 1][cycle_number] = phases[i]

    return list(output_data)

def process_data_IQ(data, freq, sample_rate):
    '''
    demulate all the IQ data in the full data object
    Args:
        data (tuple<np.ndarray>) : data set of multiple channals
        freq (list<double>) : list of the frequencies that need to be demodulated
        sample_rate (double) : sample rate of the digitizer

    returns:
        output_data (tuple<np.ndarray>) : arrays of the demodulated data (sorting as, data_set_1_f1_amp, data_set_1_f1_phase, data_set_1_f2_amp, ...)
    '''
    output_data = list()
    
    for data_set_single in data:
        output_data += process_data_single_set(data_set_single,freq, sample_rate)

    return tuple(output_data)

def construct_1D_scan_MOD(gate, swing, modulation_amplitude ,n_pt, MOD_gates, freq_start, freq_step , biasT_corr, pulse_lib, digitizer, n_periods = 10):
    """
    1D modulated scan object for V2.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        modulation_amplitude (double) : amplitude of the swing
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        MOD_gates (list<str>) : list with gates to be modulated
        freq_start (double) : freq to start for the modulation (e.g. 100kHz)
        freq_step (double) : step to be used (e.g. 100kHz  generates--> 100kHz, 300kHz ,300kHz, 400kHz, ...)
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """
    
    charge_st_1D  = pulse_lib.mk_segment()

    
    vp = swing/2

    # 10 times longer than the bandwith
    t_measure = 1/freq_step*n_periods*1e9

    getattr(charge_st_1D, gate).add_HVI_variable("t_measure", int(t_measure))
    getattr(charge_st_1D, gate).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_1D, gate).add_HVI_variable("number_of_points", int(n_pt))
    getattr(charge_st_1D, gate).add_HVI_variable("averaging", False)

    # set up timing for the scan
    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    step_eff = 2000 + 120 + t_measure

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages = np.zeros(n_pt)
    if biasT_corr == True:
        voltages[::2] = np.linspace(-vp,vp,n_pt)[:len(voltages[::2])]
        voltages[1::2] = np.linspace(-vp,vp,n_pt)[len(voltages[1::2]):][::-1]
    else:
        voltages = np.linspace(-vp,vp,n_pt)

    for  voltage in voltages:
        getattr(charge_st_1D, gate).add_block(0, step_eff, voltage)
        getattr(charge_st_1D, gate).add_sin(0, t_measure, modulation_amplitude, freq_start)
        freq = freq_start + freq_step
        
        for MOD_gate in MOD_gates:
            getattr(charge_st_1D, MOD_gate).add_sin(0, t_measure, modulation_amplitude, freq)
            freq += freq_step
        
        charge_st_1D.reset_time()
    

    # 100 time points per step to make sure that everything looks good (this is more than needed).
    sample_rate = (freq_start + freq_step*len(MOD_gates))*10
    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_1D])
    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 10000
    my_seq.sample_rate = sample_rate

    my_seq.upload([0])
    # my_seq.play([0], release = True)
    # pulse_lib.uploader.wait_until_AWG_idle()
    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_measure, (n_pt, ), (gate, ), (np.sort(voltages), ), biasT_corr, sample_rate, data_mode=DATA_MODE.FULL)

class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, sample_rate, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2]):
        """
        args:
            digitizer (SD_DIG) : digizer driver:
            my_seq (sequencer) : sequence of the 1D scan
            pulse_lib (pulselib): pulse library object
            t_measure (int) : time to measure per step
            shape (tuple<int>): expected output shape
            names (tuple<str>): name of the gate(s) that are measured.
            setpoint (tuple<np.ndarray>): array witht the setpoints of the input data
            biasT_corr (bool): bias T correction or not -- if enabled -- automatic reshaping of the data. 
            sample_rate (float): sample rate of the digitizer card that should be used.
            data mode (int): data mode of the digizer
            channels (list<int>): channels to measure
        """
        super().__init__(name=digitizer.name, names = digitizer.measure.names, shapes = tuple([shape]*len(digitizer.measure.names)),
                        labels = digitizer.measure.labels, units = digitizer.measure.units,
                        setpoints = tuple([setpoint]*len(digitizer.measure.names)), setpoint_names=tuple([names]*len(digitizer.measure.names)),
                        setpoint_labels=tuple([names]*len(digitizer.measure.names)), setpoint_units=tuple([tuple(["mV"]*len(names))]*len(digitizer.measure.names)),
                        docstring='1D scan parameter for digitizer')
        self.dig = digitizer
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.n_rep = np.prod(shape)
        self.sample_rate =sample_rate
        self.data_mode = data_mode
        self.channels = channels
        self.biasT_corr = biasT_corr
        self.shape = shape

    def get_raw(self):
        # clean up the digitizer
        self.dig.daq_flush(1)
        self.dig.daq_flush(2)
        self.dig.daq_flush(3)
        self.dig.daq_flush(4)
        # set digitizer
        self.dig.set_aquisition_mode(MODES.NORMAL)
        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate, data_mode = self.data_mode, channels = self.channels)

        # play sequence
        self.my_seq.play([0], release = False)
        self.pulse_lib.uploader.wait_until_AWG_idle()

        data_out = []
        for i in self.channels:
            data_out.append(np.zeros(self.shape))

        # get the data
        data = list(self.dig.measure())
                
        return tuple(data)

    def __del__(self):
        # remove pulse sequence from the AWG's memory.
        self.my_seq.play([0], release = True)
        # no blocking on HVI, so can just overwrite this.
        self.pulse_lib.uploader.release_memory()

def construct_1D_scan_MOD_DEMO(gate, swing, modulation_amplitude ,n_pt, MOD_gates, freq_start, freq_step , biasT_corr ,digitizer, DEMOD_method = DEMOD_methods.COSINE):
    """
    1D modulated scan object for V2.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        modulation_amplitude (double) : amplitude of the swing
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        MOD_gates (list<str>) : list with gates to be modulated
        freq_start (double) : freq to start for the modulation (e.g. 100kHz)
        freq_step (double) : step to be used (e.g. 100kHz  generates--> 100kHz, 300kHz ,300kHz, 400kHz, ...)
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    BW = freq_step
    freq = 100e3

    t_measure = 1/BW*10
    voltages = np.linspace(0, 50, n_pt)
    modulated_gates = [gate] + MOD_gates
    sample_rate = 20e6
    biasT_corr = False
    
    frequencies = [freq_start]
    for i in range(len(MOD_gates)):
        frequencies.append((i+1)*freq_step + freq_start)

    return _digitzer_scan_parameter_demo(digitizer, None, None, t_measure, (n_pt, ), tuple(modulated_gates), frequencies, DEMOD_method, (np.sort(voltages), ), biasT_corr, sample_rate, data_mode=DATA_MODE.FULL)


class _digitzer_scan_parameter_demo(MultiParameter):
    """
    demo paramter used for development of demodulation utility 
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, mod_gates, frequencies, demod_method, setpoint, biasT_corr, sample_rate, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2]):
        """
        args:
            digitizer (SD_DIG) : digizer driver:
            my_seq (sequencer) : sequence of the 1D scan
            pulse_lib (pulselib): pulse library object
            t_measure (int) : time to measure per step
            shape (tuple<int>): expected output shape
            mod_gates (tuple<str>): name of the gate(s) that are measured.
            setpoint (tuple<np.ndarray>): array witht the setpoints of the input data
            biasT_corr (bool): bias T correction or not -- if enabled -- automatic reshaping of the data. 
            sample_rate (float): sample rate of the digitizer card that should be used.
            data mode (int): data mode of the digizer
            channels (list<int>): channels to measure
        """
        # bit of preformatting 
        shapes = tuple([shape]*len(frequencies)*2*len(channels))
        names = []
        labels = []
        units =[]

        for chan in channels:
            for gate in mod_gates:
                names += ["DEMOD {} amp ch{}".format(gate, chan)]
                labels += ["DEMOD {} amp ch{}".format(gate, chan)]
                units += ["mV"]
                names += ["DEMOD {} phase ch{}".format(gate, chan)]
                labels += ["DEMOD {} phase ch{}".format(gate, chan)]
                units += ["rad"]

        super().__init__(name=digitizer.name, names = tuple(names), shapes = shapes,
                        labels = tuple(labels), units = tuple(units),
                        setpoints = tuple([(tuple(setpoint[0]),)]*len(shapes)), setpoint_names=tuple([(mod_gates[0],)]*len(shapes)),
                        setpoint_labels=tuple([(mod_gates[0],)]*len(shapes)), setpoint_units=tuple([("mV",)]*len(shapes)),
                        docstring='1D scan parameter for digitizer')
        self.dig = digitizer
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.n_rep = np.prod(shape)
        self.sample_rate =sample_rate
        self.data_mode = data_mode
        self.channels = channels
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.frequencies = frequencies
        self.npt = len(setpoint[0])
        self.sample_rate = sample_rate

    def get_raw(self):
        data = generate_dig_data_set(self.npt, self.sample_rate, self.t_measure, self.frequencies)
        
        return process_data_IQ(data, self.frequencies, 250e6)



if __name__ == '__main__':
    # import V2_software.drivers.M3102A.M3102A as M3102A
    # from V2_software.drivers.M3102A.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
    # from V2_software.pulse_lib_config.Init_pulse_lib_debug import return_pulse_lib
    # from qcodes.instrument_drivers.Keysight.SD_common.SD_AWG import SD_AWG
    from V2_software.LivePlotting.data_getter.scan_generator_Virtual import fake_digitizer
    from qdev_wrappers.file_setup import (
        CURRENT_EXPERIMENT, my_init, close_station, init_python_logger)
    from qdev_wrappers.sweep_functions import do0d, do1d, do2d

    # Set up folders, settings and logging for the experiment
    my_init("Wiscosin batch 3 sample 2", None,
            pdf_folder=False, png_folder=False, analysis_folder=True,
            waveforms_folder=False, calib_config=False,
            annotate_image=False, mainfolder="D:/data/", display_pdf=False,
            display_individual_pdf=False, qubit_count=2)
    from qcodes import new_experiment, new_data_set


    dig = fake_digitizer("digitizer1")
    param = construct_1D_scan_MOD_DEMO(gate = "G4_1", swing = 100, modulation_amplitude = 1, n_pt = 20, MOD_gates = ["G4_2", "G4_3"], freq_start=100e3, freq_step=50e3 , biasT_corr= False, digitizer = dig)
    # data = param.get()
    print(param.setpoints)
    do0d(param)