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

    def __init__(self, pulse_lib=None, digitisers=None, markers=[]):
        if self.pulse_lib is None:
            self.pulse_lib = pulse_lib
            if not isinstance(digitisers, (list, tuple)):
                digitisers = [digitisers]

            self.digitisers = digitisers
            self.markers = markers

            for dig in digitisers:
                load_iq_image(dig.SD_AIN)

    def video_mode(self):
        for dig in self.digitisers:
            dig.set_acquisition_mode(MODES.AVERAGE)
        
        schedule = Hvi2ScheduleLoader(self.pulse_lib, 'VideoMode', self.digitisers) #acquisition_delay_ns=1000# Add acquisition delay if video mode is too fast for resonator

        return schedule

    def single_shot(self, n_triggers):
        schedule =  Hvi2ScheduleLoader(self.pulse_lib, 'SingleShot', self.digitisers)

        return schedule
        
    def __check_init(self):
        if self.pulse_lib is None:
            raise ValueError('ScheduleMgr is not initialized. Please run in init.')
