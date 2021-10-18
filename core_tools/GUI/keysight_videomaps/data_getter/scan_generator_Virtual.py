import time
import numpy as np
from qcodes import MultiParameter

class fake_digitizer(MultiParameter):
        """docstring for fake_digitizer"""
        def __init__(self, name):
            super().__init__(name=name, names = ("chan_1", "chan_2"), shapes = tuple([(20,20)]*2),
                        labels = ("chan 1", "chan 2"), units =("mV", "mV"),
                        docstring='1D scan parameter for digitizer')

        def get_raw(self):
            return 0


def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer, channels,
                           dig_samplerate, dig_vmax=2.0, iq_mode=None, acquisition_delay_ns=None,
                           enabled_markers=[], channel_map=None, pulse_gates={}, line_margin=0):
    """
    1D fast scan parameter constructor.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point.
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object
        iq_mode (str or dict): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels. A dict can be used to specify selection per channel, e.g. {1:'abs', 2:'angle'}.
                Note: channel_map is a more generic replacement for iq_mode.
        acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
        enable_markers (List[str]): marker channels to enable during scan
        channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray])]):
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
            E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
            The default channel_map is:
                {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
        pulse_gates (Dict[str, float]):
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        line_margin (int): number of points to add to sweep 1 to mask transition effects due to voltage step.
            The points are added to begin and end for symmetry (bias-T).

    Returns:
        Parameter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """
    vp = swing/2

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages = np.zeros(n_pt)
    if biasT_corr == True:
        voltages[::2] = np.linspace(-vp,vp,n_pt)[:len(voltages[::2])]
        voltages[1::2] = np.linspace(-vp,vp,n_pt)[len(voltages[1::2]):][::-1]
    else:
        voltages = np.linspace(-vp,vp,n_pt)

    return dummy_digitzer_scan_parameter(digitizer, None, pulse_lib, t_step, (n_pt, ), (gate, ),
                                         ( tuple(np.sort(voltages)), ), biasT_corr, 500e6)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer, channels, dig_samplerate, dig_vmax=2.0, iq_mode=None,
                           acquisition_delay_ns=None, enabled_markers=[], channel_map=None,
                           pulse_gates={}, line_margin=0):
    """
    2D fast scan parameter constructor.

    Args:
        gates1 (str) : gate that you want to sweep on x axis.
        swing1 (double) : swing to apply on the AWG gates.
        n_pt1 (int) : number of points to measure (current firmware limits to 1000)
        gate2 (str) : gate that you want to sweep on y axis.
        swing2 (double) : swing to apply on the AWG gates.
        n_pt2 (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point.
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object
        iq_mode (str or dict): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels. A dict can be used to speicify selection per channel, e.g. {1:'abs', 2:'angle'}
                Note: channel_map is a more generic replacement for iq_mode.
        acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
        enable_markers (List[str]): marker channels to enable during scan
        channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray])]):
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
            E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
            The default channel_map is:
                {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
        pulse_gates (Dict[str, float]):
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        line_margin (int): number of points to add to sweep 1 to mask transition effects due to voltage step.
            The points are added to begin and end for symmetry (bias-T).

    Returns:
        Parameter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1 = np.linspace(-vp1,vp1,n_pt1)
    voltages2 = np.zeros(n_pt2)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)
    if biasT_corr == True:
        voltages2[::2] = voltages2_sp[:len(voltages2[::2])]
        voltages2[1::2] = voltages2_sp[len(voltages2[1::2]):][::-1]
    else:
        voltages2 = voltages2_sp

    # Note: setpoints are in qcodes order
    return dummy_digitzer_scan_parameter(digitizer, None, pulse_lib, t_step,
                                         (n_pt2, n_pt1), (gate2, gate1),
                                         (tuple(voltages2_sp), (tuple(voltages1),)*n_pt2),
                                         biasT_corr, 500e6)


class dummy_digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, sample_rate,
                 data_mode = 0, channels = [1,2]):
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
        super().__init__(name=digitizer.name, names = digitizer.names, shapes = tuple([shape]*len(digitizer.names)),
                        labels = digitizer.labels, units = digitizer.units,
                        setpoints = tuple([setpoint]*len(digitizer.names)), setpoint_names=tuple([names]*len(digitizer.names)),
                        setpoint_labels=tuple([names]*len(digitizer.names)), setpoint_units=tuple([tuple(["mV"]*len(names))]*len(digitizer.names)),
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

        data = []
        data_out = []
        for i in self.channels:
            data.append(np.zeros(self.shape))
            data_out.append(np.zeros(self.shape))

        # get the data
        for i in range(len(data_out)):
            data[i].flat = np.linspace(0,50, len(data_out[i].flat)) + np.random.random([len(data_out[i].flat)]) + i*2

        # make sure that data is put in the right order.
        for i in range(len(data)):
            data[i] = data[i].reshape(self.shape)
            if self.biasT_corr:
                data_out[i][:len(data[i][::2])] = data[i][::2]
                data_out[i][len(data[i][::2]):] = data[i][1::2][::-1]
            else:
                data_out[i] = data[i]

        time.sleep(0.05)

        return tuple(data_out)

    def stop(self):
        pass

    def restart(self):
        pass

    def __del__(self):
        pass


if __name__ == '__main__':
    dig = fake_digitizer("test")

    param = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, None, dig)
    data = param.get()
    print(data)

    param_1D = construct_1D_scan_fast("P2", 10,10,5000, True, None, dig)
    data_1D = param_1D.get()
    print(data_1D)