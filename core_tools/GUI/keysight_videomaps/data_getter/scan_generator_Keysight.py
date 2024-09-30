from collections import defaultdict
import time
import logging
import numpy as np

from core_tools.drivers.M3102A import DATA_MODE, MODES
from core_tools.HVI2.hvi2_video_mode import Hvi2VideoMode
from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader

from .scan_generator_base import FastScanParameterBase, FastScanGeneratorBase, ScanConfigBase


logger = logging.getLogger(__name__)


class KeysightFastScanParameter(FastScanParameterBase):
    """Fast scan parameter (qcodes.Multiparameter) for Keysight.
    The parameter reads the digitizer and returns 1D / 2D data according to
    scan_config.
    """

    def __init__(
            self,
            scan_config: ScanConfigBase,
            pulse_lib,
            pulse_sequence,
            digitizer = None,
            ):
        """
        args:
            pulse_lib (pulselib): pulse library object
            pulse_sequence (sequencer) : sequence of the 1D scan
            digitizer (SD_DIG) : digizer driver:
        """
        self.config = scan_config
        self.digitizer = digitizer
        self.pulse_lib = pulse_lib
        self.my_seq = pulse_sequence

        super().__init__(scan_config)

        # Create dict with digitizers and used channel numbers.
        # dict[digitizer, List[channel_numbers]]
        self.dig_channel_nums: dict[any, list[int]] = defaultdict(set)
        channels = [ch for ch, _, _ in scan_config.channel_map.values()]
        if digitizer is not None:
            for ch in channels:
                self.dig_channel_nums[digitizer].add(ch)
        else:
            for ch_name in channels:
                ch_conf = pulse_lib.digitizer_channels[ch_name]
                digitizer = pulse_lib.digitizers[ch_conf.module_name]
                for ch_num in ch_conf.channel_numbers:
                    self.dig_channel_nums[digitizer].add(ch_num)

        self.acquisition_channels = set(channels)
        self._configure_digitizer()

    def _configure_digitizer(self):
        npts = int(np.prod(self.config.shape))
        for digitizer, ch_nums in self.dig_channel_nums.items():
            # clean up the digitizer before start
            for ch in ch_nums:
                digitizer.daq_stop(ch)
                digitizer.daq_flush(ch)

            # configure digitizer
            digitizer.set_digitizer_HVI(
                self.config.t_measure,
                npts,
                sample_rate=500e6,
                data_mode=DATA_MODE.AVERAGE_TIME,
                channels=list(ch_nums))

    def get_channel_data(self) -> dict[str, np.ndarray]:
        """Starts scan and retrieves data.

        Returns:
            dictionary with per channel real or complex data in 1D ndarray.
        """
        self._configure_digitizer()

        # Play sequence
        start = time.perf_counter()
        self.my_seq.play(release=False)
        self.pulse_lib.uploader.wait_until_AWG_idle()
        end = time.perf_counter()
        logger.debug(f'Scan play {(end-start)*1000:3.1f} ms')

        # Retrieve data
        raw = {}
        if self.digitizer is None:
            dig_data = {}
            for dig in self.dig_channel_nums:
                dig_data[dig.name] = {}
                active_channels = dig.active_channels
                data = dig.measure.get_data()
                for ch_num, ch_data in zip(active_channels, data):
                    dig_data[dig.name][ch_num] = ch_data
            for channel_name in self.acquisition_channels:
                channel = self.pulse_lib.digitizer_channels[channel_name]
                dig_name = channel.module_name
                in_ch = channel.channel_numbers
                # Note: Digitizer FPGA returns IQ in complex value.
                #       2 input channels are used with external IQ demodulation without processing in FPGA.
                if len(in_ch) == 2:
                    raw_I = dig_data[dig_name][in_ch[0]]
                    raw_Q = dig_data[dig_name][in_ch[1]]
                    if dig.get_channel_acquisition_mode(in_ch[0]) in [2, 3, 4, 5]:
                        # Note: Wrong configuration! len(in_ch) should be 1
                        # phase shift is already applied in HW. Only use data of first channel
                        raw_ch = raw_I
                    else:
                        raw_ch = (raw_I + 1j * raw_Q) * np.exp(1j*channel.phase)
                else:
                    # this can be complex valued output with LO modulation or phase shift in digitizer (FPGA)
                    raw_ch = dig_data[dig_name][in_ch[0]]

                if not channel.iq_out:
                    raw_ch = raw_ch.real

                raw[channel_name] = raw_ch
        else:
            dig_data = self.digitizer.measure.get_data()
            for i, channel_num in enumerate(sorted(self.acquisition_channels)):
                raw[channel_num] = dig_data[i]

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
            logger.warning('Cleanup in __del__(); Please, call m_param.close() on measurement parameter!')
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

        if biasT_corr and config.line_margin > 0:
            print('Line margin is ignored with biasT_corr on')
            config.line_margin = 0

        add_line_delay = config.biasT_corr and len(config.pulse_gates) > 0

        min_step_eff = 200 if not add_line_delay else 350
        step_eff = self._get_t_step_eff(t_measure, min_step_eff)

        start_delay = config.line_margin * step_eff + self.acquisition_delay_ns
        line_delay_pts = 1
        n_lines = n_pt if add_line_delay else 1

        if not biasT_corr:
            prebias_pts = (config.n_ptx)//2
            t_prebias = prebias_pts * step_eff
            start_delay += t_prebias

        seg = self.pulse_lib.mk_segment()
        g1 = seg[gate]
        pulse_channels = []
        for ch, v in pulse_gates.items():
            pulse_channels.append((seg[ch], v))

        if not biasT_corr:
            # pre-pulse to condition bias-T
            g1.add_ramp_ss(0, t_prebias, 0, config.vpx)
            for gp, v in pulse_channels:
                gp.add_block(0, t_prebias, -v)
            seg.reset_time()

        for voltage in config.voltages:
            g1.add_block(0, step_eff, voltage)

            for gp, v in pulse_channels:
                gp.add_block(0, step_eff, v)
                # compensation for pulse gates
                if biasT_corr:
                    gp.add_block(step_eff, 2*step_eff, -v)
            seg.reset_time()

        if not biasT_corr:
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

        # 100 time points per step to make sure that everything looks good (this is more than needed).
        awg_t_step = t_measure / 100
        # prescaler is limited to 255 when hvi_queueing_control is enabled. Limit other cases as well
        if awg_t_step > 5 * 255:
            awg_t_step = 5 * 255
        sample_rate = 1/(awg_t_step*1e-9)
        seg.sample_rate = sample_rate

        my_seq = self._create_sequence(
            seg,
            acquisition_period=step_eff,
            n_pts=int(n_pt) if not add_line_delay else 1,
            n_lines=n_lines,
            start_delay=int(start_delay),
            line_delay=int(line_delay_pts*step_eff) if add_line_delay else 500,
            )

        my_seq.upload()

        return KeysightFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq,
            digitizer=self.digitizer)

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

        min_step_eff = 200
        step_eff = self._get_t_step_eff(t_measure, min_step_eff)

        add_pulse_gate_correction = biasT_corr and len(pulse_gates) > 0

        start_delay = config.line_margin * step_eff + self.acquisition_delay_ns
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

        # 20 time points per step to make sure that everything looks good (this is more than needed).
        awg_t_step = step_eff / 20
        # prescaler is limited to 255 when hvi_queueing_control is enabled.
        # Limit all cases to 800 kSa/s
        if awg_t_step > 5 * 250:
            awg_t_step = 5 * 250

        sample_rate = 1/(awg_t_step*1e-9)
        seg.sample_rate = sample_rate

        if line_delay_pts > 0:
            n_pts = int(n_pt1)
            n_lines = int(n_pt2)
            line_delay = int(line_delay_pts*step_eff)
        else:
            n_pts = int(n_pt1*n_pt2)
            n_lines = 1
            # Wait minimum time required by HVI schedule
            line_delay = 500

        my_seq = self._create_sequence(
            seg,
            acquisition_period=step_eff,
            n_pts=n_pts,
            n_lines=n_lines,
            start_delay=int(start_delay),
            line_delay=line_delay,
            )

        my_seq.upload()

        return KeysightFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq,
            digitizer=self.digitizer)

    def _get_t_step_eff(self, t_step, min_step_eff):

        raw_mode = False

        dig_channels = [ch for ch, _, _ in self.channel_map.values()]
        if self.digitizer is None:
            for ch_name in dig_channels:
                ch_conf = self.pulse_lib.digitizer_channels[ch_name]
                digitizer = self.pulse_lib.digitizers[ch_conf.module_name]
                for ch_num in ch_conf.channel_numbers:
                    if digitizer.get_channel_acquisition_mode(ch_num) == MODES.NORMAL:
                        raw_mode = True
        else:
            for ch_num in dig_channels:
                if self.digitizer.get_channel_acquisition_mode(ch_num) == MODES.NORMAL:
                    raw_mode = True

        min_gap = Hvi2VideoMode.get_minimum_acquisition_delay(raw_mode)
        gap = max(min_gap, self.acquisition_delay_ns)
        # set up timing for the scan
        step_eff = t_step + gap

        if step_eff < min_step_eff:
            msg = f'Measurement time too short. Minimum is {t_step + 200-step_eff}'
            logger.error(msg)
            raise Exception(msg)

        return step_eff

    def _create_sequence(
            self,
            seg,
            acquisition_period: int,
            n_pts: int,
            n_lines: int,
            start_delay: int,
            line_delay: int,
            ):

        # generate the sequence and upload it.
        my_seq = self.pulse_lib.mk_sequence([seg])
        # TODO Force configuration of digitizer in pulse_lib.
        my_seq.set_hw_schedule(Hvi2ScheduleLoader(self.pulse_lib, 'VideoMode', self.digitizer))

        hvi_dig_channels = defaultdict(set)
        dig_channels = [ch for ch, _, _ in self.channel_map.values()]
        if self.digitizer is None:
            for ch_name in dig_channels:
                ch_conf = self.pulse_lib.digitizer_channels[ch_name]
                hvi_dig_channels[ch_conf.module_name] |= set(ch_conf.channel_numbers)
        else:
            for ch_num in dig_channels:
                hvi_dig_channels[self.digitizer.name].add(ch_num)
        video_mode_channels = {name:list(channels) for name, channels in hvi_dig_channels.items()}

        if not hasattr(my_seq, 'schedule_params'):
            raise Exception('Update pulse-lib to v1.7.11+')

        my_seq.schedule_params["acquisition_period"]= acquisition_period
        my_seq.schedule_params["number_of_points"] = n_pts
        my_seq.schedule_params["number_of_lines"] = n_lines
        my_seq.schedule_params["start_delay"] = start_delay
        my_seq.schedule_params["line_delay"] = line_delay
        my_seq.schedule_params["video_mode_channels"] = video_mode_channels

        my_seq.n_rep = 1
        my_seq.configure_digitizer = False

        return my_seq


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
