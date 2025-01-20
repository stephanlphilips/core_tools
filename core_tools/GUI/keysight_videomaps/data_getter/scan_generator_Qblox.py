# -*- coding: utf-8 -*-
import numpy as np
import time
import logging


from .scan_generator_base import FastScanParameterBase, FastScanGeneratorBase, ScanConfigBase


logger = logging.getLogger(__name__)


class QbloxFastScanParameter(FastScanParameterBase):

    def __init__(
            self,
            scan_config: ScanConfigBase,
            pulse_lib,
            pulse_sequence,
    ):
        """
        args:
            pulse_lib (pulselib): pulse library object
            pulse_sequence (sequencer) : sequence of the 1D scan
        """
        self.pulse_lib = pulse_lib
        self.my_seq = pulse_sequence
        self._recompile_requested = False

        super().__init__(scan_config)

    def recompile(self):
        self._recompile_requested = True

    def get_channel_data(self) -> dict[str, np.ndarray]:
        """Starts scan and retrieves data.

        Returns:
            dictionary with per channel real or complex data in 1D ndarray.
        """
        if self._recompile_requested:
            self._recompile_requested = False
            start = time.perf_counter()
            self.my_seq.recompile()
            self.my_seq.upload()
            duration = time.perf_counter() - start
            logger.info(f"Recompiled in {duration*1000:.1f} ms")

        start = time.perf_counter()
        # play sequence
        self.my_seq.play(release=False)
        logger.debug(f'Play {(time.perf_counter()-start)*1000:3.1f} ms')
        raw = self.my_seq.get_channel_data()

        return raw

    def close(self):
        if self.my_seq is not None and self.pulse_lib is not None:
            logger.debug('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None

    def __del__(self):
        if self.my_seq is not None and self.pulse_lib is not None:
            logger.debug('Cleanup in __del__(); Please, call m_param.close() on measurement parameter!')
            self.close()


class FastScanGenerator(FastScanGeneratorBase):

    def create_1D_scan(
            self,
            gate: str, swing: float, n_pt: int, t_measure: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = False,
    ) -> FastScanParameterBase:
        """Creates 1D fast scan parameter.

        Args:
            gate: gates to sweep.
            swing: swing to apply on the AWG gate. [mV]
            n_pt: number of points to measure
            t_measure: time in ns to measure per point. [ns]
            pulse_gates:
                Gates to pulse during scan with pulse voltage in mV.
                E.g. {'vP1': 10.0, 'vB2': -29.1}
            biasT_corr: correct for biasT by taking data in different order.

        Returns:
            Parameter that can be used as input in a scan/measurement functions.
        """
        logger.info(f'Create 1D Scan: {gate}')

        config = self.get_config1D(gate, swing, n_pt, t_measure, pulse_gates, biasT_corr)

        # set up timing for the scan
        config.acquisition_delay_ns = max(100, config.acquisition_delay_ns)
        step_eff = t_measure + config.acquisition_delay_ns

        if t_measure < 1000:
            msg = 'Measurement time too short. Minimum is 1000 ns'
            logger.error(msg)
            raise Exception(msg)

        acq_channels = set(v[0] for v in config.channel_map.values())

        seg = self.pulse_lib.mk_segment()
        g1 = seg[gate]
        pulse_channels = []
        for ch, v in pulse_gates.items():
            pulse_channels.append((seg[ch], v))

        if not config.biasT_corr:
            # pre-pulse to condition bias-T
            t_prebias = config.n_ptx/2 * step_eff
            g1.add_ramp_ss(0, t_prebias, 0, config.vpx)
            for gp, v in pulse_channels:
                gp.add_block(0, t_prebias, -v)
            seg.reset_time()

        for i, voltage in enumerate(config.voltages):
            g1.add_block(0, step_eff, voltage)
            if 0 <= i-config.line_margin < n_pt:
                for acq_ch in acq_channels:
                    seg[acq_ch].acquire(config.acquisition_delay_ns, t_measure)

            for gp, v in pulse_channels:
                gp.add_block(0, step_eff, v)
                # compensation for pulse gates
                if biasT_corr:
                    gp.add_block(step_eff, 2*step_eff, -v)
            seg.reset_time()

        if not config.biasT_corr:
            # post-pulse to discharge bias-T
            g1.add_ramp_ss(0, t_prebias, -config.vpx, 0)
            for gp, v in pulse_channels:
                gp.add_block(0, t_prebias, -v)
            seg.reset_time()

        end_time = seg.total_time[0]
        for marker in config.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        # generate the sequence and upload it.
        my_seq = self.pulse_lib.mk_sequence([seg])
        my_seq.n_rep = 1
        # Note: set average repetitions to retrieve 1D array with channel data
        my_seq.set_acquisition(t_measure=t_measure, channels=acq_channels, average_repetitions=True)

        my_seq.upload()

        return QbloxFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq,
        )

    def create_2D_scan(self,
                       gate1: str, swing1: float, n_pt1: int,
                       gate2: str, swing2: float, n_pt2: int,
                       t_measure: float,
                       pulse_gates: dict[str, float] = {},
                       biasT_corr: bool = True,
                       ) -> FastScanParameterBase:
        """Creates 2D fast scan parameter.

        Args:
            gates1: gate that you want to sweep on x axis.
            swing1: swing to apply on the AWG gates.
            n_pt1: number of points to measure (current firmware limits to 1000)
            gate2: gate that you want to sweep on y axis.
            swing2: swing to apply on the AWG gates.
            n_pt2: number of points to measure (current firmware limits to 1000)
            t_measure: time in ns to measure per point.
            biasT_corr: correct for biasT by taking data in different order.
            pulse_gates:
                Gates to pulse during scan with pulse voltage in mV.
                E.g. {'vP1': 10.0, 'vB2': -29.1}

        Returns:
            Parameter that can be used as input in a scan/measurement functions.
        """
        logger.info(f'Construct 2D: {gate1} {gate2}')

        config = self.get_config2D(
            gate1, swing1, n_pt1,
            gate2, swing2, n_pt2,
            t_measure, pulse_gates, biasT_corr)

        acq_channels = set(v[0] for v in config.channel_map.values())

        # set up timing for the scan
        config.acquisition_delay_ns = max(100, config.acquisition_delay_ns)
        step_eff = t_measure + config.acquisition_delay_ns

        if t_measure < 1000:
            msg = 'Measurement time too short. Minimum is 1000 ns'
            logger.error(msg)
            raise Exception(msg)

        add_pulse_gate_correction = biasT_corr and len(pulse_gates) > 0

        seg = self.pulse_lib.mk_segment()

        g1 = seg[gate1]
        g2 = seg[gate2]
        pulse_channels = []
        for ch, v in pulse_gates.items():
            pulse_channels.append((seg[ch], v))

        if config.biasT_corr:
            # prebias: add half line with +vp2
            prebias_pts = (config.n_ptx)//2
            t_prebias = prebias_pts * step_eff
            # pulse on fast gate to pre-charge bias-T
            g1.add_block(0, t_prebias, config.vpx*0.35)
            # correct voltage to ensure average == 0.0 (No DC correction pulse needed at end)
            # Note that voltage on g2 ends center of sweep, i.e. (close to) 0.0 V
            total_duration = 2 * prebias_pts + config.n_ptx*n_pt2 * (2 if add_pulse_gate_correction else 1)
            g2.add_block(0, -1, -(prebias_pts * config.vp2)/total_duration)
            g2.add_block(0, t_prebias, config.vp2)
            for g, v in pulse_channels:
                g.add_block(0, t_prebias, -v)
            seg.reset_time()

        for v2 in config.voltages2:

            g1.add_ramp_ss(0, step_eff*config.n_ptx, -config.vpx, config.vpx)
            g2.add_block(0, step_eff*config.n_ptx, v2)
            for acq_ch in acq_channels:
                seg[acq_ch].acquire(step_eff*config.line_margin+config.acquisition_delay_ns,
                                    n_repeat=n_pt1, interval=step_eff)
            for g, v in pulse_channels:
                g.add_block(0, step_eff*config.n_ptx, v)
            seg.reset_time()

            if add_pulse_gate_correction:
                # add compensation pulses of pulse_channels
                # sweep g1 onces more; best effect on bias-T
                # keep g2 on 0
                g1.add_ramp_ss(0, step_eff*config.n_ptx, -config.vpx, config.vpx)
                for g, v in pulse_channels:
                    g.add_block(0, step_eff*config.n_ptx, -v)
                seg.reset_time()

        if config.biasT_corr:
            # pulses to discharge bias-T
            # Note: g2 is already 0.0 V
            g1.add_block(0, t_prebias, -config.vpx*0.35)
            for g, v in pulse_channels:
                g.add_block(0, t_prebias, +v)
            seg.reset_time()

        end_time = seg.total_time[0]
        for marker in config.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        # generate the sequence and upload it.
        my_seq = self.pulse_lib.mk_sequence([seg])
        my_seq.n_rep = 1
        # Note: set average repetitions to retrieve 1D array with channel data
        my_seq.set_acquisition(t_measure=t_measure, channels=acq_channels, average_repetitions=True)

        my_seq.upload()

        return QbloxFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq
        )


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
        channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray], str)]):
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
            E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
            The default channel_map is:
                {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
        pulse_gates (Dict[str, float]):
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        line_margin (int): number of points to add to sweep 1 to mask transition effects due to voltage step.
            The points are added to begin and end for symmetry (bias-T).

    Returns:
        Parameter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """
    scan_generator = FastScanGenerator()
    scan_generator.set_pulse_lib(pulse_lib)
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_1D_scan(gate, swing, n_pt, t_step, pulse_gates=pulse_gates, biasT_corr=biasT_corr)


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
        channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray], str)]):
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
            E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
            The default channel_map is:
                {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
        pulse_gates (Dict[str, float]):
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        line_margin (int): number of points to add to sweep 1 to mask transition effects due to voltage step.
            The points are added to begin and end for symmetry (bias-T).

    Returns:
        Parameter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """
    scan_generator = FastScanGenerator()
    scan_generator.set_pulse_lib(pulse_lib)
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_2D_scan(
        gate1, swing1, n_pt1,
        gate2, swing2, n_pt2,
        t_step, pulse_gates=pulse_gates, biasT_corr=biasT_corr)
