# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 16:50:02 2019

@author: V2
"""
from qcodes import MultiParameter
from core_tools.drivers.M3102A import DATA_MODE
from core_tools.HVI2.hvi2_video_mode import Hvi2VideoMode
from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader
import matplotlib.pyplot as plt
import numpy as np
import time
import logging


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


    vp = swing/2

    # set up timing for the scan
    step_eff = t_step + Hvi2VideoMode.get_acquisition_gap(digitizer, acquisition_delay_ns)

    logging.info(f'Construct 1D: {gate}')

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages_sp = np.linspace(-vp,vp,n_pt)
    if biasT_corr:
        m = (n_pt+1)//2
        voltages = np.zeros(n_pt)
        voltages[::2] = voltages_sp[:m]
        voltages[1::2] = voltages_sp[m:][::-1]
    else:
        voltages = voltages_sp

    seg  = pulse_lib.mk_segment()
    g1 = seg[gate]
    for  voltage in voltages:
        g1.add_block(0, step_eff, voltage)
        g1.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)

    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step / 100
    # prescaler is limited to 255 when hvi_queueing_control is enabled. Limit other cases as well
    if awg_t_step > 5 * 255:
        awg_t_step = 5 * 255
    sample_rate = 1/(awg_t_step*1e-9)

    seg.add_HVI_variable("t_measure", int(t_step))
    seg.add_HVI_variable("digitizer", digitizer)
    seg.add_HVI_variable("number_of_points", int(n_pt))
    seg.add_HVI_variable("averaging", True)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    my_seq.set_hw_schedule(Hvi2ScheduleLoader(pulse_lib, 'VideoMode', digitizer,
                                              acquisition_delay_ns=acquisition_delay_ns))
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Upload')
    my_seq.upload([0])

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt, ), (gate, ), (tuple(voltages_sp), ),
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

    # set up timing for the scan
    step_eff = t_step + Hvi2VideoMode.get_acquisition_gap(digitizer, acquisition_delay_ns)

    if step_eff < 200:
        msg = f'Measurement time too short. Minimum is {t_step + 200-step_eff}'
        logging.error(msg)
        raise Exception(msg)

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1 = np.linspace(-vp1,vp1,n_pt1)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)

    if biasT_corr:
        m = (n_pt2+1)//2
        voltages2 = np.zeros(n_pt2)
        voltages2[::2] = voltages2_sp[:m]
        voltages2[1::2] = voltages2_sp[m:][::-1]
    else:
        voltages2 = voltages2_sp

    seg  = pulse_lib.mk_segment()
    g1 = seg[gate1]
    g2 = seg[gate2]


    for i in range(n_pt2):
        v2 = voltages2[i]

        g1.add_ramp_ss(0, step_eff*n_pt1, -vp1, vp1)
        g2.add_block(0, step_eff*n_pt1, v2)
        seg.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)

    # 20 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = step_eff / 20
    # prescaler is limited to 255 when hvi_queueing_control is enabled. Limit other cases as well
    if awg_t_step > 5 * 255:
        awg_t_step = 5 * 255

    sample_rate = 1/(awg_t_step*1e-9)

    seg.add_HVI_variable("t_measure", int(t_step))
    seg.add_HVI_variable("digitizer", digitizer)
    seg.add_HVI_variable("number_of_points", int(n_pt1*n_pt2))
    seg.add_HVI_variable("averaging", True)

    print(f'step_eff: {step_eff}')

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    logging.info(f'Add HVI')
    my_seq.set_hw_schedule(Hvi2ScheduleLoader(pulse_lib, 'VideoMode', digitizer,
                                              acquisition_delay_ns=acquisition_delay_ns))
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Seq upload')
    my_seq.upload([0])

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt2, n_pt1), (gate2, gate1),
                                    (tuple(voltages2_sp), (tuple(voltages1),)*n_pt2),
                                    biasT_corr, dig_samplerate,
                                     channels=channels, Vmax=dig_vmax, iq_mode=iq_mode, channel_map=channel_map)


class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, sample_rate,
                 data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2,3,4], Vmax=2.0, iq_mode=None, channel_map=None):
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
        self.n_rep = np.prod(shape)
        self.sample_rate =sample_rate
        self.data_mode = data_mode
        self.channels = channels
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.Vmax = Vmax
        self._init_channels(channels, channel_map, iq_mode)

        # clean up the digitizer before start
        for ch in range(1,5):
            digitizer.daq_stop(ch)
            digitizer.daq_flush(ch)

        self.sample_rate = 500e6

        # set digitizer for proper init
        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate,
                                   data_mode = self.data_mode, channels = self.channels, Vmax=self.Vmax)

        n_out_ch = len(self.channel_names)
        super().__init__(name=digitizer.name, names = self.channel_names,
                        shapes = tuple([shape]*n_out_ch),
                        labels = self.channel_names, units = tuple(['mV']*n_out_ch),
                        setpoints = tuple([setpoint]*n_out_ch), setpoint_names=tuple([names]*n_out_ch),
                        setpoint_labels=tuple([names]*n_out_ch), setpoint_units=(("mV",)*len(names),)*n_out_ch,
                        docstring='Scan parameter for digitizer')

    def _init_channels(self, channels, channel_map, iq_mode):

        self.channel_map = (
                channel_map if channel_map is not None
                else {f'ch{i}':(i, np.real) for i in channels})

        # backwards compatibility with older iq_mode parameter
        iq_mode2numpy = {'I': np.real, 'Q': np.imag, 'abs': np.abs,
                    'angle': np.angle, 'angle_deg': lambda x:np.angle(x, deg=True)}

        if iq_mode is not None:
            if channel_map is not None:
                logging.warning('iq_mode is ignored when channel_map is also specified')
            elif isinstance(iq_mode, str):
                self.channel_map = {f'ch{i}':(i, iq_mode2numpy[iq_mode]) for i in channels}
            else:
                for ch, mode in iq_mode.items():
                    self.channel_map[f'ch{ch}'] = (ch, iq_mode2numpy[mode])

        self.channel_names = tuple(self.channel_map.keys())


    def get_raw(self):

        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate,
                                   data_mode = self.data_mode, channels = self.channels, Vmax=self.Vmax)

        logging.info(f'Play')
        start = time.perf_counter()
        # play sequence
        self.my_seq.play([0], release = False)
        start2 = time.perf_counter()
        self.pulse_lib.uploader.wait_until_AWG_idle()
        logging.info(f'AWG idle after {(time.perf_counter()-start)*1000:3.1f} ms, ({(time.perf_counter()-start2)*1000:3.1f} ms)')


        # get the data
        raw = self.dig.measure()
        data = []
        for setting in self.channel_map.values():
            ch, func = setting
            ch_data = raw[self.channels.index(ch)]
            data.append(func(ch_data))

        # make sure that data is put in the right order.
        data_out = [np.zeros(self.shape) for i in range(len(data))]

        for i in range(len(data)):
            ch_data = data[i].reshape(self.shape)
            if self.biasT_corr:
                data_out[i][:len(ch_data[::2])] = ch_data[::2]
                data_out[i][len(ch_data[::2]):] = ch_data[1::2][::-1]

            else:
                data_out[i] = ch_data

        logging.info(f'Done')
        return tuple(data_out)

    def restart(self):
        pass

    def stop(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.info('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None


    def __del__(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.error(f'Cleanup in __del__(); Call stop()!')
            self.stop()

if __name__ == '__main__':
    import V2_software.drivers.M3102A as M3102A
    from V2_software.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
    from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib_debug
    from qcodes.instrument_drivers.Keysight.SD_common.SD_AWG import SD_AWG


    dig = M3102A.SD_DIG("digitizer1", chassis = 0, slot = 6)
    firmware_loader(dig, M3102A_AVG)

    awg1 = SD_AWG("AWG1", chassis = 0, slot = 2, channels=4, triggers=8)
    awg2 = SD_AWG("AWG2", chassis = 0, slot = 3, channels=4, triggers=8)
    awg3 = SD_AWG("AWG3", chassis = 0, slot = 4, channels=4, triggers=8)
    awg4 = SD_AWG("AWG4", chassis = 0, slot = 5, channels=4, triggers=8)

    pulse, vg, fs = return_pulse_lib(awg1, awg2, awg3, awg4)

    param = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, pulse, dig)
    data = param.get()
    print(data)

    param_1D = construct_1D_scan_fast("P2", 10,10,5000, True, pulse, dig)
    data_1D = param.get()
    print(data_1D)