import time
import numpy as np

from .scan_generator_base import FastScanParameterBase, FastScanGeneratorBase, ScanConfigBase

class _FastScanParameter(FastScanParameterBase):

    def __init__(
            self,
            scan_config: ScanConfigBase,
            ):
        super().__init__(scan_config)

        self.acquisition_channels = set(ch for ch, _, _ in scan_config.channel_map.values())
        self.offset = 0.0

    def get_channel_data(self) -> dict[str, np.ndarray]:

        raw = {}

        for i, ch_name in enumerate(self.acquisition_channels):
            data = np.zeros(self.config.shape)
            n = len(data.flat)
            data.flat = np.linspace(0, 50, n) + np.random.random(n)*10 + i*20
            raw[ch_name] = data

        self.offset = (self.offset + 0.2) % 10

        time.sleep(0.05)

        return raw

    def close(self):
        pass


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
            pulse_gates (Dict[str, float]):
                Gates to pulse during scan with pulse voltage in mV.
                E.g. {'vP1': 10.0, 'vB2': -29.1}
            biasT_corr: correct for biasT by taking data in different order.

        Returns:
            Parameter that can be used as input in a scan/measurement functions.
        """
        config = self.get_config1D(gate, swing, n_pt, t_measure, pulse_gates, biasT_corr)

        return _FastScanParameter(config)

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
        config = self.get_config2D(
            gate1, swing1, n_pt1,
            gate2, swing2, n_pt2,
            t_measure, pulse_gates, biasT_corr)

        return _FastScanParameter(config)



def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer, channels,
                           dig_samplerate=None, iq_mode=None, acquisition_delay_ns=None,
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
    scan_generator = FastScanGenerator(pulse_lib)
    scan_generator.set_digitizer(digitizer)
    scan_generator.configure(acquisition_delay_ns, enabled_markers, line_margin)
    if channel_map:
        scan_generator.set_channel_map(channel_map)
    else:
        scan_generator.set_channels(channels, iq_mode)

    return scan_generator.create_1D_scan(gate, swing, n_pt, t_step, pulse_gates=pulse_gates, biasT_corr=biasT_corr)


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib,
                           digitizer, channels, dig_samplerate=None, iq_mode=None,
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
    scan_generator = FastScanGenerator(pulse_lib)
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
