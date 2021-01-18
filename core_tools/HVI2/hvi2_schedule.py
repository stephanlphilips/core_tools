# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:49:54 2020

@author: sdesnoo
"""
import logging

from pulse_lib.schedule.hardware_schedule import HardwareSchedule

from projects.keysight_hvi2.system import HviSystem
from projects.keysight_hvi2.sequencer import HviSequencer
import keysightSD1 as SD1
import uuid

class Hvi2Schedule(HardwareSchedule):
    verbose = True

    def __init__(self, hardware, script, extensions=None):
        self.hardware = hardware
        self.script = script
        self.extensions = extensions
        self.hvi_system = None
        self.hvi_sequence = None
        self.hvi_exec = None
        self._is_loaded = False
        self.schedule_parms = {}
        self.hvi_id = uuid.uuid4()

    def set_schedule_parameters(self, **kwargs):
        for key,value in kwargs.items():
            self.schedule_parms[key] = value

    def configure_modules(self):
        for awg in self.hardware.awgs:
            for ch in range(1, 5):
                awg.awg_stop(ch)
                awg.set_channel_wave_shape(SD1.SD_Waveshapes.AOU_AWG, ch)
                awg.awg_queue_config(ch, SD1.SD_QueueMode.CYCLIC)
        for dig in self.hardware.digitizers:
            dig.daq_stop_multiple(0b1111)
            dig.daq_flush_multiple(0b1111)

    def compile(self):
        logging.info(f"Compile HVI2 schedule with script '{self.script.name}'")
        hvi_system = HviSystem()
        for awg in self.hardware.awgs:
            sd_aou = awg.awg
            hvi_system.add_awg(sd_aou, awg.name)
        for dig in self.hardware.digitizers:
            sd_ain = dig.SD_AIN
            hvi_system.add_digitizer(sd_ain, dig.name)
        self.hvi_system = hvi_system

        if self.extensions is not None:
            self.extensions(hvi_system)

        sequencer = HviSequencer(hvi_system)
        self.sequencer = sequencer
        self.script.sequence(sequencer, self.hardware)
        if self.verbose:
            logging.debug(f"Script '{self.script.name}':\n" + self.sequencer.describe())

        try:
            self.hvi_exec = self.sequencer.compile()
        except:
            logging.error(f'Exception in compilation', exc_info=True)
            logging.error(f"Compilation '{self.script.name}' failed:\n" + self.sequencer.describe())

    def is_loaded(self):
        return self._is_loaded

    def load(self):
        if self._is_loaded:
            logging.warning(f'HVI2 schedule already loaded')
            return
        if self.hvi_exec is None:
            self.compile()

        logging.info(f"Load HVI2 schedule with script '{self.script.name}'")
        self.hardware.release_schedule()
        self.configure_modules()
        self.hvi_exec.load()
        if self.hvi_exec.is_running():
            logging.warning(f'HVI running after load: stop HVI and modules')
            self.hvi_exec.stop()
            self.configure_modules()
            if self.hvi_exec.is_running():
                logging.eror(f'Still Running after stop')
        self.hardware.set_schedule(self)
        self._is_loaded = True

    def unload(self):
        if not self._is_loaded:
            return
        self.script.stop(self.hvi_exec)
        logging.info(f"Unload HVI2 schedule with script '{self.script.name}'")
        self.hvi_exec.unload()
        self._is_loaded = False
        self.hardware.release_schedule()

    def is_running(self):
        return self.hvi_exec.is_running()

    def start(self, waveform_duration, n_repetitions, sequence_variables):
        hvi_params = {**self.schedule_parms, **sequence_variables}
        if self.verbose:
            logging.debug(f'start: {hvi_params}')
        self.script.start(self.hvi_exec, waveform_duration, n_repetitions, hvi_params)

    def close(self):
        self.unload()


    def __del__(self):
        if self._is_loaded:
            try:
                logging.warning(f'Automatic close of Hvi2Schedule in __del__()')
                self.unload()
                raise Exception('boom')
            except:
                logging.error(f'Exception unloading HVI', exc_info=True)
