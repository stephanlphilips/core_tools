from qcodes import Instrument, MultiParameter
from dataclasses import dataclass
import warnings
import logging
import time

try:
    import keysightSD1
except:
    warnings.warn("\nAttemting to use a file that needs Keysight AWG libraries. Please install if you need them.\n")

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
    Modes to be operating in
    """
    NORMAL = 0
    AVERAGE = 1 #note different firmware needed for this (DEMOD package)

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
            self.trigger_digitzers()

        return self.get_data()


    def _read_channel_data(self, channel_number, channel_data_raw):
        start = time.perf_counter()
        i = 0
        points_aquired = 0
        while points_aquired < len(channel_data_raw):
            np_ready = self.my_instrument.SD_AIN.DAQcounterRead(channel_number)
            check_error(np_ready)

            if np_ready + points_aquired > len(channel_data_raw):
                np_ready = len(channel_data_raw) - points_aquired
                logging.error("more data points in digitizer ram then what is being collected.")


            if np_ready > 0:
                # Always read with a timeout to prevent infinite blocking of HW (and reboot of system).
                # There are np_ready points available. This can be read in 1 second.
                req_points = self.my_instrument.SD_AIN.DAQread(channel_number, np_ready, 1000)
                check_error(req_points)
                if not type(req_points) is int and len(req_points) != np_ready:
                    logging.error(f'DAQread failure. ready:{np_ready} read:{len(req_points)}')

                channel_data_raw[points_aquired: points_aquired + np_ready] = req_points
                points_aquired = points_aquired + np_ready
                i = 0

            if np_ready == 0:
                i+=1
                time.sleep(0.001)
                if i > 100:
                    logging.error(f"digitizer did not manage to collect enough data points for channel {channel_number}, "
                                  f"returning zeros. ({points_aquired})")
                    break

        logging.info(f'channel {channel_number}: retrieved {points_aquired} points in {(time.perf_counter()-start)*1000:3.1f} ms')


    def _get_data_normal(self):
        data_out = tuple()

        for channel_property in self.my_instrument.channel_properties.values():
            if channel_property.active == False:
                continue

            # make flat data structures.
            channel_data_raw = np.zeros([channel_property.cycles*channel_property.points_per_cycle], np.double)

            self._read_channel_data(channel_property.number, channel_data_raw)

            # format the data with correct amplitude
            # convert 16-bit to relative scale (-1.0 .. 1.0)
            f = 1 / 32768
            # multiply with the relevant channel amplitude (standard in volt -> mV!)
            f *= channel_property.full_scale*1000
            # inplace multiplication on numpy array is fast
            channel_data_raw *= f

            # reshape for [repetitions, time] and average
            channel_data_raw = channel_data_raw.reshape([channel_property.cycles, channel_property.points_per_cycle])

            if self.my_instrument.data_mode == DATA_MODE.FULL:
                data_out += (channel_data_raw, )
            elif self.my_instrument.data_mode == DATA_MODE.AVERAGE_TIME:
                data_out += (np.average(channel_data_raw, axis = 1), )
            elif self.my_instrument.data_mode == DATA_MODE.AVERAGE_CYCLES:
                data_out += (np.average(channel_data_raw, axis = 0), )
            elif self.my_instrument.data_mode == DATA_MODE.AVERAGE_TIME_AND_CYCLES:
                data_out += (np.average(channel_data_raw), )

        return data_out


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
            # outputs V, 5 for the aquisition in blocks of 5
            channel_data[0] *= 5 * 2/(channel_property.t_measure-160)*channel_property.full_scale / 2**15
            channel_data[1] *= 5 * 2/(channel_property.t_measure-160)*channel_property.full_scale / 2**15

            # only add the data of the selected channels.
            if channel_property.number in self.channels:
                if self.my_instrument.data_mode in [DATA_MODE.AVERAGE_CYCLES, DATA_MODE.AVERAGE_TIME_AND_CYCLES]:
                   data_out += (np.average(channel_data[0]), )
                else:
                    data_out += (channel_data[0], )

            if channel_property.number + 1 in self.channels:
                if self.my_instrument.data_mode in [DATA_MODE.AVERAGE_CYCLES, DATA_MODE.AVERAGE_TIME_AND_CYCLES]:
                   data_out += (np.average(channel_data[1]), )
                else:
                    data_out += (channel_data[1], )

        return data_out


    def get_data(self):
        """
        Get data from the cards
        """
        if self.my_instrument.mode == MODES.NORMAL:
            return self._get_data_normal()
        else:
            return self._get_data_average()


    def start_digitizers(self):
        # start digizers.
        self.my_instrument.daq_start_multiple(self.channel_mask)

    def trigger_digitzers(self):
        # trigger the digitizers.
        for i in range(self.my_instrument.channel_properties['ch{}'.format(self.channels[0])].cycles):
            self.my_instrument.daq_trigger_multiple(self.channel_mask)

    def _generate_parameter_info(self):
        """
        Generate the correct labels/units for the digitizer parameter
        """
        self.names = tuple()
        self.shapes = tuple()
        self.labels = tuple()
        self.units = tuple()

        self.setpoints = tuple()
        self.setpoint_labels = tuple()
        self.setpoint_names = tuple()
        self.setpoint_units = tuple()

        for channel_property in self.my_instrument.channel_properties.values():
            if channel_property.active == True:
                self.names += (channel_property.name, )
                self.labels += ("digitizer output ch{}".format(channel_property.number) , )
                self.units += ("mV" , )

                shape = tuple()
                setpoints = tuple()
                setpoint_names = tuple()
                setpoint_labels = tuple()
                setpoint_units = tuple()
                if self.my_instrument.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_TIME] :
                    shape += (channel_property.cycles, )
                    # setpoints need to be a tuple for hash look-up in qcodes ..
                    setpoints += (tuple(np.linspace(1,channel_property.cycles,channel_property.cycles)), )
                    setpoint_names += ("nth_cycle_ch{}".format(channel_property.number ), )
                    setpoint_labels += ("nth cycle", )
                    setpoint_units += ("#", )

                if self.my_instrument.data_mode in [DATA_MODE.FULL, DATA_MODE.AVERAGE_CYCLES] :
                    if self.my_instrument.mode == MODES.NORMAL:
                        shape += (channel_property.points_per_cycle, )
                        setpoints += (tuple(np.linspace(1/channel_property.sample_rate*1e9,channel_property.t_measure,channel_property.points_per_cycle)), )
                        setpoint_names += ("time_ch_{}".format(channel_property.number ), )
                        setpoint_labels += ("time", )
                        setpoint_units += ("ns", )

                self.shapes += (shape, )

                self.setpoints += (setpoints, )
                self.setpoint_labels +=  (setpoint_labels, )
                self.setpoint_names += (setpoint_names, )
                self.setpoint_units += (setpoint_units, )

@dataclass
class channel_properties:
    """
    structure to save relevant information about marker data.
    """
    name : str
    number : int
    active : bool = False
    points_per_cycle : int = 0
    cycles : int = 0
    full_scale : float = 0 #peak voltage
    t_measure : float = 0 #measurement time in ns of the channel
    sample_rate : float = 500e6

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
        dig_name = self.SD_AIN.getProductNameBySlot(chassis, slot)
        self.SD_AIN.openWithSlot(dig_name, chassis, slot)
        self.chassis = chassis
        self.slot = slot

        """
        Modes to be operating in:
            0 : normal
            1 : averaging of traces (different firmware)
        """
        self.mode = 0

        """
        Modes for operation
            0 : use software triggers (does call start and trigger in software)
            1 : use external triggering (does call start digitizer)
            2 : use HVI for triggering (no calls done)
        """
        self.operation_mode = 0

        """
        mode of handling data. Determines what will be saved.
            0 : no averaging at all, get back full output data
            1 : average on x axis --> average a full trace to a single point
            2 : average on y axis --> average over all the iterations
            3 : average on x and y axis, in other words, get back a single point
        """
        self.data_mode = 0

        self.channel_properties = dict()
        for i in range(n_channels):
            self.channel_properties['ch{}'.format(i+1)] = channel_properties('ch{}'.format(i+1), i + 1)

        self.add_parameter(
            'measure',
            inst_name = self.name,
            parameter_class=line_trace,
            raw =False
            )

    def set_aquisition_mode(self, mode):
        """
        Modes to be operating in:
            0 : normal
            1 : averaging of traces (Keysight DEMOD modules needed for this)
        """
        self.mode = mode
        self.measure._generate_parameter_info()

    def set_data_handling_mode(self, data_mode):
        """
        mode of handling data. Determines what will be saved.
            0 : no averaging at all, get back full output data
            1 : average on x axis --> average a full trace to a single point
            2 : average on y axis --> average over all the iterations
            3 : average on x and y axis, in other words, get back a single point
        """
        self.data_mode = data_mode
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
        for channel_property in self.channel_properties.values():
            if channel_property.number in channels:
                channel_property.active = True
            else:
                channel_property.active = False

        self.measure._generate_parameter_info()

    def set_channel_properties(self, channel, V_range, impedance=1, coupling=0):
        """
        sets quickly relevant channel properties.
        TODO: We need a validator on Vrange.
        Args:
            channel : channel number (1 to 4)
            V_range: amplitude range +- X Volts
            impedance: 0(HiZ), 1 (50 Ohm)
            coulping: 0 (DC), 1 (AC)
            prescalor: see manual, default 0
        """
        self.SD_AIN.channelInputConfig(channel, V_range, impedance, coupling)
        # assign channel_properties
        self.channel_properties['ch{}'.format(channel)].full_scale = V_range
        self.measure._generate_parameter_info()

    def set_daq_settings(self, channel, n_cycles, t_measure, sample_rate = 500e6, DAQ_trigger_delay = 0, DAQ_trigger_mode = 1):
        """
        quickset for the daq settings
        Args:
            n_cycles (int) : number of trigger to record.
            t_measure (float) : time to measure (unit : ns)
            sample_rate (float) : sample rate of the channel in S/s
            DAQ_trigger_delay (int) : use HVI for this..
            DAQ_trigger_mode (int) : 1 for HVI see manual for other options. (2 is external trigger)
        """

        # find aproriate prescalor if needed
        prescaler = int(500e6/sample_rate -1)
#        print(prescaler)
        if prescaler < 0:
            prescaler = 0
#        if prescaler > 1.: #seems to be a bug, prescalor of >1 does not seem to prescale ... .
#            prescaler = 1
#        print(prescaler)
        sample_rate = 500e6/(prescaler+1)
        # print("Effective sampling frequency is set to {}S/s (prescaler = {})".format(si_format(sample_rate, precision=1), prescaler))

        points_per_cycle = int(t_measure*1e-9*sample_rate)
#        print(t_measure)
#        print(sample_rate)
#        print(points_per_cycle)
        # variables needed to generate correct setpoints and for data aquisition
        self.channel_properties['ch{}'.format(channel)].points_per_cycle = points_per_cycle
        self.channel_properties['ch{}'.format(channel)].cycles = n_cycles
        self.channel_properties['ch{}'.format(channel)].t_measure = points_per_cycle*1e9/sample_rate
        self.channel_properties['ch{}'.format(channel)].sample_rate = sample_rate

        # overide in case of on card averaging.
        if self.mode == MODES.AVERAGE:
            points_per_cycle = 10
            prescaler = 0 #just run at max sample rate (causes problems if you change this).

        # set the settings
        self.SD_AIN.DAQconfig(channel, points_per_cycle, n_cycles, DAQ_trigger_delay, DAQ_trigger_mode)
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
        points_per_cycle = self.channel_properties['ch{}'.format(channel)].points_per_cycle
        n_cycles = self.channel_properties['ch{}'.format(channel)].cycles
        self.SD_AIN.DAQconfig(channel, points_per_cycle, n_cycles, delay, 2)

    def daq_flush(self, daq, verbose=False):
        """
        Flush the specified DAQ
        Args:
            daq (int)       : the DAQ you are flushing
        """
        self.SD_AIN.DAQflush(daq)

    def daq_stop(self, daq, verbose=False):
        """ Stop acquiring data on the specified DAQ
        Args:
            daq (int)       : the DAQ you are disabling
        """
        self.SD_AIN.DAQstop(daq)

    def writeRegisterByNumber(self, regNumber, varValue):
        """
        Write to a register of the AWG, by reffreing to the register number
        Args:
            regNumber (int) : number of the registry (0 to 16)
            varValue (int/double) : value to be written into the registry
        Returns:
            Value (int) : error out (negative number)
        """
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
    # firmware specific functions # (custom for V2, bound to change.)
    ###############################

    def set_MAV_filter(self, maf_length = 16, maf_modulo = 1, fourchannel = False):
        """
        set the moving avererage filter
        Args:
            maf_length (int)
            maf_modulo (int)
        """
#        logging.info(f'MAV filter {maf_length}/{maf_modulo}')
        self.SD_AIN.FPGAwritePCport(3, [maf_length], 0, 1, 0)
        self.SD_AIN.FPGAwritePCport(3, [maf_modulo], 1, 1, 0)
        if fourchannel:
#            print('fourchannel MAV')
            self.SD_AIN.FPGAwritePCport(1, [maf_length], 0, 1, 0)
            self.SD_AIN.FPGAwritePCport(1, [maf_modulo], 1, 1, 0)

    def set_meas_time(self, total_time, fourchannel = False):
        """
        set time that there should be sampled.
        Args:
            total_time (ns)
        """
#        logging.info(f'meas time')
        for channel_property in self.channel_properties.values():
            if channel_property.active == True:
                channel_property.t_measure = int(total_time/10)*10

        self.SD_AIN.FPGAwritePCport(2,[ int(total_time/10)], 36, 1, 0)
        if fourchannel:
#            print('fourchannel meastime' + str(int(total_time/10)))
            self.SD_AIN.FPGAwritePCport(0,[ int(total_time/10)], 36, 1, 0)

    ###########################################################
    # automatic set function for common experimental settings #
    ###########################################################

    def set_digitizer_software(self, t_measure, cycles, sample_rate= 500e6, data_mode = DATA_MODE.FULL, channels = [1,2], Vmax = 2, fourchannel = False):
        """
        quick set of minumal settings to make it work.
        Args:
            t_measure (float) : time to measure in ns
            cycles (int) : number of cycles
            sample_rate (float) : sample rate you want to use (in #Samples/second). Will automatically choose the most approriate one.
            data_mode (int) : data mode of the digizer (output format)
            channels (list) : channels you want to measure
            vmax (double) : maximum voltage of input (Vpeak)
        """
        logging.info(f'set digitizer software')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.SOFT_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
#            print('sds input is: %.1f' % sample_rate)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate)

        if self.mode == MODES.AVERAGE:
#            print('setting time and MAF')
            self.set_meas_time(t_measure, fourchannel = fourchannel)
            self.set_MAV_filter(16,1, fourchannel = fourchannel)

    def set_digitizer_analog_trg(self, t_measure, cycles, sample_rate= 500e6, data_mode = DATA_MODE.FULL, channels = [1,2], Vmax = 2):
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
        """
        logging.info(f'set digitizer analog')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.ANALOG_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate)
            self.set_ext_digital_trigger(channel)

        if self.mode == MODES.AVERAGE:
            self.set_meas_time(t_measure)
            self.set_MAV_filter(16,1)

    def set_digitizer_HVI(self, t_measure, cycles, sample_rate=500e6, data_mode=DATA_MODE.FULL, channels=[1,2], Vmax=2):
        """
        quick set of minimal settings to make it work.
        Args:
            t_measure (float) : time to measure in ns
            cycles (int) : number of cycles
            sample_rate (float) : sample rate you want to use (in #Samples/second). Will automatically choose the most approriate one.
            data_mode (int) : data mode of the digizer (output format)
            channels (list) : channels you want to measure
            vmax (double) : maximum voltage of input (Vpeak)
        """
        logging.info(f'set digitizer HVI')
        self.set_data_handling_mode(data_mode)

        self.set_operating_mode(OPERATION_MODES.HVI_TRG)
        self.set_active_channels(channels)
        for channel in channels:
            self.set_channel_properties(channel, Vmax)
            self.set_daq_settings(channel, cycles, t_measure, sample_rate)


if __name__ == '__main__':
#%%
          # load digitizer
    # digitizer1.close()
    digitizer1 = SD_DIG("digitizer1", chassis = 0, slot = 6)

    # clear all ram (normally not needed, but just to sure)
    digitizer1.daq_flush(1)
    digitizer1.daq_flush(2)
    digitizer1.daq_flush(3)
    digitizer1.daq_flush(4)

    # digitizer1.set_aquisition_mode(MODES.AVERAGE)

    #%%
    # simple example
    digitizer1.set_digitizer_software(1e3, 10, sample_rate=500e6, data_mode=DATA_MODE.AVERAGE_TIME_AND_CYCLES, channels=[1,2], Vmax=0.25, fourchannel=False)
    print(digitizer1.measure())
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