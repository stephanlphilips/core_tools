import logging

from keysight_fpga.qcodes.M3202A_fpga import FpgaAwgQueueingExtension

class Hvi2ContinuousMode():
    verbose = True

    name = "Continuous"
    ''' Name of the script (class varriable) '''

    def __init__(self, configuration):
        '''
        Creates an HVI2 script that starts the awgs and let's them run continuously.
        No markers, no digitizers.


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
        self.started = False


    def _module_config(self, seq, key):
        return self._configuration[seq.engine.alias][key]


    def sequence(self, sequencer, hardware):
        self.hardware = hardware
        for awg in hardware.awgs:
            if self._configuration[awg.name]['hvi_queue_control']:
                for register in FpgaAwgQueueingExtension.get_registers():
                    sequencer.add_module_register(register, module_aliases=[awg.name])

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')

        with sync.Main():

            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    awg_seq.log.write(1)
                    if self._module_config(awg_seq, 'hvi_queue_control'):
                        awg_seq.queueing.queue_waveforms(cycles=0)
                    awg_seq.start()
                    awg_seq.wait(1000)

                    los = self._module_config(awg_seq, 'active_los')
                    if len(los)>0:
                        awg_seq.lo.reset_phase(los)
                    else:
                        awg_seq.wait(10)
                    awg_seq.trigger()


    def start(self, hvi_exec, waveform_duration, n_repetitions, hvi_params):

        for awg in self.hardware.awgs:
            if self._configuration[awg.name]['hvi_queue_control']:
                awg.write_queue_mem()

        hvi_exec.start()


    def stop(self, hvi_exec):
        for awg in self.hardware.awgs:
            awg.awg_stop_multiple(0b1111)
        logging.info(f'stop HVI')

