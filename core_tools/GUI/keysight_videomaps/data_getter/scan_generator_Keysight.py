from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import time
import logging
import numpy as np

from qcodes import MultiParameter
from core_tools.drivers.M3102A import DATA_MODE
from core_tools.HVI2.hvi2_video_mode import Hvi2VideoMode
from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader
from .iq_modes import get_channel_map, get_channel_map_dig_4ch, add_channel_map_units

logger = logging.getLogger(__name__)


def _get_t_step_eff(pulse, digitizer, t_step, acquisition_delay_ns, min_step_eff):
    if digitizer is None:
        digitizers = list(pulse.digitizers.values())
        if not digitizers:
            raise Exception("Digitizer not specified and not defined in pulse-lib")
        min_gap = max(
            Hvi2VideoMode.get_acquisition_gap(dig, acquisition_delay_ns)
            for dig in digitizers)
    else:
        min_gap = Hvi2VideoMode.get_acquisition_gap(digitizer, acquisition_delay_ns)
    # set up timing for the scan
    step_eff = t_step + min_gap

    if step_eff < min_step_eff:
        msg = f'Measurement time too short. Minimum is {t_step + 200-step_eff}'
        logger.error(msg)
        raise Exception(msg)

    return step_eff


def _create_sequence(
        pulse_lib,
        seg,
        digitizer,
        t_measure: int,
        n_pts: int,
        n_lines: int,
        start_delay: int,
        line_delay: int,
        acquisition_delay_ns: int,
        channel_map: Dict[str, Tuple[Union[str, int], Callable[[np.ndarray], np.ndarray]]]
        ):

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([seg])
    # TODO Force configuration of digitizer in pulse_lib.
    my_seq.set_hw_schedule(Hvi2ScheduleLoader(pulse_lib, 'VideoMode', digitizer))

    hvi_dig_channels = defaultdict(set)
    dig_channels = [ch for ch, _, _ in channel_map.values()]
    if digitizer is None:
        for ch_name in dig_channels:
            ch_conf = pulse_lib.digitizer_channels[ch_name]
            hvi_dig_channels[ch_conf.module_name] |= set(ch_conf.channel_numbers)
    else:
        for ch_num in dig_channels:
            hvi_dig_channels[digitizer.name].add(ch_num)
    video_mode_channels = {name:list(channels) for name, channels in hvi_dig_channels.items()}

    if not hasattr(my_seq, 'schedule_params'):
        raise Exception('Update pulse-lib to v1.7.11+')
    my_seq.schedule_params['acquisition_delay_ns'] = acquisition_delay_ns
    my_seq.schedule_params["t_measure"]= t_measure
    my_seq.schedule_params["number_of_points"] = n_pts
    my_seq.schedule_params["number_of_lines"] = n_lines
    my_seq.schedule_params["start_delay"] = start_delay
    my_seq.schedule_params["line_delay"] = line_delay
    my_seq.schedule_params["video_mode_channels"] = video_mode_channels

    my_seq.n_rep = 1
    my_seq.configure_digitizer = False

    return my_seq


# TODO: retrieve markers linked to digitizer channels.


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
    logger.info(f'Construct 1D: {gate}')

    channel_map = _get_channel_map(pulse_lib, iq_mode, channels, channel_map, digitizer)

    vp = swing/2
    line_margin = int(line_margin)
    if biasT_corr and line_margin > 0:
        print('Line margin is ignored with biasT_corr on')
        line_margin = 0

    add_line_delay = biasT_corr and len(pulse_gates) > 0

    min_step_eff = 200 if not add_line_delay else 350
    step_eff = _get_t_step_eff(pulse_lib, digitizer, t_step, acquisition_delay_ns, min_step_eff)

    n_ptx = n_pt + 2*line_margin
    vpx = vp * (n_ptx-1)/(n_pt-1)

    # set up sweep voltages (get the right order, to compensate for the biasT).
    voltages_sp = np.linspace(-vp, vp, n_pt)
    voltages_x = np.linspace(-vpx, vpx, n_ptx)
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

    seg = pulse_lib.mk_segment()
    g1 = seg[gate]
    pulse_channels = []
    for ch, v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    if not biasT_corr:
        # pre-pulse to condition bias-T
        g1.add_ramp_ss(0, t_prebias, 0, vpx)
        for gp, v in pulse_channels:
            gp.add_block(0, t_prebias, -v)
        seg.reset_time()

    for voltage in voltages:
        g1.add_block(0, step_eff, voltage)

        for gp, v in pulse_channels:
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

    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step / 100
    # prescaler is limited to 255 when hvi_queueing_control is enabled. Limit other cases as well
    if awg_t_step > 5 * 255:
        awg_t_step = 5 * 255
    sample_rate = 1/(awg_t_step*1e-9)
    seg.sample_rate = sample_rate

    my_seq = _create_sequence(
        pulse_lib,
        seg,
        digitizer,
        t_measure=int(t_step),
        n_pts=int(n_pt) if not add_line_delay else 1,
        n_lines=n_lines,
        start_delay=int(start_delay),
        line_delay=int(line_delay_pts*step_eff) if add_line_delay else 500,
        acquisition_delay_ns=acquisition_delay_ns,
        channel_map=channel_map
        )

    my_seq.upload()

    parameters = dict(
            gate=gate,
            swing=dict(label="swing", value=swing, unit="mV"),
            n_pt=n_pt,
            t_measure=dict(label="t_measure", value=t_step, unit="ns"),
            biasT_corr=biasT_corr,
            iq_mode=iq_mode,
            acquisition_delay=dict(
                label="acquisition_delay",
                value=acquisition_delay_ns,
                unit="ns"),
            enabled_markers=enabled_markers,
            pulse_gates={
                name: dict(label=name, value=value, unit="mV")
                for name, value in pulse_gates.items()
                },
            line_margin=line_margin,
            )

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step,
                                    (n_pt, ), (gate, ), (tuple(voltages_sp), ),
                                    biasT_corr, channel_map,
                                    snapshot_extra={"parameters": parameters})


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
    logger.info(f'Construct 2D: {gate1} {gate2}')

    channel_map = _get_channel_map(pulse_lib, iq_mode, channels, channel_map, digitizer)

    min_step_eff = 200
    step_eff = _get_t_step_eff(pulse_lib, digitizer, t_step, acquisition_delay_ns, min_step_eff)

    line_margin = int(line_margin)
    add_pulse_gate_correction = biasT_corr and len(pulse_gates) > 0

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1_sp = np.linspace(-vp1, vp1, n_pt1)
    voltages2_sp = np.linspace(-vp2, vp2, n_pt2)

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

    seg = pulse_lib.mk_segment()

    g1 = seg[gate1]
    g2 = seg[gate2]
    pulse_channels = []
    for ch, v in pulse_gates.items():
        pulse_channels.append((seg[ch], v))

    if biasT_corr:
        # pulse on fast gate to pre-charge bias-T
        g1.add_block(0, t_prebias, vpx*0.35)
        # correct voltage to ensure average == 0.0 (No DC correction pulse needed at end)
        # Note that voltage on g2 ends center of sweep, i.e. (close to) 0.0 V
        total_duration = 2 * prebias_pts + n_ptx*n_pt2 * (2 if add_pulse_gate_correction else 1)
        g2.add_block(0, -1, -(prebias_pts * vp2)/total_duration)
        g2.add_block(0, t_prebias, vp2)
        for g, v in pulse_channels:
            g.add_block(0, t_prebias, -v)
        seg.reset_time()

    for v2 in voltages2:

        g1.add_ramp_ss(0, step_eff*n_ptx, -vpx, vpx)
        g2.add_block(0, step_eff*n_ptx, v2)
        for g, v in pulse_channels:
            g.add_block(0, step_eff*n_ptx, v)
        seg.reset_time()

        if add_pulse_gate_correction:
            # add compensation pulses of pulse_channels
            # sweep g1 onces more; best effect on bias-T
            # keep g2 on 0
            g1.add_ramp_ss(0, step_eff*n_ptx, -vpx, vpx)
            for g, v in pulse_channels:
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
        # Wait minimum time to required by HVI schedule
        line_delay = 500

    my_seq = _create_sequence(
        pulse_lib,
        seg,
        digitizer,
        t_measure=int(t_step),
        n_pts=n_pts,
        n_lines=n_lines,
        start_delay=int(start_delay),
        line_delay=line_delay,
        acquisition_delay_ns=acquisition_delay_ns,
        channel_map=channel_map
        )

    my_seq.upload()

    parameters = dict(
            gate1=gate1,
            swing1=dict(label="swing1", value=swing1, unit="mV"),
            n_pt1=n_pt1,
            gate2=gate2,
            swing2=dict(label="swing2", value=swing2, unit="mV"),
            n_pt2=n_pt2,
            t_measure=dict(label="t_measure", value=t_step, unit="ns"),
            biasT_corr=biasT_corr,
            iq_mode=iq_mode,
            acquisition_delay=dict(
                label="acquisition_delay",
                value=acquisition_delay_ns,
                unit="ns"),
            enabled_markers=enabled_markers,
            pulse_gates={
                name: dict(label=name, value=value, unit="mV")
                for name, value in pulse_gates.items()
                },
            line_margin=line_margin,
            )

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step,
                                    (n_pt2, n_pt1), (gate2, gate1),
                                    (tuple(voltages2_sp), (tuple(voltages1_sp),)*n_pt2),
                                    biasT_corr, channel_map,
                                    snapshot_extra={"parameters": parameters})


def _get_channel_map(pulse_lib, iq_mode, channels, channel_map, digitizer):
    if channel_map is None:
        if digitizer is None:
            channel_map = get_channel_map(pulse_lib, iq_mode, channels)
        else:
            channel_map = get_channel_map_dig_4ch(iq_mode, channels)
    else:
        # copy with units.
        channel_map = add_channel_map_units(channel_map)
    return channel_map


class _digitzer_scan_parameter(MultiParameter):

    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint,
                 biasT_corr, channel_map, snapshot_extra):
        """
        args:
            digitizer (SD_DIG) : digizer driver:
            my_seq (sequencer) : sequence of the 1D scan
            pulse_lib (pulselib): pulse library object
            t_measure (int) : time to measure per step
            shape (tuple<int>): expected output shape
            names (tuple<str>): name of the gate(s) that are measured.
            setpoint (tuple<np.ndarray>): array with the setpoints of the input data
            biasT_corr (bool): bias T correction or not -- if enabled -- automatic reshaping of the data.
            channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray], str)]):
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
                E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
                The default channel_map is:
                    {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
            snapshot_extra (dict<str, any>): snapshot
        """
        self.digitizer = digitizer
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.n_rep = np.prod(shape)
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.channel_map = channel_map
        self.channel_names = tuple(self.channel_map.keys())
        self.acquisition_channels = set(ch for ch, _, _ in self.channel_map.values())

        channel_map_snapshot = {}
        for name, mapping in channel_map.items():
            channel_map_snapshot[name] = {
                "channel": mapping[0],
                "func": getattr(mapping[1], "__name__", str(mapping[1])),
                "unit": mapping[2],
                }
        snapshot_extra["parameters"]["channel_map"] = channel_map_snapshot
        self._snapshot_extra = snapshot_extra

        # Create dict with digitizers and used channel numbers.
        # dict[digitizer, List[channel_numbers]]
        self.dig_channel_nums: Dict[Any, List[int]] = defaultdict(set)
        channels = [ch for ch, _, _ in self.channel_map.values()]
        units = tuple(unit for _, _, unit in self.channel_map.values())
        if digitizer is not None:
            for ch in channels:
                self.dig_channel_nums[digitizer].add(ch)
        else:
            for ch_name in channels:
                ch_conf = pulse_lib.digitizer_channels[ch_name]
                digitizer = pulse_lib.digitizers[ch_conf.module_name]
                for ch_num in ch_conf.channel_numbers:
                    self.dig_channel_nums[digitizer].add(ch_num)

        for digitizer, ch_nums in self.dig_channel_nums.items():
            # clean up the digitizer before start
            for ch in ch_nums:
                digitizer.daq_stop(ch)
                digitizer.daq_flush(ch)

            # configure digitizer
            digitizer.set_digitizer_HVI(
                self.t_measure,
                int(np.prod(self.shape)),
                sample_rate=500e6,
                data_mode=DATA_MODE.AVERAGE_TIME,
                channels=list(ch_nums))

        n_out_ch = len(self.channel_names)
        super().__init__(name="fast_scan",
                         names=self.channel_names,
                         shapes=tuple([shape]*n_out_ch),
                         labels=self.channel_names,
                         units=units,
                         setpoints=tuple([setpoint]*n_out_ch),
                         setpoint_names=tuple([names]*n_out_ch),
                         setpoint_labels=tuple([names]*n_out_ch),
                         setpoint_units=(("mV", )*len(names), )*n_out_ch,
                         docstring='Scan parameter for digitizer')

    def get_raw(self):

        for digitizer, ch_nums in self.dig_channel_nums.items():
            # clean up the digitizer before start
            for ch in ch_nums:
                digitizer.daq_stop(ch)
                digitizer.daq_flush(ch)

            # configure digitizer
            digitizer.set_digitizer_HVI(
                self.t_measure,
                int(np.prod(self.shape)),
                sample_rate=500e6,
                data_mode=DATA_MODE.AVERAGE_TIME,
                channels=list(ch_nums))

        start = time.perf_counter()
        # play sequence
        self.my_seq.play(release=False)
        self.pulse_lib.uploader.wait_until_AWG_idle()
        end = time.perf_counter()
        logger.debug(f'Scan play {(end-start)*1000:3.1f} ms')

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
            for i,channel_num in enumerate(sorted(self.acquisition_channels)):
                raw[channel_num] = dig_data[i]

        # Reshape and reorder data for bias-T correction
        for name in raw:
            ch_data = raw[name].reshape(self.shape)
            if self.biasT_corr:
                data = np.zeros(self.shape, dtype=ch_data.dtype)
                data[:len(ch_data[::2])] = ch_data[::2]
                data[len(ch_data[::2]):] = ch_data[1::2][::-1]
                raw[name] = data
            else:
                raw[name] = ch_data

        # post-process data
        data_out = []
        for ch, func, _ in self.channel_map.values():
            ch_data = raw[ch]
            data_out.append(func(ch_data))

        return tuple(data_out)

    def snapshot_base(self,
                      update: Optional[bool] = True,
                      params_to_skip_update: Optional[Sequence[str]] = None
                      ) -> Dict[Any, Any]:
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot.update(self._snapshot_extra)
        return snapshot

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
