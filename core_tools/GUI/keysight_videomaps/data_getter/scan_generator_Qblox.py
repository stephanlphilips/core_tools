# -*- coding: utf-8 -*-
import numpy as np
import time
import logging

from qcodes import MultiParameter

from .iq_modes import get_channel_map

logger = logging.getLogger(__name__)


def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib,
                           digitizer=None, channels=None,
                           iq_mode=None, acquisition_delay_ns=100,
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
        digitizer : Not used.
        channels : digitizer channels to read
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
    logger.info(f'Construct 1D: {gate}')

    if channel_map is None:
        channel_map = get_channel_map(pulse_lib, iq_mode, channels)

    if channels is None:
        acq_channels = set(v[0] for v in channel_map.values())
    else:
        acq_channels = channels

    vp = swing/2
    line_margin = int(line_margin)
    if biasT_corr and line_margin > 0:
        print('Line margin is ignored with biasT_corr on')
        line_margin = 0

    # set up timing for the scan
    acquisition_delay = max(100, acquisition_delay_ns)
    step_eff = t_step + acquisition_delay

    if t_step < 1000:
        msg = 'Measurement time too short. Minimum is 1000 ns'
        logger.error(msg)
        raise Exception(msg)

    n_ptx = n_pt + 2*line_margin
    vpx = vp * (n_ptx-1)/(n_pt-1)

    # set up sweep voltages (get the right order, to compensate for the biasT).
    voltages_sp = np.linspace(-vp,vp,n_pt)
    voltages_x = np.linspace(-vpx,vpx,n_ptx)
    if biasT_corr:
        m = (n_ptx+1)//2
        voltages = np.zeros(n_ptx)
        voltages[::2] = voltages_x[:m]
        voltages[1::2] = voltages_x[m:][::-1]
    else:
        voltages = voltages_x

    seg  = pulse_lib.mk_segment()
    g1 = seg[gate]
    pulse_channels = []
    for ch,v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    if not biasT_corr:
        # pre-pulse to condition bias-T
        t_prebias = n_ptx/2 * step_eff
        g1.add_ramp_ss(0, t_prebias, 0, vpx)
        for gp, v in pulse_channels:
            gp.add_block(0, t_prebias, -v)
        seg.reset_time()

    for i,voltage in enumerate(voltages):
        g1.add_block(0, step_eff, voltage)
        if 0 <= i-line_margin < n_pt:
            for acq_ch in acq_channels:
                seg[acq_ch].acquire(acquisition_delay, t_step)

        for gp,v in pulse_channels:
            gp.add_block(0, step_eff, v)
            # compensation for pulse gates
            if biasT_corr:
                gp.add_block(step_eff, 2*step_eff, -v)
        seg.reset_time()

    if not biasT_corr:
        # post-pulse to discharge bias-T
        g1.add_ramp_ss(0, t_prebias, -vpx, 0)
        for gp, v in pulse_channels:
            gp.add_block(0, t_prebias, -v)
        seg.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    my_seq.n_rep = 1
    # Note: set average repetitions to retrieve 1D array with channel data
    my_seq.set_acquisition(t_measure=t_step, channels=acq_channels, average_repetitions=True)

    my_seq.upload()

    return _digitzer_scan_parameter(my_seq, pulse_lib, t_step,
    								(n_pt, ), (gate, ), (tuple(voltages_sp), ),
                                    biasT_corr, channel_map)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer=None, channels=None, iq_mode=None,
                           acquisition_delay_ns=100, enabled_markers=[], channel_map=None,
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
        digitizer : Not used.
        iq_mode (str or dict): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels. A dict can be used to speicify selection per channel, e.g. {1:'abs', 2:'angle'}
                Note: channel_map is a more generic replacement for iq_mode.
        acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
        enabled_markers (List[str]): marker channels to enable during scan
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
    logger.info(f'Construct 2D: {gate1} {gate2}')

    if channel_map is None:
        channel_map = get_channel_map(pulse_lib, iq_mode, channels)

    if channels is None:
        acq_channels = set(v[0] for v in channel_map.values())
    else:
        acq_channels = channels

    # set up timing for the scan
    acquisition_delay = max(100, acquisition_delay_ns)
    step_eff = t_step + acquisition_delay

    if t_step < 1000:
        msg = 'Measurement time too short. Minimum is 1000 ns'
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

    seg  = pulse_lib.mk_segment()

    g1 = seg[gate1]
    g2 = seg[gate2]
    pulse_channels = []
    for ch,v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    if biasT_corr:
        # prebias: add half line with +vp2
        prebias_pts = (n_ptx)//2
        t_prebias = prebias_pts * step_eff
        # pulse on fast gate to pre-charge bias-T
        g1.add_block(0, t_prebias, vpx*0.35)
        # correct voltage to ensure average == 0.0 (No DC correction pulse needed at end)
        # Note that voltage on g2 ends center of sweep, i.e. (close to) 0.0 V
        total_duration = 2 * prebias_pts + n_ptx*n_pt2 * (2 if add_pulse_gate_correction else 1)
        g2.add_block(0, -1, -(prebias_pts * vp2)/total_duration)
        g2.add_block(0, t_prebias, vp2)
        for g,v in pulse_channels:
            g.add_block(0, t_prebias, -v)
        seg.reset_time()

    for v2 in voltages2:

        g1.add_ramp_ss(0, step_eff*n_ptx, -vpx, vpx)
        g2.add_block(0, step_eff*n_ptx, v2)
        for acq_ch in acq_channels:
            seg[acq_ch].acquire(step_eff*line_margin+acquisition_delay, n_repeat=n_pt1, interval=step_eff)
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
        for g, v in pulse_channels:
            g.add_block(0, t_prebias, +v)
        seg.reset_time()

    end_time = seg.total_time[0]
    for marker in enabled_markers:
        marker_ch = seg[marker]
        marker_ch.reset_time(0)
        marker_ch.add_marker(0, end_time)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    my_seq.n_rep = 1
    # Note: set average repetitions to retrieve 1D array with channel data
    my_seq.set_acquisition(t_measure=t_step, channels=acq_channels, average_repetitions=True)

    my_seq.upload()

    return _digitzer_scan_parameter(my_seq, pulse_lib, t_step,
                                    (n_pt2, n_pt1), (gate2, gate1),
                                    (tuple(voltages2_sp), (tuple(voltages1_sp),)*n_pt2),
                                    biasT_corr, channel_map)


class _digitzer_scan_parameter(MultiParameter):

    def __init__(self, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, channel_map):
        """
        args:
            my_seq (sequencer) : sequence of the 1D scan
            pulse_lib (pulselib): pulse library object
            t_measure (int) : time to measure per step
            shape (tuple<int>): expected output shape
            names (tuple<str>): name of the gate(s) that are measured.
            setpoint (tuple<np.ndarray>): array witht the setpoints of the input data
            biasT_corr (bool): bias T correction or not -- if enabled -- automatic reshaping of the data.
            TODO correct channel_map description.
            channel_map (Dict[str, Tuple(str, Callable[[np.ndarray], np.ndarray])]):
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
                E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
                The default channel_map is:
                    {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
        """
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.n_rep = np.prod(shape)
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.channel_map = channel_map
        self.channel_names = tuple(self.channel_map.keys())

        n_out_ch = len(self.channel_names)
        super().__init__(name='fastScan',
                         names = self.channel_names,
                         shapes = tuple([shape]*n_out_ch),
                         labels = self.channel_names,
                         units = tuple(['mV']*n_out_ch),
                         setpoints = tuple([setpoint]*n_out_ch),
                         setpoint_names=tuple([names]*n_out_ch),
                         setpoint_labels=tuple([names]*n_out_ch),
                         setpoint_units=(("mV",)*len(names),)*n_out_ch,
                         docstring='Scan parameter for digitizer')


    def get_raw(self):

        start = time.perf_counter()
        # play sequence
        self.my_seq.play(release=False)
        logger.debug(f'Play {(time.perf_counter()-start)*1000:3.1f} ms')
        raw_dict = self.my_seq.get_channel_data()

        # Reorder data for bias-T correction
        data = {}
        for name, raw in raw_dict.items():
            if self.biasT_corr:
                raw = raw.reshape(self.shape)
                ch_data = np.zeros(self.shape, dtype=raw.dtype)
                ch_data[:len(ch_data[::2])] = raw[::2]
                ch_data[len(ch_data[::2]):] = raw[1::2][::-1]
                data[name] = ch_data
            else:
                data[name] = raw.reshape(self.shape)

        # post-process data
        data_out = []
        for ch, func in self.channel_map.values():
            ch_data = data[ch]
            data_out.append(func(ch_data))

        return tuple(data_out)

    def restart(self):
        pass

    def stop(self):
        if self.my_seq is not None and self.pulse_lib is not None:
            logger.debug('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None

    def close(self):
        self.stop()

    def __del__(self):
        if self.my_seq is not None and self.pulse_lib is not None:
            logger.warning('Cleanup in __del__(); Call stop()!')
            self.stop()
