import logging
from typing import List, Union
from collections.abc import Iterable

from pulse_lib.base_pulse import pulselib
from pulse_lib.schedule.hardware_schedule import HardwareSchedule

from core_tools.drivers.M3102A import SD_DIG

from .scheduler_hardware import default_scheduler_hardware
from .hvi2_single_shot import Hvi2SingleShot
from .hvi2_video_mode import Hvi2VideoMode
from .hvi2_continuous_mode import Hvi2ContinuousMode
from .hvi2_schedule import Hvi2Schedule

logger = logging.getLogger(__name__)


# TODO: make scheduler into QCoDeS instrument. This solves closing and reloading issues.
class Hvi2ScheduleLoader(HardwareSchedule):
    schedule_cache = {}
    script_classes = {
            Hvi2VideoMode,
            Hvi2SingleShot,
            Hvi2ContinuousMode,
        }

    def __init__(self, pulse_lib: pulselib, script_name: str,
                 digitizers: Union[None, SD_DIG, List[SD_DIG]] = None,
                 acquisition_delay_ns=None, switch_los=False, enabled_los=None):
        '''
        Args:
            acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
            switch_los (bool): whether to switch LOs on/off
            enabled_los (List[List[Tuple[str,int,int]]):
                per switch interval list with (awg, channel, active local oscillator).
                if None, then all los are switched on/off.
        '''
        self._pulse_lib = pulse_lib
        self._script_name = script_name
        self._hardware = self._update_hardware(pulse_lib, digitizers)
        self._configuration = None
        self._schedule = None
        self._acquisition_delay_ns = acquisition_delay_ns
        self._switch_los = switch_los
        self._enabled_los = enabled_los

    @property
    def script_name(self):
        return self._script_name

    def _update_hardware(self, pulse_lib, digitizers):
        hw = default_scheduler_hardware
        for awg in pulse_lib.awg_devices.values():
            if awg not in hw.awgs:
                hw.add_awg(awg)

        if hasattr(pulse_lib, 'digitizers'):
            for digitizer in pulse_lib.digitizers.values():
                if digitizer not in hw.digitizers:
                    hw.add_digitizer(digitizer)

        if digitizers is not None:
            if not isinstance(digitizers, Iterable):
                digitizers = [digitizers]

            for digitizer in digitizers:
                if digitizer not in hw.digitizers:
                    hw.add_digitizer(digitizer)
        return hw

    @staticmethod
    def close_all():
        n_schedules = len(Hvi2ScheduleLoader.schedule_cache)
        if n_schedules > 0:
            logger.info(f'Closing and deleting {n_schedules} schedules')
        for entry in Hvi2ScheduleLoader.schedule_cache.values():
            entry.close()
        Hvi2ScheduleLoader.schedule_cache = {}

    def set_schedule_parameters(self, **kwargs):
        self._schedule_parameters = kwargs

    def _get_n_measurements(self, hvi_params):
        n = 0
        while True:
            if n == 0 and 'dig_wait' in hvi_params:
                n += 1
            elif f'dig_wait_{n+1}' in hvi_params or f'dig_trigger_{n+1}' in hvi_params:
                n += 1
            else:
                return n

    def set_configuration(self, hvi_params, n_waveforms):
        conf = {}
        conf['script_name'] = self._script_name
        conf['n_triggers'] = self._get_n_measurements(hvi_params)

        # If hvi queue control is not used, then do not add the information.
        # Otherwise a new schedule will be generated when the number of waveforms changes.
        uses_hvi_queue_control = any(getattr(awg, 'hvi_queue_control', False)
                                     for awg in self._pulse_lib.awg_devices.values())
        conf['n_waveforms'] = n_waveforms if uses_hvi_queue_control else -1

        acquisition_delay_ns = hvi_params.get('acquisition_delay_ns', self._acquisition_delay_ns)
        if acquisition_delay_ns is not None:
            # only add if configured
            conf['acquisition_delay_ns'] = acquisition_delay_ns

        for awg_name, awg in self._pulse_lib.awg_devices.items():
            awg_conf = {}
            awg_conf['hvi_queue_control'] = getattr(awg, 'hvi_queue_control', False)
            awg_conf['sequencer'] = hvi_params.get(f'use_awg_sequencers_{awg_name}', hasattr(awg, 'get_sequencer'))
            # 'active_los' is List[Tuple[channel, LO]] # @@@ Tuple?
            awg_conf['active_los'] = getattr(awg, 'active_los', {})
            awg_conf['switch_los'] = hvi_params.get('switch_los', self._switch_los)
            enabled_los = hvi_params.get('enabled_los', self._enabled_los)
            if enabled_los:
                enabled_los_awg = []
                for i, enabled_los_i in enumerate(enabled_los):
                    enabled_i = []
                    enabled_los_awg.append(enabled_i)
                    for name, ch, lo in enabled_los_i:
                        if awg_name == name:
                            enabled_i.append((ch, lo))
                awg_conf['enabled_los'] = enabled_los_awg
            else:
                awg_conf['enabled_los'] = []
            awg_video_mode_los = []
            for name, ch, lo in hvi_params.get('video_mode_los', []):
                if awg_name == name:
                    awg_video_mode_los.append((ch, lo))
            awg_conf['video_mode_los'] = awg_video_mode_los
            awg_conf['trigger_out'] = False  # correct value will be set below
            conf[awg.name] = awg_conf

        for marker_channel in self._pulse_lib.marker_channels.values():
            # TODO: Do not use internals of pulse_lib
            if marker_channel.channel_number == 0:
                awg = self._pulse_lib.awg_devices[marker_channel.module_name]
                conf[awg.name]['trigger_out'] = True

        for dig in self._hardware.digitizers:
            dig_conf = {}
            modes = {ch: dig.get_channel_acquisition_mode(ch) for ch in dig.active_channels}
            dig_conf['all_ch'] = list(modes.keys())
            dig_conf['raw_ch'] = [channel for channel, mode in modes.items() if mode == 0]
            dig_conf['ds_ch'] = [channel for channel, mode in modes.items() if mode != 0]
            dig_conf['iq_ch'] = [channel for channel, mode in modes.items() if mode in [2, 3]]
            dig_conf['sequencer'] = hvi_params.get(f'use_digitizer_sequencers_{dig.name}', hasattr(dig, 'get_sequencer'))
            if f'dig_trigger_channels_{dig.name}' in hvi_params:
                dig_conf['trigger_ch'] = hvi_params[f'dig_trigger_channels_{dig.name}']

            conf[dig.name] = dig_conf

        if self._configuration != conf:
            if self._schedule:
                self._schedule.unload()
            self._schedule = None
            self._configuration = conf

    def load(self):
        if not self._configuration:
            logger.warning('Cannot load schedule without configuration')
            return
        if not self._schedule:
            self._get_schedule()
        self._schedule.load()

    def unload(self):
        if self._schedule:
            self._schedule.unload()

    def start(self, waveform_duration, n_repetitions, sequence_params):
        self.load()
        self._schedule.set_schedule_parameters(**self._schedule_parameters)
        self._schedule.start(waveform_duration, n_repetitions, sequence_params)

    def is_running(self):
        return self._schedule and self._schedule.is_running()

    def stop(self):
        if self._schedule:
            self._schedule.stop()

    def close(self):
        if self._schedule:
            self._schedule.close()
        self._schedule = None

    def _get_script(self):
        for script_class in Hvi2ScheduleLoader.script_classes:
            if script_class.name == self._script_name:
                logger.info(f'Create {self._script_name} {self._configuration}')
                return script_class(self._configuration)
        raise ValueError(f"Unknown script '{self._script_name}'")

    def _get_schedule(self):
        script_conf = str(self._configuration)
        if script_conf not in Hvi2ScheduleLoader.schedule_cache:
            self._schedule = Hvi2Schedule(self._hardware, self._get_script())
            Hvi2ScheduleLoader.schedule_cache[script_conf] = self._schedule

        self._schedule = Hvi2ScheduleLoader.schedule_cache[script_conf]
