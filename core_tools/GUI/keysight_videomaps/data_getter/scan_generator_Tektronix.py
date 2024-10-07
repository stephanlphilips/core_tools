import numpy as np
import time
import logging

from pulse_lib.schedule.tektronix_schedule import TektronixSchedule
from .scan_generator_base import FastScanParameterBase, FastScanGeneratorBase, ScanConfigBase

try:
    import pyspcm
except:
    pass


logger = logging.getLogger(__name__)


class M4iFastScanParameter(FastScanParameterBase):

    def __init__(
            self,
            scan_config: ScanConfigBase,
            pulse_lib,
            pulse_sequence,
            digitizer,
            n_lines,
            line_delay_pts,
            digitizer_sample_rate=60e6,
            ):
        """
        args:
            pulse_lib (pulselib): pulse library object
            pulse_sequence (sequencer) : sequence of the 1D scan
            digitizer (M4i) : Spectrum M4i digitizer driver:
            n_lines (int): number of scan lines
            line_delay_pts (int): line delay in number of points.
            sample_rate (float): sample rate of the digitizer card that should be used.
        """
        self.pulse_lib = pulse_lib
        self.my_seq = pulse_sequence
        self.dig = digitizer
        self.n_lines = n_lines
        self.line_delay_pts = line_delay_pts
        self.n_points = np.prod(scan_config.shape)
        self._recompile_requested = False

        super().__init__(scan_config)

        if digitizer_sample_rate > 60e6:
            digitizer_sample_rate = 60e6
        # digitizer sample rate is matched to hardware value by driver
        digitizer.sample_rate(digitizer_sample_rate)
        self.sample_rate = digitizer.sample_rate()

        acq_channels = set(channel_num for channel_num, _, _ in self.channel_map.values())
        self.n_ch = len(acq_channels)
        self.acq_channels = sorted(acq_channels)

        if self.n_ch not in [1,2,4]:
            raise Exception('Number of enabled channels on M4i must be 1, 2 or 4.')
        digitizer.enable_channels(sum([2**ch for ch in acq_channels]))

        # is demodulation configured in pulse-lib?
        self._demodulate = []
        for dig_ch in self.pulse_lib.digitizer_channels.values():
            if dig_ch.frequency is not None:
                if len(dig_ch.channel_numbers) == 1:
                    if dig_ch.channel_numbers[0] not in self.channels:
                        # skip this channel
                        continue
                else:
                    if ((dig_ch.channel_numbers[0] in self.channels) !=
                        (dig_ch.channel_numbers[1] in self.channels)):
                        raise Exception(f'Channels {dig_ch.channel_numbers} of {dig_ch.name} '
                                        'must both be present or absent in acquisition for demodulation')
                    if dig_ch.channel_numbers[0] not in self.channels:
                        # skip these channels
                        continue
                self._demodulate.append(
                        (dig_ch.channel_numbers, dig_ch.frequency, dig_ch.phase, dig_ch.iq_out))

        # note: force float calculation to avoid intermediate int overflow.
        self.seg_size = int(float(self.config.t_measure + self.config.acquisition_delay_ns)
                            * (self.n_points + self.n_lines * self.line_delay_pts)
                            * self.sample_rate * 1e-9)

        self.dig.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)
        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

    def recompile(self):
        self._recompile_requested = True

    def get_channel_data(self) -> dict[str, np.ndarray]:
        if self._recompile_requested:
            self._recompile_requested = False
            start = time.perf_counter()
            self.my_seq.recompile()
            self.my_seq.upload()
            duration = time.perf_counter() - start
            logger.info(f"Recompiled in {duration*1000:.1f} ms")

        start = time.perf_counter()
        logger.debug('Play')
        # play sequence
        self.my_seq.play(release=False)

        # get the data
        raw_data = self.dig.get_data()

        duration = (time.perf_counter() - start)*1000
        logger.debug(f'Acquired ({duration:5.1f} ms)')

        pretrigger = self.dig.pretrigger_memory_size()
        raw_data = raw_data[:,pretrigger:pretrigger++self.seg_size]

        for channels, frequency, phase, iq_out in self._demodulate:
            if iq_out and raw_data.dtype != complex:
                raw_data = raw_data.astype(complex)
            t = np.arange(self.seg_size) / self.sample_rate
            channels = [self.acq_channels.index(ch) for ch in channels]
            iq = np.exp(-1j*(2*np.pi*t*frequency+phase))
            if len(channels) == 1:
                demodulated = raw_data[channels[0]] * iq
                if iq_out:
                    raw_data[channels[0]] = demodulated
                else:
                    raw_data[channels[0]] = demodulated.real
            else:
                demodulated = (raw_data[channels[0]]+1j*raw_data[channels[1]])*iq
                if iq_out:
                    raw_data[channels[0]] = demodulated
                    raw_data[channels[1]] = demodulated
                else:
                    raw_data[channels[0]] = demodulated.real
                    raw_data[channels[1]] = demodulated.imag

        point_data = np.zeros((len(self.acq_channels), self.n_points), dtype=raw_data.dtype)

        samples_t_measure = self.config.t_measure * self.sample_rate * 1e-9
        samples_acq_delay = self.config.acquisition_delay_ns * self.sample_rate * 1e-9
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
        logger.debug(f'Averaged ({duration:5.1f} ms)')

        return point_data

    def restart(self):
        self.dig.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)
        self.dig.setup_multi_recording(self.seg_size, n_triggers=1)

    def stop(self):
        self.close()

    def close(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logger.info('stop: release memory')
            # remove pulse sequence from the AWG's memory, unload schedule and free memory.
            self.my_seq.close()
            self.my_seq = None
            self.pulse_lib = None

    def __del__(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logger.warning('Cleanup in __del__(); Call param.close()!')
            self.close()


class FastScanGenerator(FastScanGeneratorBase):

    # TODO: retrieve markers linked to digitizer channels.

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

        add_line_delay = biasT_corr and len(pulse_gates) > 0

        if not config.acquisition_delay_ns:
            config.acquisition_delay_ns = 500
        step_eff = config.acquisition_delay_ns + t_measure

        min_step_eff = 200 if not add_line_delay else 350
        if step_eff < min_step_eff:
            msg = f'Measurement time too short. Minimum is {min_step_eff-config.acquisition_delay_ns}'
            logger.error(msg)
            raise Exception(msg)

        start_delay = config.line_margin * step_eff + config.acquisition_delay_ns
        line_delay_pts = 1
        n_lines = n_pt if add_line_delay else 1

        if not config.biasT_corr:
            prebias_pts = (config.n_ptx)//2
            t_prebias = prebias_pts * step_eff
            start_delay += t_prebias

        seg  = self.pulse_lib.mk_segment()
        g1 = seg[gate]
        pulse_channels = []
        for ch,v in pulse_gates.items():
            pulse_channels.append((seg[ch], v))

        if not biasT_corr:
            # pre-pulse to condition bias-T
            g1.add_ramp_ss(0, t_prebias, 0, config.vpx)
            for gp,v in pulse_channels:
                gp.add_block(0, t_prebias, -v)
            seg.reset_time()

        for voltage in config.voltages:
            g1.add_block(0, step_eff, voltage)

            for gp,v in pulse_channels:
                gp.add_block(0, step_eff, v)
                # compensation for pulse gates
                if biasT_corr:
                    gp.add_block(step_eff, 2*step_eff, -v)
            seg.reset_time()

        if not biasT_corr:
            # post-pulse to discharge bias-T
            g1.add_ramp_ss(0, t_prebias, -config.vpx, 0)
            for gp,v in pulse_channels:
                gp.add_block(0, t_prebias, -v)
            seg.reset_time()

        end_time = seg.total_time[0]
        for marker in self.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        sample_rate = 10e6 # lowest sample rate of Tektronix

        # generate the sequence and upload it.
        my_seq = self.pulse_lib.mk_sequence([seg])
        my_seq.set_hw_schedule(TektronixSchedule(self.pulse_lib))
        my_seq.configure_digitizer = False
        my_seq.n_rep = 1
        my_seq.sample_rate = sample_rate

        if not hasattr(my_seq, 'schedule_params'):
            raise Exception('Update pulse-lib to v1.7.11+')
        my_seq.schedule_params['dig_trigger_1'] = start_delay

        logger.debug('Upload')
        my_seq.upload()

        return M4iFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq,
            digitizer=self.digitizer,
            n_lines=n_lines,
            line_delay_pts=line_delay_pts,
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

        if not config.acquisition_delay_ns:
            config.acquisition_delay_ns = 500

        min_step_eff = 200
        step_eff = t_measure + config.acquisition_delay_ns
        if step_eff < min_step_eff:
            msg = f'Measurement time too short. Minimum is {min_step_eff-config.acquisition_delay_ns}'
            logger.error(msg)
            raise Exception(msg)

        add_pulse_gate_correction = biasT_corr and len(pulse_gates) > 0

        start_delay = config.line_margin * step_eff + config.acquisition_delay_ns
        if biasT_corr:
            # prebias: add half line with +vp2
            prebias_pts = (config.n_ptx)//2
            t_prebias = prebias_pts * step_eff
            start_delay += t_prebias

        line_delay_pts = 2 * config.line_margin
        if add_pulse_gate_correction:
            line_delay_pts += config.n_ptx

        seg = self.pulse_lib.mk_segment()

        g1 = seg[gate1]
        g2 = seg[gate2]
        pulse_channels = []
        for ch, v in pulse_gates.items():
            pulse_channels.append((seg[ch], v))

        if biasT_corr:
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

        if biasT_corr:
            # pulses to discharge bias-T
            # Note: g2 is already 0.0 V
            g1.add_block(0, t_prebias, -config.vpx*0.35)
            for g, v in pulse_channels:
                g.add_block(0, t_prebias, +v)
            seg.reset_time()

        end_time = seg.total_time[0]
        for marker in self.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        sample_rate = 10e6 # lowest sample rate of Tektronix

        # generate the sequence and upload it.
        my_seq = self.pulse_lib.mk_sequence([seg])
        my_seq.set_hw_schedule(TektronixSchedule(self.pulse_lib))
        my_seq.configure_digitizer = False
        my_seq.n_rep = 1
        my_seq.sample_rate = sample_rate

        if not hasattr(my_seq, 'schedule_params'):
            raise Exception('Update pulse-lib to v1.7.11+')
        my_seq.schedule_params['dig_trigger_1'] = start_delay

        logger.debug('Seq upload')
        my_seq.upload()

        n_lines = n_pt2
        return M4iFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq,
            digitizer=self.digitizer,
            n_lines=n_lines,
            line_delay_pts=line_delay_pts,
            )

def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib,
                           digitizer=None, channels=None,
                           iq_mode=None, acquisition_delay_ns=500,
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
        channels (list[str] or list[int]) : digitizer channels to read
        iq_mode (optional str): for digitizer IQ channels this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels.
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
    scan_generator.set_digitizer(digitizer)
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_1D_scan(gate, swing, n_pt, t_step, pulse_gates=pulse_gates, biasT_corr=biasT_corr)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer=None, channels=None, iq_mode=None,
                           acquisition_delay_ns=500, enabled_markers=[], channel_map=None,
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
        digitizer: digitizer object
        channels (list[str] or list[int]) : digitizer channels to read
        iq_mode (optional str): for digitizer IQ channels this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels.
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
    scan_generator.set_digitizer(digitizer)
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_2D_scan(
        gate1, swing1, n_pt1,
        gate2, swing2, n_pt2,
        t_step, pulse_gates=pulse_gates, biasT_corr=biasT_corr)
