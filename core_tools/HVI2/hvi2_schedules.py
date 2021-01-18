"""
@author: sdesnoo
"""
import os
import logging
from typing import List, Union
from functools import wraps

from pulse_lib.base_pulse import pulselib
from .scheduler_hardware import default_scheduler_hardware

from .hvi2_schedule import Hvi2Schedule
from .hvi2_video_mode import Hvi2VideoMode
from .hvi2_single_shot import Hvi2SingleShot

from projects.keysight_measurement.M3102A import SD_DIG
from projects.keysight_fpga.M3202A_fpga import FpgaLocalOscillatorExtension

from projects.keysight_fpga.fpga_utils import \
    FpgaSysExtension, FpgaLogExtension, get_fpga_image_path, has_fpga_info, FpgaMissingExtension
from projects.keysight_fpga.dig_iq import get_iq_image_filename, is_iq_image_loaded, FpgaDownsamplerExtension


def get_awg_image_filename(module):
    return os.path.join(get_fpga_image_path(module), 'awg_enhanced.k7z')


def add_extensions(hvi_system):
    for awg_engine in hvi_system.get_engines(module_type='awg'):
        awg = awg_engine.module
        if has_fpga_info(awg):
            bitstream = get_awg_image_filename(awg)
            awg_engine.load_fpga_symbols(bitstream)
            awg_engine.add_extension('sys', FpgaSysExtension)
            awg_engine.add_extension('log', FpgaLogExtension)
            awg_engine.add_extension('lo', FpgaLocalOscillatorExtension)
        else:
            for ext in ['sys','log', 'lo']:
                awg_engine.add_extension(ext, FpgaMissingExtension)

    for dig_engine in hvi_system.get_engines(module_type='digitizer'):
        digitizer = dig_engine.module
        if not is_iq_image_loaded(digitizer):
            logging.warn(f'downsampler-iq FPGA image not loaded')

        if has_fpga_info(digitizer):
            dig_bitstream = get_iq_image_filename(digitizer)
            dig_engine.load_fpga_symbols(dig_bitstream)
            dig_engine.add_extension('sys', FpgaSysExtension)
            dig_engine.add_extension('log', FpgaLogExtension)
            dig_engine.add_extension('ds', FpgaDownsamplerExtension)
        else:
            for ext in ['sys','log', 'ds']:
                dig_engine.add_extension(ext, FpgaMissingExtension)


def signature(f):
    '''
    Decorator setting parameter signature on function
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        l = [str(arg) for arg in args[1:]]
        l += [f'{kw}={str(value)}' for kw,value in kwargs.items()]
        s = ','.join(l)
        args[0]._signature = s
        return f(*args, **kwargs)
    return wrapper


class Hvi2Schedules:

    def __init__(self, pulse_lib:pulselib, digitizers:Union[SD_DIG,List[SD_DIG]]):
        self.schedules = {}
        self._update_hardware(pulse_lib, digitizers)


    def _update_hardware(self, pulse_lib, digitizers):
        hw = default_scheduler_hardware
        for awg in pulse_lib.awg_devices.values():
            if awg not in hw.awgs:
                hw.add_awg(awg)

        if isinstance(digitizers, SD_DIG):
            digitizers = [digitizers]

        for digitizer in digitizers:
            if digitizer not in hw.digitizers:
                hw.add_digitizer(digitizer)

    def _get_dig_channel_modes(self, digitizer_mode, dig_channel_modes):
        hw = default_scheduler_hardware

        if dig_channel_modes is None:
            if digitizer_mode is None:
                raise Exception('`digitizer_mode` or `dig_channel_modes` must be specified')
            dig_channel_modes = {}
            for dig in hw.digitizers:
                dig_channel_modes[dig.name] = {ch:digitizer_mode for ch in range(1,5)}

        return dig_channel_modes


    @signature
    def get_single_shot(self, digitizer_mode=None, dig_channel_modes=None, awg_channel_los=[],
                        n_triggers=1, switch_los=False, enabled_los=None):
        dig_channel_modes = self._get_dig_channel_modes(digitizer_mode, dig_channel_modes)

        s = self._signature
        name = f'single_shot({s})'

        if name not in self.schedules:
            logging.info(f'create schedule {name}')
            hw = default_scheduler_hardware
            script = Hvi2SingleShot(dig_channel_modes, awg_channel_los, n_triggers=n_triggers,
                                    switch_los=switch_los, enabled_los=enabled_los)
            schedule = Hvi2Schedule(hw, script, extensions=add_extensions)
            self.schedules[name] = schedule

        return self.schedules[name]


    @signature
    def get_video_mode(self, digitizer_mode:int, awg_channel_los=None):

        s = self._signature
        name = f'video_mode({s})'

        if name not in self.schedules:
            logging.info(f'create schedule {name}')
            hw = default_scheduler_hardware
            schedule = Hvi2Schedule(hw, Hvi2VideoMode(digitizer_mode, awg_channel_los), extensions=add_extensions)
            self.schedules[name] = schedule
        return self.schedules[name]


    def clear(self):
        for schedule in self.schedules.values():
            schedule.close()
        self.schedules = {}

    def close(self):
        self.clear()

