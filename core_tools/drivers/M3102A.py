
from qcodes import Instrument, MultiParameter
from dataclasses import dataclass
from typing import Optional
import warnings
import logging
import time
import copy
from si_prefix import si_format

try:
    import keysightSD1
except:
    warnings.warn("\nM3102A needs Keysight AWG libraries. Please install if you need them.\n")

# check whether SD1 version 2.x or 3.x
is_sd1_3x = 'SD_SandBoxRegister' in dir(keysightSD1)
if is_sd1_3x:
    # import function for hvi2 downsampler FPGA image
    from keysight_fpga.sd1.dig_iq import config_channel, \
        is_iq_image_loaded, dig_set_lo, dig_set_input_channel, dig_set_downsampler


import numpy as np

def check_error(res, s=''):
    if (type(res) is int and res < 0):
        error = res
        msg = f'Keysight error: {keysightSD1.SD_Error.getErrorMessage(error)} ({error}) {s}'
        logging.error(msg)
    return res

"""
Minimalistic qcodes driver for the Keysight digizer card (M3102A)
Author : Stephan Philips (TuDelft)
"""

class MODES:
    """
    Modes to be operating in:
        NORMAL : normal / raw data
        AVERAGE : averaging / downsampling of traces
        IQ_DEMODULATION : IQ demodulation
        IQ_DEMOD_I_ONLY : IQ demodulation output I-only

    The operating modes other than NORMAL require an FPGA image.
    """
    NORMAL = 0
    AVERAGE = 1
    IQ_DEMODULATION = 2
    IQ_DEMOD_I_ONLY = 3


class OPERATION_MODES:
    """
    Modes for operation
        SOFT_TRG : use software triggers (does call start and trigger in software)
        ANALOG_TRG : use external triggering (does call start digitizer)
        HVI_TRG : use HVI for triggering (no calls done)
    """
    SOFT_TRG = 0
    ANALOG_TRG = 1
    HVI_TRG = 2


class DATA_MODE:
    """
    Mode of handling data. Determines what will be saved.
        FULL : no averaging at all, get back full output data
        AVERAGE_TIME : average on x axis --> average a full trace to a single point
        AVERAGE_CYCLES : average on y axis --> average over all the iterations
        AVERAGE_TIME_AND_CYCLES : average on x and y axis, in other words, get back a single point
    """
    FULL = 0
    AVERAGE_TIME = 1
    AVERAGE_CYCLES = 2
    AVERAGE_TIME_AND_CYCLES = 3


class line_trace(MultiParameter):
    """
    class that defines the parameter for the measured data.
    """
    def __init__(self, name, instrument, inst_name , raw=False):
        self.my_instrument = instrument
        super().__init__(name=inst_name,
                         names = (name +'_ch1', name +'_ch2'),
                         shapes=((1,),(1,)),
                         docstring='Averaged traces from digitizer')
        self.cached_properties = dict()

    @property
    def channels(self):
        """
        list with active channels on the digitizer.
        """
        channels = []
        for channel_property in self.my_instrument.channel_properties.values():
            if channel_property.active == True:
                channels.append(channel_property.number)

        return channels

    @property
    def channel_mask(self):
        """
        generate channels mask for start multiple control functions
        """
        channel_mask = 0

        for i in self.channels:
            channel_mask += 1 << (i - 1)

        return channel_mask

    def get_raw(self):
        if self.my_instrument.operation_mode in [OPERATION_MODES.SOFT_TRG, OPERATION_MODES.ANALOG_TRG]:
            self.start_digitizers()

        if self.my_instrument.operation_mode == OPERATION_MODES.SOFT_TRG:
            self.trigger_digitizers()

        return self.get_data()


    def _read_available(self, ch, buffer, offset):
        available = self.my_instrument.SD_AIN.DAQcounterRead(ch)
        check_error(available)

        if available <= 0:
            return available

        length = len(buffer)
        if available + offset > length:
            logging.warning(f"ch{ch} more data points in digitizer ram ({available}+{offset}) "
                            f"than what is being collected ({length}).")
            available = length - offset

        # Always read with a timeout to prevent infinite blocking of HW (and reboot of system).
        # Transfer rate is ~55 MSa/s. Add one second marging
        read_timeout = int((available / 50e6 + 1) * 1000)
        received = self.my_instrument.SD_AIN.DAQread(ch, available, read_timeout)
        check_error(received)
        if isinstance(received, int) and received < 0:
            # the error has already been logged
            return received

        n_received = len(received)
#        logging.debug(f'DAQread ch:{ch} ready:{available} read:{n_received} offset:{offset}')
        if n_received != available:
            if available > n_received and available - n_received < 4:
                # It seems that M3102A only returns multiples of 4 bytes.
                logging.warning(f'DAQread data remaining. ch:{ch} ready:{available} read:{n_received}')
            else:
                logging.error(f'DAQread failure. ch:{ch} ready:{available} read:{n_received}')

        if n_received > 0:
            buffer[offset:offset + n_received] = received

        return n_received


    def _read_channels(self, daq_points_per_channel):
        start = time.perf_counter()
        data_read = {channel:0 for channel in daq_points_per_channel}

        channels = daq_points_per_channel.keys()
        channels_to_read = list(channels)
        no_data_count = 0
        consecutive_error_count = 0
        last_read = time.perf_counter()
        has_read_timeout = False

        while len(channels_to_read) > 0 and not has_read_timeout and consecutive_error_count < 5:
            any_read = False

            for ch in channels_to_read:
                n_read = self._read_available(ch, daq_points_per_channel[ch], data_read[ch])
#                logging.debug(f'ch{ch}: {n_read}')

                if n_read < 0:
                    consecutive_error_count += 1
                if n_read > 0:
                    data_read[ch] = data_read[ch] + n_read
                    consecutive_error_count = 0
                    any_read = True

                    if data_read[ch] == len(daq_points_per_channel[ch]):
                        # all read: remove from list
                        channels_to_read.remove(ch)

            if any_read:
                no_data_count = 0
                last_read = time.perf_counter()
            else:
                no_data_time = time.perf_counter() - last_read
                no_data_count += 1
                time.sleep(0.001)
                # abort when no data has been received for 30 s and at least 2 checks without any data
                # the timeout of 30 s is needed for T1 measurement of 100 ms and one flush every 256 measurements.
                has_read_timeout = no_data_count >= 2 and (no_data_time > 30)
                if (no_data_time > 0.5 and no_data_count < 100) or no_data_count % 100 == 0:
                    logging.debug(f'no data available ({no_data_count}, {no_data_time:4.2f} s); wait...')

        logging.info(f'channels {channels}: retrieved {data_read} points in {(time.perf_counter()-start)*1000:3.1f} ms')
        for ch in channels:
            if data_read[ch] != len(daq_points_per_channel[ch]):
                logging.error(f"digitizer did not collect enough data points for channel {ch}; "
                              f"requested:{len(daq_points_per_channel[ch])} received:{data_read[ch]}; "
                              "last values are zeros.")

    def _get_data(self):
        data_out = tuple()

        daq_points_per_channel = {}
        for channel_property in self.my_instrument.channel_properties.values():
            if channel_property.active == False:
                continue
            channel = channel_property.number
            daq_cycles = channel_property.daq_cycles
            daq_points_per_cycle = channel_property.daq_points_per_cycle

            daq_points = daq_cycles * daq_points_per_cycle
            daq_points_per_channel[channel] = np.zeros(daq_points, np.double)


        self._read_channels(daq_points_per_channel)


        for channel_property in self.my_instrument.channel_properties.values():
            if channel_property.active == False:
                continue

            channel_data_raw = daq_points_per_channel[channel_property.number]
            # convert 16 bit signed to mV. (inplace multiplication on numpy array is fast)
            channel_data_raw *= channel_property.full_scale * 1000 / 32768

            if channel_property.acquisition_mode == MODES.NORMAL:
                # reshape for [repetitions, time] and average
                channel_data_raw = channel_data_raw.reshape([channel_property.cycles, channel_property.daq_points_per_cycle])
                # remove extra samples due to alignment
                channel_data_raw = channel_data_raw[:,:channel_property.points_per_cycle]

            elif channel_property.acquisition_mode == MODES.IQ_DEMODULATION:
                # remove aligment point
                total_points = channel_property.points_per_cycle * channel_property.cycles * 2
                channel_data_raw = channel_data_raw[:total_points]
                # convert to array with complex values
                channel_data_raw = channel_data_raw[::2] + 1j * channel_data_raw[1::2]
                # reshape for [repetitions, time] and average
                channel_data_raw = channel_data_raw.reshape([channel_property.cycles, channel_property.points_per_cycle])
            else:
                # remove aligment point
                total_points = channel_property.points_per_cycle * channel_property.cycles
                channel_data_raw = channel_data_raw[:total_points]
                # reshape for [repetitions, time] and average
                channel_data_raw = channel_data_raw.reshape([channel_property.cycles, channel_property.points_per_cycle])


            if channel_property.data_mode == DATA_MODE.FULL:
                data_out += (channel_data_raw, )
            elif channel_property.data_mode == DATA_MODE.AVERAGE_TIME:
                data_out += (np.average(channel_data_raw, axis = 1), )
            elif channel_property.data_mode == DATA_MODE.AVERAGE_CYCLES:
                data_out += (np.average(channel_data_raw, axis = 0), )
            elif channel_property.data_mode == DATA_MODE.AVERAGE_TIME_AND_CYCLES:
                data_out += (np.average(channel_data_raw), )

        return data_out

    # NOTE: only used for old fpga image
    def _read_channel_data(self, channel_number, channel_data_raw):
        start = time.perf_counter()
        data_length = len(channel_data_raw)

        no_data_count = 0
        consecutive_error_count = 0
        points_acquired = 0

        while points_acquired < data_length and consecutive_error_count < 3:
            np_ready = self.my_instrument.SD_AIN.DAQcounterRead(channel_number)
            check_error(np_ready)

            if np_ready + points_acquired > data_length:
                np_ready = data_length - points_acquired
                logging.warning("more data points in digitizer ram than what is being collected.")

            n_received = 0
            if np_ready > 0:
                # Always read with a timeout to prevent infinite blocking of HW (and reboot of system).
                # There are np_ready points available. This can be read in 1 second.
                received = self.my_instrument.SD_AIN.DAQread(channel_number, np_ready, 1000)
                check_error(received)
                if isinstance(received, int) and received < 0:
                    # the error has already been logged
                    consecutive_error_count += 1
                    continue

                n_received = len(received)
#                logging.debug(f'DAQread ready:{np_ready} read:{n_received}')
                if n_received != np_ready:
                    if np_ready > n_received and np_ready - n_received < 4:
                        # It seems that M3102A only returns multiples of 4 bytes.
                        logging.warning(f'DAQread data remaining. ready:{np_ready} read:{n_received}')
                    else:
                        logging.error(f'DAQread failure. ready:{np_ready} read:{n_received}')

            if n_received > 0:
                channel_data_raw[points_acquired: points_acquired + n_received] = received
                points_acquired = points_acquired + n_received
                no_data_count = 0
                consecutive_error_count = 0
            else:
#                logging.debug(f'no data; wait...')
                no_data_count += 1
                if no_data_count > 100:
                    break
                time.sleep(0.001)

        if points_acquired != data_length:
            logging.error(f"digitizer did not collect enough data points for channel {channel_number}; "
                          f"requested:{data_length} received:{points_acquired}; last values are zeros.")

        logging.info(f'channel {channel_number}: retrieved {points_acquired} points in {(time.perf_counter()-start)*1000:3.1f} ms')


    # NOTE: only used for old fpga image
    def _get_data_average(self):
        data_out = tuple()

         # note that we are acquirering two channels at the same time in this mode.
        for channel_property in self.my_instrument.channel_properties.values():
            # averaging mode: channels are read in pairs.
            if channel_property.number in [2,4]:
                # even numbers are read with odd channel.
                continue
            if channel_property.number not in self.channels and channel_property.number+1 not in self.channels:
                # don't read anything if both channels not active.
                continue

            # make flat data structures.
            channel_data_raw = np.zeros([channel_property.cycles*10], np.uint16)

            self._read_channel_data(channel_property.number, channel_data_raw)

            # format the data
            channel_data_raw = channel_data_raw.reshape([channel_property.cycles, 10]).transpose().astype(np.int32)
            channel_data = np.empty([2,channel_property.cycles])
            channel_data[0] = ((channel_data_raw[1] & 2**16-1) << 16) | (channel_data_raw[0] & 2**16-1)
            channel_data[1] = ((channel_data_raw[3] & 2**16-1) << 16) | (channel_data_raw[2] & 2**16-1)

            # correct amplitude,
            # outputs V, 5 for the acquisition in blocks of 5
            channel_data[0] *= 5 * 2/(channel_property.t_measure-160)*channel_property.full_scale / 2**15
            channel_data[1] *= 5 * 2/(channel_property.t_measure-160)*channel_property.full_scale / 2**15

            # only add the data of the selected channels.
            if channel_property.number in self.channels:
                if channel_property.data_mode in [DATA_MODE.AVERAGE_CYCLES, DATA_MODE.AVERAGE_TIME_AND_CYCLES]:
                   data_out += (np.average(channel_data[0]), )
                else:
                    data_out += (channel_data[0], )

            if channel_property.number + 1 in self.channels:
                if channel_property.data_mode in [DATA_MODE.AVERAGE_CYCLES, DATA_MODE.AVERAGE_TIME_AND_CYCLES]:
                   data_out += (np.average(channel_data[1]), )
                else:
                    data_out += (channel_data[1], )

        return data_out


    def get_data(self):
        """
        Get data from the cards
        """
        if self.my_instrument.use_old_fpga_averaging:
            return self._get_data_average()
        else:
            return self._get_data()


    def start_digitizers(self):
        # start digizers.
        self.my_instrument.daq_start_multiple(self.channel_mask)

    def trigger_digitizers(self):
        # trigger the digitizers.
        for i in range(self.my_instrument.channel_properties[f'ch{self.channels[0]}'].cycles):
            self.my_instrument.daq_trigger_multiple(self.channel_mask)

    def _generate_parameter_info(self):
        """
        Generate the correct labels/units for the digitizer parameter
        """
        channels_changed = False
        mode_changed = False
        shape_changed = False

        for properties in self.my_instrument.channel_properties.values():
            if not properties.name in self.cached_properties:
                self.cached_properties[properties.name] = channel_properties(properties.name, properties.number)
            cached = self.cached_properties[properties.name]

            channels_changed |= properties.active != cached.active
            mode_changed |= properties.data_mode != cached.data_mode
            shape_changed |= (
                    properties.cycles != cached.cycles
                    or properties.t_measure != cached.t_measure
                    or properties.points_per_cycle != cached.points_per_cycle
                    )
            self.cached_properties[properties.name] = copy.copy(properties)

        if channels_changed:
            self.names = tuple()
            self.labels = tuple()
            self.units = tuple()

            for properties in self.my_instrument.channel_properties.values():
                if properties.active:
                    self.names += (properties.name, )
                    self.labels += (f"digitizer output {properties.name}", )
                    self.units += ("mV" , )

        if channels_changed or mode_changed:
            self.setpoint_labels = tuple()
            self.setpoint_names = tuple()
            self.setpoint_units = tuple()

            for properties in self.my_instrument.channel_properties.values():
                if properties.active:
                    setpoint_names = tuple()
                    setpoint_labels = tuple()
                    setpoint_units = tuple()

                    if properties.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_TIME]:
                        setpoint_names += (f"nth_cycle_{properties.name}", )
                        setpoint_labels += ("nth cycle", )
                        setpoint_units += ("#", )

                    if (properties.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_CYCLES]
                        and (properties.acquisition_mode == MODES.NORMAL or properties.points_per_cycle > 1)):
                        setpoint_names += (f"time_ch_{properties.name}", )
                        setpoint_labels += ("time", )
                        setpoint_units += ("ns", )

                    self.setpoint_labels +=  (setpoint_labels, )
                    self.setpoint_names += (setpoint_names, )
                    self.setpoint_units += (setpoint_units, )

        if channels_changed or mode_changed or shape_changed:
            self.shapes = tuple()
            self.setpoints = tuple()

            for properties in self.my_instrument.channel_properties.values():
                if properties.active:
                    shape = tuple()
                    setpoints = tuple()

                    if properties.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_TIME]:
                        shape += (properties.cycles, )
                        # setpoints need to be a tuple for hash look-up in qcodes ..
                        setpoints += (tuple(np.linspace(1, properties.cycles, properties.cycles)), )

                    if (properties.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_CYCLES]
                        and (properties.acquisition_mode == MODES.NORMAL or properties.points_per_cycle > 1)):
                        n = properties.points_per_cycle
                        shape += (n, )
                        setpoints += (tuple(np.linspace(properties.t_measure/n, properties.t_measure, n)), )

                    self.shapes += (shape, )
                    self.setpoints += (setpoints, )


@dataclass
class channel_properties:
    """
    structure to save relevant information about marker data.
    """
    name : str
    number : int
    active : bool = False
    acquisition_mode : MODES = MODES.NORMAL
    data_mode : DATA_MODE = DATA_MODE.FULL
    points_per_cycle : int = 1
    cycles : int = 0
    full_scale : float = 0 #peak voltage
    t_measure : float = 0 #measurement time in ns of the channel
    sample_rate : float = 500e6
    # daq configuration
    prescaler : int = 0
    daq_points_per_cycle: int = 1
    daq_cycles: int = 0
    # settings of downsampler-iq FPGA image
    downsampled_rate : Optional[float] = None
    power2decimation : int = 0
    downsampling_factor : int = 1
    lo_frequency : float = 0
    lo_phase : float = 0
    input_channel : int = 0


class SD_DIG(Instrument):
    """docstring for SD_DIG"""
    def __init__(self, name, chassis, slot, n_channels = 4):
        super().__init__(name)
        """
        init keysight digitizer

        Args:
            name (str) : name of the digitizer
            chassis (int) : chassis number
            slot (int) : slot in the chassis where the digitizer is.
            n_channels (int) : number of channels on the digitizer card.

        NOTE: channels start for number 1! (e.g. channel 1, channel 2, channel 3, channel 4)
        """
        self.SD_AIN = keysightSD1.SD_AIN()
        dig_name = check_error(self.SD_AIN.getProductNameBySlot(chassis, slot), 'getProductNameBySlot')
        check_error(self.SD_AIN.openWithSlot(dig_name, chassis, slot), 'openWithSlot')

        firmware_version = self.SD_AIN.getFirmwareVersion()
        major,minor,revision = firmware_version.split('.')

        if (major == '02') != is_sd1_3x:
            raise Exception(f'KeysightSD1 driver not compatible with firmware "{firmware_version}"')

        self.chassis = chassis
        self.slot = slot

        self.operation_mode = OPERATION_MODES.SOFT_TRG

        self.use_old_fpga_averaging = False

        self.channel_properties = dict()
        for i in range(n_channels):
            properties = channel_properties(f'ch{i+1}', i + 1)
            self.channel_properties[f'ch{i+1}'] = properties

        self.add_parameter(
            'measure',
            inst_name = self.name,
            parameter_class=line_trace,
            raw =False
            )

    def close(self):
        self.SD_AIN.close()
        super().close()

    def snapshot_base(self, update = False, params_to_skip_update = None):
        param_to_skip = ['measure']
        if params_to_skip_update is not None:
            param_to_skip += params_to_skip_update

        return super().snapshot_base(update, params_to_skip_update=param_to_skip)

    def set_aquisition_mode(self, mode):
        logging.warning('M3102A.set_aquisition_mode is deprecated. Use M3102A.set_acquisition_mode')
        self.set_acquisition_mode(mode)

    def set_acquisition_mode(self, mode):
        """
        Modes to be operating in:
            0 : normal
            1 : averaging of traces (Keysight DEMOD modules needed for this)
            2 : IQ demodulation
            3 : IQ demodulation I values only
        """
        changed = False
        for properties in self.channel_properties.values():
            if properties.acquisition_mode != mode:
                properties.acquisition_mode = mode
                changed = True

        if not is_sd1_3x and mode in [MODES.IQ_DEMODULATION, MODES.IQ_DEMOD_I_ONLY]:
            raise Exception('IQ modes not supported for old Keysight firmware')

        self.use_old_fpga_averaging = not is_sd1_3x and mode == MODES.AVERAGE

        if changed:
            self.measure._generate_parameter_info()

    def set_channel_acquisition_mode(self, channel, mode):
        """
        Modes to be operating in:
            0 : normal
            1 : averaging of traces (Keysight DEMOD modules needed for this)
            2 : IQ demodulation
            3 : IQ demodulation I values only
        """
        if not is_sd1_3x:
            raise Exception('Operation not support for old KeysightSD1')

        properties = self.channel_properties[f'ch{channel}']
        if properties.acquisition_mode != mode:
            properties.acquisition_mode = mode
            self.measure._generate_parameter_info()


    def get_channel_acquisition_mode(self, channel):
        return self.channel_properties[f'ch{channel}'].acquisition_mode


    def set_data_handling_mode(self, data_mode):
        """
        mode of handling data. Determines what will be saved.
            0 : no averaging at all, get back full output data
            1 : average on x axis --> average a full trace to a single point
            2 : average on y axis --> average over all the iterations
            3 : average on x and y axis, in other words, get back a single point
        """
        changed = False

        for properties in self.channel_properties.values():
            if properties.data_mode != data_mode:
                properties.data_mode = data_mode
                changed = True

        if changed:
            self.measure._generate_parameter_info()

    def set_channel_data_handling_mode(self, channel, data_mode):
        """
        mode of handling data. Determines what will be saved.
            0 : no averaging at all, get back full output data
            1 : average on x axis --> average a full trace to a single point
            2 : average on y axis --> average over all the iterations
            3 : average on x and y axis, in other words, get back a single point
        """
        properties = self.channel_properties[f'ch{channel}']
        if properties.data_mode != data_mode:
            properties.data_mode = data_mode
            self.measure._generate_parameter_info()

    def set_operating_mode(self, operation_mode):
        """
        Modes for operation

        Only affects daq start and daq trigger in get_raw().

        Args:
            operation_mode (int) : mode of operation
                0 : use software triggers (does call start and trigger in software)
                1 : use external triggering (does call start digitizer)
                2 : use HVI for triggering (no calls done)
        """
        self.operation_mode = operation_mode

    def set_active_channels(self, channels):
        """
        set the active channels:

        Args:
            channels (list) : channels numbers that need to be used
        """
        changed = False
        for channel_property in self.channel_properties.values():
            active = channel_property.number in channels
            if channel_property.active != active:
                channel_property.active = active
                changed = True

        if changed:
            self.measure._generate_parameter_info()

    @property
    def active_channels(self):
        result = []
        for properties in self.channel_properties.values():
            if properties.active:
                result.append(properties.number)
        return result

    def set_channel_properties(self, channel, V_range, impedance=1, coupling=0):
        """
        sets quickly relevant channel properties.
        TODO: We need a validator on Vrange.
        Args:
            channel : channel number (1 to 4)
            V_range: amplitude range +- X Volts
            impedance: 0(HiZ), 1 (50 Ohm)
            coulping: 0 (DC), 1 (AC)
        """
        self.SD_AIN.channelInputConfig(channel, V_range, impedance, coupling)

        properties = self.channel_properties[f'ch{channel}']
        if properties.full_scale != V_range:
            properties.full_scale = V_range
            self.measure._generate_parameter_info()


    def set_daq_settings(self, channel, n_cycles, t_measure, sample_rate = 500e6,
                         DAQ_trigger_delay = 0, DAQ_trigger_mode = 1, downsampled_rate = None, power2decimation = 0):
        """
        quickset for the daq settings

        Args:
            n_cycles (int) : number of trigger to record.
            t_measure (float) : time to measure (unit : ns)
            sample_rate (float) : sample rate of the channel in Sa/s
            DAQ_trigger_delay (int) : use HVI for this..
            DAQ_trigger_mode (int) : 1 for HVI see manual for other options. (2 is external trigger)
            downsampled_rate (float) : sample rate after downsampling in Sa/s, if None then downsampled_rate = 1/t_measure
            power2decimation (int) : number of decimate-by-2 steps applied (with anti-alias filter)
        """
        properties = self.channel_properties[f'ch{channel}']
        properties.active = True

        # find aproriate prescalor if needed
        if properties.acquisition_mode == MODES.NORMAL:
            if downsampled_rate is not None or power2decimation > 0:
                logging.warning(f'ch{channel} downsampled_rate and power2decimation are ignored in NORMAL mode')
                downsampled_rate = None
                power2decimation = 0

            prescaler = max(0, int(500e6/sample_rate -1))

            # The M3102A prescaler maximum value is 4.
            if prescaler > 4:
                raise ValueError(f'Sample rate {sample_rate} not supported.'
                                  'M3102A frequency is limited to range [100..500] MHz')
            sample_rate = 500e6/(prescaler+1)
            if properties.sample_rate != sample_rate:
                logging.info("Effective sampling frequency is set to {}Sa/s (prescaler = {})"
                             .format(si_format(sample_rate, precision=1), prescaler))

            points_per_cycle = int(t_measure*1e-9*sample_rate)
            daq_points_per_cycle = points_per_cycle
            daq_cycles = n_cycles
            eff_t_measure = points_per_cycle * 1e9 / sample_rate
            downsampling_factor = 1

            if is_iq_image_loaded(self.SD_AIN):
                config_channel(self.SD_AIN, channel, properties.acquisition_mode, 1, 1, input_ch=0)

        elif not is_sd1_3x:
            if properties.acquisition_mode == MODES.AVERAGE:
                prescaler = 0
                sample_rate = 500e6
                points_per_cycle = 1
                daq_points_per_cycle = 10
                daq_cycles = n_cycles
                eff_t_measure = (t_measure//10) * 10
                downsampling_factor = 1
            else:
                raise Exception(f'mode {properties.acquisition_mode} not supported for old firmware')

        else:
            if sample_rate != 500e6:
                logging.warning(f'Sample rate is always 500 MSa/s in mode {properties.acquisition_mode}. '
                                f'Ignoring requested {sample_rate}')

            prescaler = 0
            sample_rate = 500e6
            if downsampled_rate is None:
                downsampling_factor = int(max(1, round(t_measure / 10 / 2**power2decimation)))
                points_per_cycle = 1
            else:
                downsampling_factor = int(max(1, round(100e6 / downsampled_rate / 2**power2decimation)))
                t_downsampling = downsampling_factor * 10 * 2**power2decimation
                points_per_cycle = max(1, round(t_measure/t_downsampling))

            eff_t_measure = points_per_cycle * downsampling_factor * 10 * 2**power2decimation

            values_per_point = 2 if properties.acquisition_mode == MODES.IQ_DEMODULATION else 1
            # add points to align with data retrieval size; minimum number for downsampler is 8
            daq_points_per_cycle = max(8, n_cycles * points_per_cycle * values_per_point)
            daq_cycles = 1
            config_input_channel = properties.input_channel if properties.input_channel != 0 else channel

            config_channel(self.SD_AIN, channel, properties.acquisition_mode, downsampling_factor, points_per_cycle,
                           LO_f=properties.lo_frequency, phase=properties.lo_phase,
                           p2decim=power2decimation, input_ch=config_input_channel)

        # add extra points for acquisition alignment
        daq_points_per_cycle = self._get_aligned_npoints(daq_points_per_cycle)

        # variables needed to generate correct setpoints and for data acquisition
        properties.cycles = n_cycles
        properties.points_per_cycle = points_per_cycle
        properties.t_measure = eff_t_measure
        properties.sample_rate = sample_rate
        properties.prescaler = prescaler
        properties.downsampled_rate = downsampled_rate
        properties.power2decimation = power2decimation
        properties.downsampling_factor = downsampling_factor
        properties.daq_points_per_cycle = daq_points_per_cycle
        properties.daq_cycles = daq_cycles

        logging.debug(f'ch{channel} config: {daq_points_per_cycle}, {daq_cycles}')
        self.SD_AIN.DAQconfig(channel, daq_points_per_cycle, daq_cycles, DAQ_trigger_delay, DAQ_trigger_mode)
        self.SD_AIN.channelPrescalerConfig(channel, prescaler)
        self.measure._generate_parameter_info()


    def set_ext_digital_trigger(self, channel, delay = 0, mode=3):
        """
        Set external trigger for current channel.
        Args:
            mode: 1(trig high), 2 (trig low), 3 (raising edge), 4 (falling edge)
        """

        logging.info('set ext trigger')

        # Make sure input port is enabled
        self.SD_AIN.triggerIOconfig(1)
        # set up the triggering config
        self.SD_AIN.DAQdigitalTriggerConfig(channel, 0 , mode)

        # overwrite to be sure.
        properties = self.channel_properties[f'ch{channel}']
        points_per_cycle = properties.points_per_cycle
        n_cycles = properties.cycles
        # NOTE: add 1 point for odd sample numbers
        self.SD_AIN.DAQconfig(channel, self._get_aligned_npoints(points_per_cycle), n_cycles, delay, 2)

    def daq_flush(self, daq, verbose=False):
        """
        Flush the specified DAQ

        Args:
            daq (int)       : the DAQ you are flushing
        """
        self.SD_AIN.DAQflush(daq)

    def daq_flush_multiple(self, daq_mask, verbose=False):
        """
        Flush the specified DAQ

        Args:
            daq_mask (int)       : the DAQs you are flushing
        """
        self.SD_AIN.DAQflushMultiple(daq_mask)

    def daq_stop(self, daq, verbose=False):
        """ Stop acquiring data on the specified DAQ

        Args:
            daq (int)       : the DAQ you are stopping
        """
        self.SD_AIN.DAQstop(daq)

    def daq_stop_multiple(self, daq_mask, verbose=False):
        """ Stop acquiring data on the specified DAQ

        Args:
            daq_mask (int)  : the input DAQs you are stopping, composed as a bitmask
                              where the LSB is for DAQ_0, bit 1 is for DAQ_1 etc.
        """
        self.SD_AIN.DAQstopMultiple(daq_mask)


    def writeRegisterByNumber(self, regNumber, varValue):
        """
        Write to a register of the AWG, by reffreing to the register number

        Args:
            regNumber (int) : number of the registry (0 to 16)
            varValue (int/double) : value to be written into the registry
        Returns:
            Value (int) : error out (negative number)
        """
        if is_sd1_3x:
            raise Exception('writeRegisterByNumber is not supported by KeysightSD1 3.x')
        return self.SD_AIN.writeRegisterByNumber(regNumber, varValue)

    def daq_start_multiple(self, daq_mask, verbose=False):
        """ Start acquiring data or waiting for a trigger on the specified DAQs

        Args:
            daq_mask (int)  : the input DAQs you are enabling, composed as a bitmask
                              where the LSB is for DAQ_0, bit 1 is for DAQ_1 etc.
        """
        self.SD_AIN.DAQstartMultiple(daq_mask)

    def daq_trigger_multiple(self, daq_mask, verbose=False):
        """ Manually trigger the specified DAQs

        Args:
            daq_mask (int)  : the DAQs you are triggering, composed as a bitmask
                              where the LSB is for DAQ_0, bit 1 is for DAQ_1 etc.
        """
        self.SD_AIN.DAQtriggerMultiple(daq_mask)

    ###############################
    # firmware specific functions #  Only for FPGA image firmware 1.x
    ###############################

    def set_MAV_filter(self, maf_length = 16, maf_modulo = 1, fourchannel = False):
        """
        set the moving avererage filter
        Args:
            maf_length (int)
            maf_modulo (int)
        """
        if is_sd1_3x:
            raise Exception('set_MAV_filter is for firmware 2.x')
        # logging.info(f'MAV filter {maf_length}/{maf_modulo}')
        self.SD_AIN.FPGAwritePCport(1, [maf_length], 0, 1, 0)
        self.SD_AIN.FPGAwritePCport(1, [maf_modulo], 1, 1, 0)
        if fourchannel:
            self.SD_AIN.FPGAwritePCport(3, [maf_length], 0, 1, 0)
            self.SD_AIN.FPGAwritePCport(3, [maf_modulo], 1, 1, 0)
        # print('fourchannel MAV')

    def set_meas_time(self, total_time, fourchannel = False):
        """
        set time that there should be sampled.
        Args:
            total_time (ns)
        """
        if is_sd1_3x:
            raise Exception('set_meas_time is for firmware 2.x')
        # logging.info(f'meas time')
        for channel_property in self.channel_properties.values():
            if channel_property.active == True:
                channel_property.t_measure = int(total_time/10)*10

        self.SD_AIN.FPGAwritePCport(0,[ int(total_time/10)], 36, 1, 0)
        if fourchannel:
            self.SD_AIN.FPGAwritePCport(2,[ int(total_time/10)], 36, 1, 0)
        # print('fourchannel meastime' + str(int(total_time/10)))

    ###############################
    # firmware specific functions #  Only for FPGA image firmware 2.x
    ###############################

    def set_lo(self, channel, frequency, phase, input_channel=None):
        '''
        Set the local oscillator for IQ demodulation.

        Args:
            channel (int): channel to configure
            frequency (float): demodulation frequency in Hz
            phase (float): phase shift in degrees
            input_channel (int): input channel to use for IQ demodulation.
        '''
        if not is_iq_image_loaded(self.SD_AIN):
            raise Exception('IQ demodulation FPGA image not loaded')

        properties = self.channel_properties[f'ch{channel}']
        properties.lo_frequency = frequency
        properties.lo_phase = phase
        properties.input_channel = input_channel if input_channel is not None else channel

        if properties.acquisition_mode in [MODES.IQ_DEMODULATION, MODES.IQ_DEMOD_I_ONLY]:
            dig_set_lo(self.SD_AIN, channel, frequency, phase)
            dig_set_input_channel(self.SD_AIN, channel, properties.input_channel)

    def set_measurement_time_averaging(self, channel, t_measure):
        '''
        Changes the measurement time for the channel for AVERAGING and IQ modes.
        It cannot be used in NORMAL mode or when downsample rate has been set, because
        the number of measurements per trigger must be 1.
        Args:
            channel (int): channel
            t_measure (float): measurement time in ns.
        '''
        properties = self.channel_properties[f'ch{channel}']
        if properties.acquisition_mode == 0:
            logging.warning(f'set_measurement_time_averaging() cannot be used in normal mode')
            return

        if properties.downsampled_rate is not None:
            # points_per_cycle cannot change without reconfiguring DAQ.
            logging.warning(f'set_measurement_time_averaging() cannot be used when downsampling ')
            return

        power2decimation = properties.power2decimation
        downsampling_factor = int(max(1, round(t_measure / 10 / 2**power2decimation)))
        eff_t_measure = downsampling_factor * 10 * 2**power2decimation

        if eff_t_measure != properties.t_measure:
            properties.downsampling_factor = downsampling_factor
            properties.points_per_cycle = 1
            properties.t_measure = eff_t_measure
            logging.debug(f'ch{channel} t_measure:{properties.t_measure}')

            dig_set_downsampler(self.SD_AIN, channel, downsampling_factor,
                                properties.points_per_cycle, power2decimation)


    ###########################################################
    # automatic set function for common experimental settings #
    ###########################################################

    def set_digitizer_software(self, t_measure, cycles, sample_rate= 500e6, data_mode = DATA_MODE.FULL,
                               channels = [1,2], Vmax = 2.0, fourchannel = False,
                               downsampled_rate = None, power2decimation = 0):
        """
        quick set of minumal settings to make it work.

        Args:
            t_measure (float) : time to measure in ns
            cycles (int) : number of cycles
            sample_rate (float) : sample rate you want to use (in #Samples/second). Will automatically choose the most approriate one.
            data_mode (int) : data mode of the digizer (output format)
            channels (list) : channels you want to measure
            vmax (double) : maximum voltage of input (Vpeak)
            downsampled_rate (float) : sample rate after downsampling in Sa/s, if None then downsampled_rate = 1/t_measure
            power2decimation (int) : decimate data with 2**power2decimation
        """
        logging.info(f'set digitizer software')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.SOFT_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
#            print('sds input is: %.1f' % sample_rate)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate,
                                  downsampled_rate=downsampled_rate, power2decimation=power2decimation)

        if self.use_old_fpga_averaging:
#            print('setting time and MAF')
            self.set_meas_time(t_measure, fourchannel = fourchannel)
            self.set_MAV_filter(16,1, fourchannel = fourchannel)


    def set_digitizer_analog_trg(self, t_measure, cycles, sample_rate= 500e6, data_mode = DATA_MODE.FULL,
                                 channels = [1,2], Vmax = 2.0, downsampled_rate = None, power2decimation = 0):
        """
        quick set of minumal settings to make it work.

        Args:
            t_measure (float) : time to measure in ns
            cycles (int) : number of cycles
            channels (list) : channels you want to measure
            sample_rate (float) : sample rate you want to use (in #Samples/second)
            data_mode (int) : data mode of the digizer (output format)
            channels (list) : channels you want to measure
            vmax (float) : maximum voltage of input (Vpeak)
            downsampled_rate (float) : sample rate after downsampling in Sa/s, if None then downsampled_rate = 1/t_measure
            power2decimation (int) : decimate data with 2**power2decimation
        """
        logging.info(f'set digitizer analog')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.ANALOG_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate,
                                  downsampled_rate=downsampled_rate, power2decimation=power2decimation)
            self.set_ext_digital_trigger(channel)

        if self.use_old_fpga_averaging:
#            print('setting time and MAF')
            self.set_meas_time(t_measure)
            self.set_MAV_filter(16,1)


    def set_digitizer_HVI(self, t_measure, cycles, sample_rate= 500e6, data_mode = DATA_MODE.FULL,
                          channels = [1,2], Vmax = 2.0, downsampled_rate = None, power2decimation = 0):
        """
        quick set of minimal settings to make it work.

        Args:
            t_measure (float) : time to measure in ns
            cycles (int) : number of cycles
            sample_rate (float) : sample rate you want to use (in #Samples/second). Will automatically choose the most approriate one.
            data_mode (int) : data mode of the digizer (output format)
            channels (list) : channels you want to measure
            vmax (double) : maximum voltage of input (Vpeak)
            downsampled_rate (float) : sample rate after downsampling in Sa/s, if None then downsampled_rate = 1/t_measure
            power2decimation (int) : decimate data with 2**power2decimation
        """
        logging.info(f'set digitizer HVI: {t_measure}, {downsampled_rate}, {channels}')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.HVI_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate,
                                  downsampled_rate=downsampled_rate, power2decimation=power2decimation)


    def _get_aligned_npoints(self, npt):
        # NOTE: add 1 point for odd sample numbers
        return (npt + 1)//2 * 2


if __name__ == '__main__':
#%%
          # load digitizer
    # digitizer1.close()
    digitizer1 = SD_DIG("digitizer1", chassis = 1, slot = 6)

    # clear all ram (normally not needed, but just to sure)
    digitizer1.daq_flush(1)
    digitizer1.daq_flush(2)
    digitizer1.daq_flush(3)
    digitizer1.daq_flush(4)

    # digitizer1.set_acquisition_mode(MODES.AVERAGE)

    #%%
    # simple example
    digitizer1.set_digitizer_software(1e3, 10, sample_rate=500e6, data_mode=DATA_MODE.AVERAGE_TIME_AND_CYCLES, channels=[1,2], Vmax=0.25, fourchannel=False)
    print(digitizer1.measure())
    print(digitizer1.snapshot())
    ####################################
    #  settings (feel free to change)  #
    # ####################################
    # t_list = np.logspace(2.3, 2.7, 20)
    # res =[]
    # for t in t_list:
    #     cycles = 1000
    #     t_measure = t #e3 # ns
    #     ####################################


    #     # show some multiparameter properties
    #     # print(digitizer1.measure.shapes)
    #     # print(digitizer1.measure.setpoint_units)
    #     # print(digitizer1.measure.setpoints)
    #     # # measure the parameter
    #     digitizer1.set_digitizer_software(t_measure, cycles, data_mode=DATA_MODE.FULL, channels = [1,2])
    #     digitizer1.set_MAV_filter()
    #     data = digitizer1.measure()
    #     #    print(data)
    # #    plt.clf()
    #     #    plt.plot(data[0][:,2], 'o-')
    #     #    plt.plot(data[0][:,3], 'o-')
    # #    plt.plot(data[1], 'o-')
    #     # print(data[0].shape, data[1].shape)

    #     res.append(np.mean(data[1]))

    # #t_list = t_list-166
    # #res = np.array(res)/np.array(t_list)
    # plt.figure(2)
    # plt.clf()
    # plt.plot(t_list, res, 'o-')

    #def fit_func(x, m, q):
    #    return x*m+q
    #
    #import scipy
    #param, var = scipy.optimize.curve_fit(fit_func, t_list, res)
    #plt.plot(np.linspace(0, max(t_list), 50), fit_func(np.linspace(0, max(t_list), 50), *param))
    #plt.xlabel('Integration time (ns)')
    #plt.title('Intercept: %.2f' %param[1])