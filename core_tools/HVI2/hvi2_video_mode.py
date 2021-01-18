import logging


class Hvi2VideoMode():
    verbose = True

    def __init__(self, digitizer_mode, awg_channel_los=None):
        '''
        Args:
            digitizer_mode (int): digitizer modes: 0 = direct, 1 = averaging/downsampling, 2,3 = IQ demodulation
            awg_channel_los (List[Tuple[str,int,int]]): list with (AWG, channel, active local oscillator).

        For video mode the digitizer measurement should return 1 value per trigger.
        There are no practical uses cases where different digitizer channels have different modes.
        '''
        self.downsampler = digitizer_mode != 0
        self.dig_channels = [1,2,3,4]
        self.iq_channels = [1,2,3,4] if digitizer_mode in [2,3] else []
        self.started = False
        self.awg_channel_los = awg_channel_los


    @property
    def name(self):
        return 'VideoMode'

    @property
    def acquisition_gap(self):
        '''
        Time in ns between consecutive acquisition traces.
        '''
        return 10 if self.downsampler else 1800

    def _get_awg_channel_los(self, awg_seq):
        result = []
        for awg, channel, lo in self.awg_channel_los:
            if awg == awg_seq.engine.alias:
                result.append((channel, lo))
        return result

    def _wait_state_clear(self, dig_seq):
        dig_seq.wait(10)
        dig_seq['channel_state'] = dig_seq.ds.state
        dig_seq.wait(20)

        with dig_seq.While(dig_seq['channel_state'] != 0):
            dig_seq['channel_state'] = dig_seq.ds.state
            dig_seq.wait(20)

    def _push_data(self, dig_seqs):
        for dig_seq in dig_seqs:
            dig_seq.ds.set_state_mask(running=self.dig_channels)
            self._wait_state_clear(dig_seq)

            dig_seq.ds.control(push=self.dig_channels)
            dig_seq.ds.set_state_mask(pushing=self.dig_channels)
            self._wait_state_clear(dig_seq)

    def sequence(self, sequencer, hardware):

        self.r_nrep = sequencer.add_sync_register('n_rep')
        self.r_wave_duration = sequencer.add_module_register('wave_duration', module_type='awg')
        self.r_dig_wait = sequencer.add_module_register('dig_wait', module_type='digitizer')
        self.r_npoints = sequencer.add_module_register('n_points', module_type='digitizer')
        sequencer.add_module_register('channel_state', module_type='digitizer')

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')
        dig_seqs = sequencer.get_module_builders(module_type='digitizer')
        all_seqs = awg_seqs + dig_seqs

        with sync.Main():

            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    awg_seq.log.write(1)
                    awg_seq.start()
                    awg_seq.wait(1000)
                for dig_seq in dig_seqs:
                    dig_seq.log.write(1)
                    dig_seq.start(self.dig_channels)

                    if self.downsampler:
                        dig_seq.wait(20)
                        dig_seq.trigger(self.dig_channels)

            with sync.Repeat(sync['n_rep']):
                with sync.SyncedModules():
                    for awg_seq in awg_seqs:
                        awg_seq.trigger()
                        if self.awg_channel_los is not None:
                            los = self._get_awg_channel_los(awg_seq)
                            awg_seq.lo.reset_phase(los)
                        awg_seq.log.write(2)
                        awg_seq.wait(awg_seq['wave_duration'])

                    for dig_seq in dig_seqs:
                        if self.downsampler:
                            dig_seq.ds.control(phase_reset=self.iq_channels)
                            dig_seq.wait(340 - 60)
                        else:
                            dig_seq.wait(310 - 60)

                        with dig_seq.Repeat(dig_seq['n_points']):
                            if self.downsampler:
                                dig_seq.ds.control(start=self.dig_channels)
                            else:
                                dig_seq.trigger()
                            dig_seq.wait(dig_seq['dig_wait'])

            if self.downsampler:
                with sync.SyncedModules():
                    self._push_data(dig_seqs)

            with sync.SyncedModules():
                for seq in all_seqs:
                    seq.stop()


    def start(self, hvi_exec, waveform_duration, n_repetitions, hvi_params):

        hvi_exec.set_register(self.r_nrep, n_repetitions)
        hvi_exec.set_register(self.r_npoints, hvi_params['number_of_points'])

        hvi_exec.set_register(self.r_wave_duration, int(waveform_duration) // 10)

        # subtract the time needed for the repeat loop
        t_wait = int(hvi_params['t_measure']) + self.acquisition_gap - 120
        if t_wait < 10:
            raise Exception('Minimum t_measure is 120 ns')
        hvi_exec.set_register(self.r_dig_wait, t_wait//10)

        hvi_exec.start()


    def stop(self, hvi_exec):
        logging.info(f'stop HVI')

