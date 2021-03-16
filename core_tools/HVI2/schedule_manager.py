from keysight_fpga.sd1.dig_iq import load_iq_image

from core_tools.HVI2.hvi2_schedules import Hvi2Schedules
from core_tools.drivers.M3102A import MODES

class ScheduleMgr():
    pulse_lib = None
    digitisers = None

    schedules = None
    __instance = None
    
    def __new__(cls, *args, **kwargs):
        if ScheduleMgr.__instance is None:
            ScheduleMgr.__instance = object.__new__(cls)
        return ScheduleMgr.__instance

    def __init__(self, pulse_lib=None, digitisers=None, markers=[]):
        if self.pulse_lib is None:
            self.pulse_lib = pulse_lib
            if not isinstance(digitisers, (list, tuple)):
                digitisers = [digitisers]

            self.digitisers = digitisers

            self.schedules =  Hvi2Schedules(self.pulse_lib, self.digitisers)
            self.markers = markers
            for dig in digitisers:
                load_iq_image(dig.SD_AIN)

    def video_mode(self):
        for dig in self.digitisers:
            dig.set_acquisition_mode(MODES.AVERAGE)
        return self.schedules.get_video_mode(MODES.AVERAGE, hvi_queue_control=True,  trigger_out=True, enable_markers=self.markers)

    def single_shot(self, n_triggers):
        return self.schedules.get_single_shot(MODES.AVERAGE, n_triggers=n_triggers, hvi_queue_control=True, trigger_out=True)

    def single_shot_raw(self, n_triggers):
        return self.schedules.get_single_shot(MODES.NORMAL, n_triggers=n_triggers, hvi_queue_control=True, trigger_out=True)

    def __check_init(self):
        if self.schedules is None:
            raise ValueError('ScheduleMgr is not initialized. Please run in init.')
