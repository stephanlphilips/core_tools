import logging

from pulse_lib.schedule.hardware_schedule import HardwareSchedule

from .hvi2_schedule_extensions import add_extensions

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer
import keysightSD1 as SD1
import uuid

logger = logging.getLogger(__name__)

class Hvi2Schedule(HardwareSchedule):
    verbose = False

    def __init__(self, hardware, script):
        self.hardware = hardware
        self.script = script
        self.extensions = add_extensions
        self.hvi_system = None
        self.hvi_sequence = None
        self.hvi_exec = None
        self._is_loaded = False
        self._might_be_loaded = False
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

    def reconfigure_modules(self):
        for awg in self.hardware.awgs:
            for ch in range(1, 5):
                awg.awg_stop(ch)
                # rewrite amplitude and offset bypassing cache.
                amplitude = awg._settings_cache['amplitude'][ch]
                if amplitude is not None:
                    awg._settings_cache['amplitude'][ch] = None
                    awg.set_channel_amplitude(amplitude, ch)
                offset = awg._settings_cache['offset'][ch]
                if offset is not None:
                    awg._settings_cache['offset'][ch] = None
                    awg.set_channel_offset(offset, ch)

                awg.set_channel_wave_shape(SD1.SD_Waveshapes.AOU_AWG, ch)
                awg.awg_queue_config(ch, SD1.SD_QueueMode.CYCLIC)
        for dig in self.hardware.digitizers:
            dig.daq_stop_multiple(0b1111)
            dig.daq_flush_multiple(0b1111)

    def compile(self):
        logger.info(f"Build HVI2 schedule with script '{self.script.name}'")
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
            logger.debug(f"Script '{self.script.name}':\n" + self.sequencer.describe())

        try:
            self.hvi_exec = self.sequencer.compile()
        except:
            logger.error(f"Exception in compilation of '{self.script.name}'", exc_info=True)
            raise

    def is_loaded(self):
        return self._is_loaded

    def load(self):
        if self._is_loaded:
            logger.info(f'HVI2 schedule already loaded')
            return

        self.hardware.release_schedule()
        self.configure_modules()

        if self.hvi_exec is None:
            self.compile()

        logger.info(f"Load HVI2 schedule with script '{self.script.name}' (id:{self.hvi_id})")
        self.hardware.set_schedule(self)
        self._might_be_loaded = True
        self.hvi_exec.load()
        if self.hvi_exec.is_running():
            logger.warning(f'HVI running after load; attempting to stop HVI and modules')
            self.hvi_exec.stop()
            self.reconfigure_modules()
            if self.hvi_exec.is_running():
                logger.eror(f'Still Running after stop')
        self._is_loaded = True

    def unload(self):
        if not self.hvi_exec:
            return
        if self._is_loaded:
            self.script.stop(self.hvi_exec)
            self._is_loaded = False
        if self._might_be_loaded:
            logger.info(f"Unload HVI2 schedule with script'{self.script.name}' (id:{self.hvi_id})")
            self.hvi_exec.unload()
            self._might_be_loaded = False
            self.hardware.release_schedule()

    def is_running(self):
        return self.hvi_exec.is_running()

    def start(self, waveform_duration, n_repetitions, sequence_variables):
        hvi_params = {**self.schedule_parms, **sequence_variables}
        if self.verbose:
            logger.debug(f'start: {hvi_params}')
        self.script.start(self.hvi_exec, waveform_duration, n_repetitions, hvi_params)

    def stop(self):
        self.script.stop(self.hvi_exec)

    def close(self):
        self.unload()
        self.hvi_exec = None

    def __del__(self):
        if self._is_loaded:
            try:
                logger.warning(f'Automatic close of Hvi2Schedule in __del__()')
#                self.unload()
            except:
                logger.error(f'Exception unloading HVI', exc_info=True)