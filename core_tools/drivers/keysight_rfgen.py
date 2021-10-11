from qcodes.instrument.base import Instrument
from qcodes.utils.validators import Bool, Numbers
from functools import partial
import logging
from keysight_fpga.sd1.dig_iq import load_iq_image

class keysight_rfgen(Instrument):
    """
    Qcodes driver for the Keysight RF generation and demodulation.

    Args:
        name (str): name of the instrument.
        awg_channel_los (dict): dict of tuples. keys indicate readable lo names.
            each tuple is of the form: (awg_name, channel, amplitude, frequency, enable)
        awg_dict (dict): dict of awg modules, typically output of pulselib.awg_devices
        dig (qcodes instrument): digitizer instrument.
        dig_channel_los (list of tuples): list of tuples with the demod channels.
            each tuple is of the form: (lo_key, channel_number, hardware_channel, IF, IF_band, phase)
                lo_key: same key as in awg_channel_los creates a link when sweeping freq
                channel_number: digitizer DAQ channel used to read data from
                hardware_channel: hardware input channel to be demod (1-4)
                IF: optional intermediate frequency demodulation, i.e. difference between awg and digi.
                IF_band: -1 for lower band, 1 for upper band.
                phase: phase of digitizer LO

    """

    def __init__(self, name, awg_channel_los, awg_dict, dig, dig_channel_los, **kwargs):
        super().__init__(name, **kwargs)

        self.awg_dict = awg_dict
        self.dig = dig
        self._los = []

        self._dig_lo_settings = dict()
        self._awg_lo_settings = dict()

        for (lo_key, (awg_name, channel, amp, freq, enab)) in awg_channel_los.items():
            lo = self.generate_lo(lo_key, awg_name, channel, amp, freq, enab)

            logging.info(f'setting channel {channel} of awg {awg_name} as lo with id {lo}')

            awg = self.awg_dict[awg_name]
            awg.set_lo_mode(channel, True)

        self.set_dig_lo_settings(dig_channel_los)

        for (lo_key, (awg_name, channel, amp, freq, enab)) in awg_channel_los.items():
            self.add_parameter(f'freq_{lo_key}',
                               label = f'frequency of lo {lo} on channel {channel} of awg {awg_name}',
                               initial_value = freq,
                               set_cmd = partial(self.set_freq, lo_key),
                               get_cmd = partial(self.get_freq, lo_key),
                               vals=Numbers(),
                               docstring='sets frequency')

            self.add_parameter(f'amp_{lo_key}',
                               label = f'amplitude of lo {lo} on channel {channel} of awg {awg_name}',
                               initial_value = amp,
                               set_cmd = partial(self.set_amp, lo_key),
                               get_cmd = partial(self.get_amp, lo_key),
                               vals=Numbers(),
                               docstring='sets amplitude')

            self.add_parameter(f'phase_{lo_key}',
                               label = f'phase of lo {lo} for demodulation in digitizer',
                               initial_value = 0,
                               set_cmd = partial(self.set_phase, lo_key),
                               get_cmd = partial(self.get_phase, lo_key),
                               vals=Numbers(),
                               docstring='sets phase')

            self.add_parameter(f'enable_{lo_key}',
                               label = f'enable of lo {lo} on channel {channel} of awg {awg_name}',
                               initial_value = enab,
                               set_cmd = partial(self.set_enab, lo_key),
                               get_cmd = partial(self.get_enab, lo_key),
                               vals=Bool(),
                               docstring='enables output')


    @property
    def all_los(self):
        return list(self._awg_lo_settings.keys())

    @property
    def lo_status(self):
        result = dict()
        for lo_key in self.all_los:
            param = getattr(self, f'enable_{lo_key}')
            result[lo_key] = param()
        return result

    @property
    def all_params(self):
        return list(self.parameters.values())[1:]

    def set_amp(self, lo_key, amp):
        self._awg_lo_settings[lo_key][3] = amp
        self.write_awg_settings(lo_key)

    def get_amp(self, lo_key):
        return self._awg_lo_settings[lo_key][3]

    def set_freq(self, lo_key, freq):
        self._awg_lo_settings[lo_key][4] = freq
        self.write_awg_settings(lo_key)
        self.write_dig_settings(lo_key)

    def get_freq(self, lo_key):
        return self._awg_lo_settings[lo_key][4]

    def set_phase(self, lo_key, phase):
        self._dig_lo_settings[lo_key][4] = phase
        self.write_dig_settings(lo_key)

    def get_phase(self, lo_key):
        return self._dig_lo_settings[lo_key][4]

    def set_enab(self, lo_key, enab):
        self._awg_lo_settings[lo_key][5] = enab
        self.write_awg_settings(lo_key)

    def get_enab(self, lo_key):
        return self._awg_lo_settings[lo_key][5]

    def write_awg_settings(self, lo_key):
        awg_name = self._awg_lo_settings[lo_key][0]
        channel = self._awg_lo_settings[lo_key][1]
        lo = self._awg_lo_settings[lo_key][2]
        amp = self._awg_lo_settings[lo_key][3]
        freq = self._awg_lo_settings[lo_key][4]
        enab = self._awg_lo_settings[lo_key][5]
        self.awg_dict[awg_name].config_lo(channel, lo, enab, freq, amp)

    def change_input_channel(self, lo_key, input_channel):
        self._dig_lo_settings[lo_key][1] = input_channel
        self.write_dig_settings(lo_key)

    def write_dig_settings(self, lo_key):
        freq = self._awg_lo_settings[lo_key][4]
        channel, hw_channel, ifreq, ifreq_band, phase = self._dig_lo_settings[lo_key]
        self.dig.set_lo(channel, freq + ifreq_band * ifreq, phase, input_channel=hw_channel)

    def set_dig_lo_settings(self, dig_channel_los):
        # empty old dict
        for key in self._dig_lo_settings.keys():
            self._dig_lo_settings[key] = ()

        load_iq_image(self.dig.SD_AIN)
        self.dig.set_acquisition_mode(2)
        for (lo_key, channel, hw_channel, ifreq, ifreq_band, *arg) in dig_channel_los:
            phase = arg[0] if len(arg) > 0 else 0.0
            self._dig_lo_settings[lo_key] = [channel, hw_channel, ifreq, ifreq_band, phase]
            self.write_dig_settings(lo_key)

    def generate_lo(self, lo_key, awg_name, channel, amp, freq, enab):
        prev_los = [awg_set[2] for awg_set in self._awg_lo_settings.values() if
                    awg_set[0] == awg_name and awg_set[1] == channel]
        lo = max(prev_los, default = -1) + 1
        self._awg_lo_settings[lo_key] = [awg_name, channel, lo, amp, freq, enab]
        self._dig_lo_settings.setdefault(lo_key, [])
        return lo

