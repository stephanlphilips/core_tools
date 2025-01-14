"""
@author: sdesnoo
"""

from pulse_lib.base_pulse import pulselib

from .hvi2_schedule_loader import Hvi2ScheduleLoader

from core_tools.drivers.M3102A import SD_DIG


class Hvi2Schedules:

    def __init__(self, pulse_lib: pulselib, digitizers: SD_DIG | list[SD_DIG]):
        self.schedules = {}
        self._pulselib = pulse_lib
        self._digitizers = digitizers

    def get_single_shot(self, digitizer_mode=None, dig_channel_modes=None, awg_channel_los=[],
                        n_triggers=1, switch_los=False, enabled_los=None, hvi_queue_control=False,
                        trigger_out=False, n_waveforms=1, acquisition_delay_ns=0):
        '''
        Return a (cached) single shot schedule.
        Args:
            dig_channel_modes (Dict[str,Dict[int,int]]): per digitizer and channel the mode.
            awg_channel_los (List[Tuple[str,int,int]]): list with (AWG, channel, active local oscillator).
            n_trigger (int): number of measurement and lo switching intervals.
            switch_los (bool): switch los on/off with measurements
            enabled_los (List[List[Tuple[str, int,int]]): per switch interval list with (AWG, channel, active local oscillator).
                if None, then all los are switched on/off.
            hvi_queue_control (bool): if True enables waveform queueing by hvi script.
            n_waveforms (int): number of waveforms per channel (only applies when hvi_queue_control=True)
            trigger_out (bool): if True enables markers via Trigger Out channel.
            acquisition_delay_ns (int): time in ns between AWG output change and digitizer acquisition start.
            hvi_queue_control (bool): if True enables waveform queueing by hvi script.
        '''
        print('Hvi2Schedules is deprecated. Use Hvi2ScheduleLoader')
        return Hvi2ScheduleLoader(
            self._pulselib, 'SingleShot',
            self._digitizers,
            acquisition_delay_ns=acquisition_delay_ns,
        )

    def get_video_mode(self, digitizer_mode: int, awg_channel_los=None, acquisition_delay_ns=500,
                       hvi_queue_control=False, trigger_out=False, enable_markers=[]):
        '''
        Return a (cached) video mode schedule.
        Args:
            digitizer_mode (int): digitizer modes: 0 = direct, 1 = averaging/downsampling, 2,3 = IQ demodulation
            awg_channel_los (List[Tuple[str,int,int]]): list with (AWG, channel, active local oscillator).
            acquisition_delay_ns (int):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
            hvi_queue_control (bool): if True enables waveform queueing by hvi script.
            enable_markers (List[str]): marker channels to enable during sweep.
            trigger_out (bool): if True enables markers via Trigger Out channel.

        For video mode the digitizer measurement should return 1 value per trigger.
        '''
        print('Hvi2Schedules is deprecated. Use Hvi2ScheduleLoader')
        return Hvi2ScheduleLoader(
            self._pulselib,
            'SingleShot',
            self._digitizers,
            acquisition_delay_ns=acquisition_delay_ns
        )

    def clear(self):
        Hvi2ScheduleLoader.close_all()

    def close(self):
        self.clear()
