import logging

from keysight_fpga.qcodes.M3202A_fpga import FpgaAwgQueueingExtension
from core_tools.drivers.M3102A import MODES

class Hvi2VideoMode():
    verbose = True

    name = "VideoMode"
    ''' Name of the script (class varriable) '''

    def __init__(self, configuration):
        '''
        Args:
            configuration (Dict[str,Any]):
                'n_waveforms' (int): number of waveforms per channel (only applies when hvi_queue_control=True)
                'acquisition_delay_ns' (int):
                Time in ns between AWG output change and digitizer acquisition start.
                This also increases the gap between acquisitions.
                'digitizer_name':
                    'all_ch' (List[int]): all channels
                    'raw_ch' (List[int]): channels in raw mode
                    'ds_ch' (List[int]): channels in downsampler mode
                    'iq_ch' (List[int]): channels in IQ mode
                `awg_name`:
                    'active_los' (List[Tuple[int,int]]): pairs of (channel, LO).
                    'switch_los' (bool): whether to switch LOs on/off
                    'enabled_los' (List[List[Tuple[int,int]]): per switch interval list with (channel, active local oscillator).
                                  if None, then all los are switched on/off.
                    'hvi_queue_control' (bool): if True enables waveform queueing by hvi script.
                    'trigger_out' (bool): if True enables markers via Trigger Out channel.
        '''
        self._configuration = configuration.copy()
        # default acquisition delay: 500 ns
        self._acquisition_delay = int(configuration.get('acquisition_delay_ns', 500)/10) * 10

        raw_mode = False
        for value in configuration.values():
            # minimum is 1800 ns when there is at least one raw_ch.
            if isinstance(value, dict) and 'raw_ch' in value and len(value['raw_ch']) > 0:
                raw_mode = True
        self._acquisition_gap = Hvi2VideoMode.__get_acquisition_gap(raw_mode, self._acquisition_delay)

        self.started = False

    @staticmethod
    def __get_acquisition_gap(raw_mode, acquisition_delay_ns):
        if raw_mode:
            return max(1800, acquisition_delay_ns)
        # Minimum time for digitizer in downsampling mode is 20 ns.
        return 20 + acquisition_delay_ns


    @staticmethod
    def get_acquisition_gap(digitizer, acquisition_delay_ns=500):
        raw_mode = False
        for ch in digitizer.active_channels:
            if digitizer.get_channel_acquisition_mode(ch) == MODES.NORMAL:
                raw_mode = True
        return Hvi2VideoMode.__get_acquisition_gap(raw_mode, acquisition_delay_ns)


    @property
    def acquisition_gap(self):
        '''
        Time in ns between consecutive acquisition traces.
        '''
        return self._acquisition_gap

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
                # NOTE: loop costs PXI registers. Better wait fixed time.
                dig_seq.wait(600)
    #            self._wait_state_clear(dig_seq, running=ds_ch)

                dig_seq.ds.control(push=ds_ch)
                dig_seq.wait(600)
    #            self._wait_state_clear(dig_seq, pushing=ds_ch)

    def sequence(self, sequencer, hardware):
        self.hardware = hardware
        self.r_nrep = sequencer.add_sync_register('n_rep')
        self.r_wave_duration = sequencer.add_module_register('wave_duration', module_type='awg')
        self.r_dig_wait = sequencer.add_module_register('dig_wait', module_type='digitizer')
        self.r_npoints = sequencer.add_module_register('n_points', module_type='digitizer')
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
                    awg_seq.wait(1000)
                for dig_seq in dig_seqs:
                    all_ch = self._module_config(dig_seq, 'all_ch')
                    ds_ch = self._module_config(dig_seq, 'ds_ch')
                    dig_seq.log.write(1)
                    dig_seq.start(all_ch)

                    if len(ds_ch) > 0:
                        dig_seq.wait(40)
                        dig_seq.trigger(ds_ch)

            with sync.Repeat(sync['n_rep']):
                with sync.SyncedModules():
                    for awg_seq in awg_seqs:
                        awg_seq.log.write(2)
                        awg_seq.trigger()
                        los = self._module_config(awg_seq, 'active_los')
                        if len(los)>0:
                            awg_seq.lo.reset_phase(los)
                        else:
                            awg_seq.wait(10)
                        if self._module_config(awg_seq, 'trigger_out'):
                            awg_seq.marker.start()
                            awg_seq.marker.trigger()
                        else:
                            awg_seq.wait(20)
                        awg_seq.wait(awg_seq['wave_duration'])
                        if self._module_config(awg_seq, 'trigger_out'):
                            awg_seq.marker.stop()

                    for dig_seq in dig_seqs:
                        dig_seq.log.write(2)
                        iq_ch = self._module_config(dig_seq, 'iq_ch')
                        ds_ch = self._module_config(dig_seq, 'ds_ch')
                        raw_ch = self._module_config(dig_seq, 'raw_ch')
                        if len(iq_ch) > 0:
                            dig_seq.ds.control(phase_reset=iq_ch)
                        else:
                            dig_seq.wait(10)

                        dig_seq.wait(290 - 130 + self._acquisition_delay)

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
                            dig_seq.wait(dig_seq['dig_wait'])

            with sync.SyncedModules():
                self._push_data(dig_seqs)
                for seq in all_seqs:
                    seq.stop()


    def start(self, hvi_exec, waveform_duration, n_repetitions, hvi_params):

#        logging.warning(f'{self._acquisition_delay} {self._acquisition_gap} {self.acquisition_gap}')

        for awg in self.hardware.awgs:
            if self._configuration[awg.name]['hvi_queue_control']:
                awg.write_queue_mem()

        hvi_exec.set_register(self.r_nrep, n_repetitions)
        hvi_exec.set_register(self.r_npoints, hvi_params['number_of_points'])

        hvi_exec.set_register(self.r_wave_duration, int(waveform_duration) // 10)

        # subtract the time needed for the repeat loop
        t_wait = int(hvi_params['t_measure']) + self.acquisition_gap - 170
        if t_wait < 10:
            raise Exception(f'Minimum t_measure is {180-self.acquisition_gap} ns')
        hvi_exec.set_register(self.r_dig_wait, t_wait//10)

        hvi_exec.start()


    def stop(self, hvi_exec):
        logging.info(f'stop HVI')

