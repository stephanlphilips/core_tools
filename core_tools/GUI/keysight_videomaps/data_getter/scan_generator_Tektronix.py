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
try:
    import pyspcm
except:
    pass

logger = logging.getLogger(__name__)

def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer, channels,
                           dig_samplerate=20e6, dig_vmax=None, iq_mode=None, acquisition_delay_ns=None,
                           enabled_markers=[], channel_map=None, pulse_gates={}, line_margin=0):
    """
    1D fast scan parameter constructor.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates. [mV]
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point. [ns]
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer : digitizer object
        channels : digitizer channels to read
        dig_samplerate : digitizer sample rate [Sa/s]
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
    if dig_vmax is not None:
        print(f'Parameter dig_vmax is deprecated.')
    logger.info(f'Construct 1D: {gate}')

    vp = swing/2
    line_margin = int(line_margin)
    if biasT_corr and line_margin > 0:
        print('Line margin is ignored with biasT_corr on')
        line_margin = 0

    add_line_delay = biasT_corr and len(pulse_gates) > 0

    if not acquisition_delay_ns:
        acquisition_delay_ns = 500
    step_eff = acquisition_delay_ns + t_step

    min_step_eff = 200 if not add_line_delay else 350
    if step_eff < min_step_eff:
        msg = f'Measurement time too short. Minimum is {t_step + min_step_eff-step_eff}'
        logger.error(msg)
        raise Exception(msg)

    n_ptx = n_pt + 2*line_margin
    vpx = vp * (n_ptx-1)/(n_pt-1)

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages_sp = np.linspace(-vp,vp,n_pt)
    voltages_x = np.linspace(-vpx,vpx,n_ptx)
    if biasT_corr:
        m = (n_ptx+1)//2
        voltages = np.zeros(n_ptx)
        voltages[::2] = voltages_x[:m]
        voltages[1::2] = voltages_x[m:][::-1]
    else:
        voltages = voltages_x

    start_delay = line_margin * step_eff
    line_delay_pts = 1
    n_lines = n_pt if add_line_delay else 1

    if not biasT_corr:
        prebias_pts = (n_ptx)//2
        t_prebias = prebias_pts * step_eff
        start_delay += t_prebias

    seg  = pulse_lib.mk_segment()
    g1 = seg[gate]
    pulse_channels = []
    for ch,v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    seg.add_HVI_variable('dig_trigger_1', acquisition_delay_ns + start_delay)
    if not biasT_corr:
        # pre-pulse to condition bias-T
        g1.add_ramp_ss(0, t_prebias, 0, vpx)
        for gp,v in pulse_channels:
            gp.add_block(0, t_prebias, -v)
        seg.reset_time()

    for voltage in voltages:
        g1.add_block(0, step_eff, voltage)

        for gp,v in pulse_channels:
            gp.add_block(0, step_eff, v)
            # compensation for pulse gates
            if biasT_corr:
                gp.add_block(step_eff, 2*step_eff, -v)
        seg.reset_time()

    if not biasT_corr:
        # post-pulse to discharge bias-T
        g1.add_ramp_ss(0, t_prebias, -vpx, 0)
        for gp,v in pulse_channels:
            gp.add_block(0, t_prebias, -v)
        seg.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)

    sample_rate = 10e6 # lowest sample rate of Tektronix

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    my_seq.set_hw_schedule(TektronixSchedule(pulse_lib))
    my_seq.configure_digitizer = False
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logger.info(f'Upload')
    my_seq.upload()

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, acquisition_delay_ns, n_lines, line_delay_pts,
                                    (n_pt, ), (gate, ), (tuple(voltages_sp), ),
                                    biasT_corr, dig_samplerate, channels = channels, Vmax=dig_vmax, iq_mode=iq_mode,
                                    channel_map=channel_map)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer, channels, dig_samplerate=20e6, dig_vmax=None, iq_mode=None,
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
    if dig_vmax is not None:
        print(f'Parameter dig_vmax is deprecated.')
    logger.info(f'Construct 2D: {gate1} {gate2}')

    # set up timing for the scan
    if not acquisition_delay_ns:
        acquisition_delay_ns = 500
    step_eff = acquisition_delay_ns + t_step

    if step_eff < 200:
        msg = f'Measurement time too short. Minimum is {t_step + 200-step_eff}'
        logger.error(msg)
        raise Exception(msg)

    line_margin = int(line_margin)
    add_pulse_gate_correction = biasT_corr and len(pulse_gates) > 0

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1_sp = np.linspace(-vp1,vp1,n_pt1)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)

    n_ptx = n_pt1 + 2*line_margin
    vpx = vp1 * (n_ptx-1)/(n_pt1-1)

    if biasT_corr:
        m = (n_pt2+1)//2
        voltages2 = np.zeros(n_pt2)
        voltages2[::2] = voltages2_sp[:m]
        voltages2[1::2] = voltages2_sp[m:][::-1]
    else:
        voltages2 = voltages2_sp

    start_delay = line_margin * step_eff
    if biasT_corr:
        # prebias: add half line with +vp2
        prebias_pts = (n_ptx)//2
        t_prebias = prebias_pts * step_eff
        start_delay += t_prebias

    line_delay_pts = 2 * line_margin
    if add_pulse_gate_correction:
        line_delay_pts += n_ptx

    seg  = pulse_lib.mk_segment()

    seg.add_HVI_marker('dig_trigger_1', acquisition_delay_ns + start_delay)

    g1 = seg[gate1]
    g2 = seg[gate2]
    pulse_channels = []
    for ch,v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    if biasT_corr:
        # pulse on fast gate to pre-charge bias-T
        g1.add_block(0, t_prebias, vpx*0.35)
        # correct voltage to ensure average == 0.0 (No DC correction pulse needed at end)
        # Note that voltage on g2 ends center of sweep, i.e. (close to) 0.0 V
        total_duration = prebias_pts + n_ptx*n_pt2 * (2 if add_pulse_gate_correction else 1)
        g2.add_block(0, -1, -(prebias_pts * vp2)/total_duration)
        g2.add_block(0, t_prebias, vp2)
        for g,v in pulse_channels:
            g.add_block(0, t_prebias, -v)
        seg.reset_time()

    for v2 in voltages2:

        g1.add_ramp_ss(0, step_eff*n_ptx, -vpx, vpx)
        g2.add_block(0, step_eff*n_ptx, v2)
        for g,v in pulse_channels:
            g.add_block(0, step_eff*n_ptx, v)
        seg.reset_time()

        if add_pulse_gate_correction:
            # add compensation pulses of pulse_channels
            # sweep g1 onces more; best effect on bias-T
            # keep g2 on 0
            g1.add_ramp_ss(0, step_eff*n_ptx, -vpx, vpx)
            for g,v in pulse_channels:
                g.add_block(0, step_eff*n_ptx, -v)
            seg.reset_time()

    if biasT_corr:
        # pulses to discharge bias-T
        # Note: g2 is already 0.0 V
        g1.add_block(0, t_prebias, -vpx*0.35)
        for g,v in pulse_channels:
            g.add_block(0, t_prebias, +v)
        seg.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)


    sample_rate = 10e6 # lowest sample rate of Tektronix

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    my_seq.set_hw_schedule(TektronixSchedule(pulse_lib))
    my_seq.configure_digitizer = False
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logger.info(f'Seq upload')
    my_seq.upload()

    n_lines = n_pt2
    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, acquisition_delay_ns, n_lines, line_delay_pts,
                                    (n_pt2, n_pt1), (gate2, gate1),
                                    (tuple(voltages2_sp), (tuple(voltages1_sp),)*n_pt2),
                                    biasT_corr, dig_samplerate,
                                    channels=channels, iq_mode=iq_mode, channel_map=channel_map)


class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, acquisition_delay_ns,
                 n_lines, line_delay_pts,
                 shape, names, setpoint, biasT_corr, sample_rate,
                 channels = [1,2,3,4], iq_mode=None, channel_map=None):
        """
        args:
            digitizer (M4i) : Spectrum M4i digitizer driver:
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
        self.n_ch = len(channels)
        self.n_lines = n_lines
        self.line_delay_pts = line_delay_pts
        self._init_channels(channels, channel_map, iq_mode)

        if sample_rate > 60e6:
            sample_rate = 60e6
        # digitizer sample rate is matched to hardware value by driver
        digitizer.sample_rate(sample_rate)
        self.sample_rate = digitizer.sample_rate()

        if self.n_ch not in [1,2,4]:
            raise Exception('Number of enabled channels on M4i must be 1, 2 or 4.')
        digitizer.enable_channels(sum([2**ch for ch in self.channels]))

        # is demodulation configured in pulse-lib?
        self._demodulate = []
        for dig_ch in self.pulse_lib.digitizer_channels.values():
            if dig_ch.frequency is not None:
                self._demodulate.append(
                        (dig_ch.channel_numbers, dig_ch.frequency, dig_ch.phase, dig_ch.iq_out))

        # note: force float calculation to avoid intermediate int overflow.
        self.seg_size = int(float(t_measure+acquisition_delay_ns)
                            * (self.n_points + self.n_lines * self.line_delay_pts)
                            * self.sample_rate * 1e-9)

        self.dig.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)
        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

        n_out_ch = len(self.channel_names)
        self.names = self.channel_names
        self.labels = tuple(f"digitizer output {name}" for name in self.names)
        self.units = tuple(["mV"]*n_out_ch)

        super().__init__(name=digitizer.name, names=self.names,
                        shapes=tuple([shape]*n_out_ch),
                        labels=self.labels,
                        units=self.units,
                        setpoints = tuple([setpoint]*n_out_ch),
                        setpoint_names=tuple([names]*n_out_ch),
                        setpoint_labels=tuple([names]*n_out_ch),
                        setpoint_units=(("mV",)*len(names),)*n_out_ch,
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
                logger.warning('iq_mode is ignored when channel_map is also specified')
            elif isinstance(iq_mode, str):
                self.channel_map = {f'ch{i+1}':(i, iq_mode2numpy[iq_mode]) for i in channels}
            else:
                for ch, mode in iq_mode.items():
                    self.channel_map[f'ch{ch}'] = (ch, iq_mode2numpy[mode])

        self.channel_names = tuple(self.channel_map.keys())

    def get_raw(self):
        start = time.perf_counter()
        logger.info('Play')
        # play sequence
        self.my_seq.play(release=False)

        # get the data
        raw_data = self.dig.get_data()

        duration = (time.perf_counter() - start)*1000
        logger.info(f'Acquired ({duration:5.1f} ms)')

        pretrigger = self.dig.pretrigger_memory_size()
        raw_data = raw_data[:,pretrigger:]

        for channels,frequency,phase,iq_out in self._demodulate:
            t = np.arange(self.seg_size) / self.sample_rate
            channels = [self.channels.index(ch) for ch in channels]
            iq = np.exp(-1j*(2*np.pi*t*frequency+phase))
            if len(channels) == 1:
                demodulated = raw_data[channels[0]] * iq
                raw_data[channels[0]] = demodulated.real
            else:
                demodulated = (raw_data[channels[0]]+1j*raw_data[channels[1]])*iq
                if iq_out:
                    raw_data[channels[0]] = demodulated
                    raw_data[channels[1]] = demodulated
                else:
                    raw_data[channels[0]] = demodulated.real
                    raw_data[channels[1]] = demodulated.imag

        point_data = np.zeros((len(self.channels), self.n_points))

        samples_t_measure = self.t_measure * self.sample_rate * 1e-9
        samples_acq_delay = self.acquisition_delay_ns * self.sample_rate * 1e-9
        samples_per_point = samples_t_measure + samples_acq_delay
        points_per_line = self.n_points // self.n_lines

        for iline in range(self.n_lines):
            for ipt in range(points_per_line):
                ix = ipt + iline * (self.line_delay_pts + points_per_line)
                start_sample = int(samples_per_point*ix)
                end_sample = int(samples_per_point*(ix+1) - samples_acq_delay)

                sample_data = raw_data[:,start_sample:end_sample]
                idata = ipt + iline * points_per_line
                point_data[:,idata] = np.mean(sample_data, axis=1) * 1000
        duration = (time.perf_counter() - start)*1000
        logger.info(f'Averaged ({duration:5.1f} ms)')


        # Reorder data for bias-T correction
        data = [np.zeros(self.shape, dtype=d.dtype) for d in point_data]

        for i in range(len(data)):
            ch_data = point_data[i].reshape(self.shape)
            if self.biasT_corr:
                data[i][:len(ch_data[::2])] = ch_data[::2]
                data[i][len(ch_data[::2]):] = ch_data[1::2][::-1]

            else:
                data[i] = ch_data

        # post-process data
        data_out = []
        for ch,func in self.channel_map.values():
            ch_data = data[self.channels.index(ch-1)]
            data_out.append(func(ch_data))

        duration = (time.perf_counter() - start)*1000
        logger.info(f'Done ({duration:5.1f} ms)')
        return tuple(data_out)

    def restart(self):
        self.dig.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)
        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

    def stop(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logger.info('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None

    def close(self):
        self.stop()

    def __del__(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logger.warning(f'Cleanup in __del__(); Call stop()!')
            self.stop()

