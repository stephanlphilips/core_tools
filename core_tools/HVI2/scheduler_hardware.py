
class SchedulerHardware:
    '''
    Collection of awgs and digitizers used with schedules.
    '''
    def __init__(self):
        self.active_schedule = None
        self.awgs = []
        self.digitizers = []

    def add_awg(self, awg):
        self.awgs.append(awg)

    def add_awgs(self, awgs):
        for awg in awgs:
            self.add_awg(awg)

    def add_digitizer(self, digitizer):
        self.digitizers.append(digitizer)

    def add_digitizers(self, digitizers):
        for digitizer in digitizers:
            self.add_digitizer(digitizer)

    def set_schedule(self, schedule):
        self.release_schedule()
        self.active_schedule = schedule

    def release_schedule(self):
        if self.active_schedule is not None:
            schedule = self.active_schedule
            self.active_schedule = None
            schedule.unload()

    def close(self):
        self.release_schedule()

default_scheduler_hardware = SchedulerHardware()
