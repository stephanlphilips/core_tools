import logging

from keysight_fpga.qcodes.M3202A_fpga import FpgaAwgQueueingExtension

logger = logging.getLogger(__name__)


class Hvi2VideoMode():
    verbose = True

    name = "VideoMode"
    ''' Name of the script (class variable) '''

    def __init__(self, configuration):
        '''
        Args:
            configuration (Dict[str,Any]):
                'n_waveforms' (int): number of waveforms per channel (only applies when hvi_queue_control=True)
                'digitizer_name':
                    'all_ch' (List[int]): all channels
                    'raw_ch' (List[int]): channels in raw mode
                    'ds_ch' (List[int]): channels in downsampler mode
                    'iq_ch' (List[int]): channels in IQ mode
                `awg_name`:
                    'active_los' (List[Tuple[int,int]]): pairs of (channel, LO).
                    'switch_los' (bool): whether to switch LOs on/off
                    'enabled_los' (List[List[Tuple[int,int]]):
                        per switch interval list with (channel, active local oscillator).
                        if None, then all los are switched on/off.
                    'hvi_queue_control' (bool): if True enables waveform queueing by hvi script.
                    'trigger_out' (bool): if True enables markers via Trigger Out channel.
        '''
        self._configuration = configuration.copy()

    @staticmethod
    def get_minimum_acquisition_delay(raw_mode: bool):
        """Returns minimum time between acquisition end and next start.

        Args:
            raw_mode: whether any channel is in raw mode.
        """
        # Minimum is 1800 ns in raw mode.
        # Minimum time for digitizer in downsampling mode is 20 ns.
        return 1800 if raw_mode else 20

    def _module_config(self, seq, key):
        return self._configuration[seq.engine.alias][key]

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
            ds_ch = self._module_config(dig_seq, 'ds_ch')
            if len(ds_ch) > 0:
                # NOTE: wait loop costs PXI triggers. Better wait fixed time.
                dig_seq.wait(600)
                # self._wait_state_clear(dig_seq, running=ds_ch)

                dig_seq.ds.control(push=ds_ch)
                dig_seq.wait(1000)
                # self._wait_state_clear(dig_seq, pushing=ds_ch)

    def sequence(self, sequencer, hardware):
        self.hardware = hardware
        self.r_nrep = sequencer.add_sync_register('n_rep')
        self.r_wave_duration = sequencer.add_module_register('wave_duration', module_type='awg')
        self.r_start_wait = sequencer.add_module_register('start_wait', module_type='digitizer')
        self.r_line_wait = sequencer.add_module_register('line_wait', module_type='digitizer')
        self.r_point_wait = sequencer.add_module_register('point_wait', module_type='digitizer')
        self.r_npoints = sequencer.add_module_register('n_points', module_type='digitizer')
        self.r_nlines = sequencer.add_module_register('n_lines', module_type='digitizer')
        sequencer.add_module_register('channel_state', module_type='digitizer')
        for awg in hardware.awgs:
            if self._configuration[awg.name]['hvi_queue_control']:
                for register in FpgaAwgQueueingExtension.get_registers():
                    sequencer.add_module_register(register, module_aliases=[awg.name])

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')
        dig_seqs = sequencer.get_module_builders(module_type='digitizer')
        all_seqs = awg_seqs + dig_seqs

        with sync.Main():

            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    awg_seq.log.write(1)
                    if self._module_config(awg_seq, 'hvi_queue_control'):
                        awg_seq.queueing.queue_waveforms()
                    awg_seq.start()
                    video_mode_los = self._module_config(awg_seq, 'video_mode_los')
                    if video_mode_los:
                        awg_seq.lo.set_los_enabled(video_mode_los, True)
                    else:
                        awg_seq.wait(10)
                    awg_seq.wait(990)
                for dig_seq in dig_seqs:
                    all_ch = self._module_config(dig_seq, 'all_ch')
                    ds_ch = self._module_config(dig_seq, 'ds_ch')
                    dig_seq.log.write(1)
                    dig_seq.start(all_ch)

                    if len(ds_ch) > 0:
                        # Push some data get DAQ in correct state
                        # Sometimes the DMA gets stuck when there is no data
                        # written to DAQ between start and trigger.
                        dig_seq.ds.control(push=ds_ch)
                        dig_seq.wait(1000)
                        dig_seq.trigger(ds_ch)

            with sync.Repeat(sync['n_rep']):
                with sync.SyncedModules():
                    for awg_seq in awg_seqs:
                        awg_seq.log.write(2)
                        los = self._module_config(awg_seq, 'active_los')
                        # phase reset of AWG and Dig must be at the same clock tick.
                        if len(los) > 0:
                            awg_seq.lo.reset_phase(los)
                        else:
                            awg_seq.wait(10)
                        # Note: sequencers are used for RF generation to drive resonators
                        if self._module_config(awg_seq, 'sequencer'):
                            awg_seq.qs.reset_phase()
                            awg_seq.qs.start()
                            # total time since start loop: 50 ns (with QS)
                            awg_seq.qs.trigger()
                            awg_seq.wait(70)
                        else:
                            awg_seq.wait(100)
                        awg_seq.trigger()
                        if self._module_config(awg_seq, 'trigger_out'):
                            awg_seq.marker.start()
                            awg_seq.marker.trigger()
                        else:
                            awg_seq.wait(20)
                        awg_seq.wait(awg_seq['wave_duration'])
                        if self._module_config(awg_seq, 'trigger_out'):
                            awg_seq.marker.stop()
                        else:
                            awg_seq.wait(10)
                        if self._module_config(awg_seq, 'sequencer'):
                            awg_seq.qs.stop()
                        else:
                            awg_seq.wait(10)

                    for dig_seq in dig_seqs:
                        dig_seq.log.write(2)
                        iq_ch = self._module_config(dig_seq, 'iq_ch')
                        ds_ch = self._module_config(dig_seq, 'ds_ch')
                        raw_ch = self._module_config(dig_seq, 'raw_ch')
                        # phase reset of AWG and Dig must be at the same clock tick.
                        if len(iq_ch) > 0:
                            dig_seq.ds.control(phase_reset=iq_ch)
                        else:
                            dig_seq.wait(10)

                        dig_seq.wait(dig_seq['start_wait'])

                        with dig_seq.Repeat(dig_seq['n_lines']):
                            with dig_seq.Repeat(dig_seq['n_points']):
                                if len(raw_ch) > 0:
                                    dig_seq.trigger()
                                else:
                                    dig_seq.wait(10)
                                dig_seq.wait(30)
                                if len(ds_ch) > 0:
                                    dig_seq.ds.control(start=ds_ch)
                                else:
                                    dig_seq.wait(10)
                                dig_seq.wait(dig_seq['point_wait'])
                            dig_seq.wait(dig_seq['line_wait'])

            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    video_mode_los = self._module_config(awg_seq, 'video_mode_los')
                    if video_mode_los:
                        awg_seq.lo.set_los_enabled(video_mode_los, False)
                self._push_data(dig_seqs)
                for seq in all_seqs:
                    seq.stop()

    def start(self, hvi_exec, waveform_duration, n_repetitions, hvi_params):

        for awg in self.hardware.awgs:
            if self._configuration[awg.name]['hvi_queue_control']:
                awg.write_queue_mem()

        # use default values for backwards compatibility with old scripts
        start_delay = int(hvi_params.get('start_delay', 0))
        n_points = hvi_params['number_of_points']
        n_lines = hvi_params.get('number_of_lines', 1)
        acquisition_period = int(hvi_params['acquisition_period'])
        line_delay = int(hvi_params.get('line_delay', 400))

        hvi_exec.set_register(self.r_nrep, n_repetitions)
        hvi_exec.set_register(self.r_npoints, n_points)
        hvi_exec.set_register(self.r_nlines, n_lines)

        hvi_exec.set_register(self.r_wave_duration, int(waveform_duration) // 10)

        # subtract the time needed for the repeat loop
        t_point_loop = 170
        t_wait = acquisition_period - t_point_loop
        if t_wait < 10:
            raise Exception(f'Minimum acquisition_period is {10+t_point_loop} ns')
        hvi_exec.set_register(self.r_point_wait, t_wait//10)

        t_dig_delay = 300
        t_till_trigger = 250  # delta with awg.trigger()
        t_start_wait = start_delay + t_dig_delay - t_till_trigger
        if t_start_wait < 10:
            raise Exception(f'Start delay too short ({start_delay} ns)')
        hvi_exec.set_register(self.r_start_wait, t_start_wait//10)

        t_line_loop = 300
        t_line_wait = line_delay - t_line_loop
        if t_line_wait < 10:
            raise Exception(f'Line delay too short ({line_delay} ns)')
        hvi_exec.set_register(self.r_line_wait, t_line_wait//10)

        hvi_exec.start()

    def stop(self, hvi_exec):
        logger.debug('stop HVI')
