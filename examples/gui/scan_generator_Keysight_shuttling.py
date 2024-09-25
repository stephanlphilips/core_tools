from collections import defaultdict
import logging
import numpy as np
from typing import Callable

from core_tools.HVI2.hvi2_schedule_loader import Hvi2ScheduleLoader

from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_base import (
    FastScanParameterBase,
    FastScanGeneratorBase,
    )
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Keysight import (
    KeysightFastScanParameter
    )


logger = logging.getLogger(__name__)


class ShuttlingSequence:
    action_step = "step"
    action_measure = "measure"
    action_scan = "scan"

    def __init__(
            self,
            v_setpoints: dict[str, float],
            sequence: list[str],
            t_shuttle_step: float,
            scan_point: str,
            t_scan: float,
            read_point: str,
            t_resolution: float,
            ):
        """Shuttling sequence definition using setpoints and lists with steps.

        Args:
            v_setpoints: voltages for the steps in the sequence.
            sequence: sequence of setpoints that make a full scan cycle.
            t_shuttle_step: time per shuttling step [ns]
            scan_point: name of the setpoint used for CSD scan.
            t_scan: time to stay in scan point [ns]
            read_point: name of the setpoint used for readout.
            t_resolution: time resolution for sequence [ns]
        """
        self._v_setpoints = v_setpoints
        self._sequence = sequence
        self._t_shuttle_step = t_shuttle_step
        self._scan_point = scan_point
        self._t_scan = t_scan
        self._read_point = read_point
        self.t_resolution = t_resolution

        if 0.0001 < (t_shuttle_step / t_resolution) % 1 < 0.9999:
            raise Exception(f"t_shuttle_step ({t_shuttle_step}) should be multiple of t_resolution ({t_resolution})")
        if 0.0001 < (t_scan / t_resolution) % 1 < 0.9999:
            raise Exception(f"t_scan ({t_scan}) should be multiple of t_resolution ({t_resolution})")

    def setpoints_loop(self):
        for point in self._sequence:
            if point == self._read_point:
                # Note: t_measure is set in 1D/2D scan
                t_point = np.nan
                action = self.action_measure
            elif point == self._scan_point:
                t_point = self._t_scan
                action = self.action_scan
            else:
                t_point = self._t_shuttle_step
                action = self.action_step
            yield action, t_point, self._v_setpoints[point]


class _CompensationCalculator:
    def __init__(
            self,
            compensation_limits: dict[str, tuple[float, float]],
            time_resolution: float):
        self._compensation_limits = compensation_limits
        self._time_resolution = time_resolution
        self._charges: dict[str, float] = defaultdict(float)

    def add_pulse(self, gate_voltages: dict[str, float], duration: float):
        for gate, voltage in gate_voltages.items():
            self._charges[gate] += voltage * duration

    def get_compensation_pulses(self) -> tuple[float, dict[str, float]]:
        limits = self._compensation_limits
        # Divide charge by maximum negative and positive voltage to get duration.
        # Get maximum duration over all gates.
        duration = np.max(
            [1.0] +
            [charge/limits[gate][0] for gate, charge in self._charges.items() if gate in limits] +
            [charge/limits[gate][1] for gate, charge in self._charges.items() if gate in limits]
            )
        duration = np.ceil(duration / self._time_resolution) * self._time_resolution
        return duration, {
            gate: -charge / duration
            for gate, charge in self._charges.items()
            if gate in limits
            }

    def reset(self):
        self._charges = defaultdict(float)


class ShuttlingScanGeneratorKeysight(FastScanGeneratorBase):

    # TODO: retrieve markers linked to digitizer channels.

    def __init__(
            self,
            pulse_lib,
            shuttling_sequence: ShuttlingSequence,
            ):
        super().__init__()
        self.set_pulse_lib(pulse_lib)
        self.shuttling_sequence = shuttling_sequence
        self._set_compensation_limits()
        self.plot_first = False

    def _set_compensation_limits(self):
        self._compensation_limits = {}
        for channel_name, awg_channel in self._pulse_lib.awg_channels.items():
            if awg_channel.compensation_limits == (0, 0):
                continue
            # convert AWG level to device level.
            self._compensation_limits[channel_name] = (
                awg_channel.compensation_limits[0] * awg_channel.attenuation,
                awg_channel.compensation_limits[1] * awg_channel.attenuation,
                )

    def _get_compensation_calculator(self) -> _CompensationCalculator:
        return _CompensationCalculator(
            self._compensation_limits,
            self.shuttling_sequence.t_resolution
            )

    def create_1D_scan(
            self,
            gate: str, swing: float, n_pt: int, t_measure: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = True,
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

        t_resolution = self.shuttling_sequence.t_resolution

        # Clear line_margin. It's not useful for shuttling scans.
        self.line_margin = 0
        self.acquisition_delay_ns = np.ceil(self.acquisition_delay_ns / t_resolution - 0.001) * t_resolution
        t_measure = np.ceil(t_measure / t_resolution - 0.001) * t_resolution
        # Always use biasT_corr for DC compensation alternating + and - voltages
        config = self.get_config1D(gate, swing, n_pt, t_measure, pulse_gates, biasT_corr=True)

        sample_rate = 1e9 / t_resolution

        compensation = self._get_compensation_calculator()

        seg = self.pulse_lib.mk_segment(sample_rate=sample_rate)

        t = 0
        start_delay = None
        loop_period = None
        for v_scan in config.voltages:

            for action, t_step, gate_voltages in self.shuttling_sequence.setpoints_loop():
                if action == ShuttlingSequence.action_scan:
                    seg[gate].add_block(0, t_step, v_scan)
                    # Note: Ignore v_scan in compensation pulse. it's compensated by alternating voltagees.
                    # compensation.add_pulse({gate: v_scan}, t_step)
                elif action == ShuttlingSequence.action_measure:
                    # Acquistion trigger is done via HVI using sequence parameters.
                    # Set start_delay for first measurement.
                    # Next set period between measurement starts.
                    if start_delay is None:
                        start_delay = t + config.acquisition_delay_ns
                    elif loop_period is None:
                        loop_period = t
                    else:
                        if loop_period != t:
                            raise Exception(f"Irregular acquisition period {loop_period}<>{t}")
                    t = 0
                    t_step = t_measure + config.acquisition_delay_ns
                if pulse_gates:
                    seg.add_block(0, t_step, list(pulse_gates.keys()), list(pulse_gates.values()))
                    compensation.add_pulse(pulse_gates, t_step)
                seg.add_block(0, t_step, list(gate_voltages.keys()), list(gate_voltages.values()))
                compensation.add_pulse(gate_voltages, t_step)
                t += t_step
                seg.reset_time()

            t_compensate, v_compensate = compensation.get_compensation_pulses()
            compensation.reset()
            seg.add_block(0, t_compensate, list(v_compensate.keys()), list(v_compensate.values()))
            seg.reset_time()
            t += t_compensate

        n_lines = 1

        end_time = seg.total_time[0]
        for marker in config.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        if self.plot_first:
            seg.plot()

        my_seq = self._create_sequence(
            seg,
            acquisition_period=int(loop_period),
            n_pts=int(n_pt),
            n_lines=n_lines,
            start_delay=int(start_delay),
            line_delay=500, # minimum value
            )

        my_seq.upload()

        return KeysightFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq)

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

        t_resolution = self.shuttling_sequence.t_resolution

        # Clear line_margin. It's not useful for shuttling scans.
        self.line_margin = 0
        self.acquisition_delay_ns = np.ceil(self.acquisition_delay_ns / t_resolution - 0.001) * t_resolution
        t_measure = np.ceil(t_measure / t_resolution - 0.001) * t_resolution

        # Always use biasT_corr for DC compensation alternating + and - voltages
        config = self.get_config2D(
            gate1, swing1, n_pt1,
            gate2, swing2, n_pt2,
            t_measure, pulse_gates, biasT_corr=True)

        sample_rate = 1e9 / t_resolution

        compensation = self._get_compensation_calculator()

        seg = self.pulse_lib.mk_segment(sample_rate=sample_rate)

        t = 0
        start_delay = None
        loop_period = None
        for v_scan2 in config.voltages2:
            for v_scan1 in np.linspace(-swing1/2, +swing1/2, n_pt1):
                for action, t_step, gate_voltages in self.shuttling_sequence.setpoints_loop():
                    if action == ShuttlingSequence.action_scan:
                        seg[gate1].add_block(0, t_step, v_scan1)
                        seg[gate2].add_block(0, t_step, v_scan2)
                        # Note: Ignore v_scan in compensation pulse. it's compensated by alternating voltagees.
                        # compensation.add_pulse({gate: v_scan}, t_step)
                    elif action == ShuttlingSequence.action_measure:
                        # Acquistion trigger is done via HVI using sequence parameters.
                        # Set start_delay for first measurement.
                        # Next set period between measurement starts.
                        if start_delay is None:
                            start_delay = t + config.acquisition_delay_ns
                        elif loop_period is None:
                            loop_period = t
                        else:
                            if loop_period != t:
                                raise Exception(f"Irregular acquisition period {loop_period}<>{t}")
                        t = 0
                        t_step = t_measure + config.acquisition_delay_ns
                    if pulse_gates:
                        seg.add_block(0, t_step, list(pulse_gates.keys()), list(pulse_gates.values()))
                        compensation.add_pulse(pulse_gates, t_step)
                    seg.add_block(0, t_step, list(gate_voltages.keys()), list(gate_voltages.values()))
                    compensation.add_pulse(gate_voltages, t_step)
                    t += t_step
                    seg.reset_time()

                t_compensate, v_compensate = compensation.get_compensation_pulses()
                compensation.reset()
                seg.add_block(0, t_compensate, list(v_compensate.keys()), list(v_compensate.values()))
                seg.reset_time()
                t += t_compensate

        n_lines = 1
        n_pts = int(n_pt1*n_pt2)

        end_time = seg.total_time[0]
        for marker in config.enabled_markers:
            marker_ch = seg[marker]
            marker_ch.reset_time(0)
            marker_ch.add_marker(0, end_time)

        if self.plot_first:
            seg.plot()

        my_seq = self._create_sequence(
            seg,
            acquisition_period=int(loop_period),
            n_pts=n_pts,
            n_lines=n_lines,
            start_delay=int(start_delay),
            line_delay=500, # minimum value
            )

        my_seq.upload()

        return KeysightFastScanParameter(
            config,
            pulse_lib=self.pulse_lib,
            pulse_sequence=my_seq)

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
        my_seq.set_hw_schedule(Hvi2ScheduleLoader(self.pulse_lib, 'VideoMode'))

        hvi_dig_channels = defaultdict(set)
        dig_channels = [ch for ch, _, _ in self.channel_map.values()]

        for ch_name in dig_channels:
            ch_conf = self.pulse_lib.digitizer_channels[ch_name]
            hvi_dig_channels[ch_conf.module_name] |= set(ch_conf.channel_numbers)

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



def create_1D_scan_shuttling(
        pulse_lib,
        shuttling_sequence: ShuttlingSequence,
        gate: str, swing: float, n_pt: int,
        t_measure: float,
        channels: list[str] | None = None,
        iq_mode: str | None = None,
        channel_map: dict[str, tuple[str, Callable[[np.ndarray], np.ndarray], str]] | None = None,
        acquisition_delay_ns=500,
        enabled_markers=[],
        pulse_gates={},
    ):
    """
    1D fast scan parameter constructor.

    Args:
        pulse_lib: pulse library object, needed to make the sweep.
        gate: gate/gates that you want to sweep.
        swing: swing to apply on the AWG gates. [mV]
        n_pt: number of points to measure (current firmware limits to 1000)
        t_measure: time in ns to measure per point. [ns]
        channels: digitizer channels to read
        iq_mode: for digitizer IQ channels this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels.
        acquisition_delay_ns:
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
        enabled_markers: marker channels to enable during scan
        channel_map:
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
            E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
            The default channel_map is:
                {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
        pulse_gates:
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        shuttling_sequence: ...
        shuttling_v_setpoints: ...

    Returns:
        Parameter that can be used as input in a scan/measurement functions.
    """
    scan_generator = ShuttlingScanGeneratorKeysight(
            pulse_lib,
            shuttling_sequence,
            )
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin=0)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_1D_scan(gate, swing, n_pt, t_measure, pulse_gates=pulse_gates, biasT_corr=False)


def create_2D_scan_shuttling(
        pulse_lib,
        shuttling_sequence: ShuttlingSequence,
        gate1: str, swing1: float, n_pt1: int,
        gate2: str, swing2: float, n_pt2: int,
        t_measure: float,
        channels: list[str] | None = None,
        iq_mode: str | None = None,
        channel_map: dict[str, tuple[str, Callable[[np.ndarray], np.ndarray], str]] | None = None,
        acquisition_delay_ns=500,
        enabled_markers=[],
        pulse_gates={},
        ):
    """
    2D fast scan parameter constructor.

    Args:
        pulse_lib: pulse library object, needed to make the sweep.
        gates1: gate that you want to sweep on x axis.
        swing1: swing to apply on the AWG gates.
        n_pt1: number of points to measure (current firmware limits to 1000)
        gate2: gate that you want to sweep on y axis.
        swing2: swing to apply on the AWG gates.
        n_pt2: number of points to measure (current firmware limits to 1000)
        t_step: time in ns to measure per point.
        channels: digitizer channels to read
        iq_mode: for digitizer IQ channels this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                all channels.
        acquisition_delay_ns:
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
        enabled_markers: marker channels to enable during scan
        channel_map:
            defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
            E.g. {('SD1-I':('SD1', np.real, 'mV'), 'SD1-Q':('SD1', np.imag, 'mV'),
                   'SD2-Amp':('SD2', np.abs, 'mV'), 'SD2-Phase':('SD2', np.angle, 'rad')}
            The default channel_map is: {ch_name: (ch_name, np.real, 'mV') for ch_name in pulse.digitizer_channels}
        pulse_gates:
            Gates to pulse during scan with pulse voltage in mV.
            E.g. {'vP1': 10.0, 'vB2': -29.1}
        shuttling_sequence: ...

    Returns:
        Parameter that can be used as input in a scan/measurement functions.
    """
    scan_generator = ShuttlingScanGeneratorKeysight(
            pulse_lib,
            shuttling_sequence,
            )
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin=0)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_2D_scan(
        gate1, swing1, n_pt1,
        gate2, swing2, n_pt2,
        t_measure, pulse_gates=pulse_gates, biasT_corr=False)
