import logging
from dataclasses import dataclass, field
from typing import List

from keysight_fpga.qcodes.M3202A_fpga import FpgaAwgQueueingExtension

'''
Single shot HVI schedule.

The start time of this schedule is 5 to 10 ms faster for repeated starts than the original Hvi2SingleShot schedule,
because it keeps the HVI running and uses a start flag to restart the schedule.
The gain is bigger when more modules are being used.
'''
@dataclass
class DigChannels:
    all_channels: List[int] = field(default_factory=list)
    raw_channels: List[int] = field(default_factory=list)
    iq_channels: List[int] = field(default_factory=list)
    ds_channels: List[int] = field(default_factory=list)


class Hvi2SingleShot():
    verbose = True

    def __init__(self, dig_channel_modes, awg_channel_los=[], n_triggers=1, switch_los=False,
                 enabled_los=None, hvi_queue_control=False):
        '''
        Args:
            dig_channel_modes (Dict[str,Dict[int,int]]): per digitizer and channel the mode.
            awg_channel_los (List[Tuple[str,int,int]]): list with (AWG, channel, active local oscillator).
            n_trigger (int): number of measurement and lo switching intervals.
            switch_los (bool): switch los on/off with measurements
            enabled_los (List[List[Tuple[str, int,int]]): per switch interval list with (AWG, channel, active local oscillator).
                if None, then all los are switched on/off.
            hvi_queue_control (boolean): if True enables waveform queueing by hvi script.
        '''
        self.digitizer_config = {}
        for dig, channels in dig_channel_modes.items():
            dig_channels = DigChannels()
            self.digitizer_config[dig] = dig_channels

            dig_channels.all_channels = list(channels.keys())
            # modes: 0 = direct, 1 = averaging/downsampling, 2,3 = IQ demodulation
            dig_channels.raw_channels = [channel for channel, mode in channels.items() if mode == 0]
            dig_channels.ds_channels = [channel for channel, mode in channels.items() if mode != 0]
            dig_channels.iq_channels = [channel for channel, mode in channels.items() if mode in [2,3]]

        self.started = False
        self.awg_channel_los = awg_channel_los
        self.n_triggers= n_triggers
        self.switch_los = switch_los
        self.enabled_los = enabled_los
        self.hvi_queue_control = hvi_queue_control

        self._n_starts = 0

    @property
    def name(self):
        return 'SingleShot'

    def _get_dig_channel_config(self, dig_seq):
        return self.digitizer_config[dig_seq.engine.alias]

    def _get_awg_channel_los(self, awg_seq):
        result = []
        for awg, channel, lo in self.awg_channel_los:
            if awg == awg_seq.engine.alias:
                result.append((channel, lo))
        return result

    def _get_enabled_channel_los(self, awg_seq, switch_number):
        if self.enabled_los is None:
            return self._get_awg_channel_los(awg_seq)

        result = []
        for awg, channel, lo in self.enabled_los[switch_number]:
            if awg == awg_seq.engine.alias:
                result.append((channel, lo))
        return result

    def _wait_state_clear(self, dig_seq, **kwargs):
        dig_seq.ds.set_state_mask(**kwargs)
        dig_seq.wait(10)
        dig_seq['channel_state'] = dig_seq.ds.state
        dig_seq.wait(20)

        with dig_seq.While(dig_seq['channel_state'] != 0):
            dig_seq['channel_state'] = dig_seq.ds.state
            dig_seq.wait(20)

    def _push_data(self, dig_seqs):
        for dig_seq in dig_seqs:
            ds_channels = self._get_dig_channel_config(dig_seq).ds_channels
            if len(ds_channels) > 0:
                # NOTE: loop costs PXI registers. Better wait fixed time.
                dig_seq.wait(600)
#                self._wait_state_clear(dig_seq, running=ds_channels)

                dig_seq.ds.control(push=ds_channels)
                dig_seq.wait(600)
#                self._wait_state_clear(dig_seq, pushing=ds_channels)


    def sequence(self, sequencer, hardware):
        self.hardware = hardware
        n_triggers = self.n_triggers

        self.r_start = sequencer.add_sync_register('start')
        self.r_stop = sequencer.add_sync_register('stop')
        self.r_nrep = sequencer.add_sync_register('n_rep')
        self.r_wave_duration = sequencer.add_module_register('wave_duration', module_type='awg')
        if self.hvi_queue_control:
            for register in FpgaAwgQueueingExtension.get_registers():
                sequencer.add_module_register(register, module_type='awg')

        self.r_dig_wait = []
        self.r_awg_los_wait = []
        self.r_awg_los_duration = []
        for i in range(n_triggers):
            self.r_dig_wait.append(sequencer.add_module_register(f'dig_wait_{i+1}', module_type='digitizer'))
            if self.switch_los:
                self.r_awg_los_wait.append(sequencer.add_module_register(f'awg_los_wait_{i+1}', module_type='awg'))
                self.r_awg_los_duration.append(sequencer.add_module_register(f'awg_los_duration_{i+1}', module_type='awg'))

        sequencer.add_module_register('channel_state', module_type='digitizer')

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')
        dig_seqs = sequencer.get_module_builders(module_type='digitizer')
        all_seqs = awg_seqs + dig_seqs

        with sync.Main():

            with sync.While(sync['stop'] == 0):

                with sync.While(sync['start'] == 1):

                    sync['start'] = 0

                    with sync.SyncedModules():
                        for awg_seq in awg_seqs:
                            if self.hvi_queue_control:
                                awg_seq.queueing.queue_waveforms()
                            awg_seq.log.write(1)
                            awg_seq.start()
                            awg_seq.wait(1000)

                        for dig_seq in dig_seqs:
                            dig_config = self._get_dig_channel_config(dig_seq)

                            dig_seq.log.write(1)
                            dig_seq.start(dig_config.all_channels)

                            ds_channels = self._get_dig_channel_config(dig_seq).ds_channels
                            if len(ds_channels) > 0:
                                dig_seq.wait(40)
                                dig_seq.trigger(ds_channels)

                    with sync.Repeat(sync['n_rep']):
                        with sync.SyncedModules():
                            for awg_seq in awg_seqs:
                                los = self._get_awg_channel_los(awg_seq)
                                awg_seq.log.write(2)
                                awg_seq.trigger()
                                awg_seq.lo.reset_phase(los)
                                if self.switch_los:
                                    # enable local oscillators
                                    for i in range(n_triggers):
                                        enabled_los = self._get_enabled_channel_los(awg_seq, i)
                                        awg_seq.wait(awg_seq[f'awg_los_wait_{i+1}'])
                                        # start delay of instruction after wait_register is 0!
                                        awg_seq.lo.set_los_enabled(enabled_los, True)
                                        awg_seq.wait(awg_seq[f'awg_los_duration_{i+1}'])
                                        awg_seq.lo.set_los_enabled(enabled_los, False)

                                awg_seq.wait(awg_seq['wave_duration'])

                            for dig_seq in dig_seqs:
                                dig_config = self._get_dig_channel_config(dig_seq)

                                dig_seq.log.write(2)
                                if len(dig_config.iq_channels) > 0:
                                    dig_seq.ds.control(phase_reset=dig_config.iq_channels)
                                else:
                                    dig_seq.wait(10)

                                for i in range(n_triggers):
                                    dig_seq.wait(dig_seq[f'dig_wait_{i+1}'])
                                    if len(dig_config.raw_channels) > 0:
                                        # start delay of instruction after wait_register is 0!
                                        # so no extra delay when not in schedule.
                                        dig_seq.trigger(dig_config.raw_channels)
                                    dig_seq.wait(40)

                                    if len(dig_config.ds_channels) > 0:
                                        dig_seq.ds.control(start=dig_config.ds_channels)
                                    else:
                                        dig_seq.wait(10)


                    with sync.SyncedModules():
                        self._push_data(dig_seqs)
                        for seq in all_seqs:
                            seq.stop()

                # A simple statement after with sync.While(sync['start'] == 1).
                # The last statement inside with sync.While(sync['stop'] == 0) shouldn't
                # be a while loop, because this results in strange timing constraint in the compiler
                with sync.SyncedModules():
                    pass


    def _get_dig_trigger(self, hvi_params, i):
        warn = self._n_starts == 1
        try:
            return hvi_params[f'dig_trigger_{i+1}']
        except:
            if warn:
                logging.warning(f"Couldn't find HVI variable dig_trigger_{i+1}; trying dig_wait_{i+1}")
        try:
            return hvi_params[f'dig_wait_{i+1}']
        except:
            if i == 0:
                if warn:
                    logging.warning(f"Couldn't find HVI variable dig_wait_{i+1}; trying dig_wait")
                return hvi_params['dig_wait']
            else:
                if warn:
                    logging.warning(f"Couldn't find HVI variable dig_wait_{i+1}")
                raise


    def _set_wait_time(self, hvi_exec, register, value_ns):
        if value_ns < 0:
            # negative value results in wait time of 40 s.
            raise Exception(f'Invalid wait time {value_ns}')
        hvi_exec.write_register(register, int(value_ns/10))


    def start(self, hvi_exec, waveform_duration, n_repetitions, hvi_params):
        if self.started != hvi_exec.is_running():
            logging.warning(f'HVI running: {hvi_exec.is_running()}; started: {self.started}')
        if not self.started:
            logging.info('start hvi')
            hvi_exec.start()
            self.started = True

        self._n_starts += 1

        hvi_exec.write_register(self.r_nrep, n_repetitions)

        # update digitizer measurement time
        if 'averaging' in hvi_params and 't_measure'in hvi_params:
            for dig in self.hardware.digitizers:
                if dig.name in self.digitizer_config:
                    dig_config = self.digitizer_config[dig.name]
                    for ch in dig_config.ds_channels:
                        dig.set_measurement_time_averaging(ch, hvi_params['t_measure'])

        # add 300 ns delay to start acquiring when awg signal arrives at digitizer.
        dig_offset = 300
        tot_wait = -dig_offset
        for i in range(0, self.n_triggers):
            t_trigger = self._get_dig_trigger(hvi_params, i)
            self._set_wait_time(hvi_exec, self.r_dig_wait[i], t_trigger - tot_wait)
            tot_wait = t_trigger + 70 # wait: +40 ns, wait_reg: +20 ns, ds.control: +10 ns

        if self.switch_los:
            tot_wait_awg = 20
            for i in range(0, self.n_triggers):
                t_on = hvi_params[f'awg_los_on_{i+1}']
                t_off = hvi_params[f'awg_los_off_{i+1}']
                self._set_wait_time(hvi_exec, self.r_awg_los_wait[i], t_on - tot_wait_awg)
                tot_wait_awg = t_on + 30 # wait_reg: +30 ns, lo.set_los_enabled: +0 ns
                self._set_wait_time(hvi_exec, self.r_awg_los_duration[i], t_off - tot_wait_awg)
                tot_wait_awg = t_off + 30
        else:
            tot_wait_awg = 0

        # add 250 ns for AWG and digitizer to get ready for next trigger.
        self._set_wait_time(hvi_exec, self.r_wave_duration, waveform_duration + 250 - tot_wait_awg)

        hvi_exec.write_register(self.r_stop, 0)
        hvi_exec.write_register(self.r_start, 1)


    def stop(self, hvi_exec):
        logging.info(f'stop HVI')
        if self.started != hvi_exec.is_running():
            logging.warning(f'HVI running-1: {hvi_exec.is_running()}; started: {self.started}')
        self.started = False
        hvi_exec.write_register(self.r_stop, 1)
        hvi_exec.write_register(self.r_start, 1)
        if self.started != hvi_exec.is_running():
            logging.warning(f'HVI running-2: {hvi_exec.is_running()}; started: {self.started}')

