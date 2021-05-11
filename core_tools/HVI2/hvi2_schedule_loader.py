"""
@author: sdesnoo
"""
import logging
from typing import List, Union

from pulse_lib.base_pulse import pulselib
from pulse_lib.schedule.hardware_schedule import HardwareSchedule

from core_tools.drivers.M3102A import SD_DIG


from .scheduler_hardware import default_scheduler_hardware
from .hvi2_single_shot import Hvi2SingleShot
from .hvi2_video_mode import Hvi2VideoMode
from .hvi2_schedule import Hvi2Schedule

# TODO: make scheduler into QCoDeS instrument. This solves closing and reloading issues.
class Hvi2ScheduleLoader(HardwareSchedule):
    schedule_cache = {}
    script_classes = {
            Hvi2VideoMode,
            Hvi2SingleShot
        }

    def __init__(self, pulse_lib:pulselib, script_name:str, digitizers:Union[None, SD_DIG,List[SD_DIG]]=None,
                 acquisition_delay_ns=None, switch_los=False, enabled_los=None):
        '''
        Args:
            acquisition_delay_ns (float):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
            switch_los (bool): whether to switch LOs on/off
            enabled_los (List[List[Tuple[str,int,int]]): per switch interval list with (awg, channel, active local oscillator).
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
            if isinstance(digitizers, SD_DIG):
                digitizers = [digitizers]

            for digitizer in digitizers:
                if digitizer not in hw.digitizers:
                    hw.add_digitizer(digitizer)
        return hw

    @staticmethod
    def close_all():
        n_schedules = len(Hvi2ScheduleLoader.schedule_cache)
        if n_schedules > 0:
            logging.info(f'Closing and deleting {n_schedules} schedules')
        for entry in Hvi2ScheduleLoader.schedule_cache.values():
            entry.close()
        Hvi2ScheduleLoader.schedule_cache = {}

    def set_schedule_parameters(self, **kwargs):
        self._schedule_parameters = kwargs

    def _get_n_measurements(self, hvi_params):
        n = 0
        while(True):
            if n == 0 and 'dig_wait' in hvi_params:
                n += 1
            elif f'dig_wait_{n+1}' in hvi_params or f'dig_trigger_{n+1}' in hvi_params:
                n += 1
            else:
                return n

    # TODO: @@@ change hvi_params to measurements
    def set_configuration(self, hvi_params, n_waveforms):
        conf = {}
        conf['script_name'] = self._script_name
        conf['n_waveforms'] = n_waveforms
        conf['n_triggers'] = self._get_n_measurements(hvi_params)
#        conf['n_triggers'] = len(measurements)
        if self._acquisition_delay_ns is not None:
            # only add if configured
            conf['acquisition_delay_ns'] = self._acquisition_delay_ns

        for awg_name, awg in self._pulse_lib.awg_devices.items():
            awg_conf = {}
            awg_conf['hvi_queue_control'] = hasattr(awg, 'hvi_queue_control') and awg.hvi_queue_control
            awg_conf['sequencer'] = hasattr(awg, 'get_sequencer')
            # 'active_lost' is List[Typle[channel, LO]]
            awg_conf['active_los'] = awg.active_los if hasattr(awg, 'active_los') else {}
            # TODO: retrieve switch_los en enabled_los from measurements / resonator_channels
            awg_conf['switch_los'] = self._switch_los
            if self._enabled_los:
                enabled_los_awg = []
                for i in range(conf['n_triggers']):
                    enabled_i = []
                    enabled_los_awg.append(enabled_i)
                    for name, ch, lo in self._enabled_los[i]:
                        if awg_name == name:
                            enabled_i.append((ch, lo))
                awg_conf['enabled_los'] = enabled_los_awg
            else:
                awg_conf['enabled_los'] = None
            awg_conf['trigger_out'] = False # correct value will be set below
            conf[awg.name] = awg_conf

        for marker_channel in self._pulse_lib.marker_channels.values():
            # TODO: Do not use internals of pulse_lib
            if marker_channel.channel_number == 0:
                awg = self._pulse_lib.awg_devices[marker_channel.module_name]
                conf[awg.name]['trigger_out'] = True

        for dig in self._hardware.digitizers:
            dig_conf = {}
            modes = {ch:dig.get_channel_acquisition_mode(ch) for ch in dig.active_channels}
            dig_conf['all_ch'] = list(modes.keys())
            dig_conf['raw_ch'] = [channel for channel, mode in modes.items() if mode == 0]
            dig_conf['ds_ch'] = [channel for channel, mode in modes.items() if mode != 0]
            dig_conf['iq_ch'] = [channel for channel, mode in modes.items() if mode in [2,3]]
            dig_conf['sequencer'] = hasattr(dig, 'get_sequencer')
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
            logging.warning('Cannot load schedule without configuration')
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
                logging.info(f'Create {self._script_name} {self._configuration}')
                return script_class(self._configuration)
        raise ValueError(f"Unknown script '{self._script_name}'")

    def _get_schedule(self):
        script_conf = str(self._configuration)
        if script_conf not in Hvi2ScheduleLoader.schedule_cache:
            self._schedule = Hvi2Schedule(self._hardware, self._get_script())
            Hvi2ScheduleLoader.schedule_cache[script_conf] = self._schedule

        self._schedule = Hvi2ScheduleLoader.schedule_cache[script_conf]

