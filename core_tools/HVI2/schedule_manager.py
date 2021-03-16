from keysight_fpga.sd1.dig_iq import load_iq_image

from .hvi2_schedule_loader import Hvi2ScheduleLoader
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

    def __init__(self, pulse_lib=None, digitisers=None):
        if self.pulse_lib is None:
            self.pulse_lib = pulse_lib
            if not isinstance(digitisers, (list, tuple)):
                digitisers = [digitisers]

            self.digitisers = digitisers


            for dig in digitisers:
                load_iq_image(dig.SD_AIN)

    def single_shot(self, n_triggers):
        schedule =  Hvi2ScheduleLoader(self.pulse_lib, 'SingleShot', self.digitisers)
        return schedule
        
    def __check_init(self):
        if self.pulse_lib is None:
            raise ValueError('ScheduleMgr is not initialized. Please run in init.')
