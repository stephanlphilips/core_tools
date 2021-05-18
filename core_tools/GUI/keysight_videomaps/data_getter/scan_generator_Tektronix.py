# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 16:50:02 2019

@author: V2
"""
from qcodes import MultiParameter
import numpy as np
import time
import logging

from pulse_lib.schedule.tektronix_schedule import TektronixSchedule

def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer, channels,
                           dig_samplerate, dig_vmax=2.0, iq_mode=None, acquisition_delay_ns=None,
                           enabled_markers=[], channel_map=None):
    """
    1D fast scan object for V2.

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

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    charge_st_1D  = pulse_lib.mk_segment()

    vp = swing/2

    if not acquisition_delay_ns:
        acquisition_delay_ns = 500
    step_eff = acquisition_delay_ns + t_step

    charge_st_1D.add_HVI_marker('dig_trigger_1', acquisition_delay_ns)

    logging.info(f'Construct 1D: {gate}')

    seg = getattr(charge_st_1D, gate)
    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages = np.zeros(n_pt)
    if biasT_corr == True:
        voltages[::2] = np.linspace(-vp,vp,n_pt)[:len(voltages[::2])]
        voltages[1::2] = np.linspace(-vp,vp,n_pt)[len(voltages[1::2]):][::-1]
    else:
        voltages = np.linspace(-vp,vp,n_pt)

    for  voltage in voltages:
        seg.add_block(0, step_eff, voltage)
        seg.reset_time()

    for marker in enabled_markers:
        marker_seg = getattr(charge_st_1D, marker)
        marker_seg.add_marker(0, n_pt*step_eff)

    sample_rate = 10e6 # lowest sample rate of Tektronix

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_1D])
    my_seq.set_hw_schedule(TektronixSchedule(pulse_lib))
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Upload')
    my_seq.upload()

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, acquisition_delay_ns,
                                    (n_pt, ), (gate, ), (tuple(voltages), ),
                                    biasT_corr, dig_samplerate, channels = channels, Vmax=dig_vmax, iq_mode=iq_mode,
                                    channel_map=channel_map)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer, channels, dig_samplerate, dig_vmax=2.0, iq_mode=None,
                           acquisition_delay_ns=None, enabled_markers=[], channel_map=None):
    """
    1D fast scan object for V2.

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
    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    logging.info(f'Construct 2D: {gate1} {gate2}')

    charge_st_2D  = pulse_lib.mk_segment()

    seg1 = getattr(charge_st_2D, gate1)

    # set up timing for the scan
    if not acquisition_delay_ns:
        acquisition_delay_ns = 500
    step_eff = acquisition_delay_ns + t_step

    charge_st_2D.add_HVI_marker('dig_trigger_1', acquisition_delay_ns)

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1 = np.linspace(-vp1,vp1,n_pt1)
    voltages2 = np.zeros(n_pt2)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)

    if biasT_corr == True:
        voltages2[::2] = np.linspace(-vp2,vp2,n_pt2)[:len(voltages2[::2])]
        voltages2[1::2] = np.linspace(-vp2,vp2,n_pt2)[-len(voltages2[1::2]):][::-1]
    else:
        voltages2 = np.linspace(-vp2,vp2,n_pt2)

    seg1.add_ramp_ss(0, step_eff*n_pt1, -vp1, vp1)
    seg1.repeat(n_pt1)

    seg2 = getattr(charge_st_2D, gate2)
    for voltage in voltages2:
        seg2.add_block(0, step_eff*n_pt1, voltage)
        seg2.reset_time()

    for marker in enabled_markers:
        marker_seg = getattr(charge_st_2D, marker)
        marker_seg.add_marker(0, n_pt1*n_pt2*step_eff)

    sample_rate = 10e6 # lowest sample rate of Tektronix

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_2D])
    my_seq.set_hw_schedule(TektronixSchedule(pulse_lib))
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Seq upload')
    my_seq.upload()

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, acquisition_delay_ns,
                                    (n_pt2, n_pt1), (gate2, gate1),
                                    (tuple(np.sort(voltages2)),tuple(voltages1)), biasT_corr, dig_samplerate,
                                     channels=channels, Vmax=dig_vmax, iq_mode=iq_mode, channel_map=channel_map)


class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, acquisition_delay_ns,
                 shape, names, setpoint, biasT_corr, sample_rate,
                 channels = [1,2,3,4], Vmax=2.0, iq_mode=None, channel_map=None):
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
            iq_mode (str or dict): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                    complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                    all channels. A dict can be used to speicify selection per channel, e.g. {1:'abs', 2:'angle'}
                    Note: channel_map is a more generic replacement for iq_mode.
            channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray])]):
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
                E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
                The default channel_map is:
                    {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
        """
        self.dig = digitizer
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.acquisition_delay_ns = acquisition_delay_ns
        self.n_points = np.prod(shape)
        self.channels = [ch-1 for ch in channels]
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.Vmax = Vmax
        self._init_channels(channels, channel_map, iq_mode)

        if sample_rate > 20e6:
            sample_rate = 20e6
        # digitizer sample rate is matched to hardware value by driver
        digitizer.sample_rate(sample_rate)
        self.sample_rate = digitizer.sample_rate()

        if len(self.channels) not in [1,2,4]:
            raise Exception('Number of enabled channels on M4i must be 1, 2 or 4.')
        digitizer.enable_channels(sum([2**ch for ch in self.channels]))
        for ch in self.channels:
            digitizer.set(f'range_channel_{ch}', Vmax*1000)

        self.seg_size = int((t_measure+acquisition_delay_ns) * self.n_points * self.sample_rate * 1e-9)

        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

        n_out_ch = len(self.channel_names)
        self.names = self.channel_names
        self.labels = tuple(f"digitizer output {name}" for name in self.names)
        self.units = tuple(["mV"]*n_out_ch)

        super().__init__(name=digitizer.name, names=self.names,
                        shapes=tuple([shape]*n_out_ch),
                        labels=self.labels,
                        units=self.units,
                        setpoints = tuple([setpoint]*n_out_ch), setpoint_names=tuple([names]*n_out_ch),
                        setpoint_labels=tuple([names]*n_out_ch), setpoint_units=(("mV",)*len(names),)*n_out_ch,
                        docstring='Scan parameter for digitizer')

    def _init_channels(self, channels, channel_map, iq_mode):

        self.channel_map = (
                channel_map if channel_map is not None
                else {f'ch{i+1}':(i, np.real) for i in channels})

        # backwards compatibility with older iq_mode parameter
        iq_mode2numpy = {'I': np.real, 'Q': np.imag, 'abs': np.abs,
                    'angle': np.angle, 'angle_deg': lambda x:np.angle(x, deg=True)}

        if iq_mode is not None:
            if channel_map is not None:
                logging.warning('iq_mode is ignored when channel_map is also specified')
            elif isinstance(iq_mode, str):
                self.channel_map = {f'ch{i+1}':(i, iq_mode2numpy[iq_mode]) for i in channels}
            else:
                for ch, mode in iq_mode.items():
                    self.channel_map[f'ch{ch}'] = (ch, iq_mode2numpy[mode])

        self.channel_names = tuple(self.channel_map.keys())

    def get_raw(self):
        start = time.perf_counter()
        # logging.info(f'Play')
        # play sequence
        self.my_seq.play(release=False)


        # get the data
        raw_data = self.dig.get_data()
        pretrigger = self.dig.pretrigger_memory_size()

        duration = (time.perf_counter() - start)*1000
        # logging.info(f'Acquired ({duration:5.1f} ms)')

        point_data = np.zeros((len(self.channels), self.n_points))

        samples_t_measure = self.t_measure * self.sample_rate * 1e-9
        samples_acq_delay = self.acquisition_delay_ns * self.sample_rate * 1e-9
        samples_per_point = samples_t_measure + samples_acq_delay

        start_sample = pretrigger
        for i in range(self.n_points):
            end_sample = pretrigger + int(samples_per_point*(i+1)- samples_acq_delay)
            point_data[:,i] = np.mean(raw_data[:,start_sample:end_sample], axis=1) * 1000
            start_sample = end_sample
        duration = (time.perf_counter() - start)*1000
        # logging.info(f'Averaged ({duration:5.1f} ms)')

        data = []
        for setting in self.channel_map.values():
            ch, func = setting
            ch_data = point_data[self.channels.index(ch-1)]
            data.append(func(ch_data))

        # make sure that data is put in the right order.
        data_out = [np.zeros(self.shape) for i in range(len(data))]

        for i in range(len(data)):
            ch_data = data[i].reshape(self.shape)
            if self.biasT_corr:
                data_out[i][:len(ch_data[::2])] = ch_data[::2]
                data_out[i][len(ch_data[1::2]):] = ch_data[1::2][::-1]
            else:
                data_out[i] = ch_data

        duration = (time.perf_counter() - start)*1000
        # logging.info(f'Done ({duration:5.1f} ms)')
        return tuple(data_out)

    def restart(self):
        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

    def stop(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.info('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None

    def __del__(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.warning(f'Cleanup in __del__(); Call stop()!')
            self.stop()

