from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from qcodes import MultiParameter

from .iq_modes import get_channel_map, get_channel_map_dig_4ch, add_channel_map_units


@dataclass
class ScanConfigBase:
    t_measure: float
    pulse_gates: dict[str, float]
    channel_map: dict[str, tuple[int, Callable[[np.ndarray], np.ndarray], str]]
    iq_mode: str
    biasT_corr: bool
    acquisition_delay_ns: int
    line_margin: int
    enabled_markers: list[str]

    # @@@ Add extra snapshot, e.g. from Shuttling...
    def snapshot(self):
        channel_map_snapshot = {}
        for name, mapping in self.channel_map.items():
            channel_map_snapshot[name] = {
                "channel": mapping[0],
                "func": getattr(mapping[1], "__name__", str(mapping[1])),
                "unit": mapping[2],
                }
        return dict(
            t_measure=dict(label="t_measure", value=self.t_measure, unit="ns"),
            channel_map=channel_map_snapshot,
            biasT_corr=self.biasT_corr,
            iq_mode=self.iq_mode,
            acquisition_delay=dict(
                label="acquisition_delay",
                value=self.acquisition_delay_ns,
                unit="ns"),
            enabled_markers=self.enabled_markers,
            pulse_gates={
                name: dict(label=name, value=value, unit="mV")
                for name, value in self.pulse_gates.items()
                },
            line_margin=self.line_margin,
            )


@dataclass
class ScanConfig1D(ScanConfigBase):
    gate: str
    swing: float
    n_pt: int
    n_ptx: int = field(init=False)
    vpx: float = field(init=False)
    voltages_sp: np.ndarray = field(init=False)
    voltages: np.ndarray = field(init=False)

    def __post_init__(self):
        vp = self.swing/2
        n_ptx = self.n_pt + 2*self.line_margin
        self.n_ptx = n_ptx
        vpx = vp * (self.n_ptx-1)/(self.n_pt-1)
        self.vpx = vpx

        # set up sweep voltages (get the right order, to compensate for the biasT).
        self.voltages_sp = np.linspace(-vp, vp, self.n_pt)
        voltages_x = np.linspace(-vpx, vpx, n_ptx)
        if self.biasT_corr:
            m = (n_ptx+1)//2
            voltages = np.zeros(n_ptx)
            voltages[::2] = voltages_x[:m]
            voltages[1::2] = voltages_x[m:][::-1]
        else:
            voltages = voltages_x
        self.voltages = voltages

    @property
    def names(self):
        return (self.gate, )

    @property
    def shape(self):
        return (self.n_pt, )

    @property
    def setpoints(self):
        return (tuple(self.voltages_sp), )

    def snapshot(self):
        snapshot_base = super().snapshot()
        snapshot_1D = dict(
            gate=self.gate,
            swing=dict(label="swing", value=self.swing, unit="mV"),
            n_pt=self.n_pt,
            )
        return snapshot_1D | snapshot_base


@dataclass
class ScanConfig2D(ScanConfigBase):
    gate1: str
    swing1: float
    n_pt1: int
    gate2: str
    swing2: float
    n_pt2: int
    n_ptx: int = field(init=False)
    vpx: float = field(init=False)
    voltages1_sp: np.ndarray = field(init=False)
    voltages2_sp: np.ndarray = field(init=False)
    voltages2: np.ndarray = field(init=False)

    def __post_init__(self):
        vp1 = self.swing1/2
        vp2 = self.swing2/2
        self.vp2 = vp2

        self.voltages1_sp = np.linspace(-vp1, vp1, self.n_pt1)
        self.voltages2_sp = np.linspace(-vp2, vp2, self.n_pt2)
        voltages2_sp = self.voltages2_sp

        self.n_ptx = self.n_pt1 + 2*self.line_margin
        vpx = vp1 * (self.n_ptx-1)/(self.n_pt1-1)
        self.vpx = vpx

        if self.biasT_corr:
            m = (self.n_pt2+1)//2
            voltages2 = np.zeros(self.n_pt2)
            voltages2[::2] = voltages2_sp[:m]
            voltages2[1::2] = voltages2_sp[m:][::-1]
        else:
            voltages2 = voltages2_sp
        self.voltages2 = voltages2

    @property
    def names(self):
        return (self.gate2, self.gate1)

    @property
    def shape(self):
        return (self.n_pt2, self.n_pt1)

    @property
    def setpoints(self):
        return (tuple(self.voltages2_sp), (tuple(self.voltages1_sp),)*self.n_pt2)

    def snapshot(self):
        snapshot_base = super().snapshot()
        snapshot_2D = dict(
            gate1=self.gate1,
            swing1=dict(label="swing1", value=self.swing1, unit="mV"),
            n_pt1=self.n_pt1,
            gate2=self.gate2,
            swing2=dict(label="swing2", value=self.swing2, unit="mV"),
            n_pt2=self.n_pt2,
            )
        return snapshot_2D | snapshot_base


class FastScanParameterBase(MultiParameter):

    def __init__(self, scan_config: ScanConfigBase):
        self.config = scan_config
        self.channel_names = tuple(self.config.channel_map.keys())

        units = tuple(unit for _, _, unit in self.config.channel_map.values())

        n_out_ch = len(self.channel_names)
        axes_names = self.config.names
        super().__init__(name="fast_scan",
                         names=self.channel_names,
                         shapes=tuple([self.config.shape]*n_out_ch),
                         labels=self.channel_names,
                         units=units,
                         setpoints=tuple([self.config.setpoints]*n_out_ch),
                         setpoint_names=tuple([axes_names]*n_out_ch),
                         setpoint_labels=tuple([axes_names]*n_out_ch),
                         setpoint_units=(("mV", )*len(axes_names), )*n_out_ch,
                         docstring='Fast scan parameter (video mode)')

    @abstractmethod
    def get_channel_data(self) -> dict[str, np.ndarray]:
        """Starts scan and retrieves data.

        Returns:
            dictionary with per channel real or complex data in 1D ndarray.
        """
        raise NotImplementedError("get_channel_data should be implemented")

    def get_raw(self):
        raw = self.get_channel_data()
        # Reshape and reorder data for bias-T correction
        shape = self.config.shape
        for name in raw:
            ch_data = raw[name].reshape(shape)
            if self.config.biasT_corr:
                data = np.zeros(shape, dtype=ch_data.dtype)
                data[:len(ch_data[::2])] = ch_data[::2]
                data[len(ch_data[::2]):] = ch_data[1::2][::-1]
                raw[name] = data
            else:
                raw[name] = ch_data

        # post-process data
        data_out = []
        for ch, func, _ in self.config.channel_map.values():
            ch_data = raw[ch]
            data_out.append(func(ch_data))

        return tuple(data_out)

    def snapshot_base(self,
                      update: bool | None = True,
                      params_to_skip_update: Sequence[str] | None = None
                      ) -> dict[any, any]:
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot.update({"parameters": self.config.snapshot()})
        return snapshot

    @abstractmethod
    def recompile(self):
        raise NotImplementedError("recompile is not implemented")

    def restart(self):
        pass

    def stop(self):
        self.close()

    @abstractmethod
    def close(self):
        """Closes parameter for further usages.
        Resources will be released.
        """
        raise NotImplementedError("close should be implemented")


class FastScanGeneratorBase:
    def __init__(self):
        self._pulse_lib = None
        self._digitizer = None
        self.iq_mode = None
        self.acquisition_delay_ns: float = 500
        self.enabled_markers: list[str] = []
        self.line_margin: int = 0
        self._channel_map: dict[str, tuple[int, Callable[[np.ndarray], np.ndarray], str]] = {}

    def set_pulse_lib(self, pulse_lib):
        """
        Args:
            pulse_lib: pulse lib object used to generate pulses.
        """
        self._pulse_lib = pulse_lib

    @property
    def pulse_lib(self):
        return self._pulse_lib

    def set_digitizer(self, digitizer):
        """
        Set digitizer object.
        This call is only needed if digitizer is not configured in pulse-lib.

        Args:
            digitizer: digitizer object used to configure acquisition

        Note:
            method is used by liveplotting.
        """
        self._digitizer = digitizer

    @property
    def digitizer(self):
        return self._digitizer

    def set_iq_mode(self, iq_mode: str | None):
        self.iq_mode = iq_mode

    def set_channels(
            self,
            channels: list[str] | list[int] | None = None,
            iq_mode: str | None = "I",
            ) -> None:
        """
        Args:
            channels:
                [optional] digitizer channels to read. if not specified all channels will be used.
            iq_mode:
                [optional] for digitizer IQ channels this parameter specifies how the
                complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'.
                If None defaults to "I".
        """
        self.iq_mode = iq_mode
        if self.digitizer is None:
            channel_map = get_channel_map(self.pulse_lib, iq_mode, channels)
        else:
            channel_map = get_channel_map_dig_4ch(iq_mode, channels)
        self._channel_map = channel_map

    def set_channel_map(
            self,
            channel_map: dict[str, tuple[int, Callable[[np.ndarray], np.ndarray]]],
            ) -> None:
        """
        Args:
            channel_map:
                Mapping of names to digitizer channels, function and [optional] unit.
                E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
                The default channel_map is:
                    {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
        """
        # copy with units.
        self._channel_map = add_channel_map_units(channel_map)

    @property
    def channel_map(self) -> dict[str, tuple[int, Callable[[np.ndarray], np.ndarray], str]]:
        return self._channel_map

    def configure(
            self,
            acquisition_delay_ns: float = 500,
            enabled_markers: list[str] = [],
            line_margin: int = 0,
            ):
        """
        Args:
            acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
            enabled_markers (List[str]): marker channels to enable during scan
            line_margin (int):
                Number of points to add to sweep 1 to mask transition effects due to voltage step.
                The points are added to begin and end for symmetry (bias-T).
        """
        self.acquisition_delay_ns = acquisition_delay_ns
        self.enabled_markers = enabled_markers
        self.line_margin = int(line_margin)

    def get_config1D(
            self,
            gate: str, swing: float, n_pt: int, t_measure: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = False,
            ) -> ScanConfig1D:
        return ScanConfig1D(
            t_measure, pulse_gates, self.channel_map, self.iq_mode, biasT_corr,
            self.acquisition_delay_ns, self.line_margin, self.enabled_markers,
            gate, swing, n_pt)

    def get_config2D(
            self,
            gate1: str, swing1: float, n_pt1: int,
            gate2: str, swing2: float, n_pt2: int,
            t_measure: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = False,
            ) -> ScanConfig2D:
        return ScanConfig2D(
            t_measure, pulse_gates, self.channel_map, self.iq_mode, biasT_corr,
            self.acquisition_delay_ns, self.line_margin, self.enabled_markers,
            gate1, swing1, n_pt1,
            gate2, swing2, n_pt2,
            )

    @abstractmethod
    def create_1D_scan(
            self,
            gate: str, swing: float, n_pt: int, t_step: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = False,
            ) -> FastScanParameterBase:
        """Creates 1D fast scan parameter.

        Args:
            gate: gates to sweep.
            swing: swing to apply on the AWG gate. [mV]
            n_pt: number of points to measure
            t_step: time in ns to measure per point. [ns]
            biasT_corr: correct for biasT by taking data in different order.
            channel_map:
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func, unit).
                E.g. {('ch1-I':(1, np.real, 'mV'), 'ch1-Q':(1, np.imag, 'mV'), 'ch3-Amp':(3, np.abs, 'mV'), 'ch3-Phase':(3, np.angle, 'rad')}
                The default channel_map is:
                    {'ch1':(1, np.real, 'mV'), 'ch2':(2, np.real, 'mV'), 'ch3':(3, np.real, 'mV'), 'ch4':(4, np.real, 'mV')}
            pulse_gates (Dict[str, float]):
                Gates to pulse during scan with pulse voltage in mV.
                E.g. {'vP1': 10.0, 'vB2': -29.1}

        Returns:
            Parameter that can be used as input in a scan/measurement functions.
        """
        raise NotImplementedError("create_1D_scan should be implemented")

    @abstractmethod
    def create_2D_scan(self,
            gate1: str, swing1: float, n_pt1: int,
            gate2: str, swing2: float, n_pt2: int,
            t_step: float,
            pulse_gates: dict[str, float] = {},
            biasT_corr: bool = True,
            ) -> FastScanParameterBase:
        """Creates 2D fast scan parameter.

        Args:
            gates1 (str) : gate that you want to sweep on x axis.
            swing1 (double) : swing to apply on the AWG gates.
            n_pt1 (int) : number of points to measure (current firmware limits to 1000)
            gate2 (str) : gate that you want to sweep on y axis.
            swing2 (double) : swing to apply on the AWG gates.
            n_pt2 (int) : number of points to measure (current firmware limits to 1000)
            t_step (double) : time in ns to measure per point.
            biasT_corr (bool) : correct for biasT by taking data in different order.
            pulse_gates (Dict[str, float]):
                Gates to pulse during scan with pulse voltage in mV.
                E.g. {'vP1': 10.0, 'vB2': -29.1}

        Returns:
            Parameter that can be used as input in a scan/measurement functions.
        """
        raise NotImplementedError("create_1D_scan should be implemented")
