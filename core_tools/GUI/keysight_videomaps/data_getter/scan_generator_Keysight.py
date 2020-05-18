# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 16:50:02 2019

@author: V2
"""
from qcodes import MultiParameter
from projects.keysight_measurement.HVI.ChargeStabilityDiagram.HVI_charge_stability_diagram import load_HVI, set_and_compile_HVI, excute_HVI, HVI_ID
from projects.keysight_measurement.M3102A import DATA_MODE
import matplotlib.pyplot as plt
import numpy as np
import time
import logging

def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer, channels, dig_samplerate):
    """
    1D fast scan object for V2.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point.
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    charge_st_1D  = pulse_lib.mk_segment()


    vp = swing/2

    getattr(charge_st_1D, gate).add_HVI_variable("t_measure", int(t_step))
    getattr(charge_st_1D, gate).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_1D, gate).add_HVI_variable("number_of_points", int(n_pt))
    getattr(charge_st_1D, gate).add_HVI_variable("averaging", True)

    # set up timing for the scan
    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    step_eff = 2000 + 120 + t_step

    logging.info(f'Construct 1D: {gate}')

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages = np.zeros(n_pt)
    if biasT_corr == True:
        voltages[::2] = np.linspace(-vp,vp,n_pt)[:len(voltages[::2])]
        voltages[1::2] = np.linspace(-vp,vp,n_pt)[len(voltages[1::2]):][::-1]
    else:
        voltages = np.linspace(-vp,vp,n_pt)

    for  voltage in voltages:
        getattr(charge_st_1D, gate).add_block(0, step_eff, voltage)
        getattr(charge_st_1D, gate).reset_time()


    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_1D])
    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Upload')
    my_seq.upload([0])

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt, ), (gate, ), (tuple(voltages), ), biasT_corr, dig_samplerate, channels = channels)

def construct_1D_scan_MOD(gate, swing, n_pt, MOD_gates, freq_start, freq_step , biasT_corr, pulse_lib, digitizer, channels, dig_samplerate):
    """
    1D fast scan object for V2.

    Args:
        gate (str) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        MOD_gates (list<str>) : list with gates to be modulated
        freq_start (double) : freq to start for the modulation (e.g. 100kHz)
        freq_step (double) : step to be used (e.g. 100kHz  generates--> 100kHz, 300kHz ,300kHz, 400kHz, ...)
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    charge_st_1D  = pulse_lib.mk_segment()


    vp = swing/2

    # 10 times longer than the bandwith
    t_measure = 1/freq_step*10

    getattr(charge_st_1D, gate).add_HVI_variable("t_measure", int(t_step))
    getattr(charge_st_1D, gate).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_1D, gate).add_HVI_variable("number_of_points", int(n_pt))
    getattr(charge_st_1D, gate).add_HVI_variable("averaging", False)

    # set up timing for the scan
    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    step_eff = 2000 + 120 + t_step

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    voltages = np.zeros(n_pt)
    if biasT_corr == True:
        voltages[::2] = np.linspace(-vp,vp,n_pt)[:len(voltages[::2])]
        voltages[1::2] = np.linspace(-vp,vp,n_pt)[len(voltages[1::2]):][::-1]
    else:
        voltages = np.linspace(-vp,vp,n_pt)

    for  voltage in voltages:
        getattr(charge_st_1D, gate).add_block(0, step_eff, voltage)
        getattr(charge_st_1D, gate).reset_time()


    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_1D])
    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    my_seq.upload([0])

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt, ), (gate, ), (tuple(voltages), ), biasT_corr, dig_samplerate, channels = channels)

def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib, digitizer, channels, dig_samplerate):
    """
    1D fast scan object for V2.

    Args:
        gates1 (str) : gate that you want to sweep on x axis.
        swing1 (double) : swing to apply on the AWG gates.
        n_pt1 (int) : number of points to measure (current firmware limits to 1000)
        gate2 (str) : gate that you want to sweep on y axis.
        swing2 (double) : swing to apply on the AWG gates.
        n_pt2 (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point.
        biasT_corr (bool) : correct for biasT by taking data in different order.
        pulse_lib : pulse library object, needed to make the sweep.
        digitizer_measure : digitizer object

    Returns:
        Paramter (QCODES multiparameter) : parameter that can be used as input in a conversional scan function.
    """

    logging.info(f'Construct 2D: {gate1} {gate2}')

    charge_st_2D  = pulse_lib.mk_segment()

    getattr(charge_st_2D, gate1).add_HVI_variable("t_measure", int(t_step))
    getattr(charge_st_2D, gate1).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_2D, gate1).add_HVI_variable("number_of_points", int(n_pt1*n_pt2))
    getattr(charge_st_2D, gate1).add_HVI_variable("averaging", True)

    # set up timing for the scan
    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    # [SdS] Why is the value below 120 ns?
    step_eff = 2000 + 120 + t_step

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1 = np.linspace(-vp1,vp1,n_pt1)
    voltages2 = np.zeros(n_pt2)
    voltages2_sp = np.linspace(-vp2,vp2,n_pt2)

    if biasT_corr == True:
        voltages2[::2] = np.linspace(-vp2,vp2,n_pt2)[:len(voltages2[::2])]
        voltages2[1::2] = np.linspace(-vp2,vp2,n_pt2)[-len(voltages2[1::2]):][::-1]
    else:
        voltages2 = np.linspace(-vp2,vp2,n_pt2)

    getattr(charge_st_2D, gate1).add_ramp_ss(0, step_eff*n_pt1, -vp1, vp1)
    getattr(charge_st_2D, gate1).repeat(n_pt1)

    for voltage in voltages2:
        getattr(charge_st_2D,gate2).add_block(0, step_eff*n_pt1, voltage)
        getattr(charge_st_2D,gate2).reset_time()

    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_2D])
    logging.info(f'Add HVI')
    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    logging.info(f'Seq upload')
    my_seq.upload([0])

    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt2, n_pt1), (gate2, gate1), (tuple(voltages2_sp), (tuple(voltages1),)*n_pt2), biasT_corr, dig_samplerate, channels = channels)


class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, sample_rate, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2,3,4]):
        """
        args:
            digitizer (SD_DIG) : digizer driver:
            my_seq (sequencer) : sequence of the 1D scan
            pulse_lib (pulselib): pulse library object
            t_measure (int) : time to measure per step
            shape (tuple<int>): expected output shape
            names (tuple<str>): name of the gate(s) that are measured.
            setpoint (tuple<np.ndarray>): array witht the setpoints of the input data
            biasT_corr (bool): bias T correction or not -- if enabled -- automatic reshaping of the data.
            sample_rate (float): sample rate of the digitizer card that should be used.
            data mode (int): data mode of the digizer
            channels (list<int>): channels to measure
        """
        self.dig = digitizer
        self.my_seq = my_seq
        self.pulse_lib = pulse_lib
        self.t_measure = t_measure
        self.n_rep = np.prod(shape)
        self.sample_rate =sample_rate
        self.data_mode = data_mode
        self.channels = channels
        self.biasT_corr = biasT_corr
        self.shape = shape
        self.n_ch = len(channels)

        # set digitizer for proper init
        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate, data_mode = self.data_mode, channels = self.channels)

        super().__init__(name=digitizer.name, names = digitizer.measure.names,
                        shapes = tuple([shape]*self.n_ch),
                        labels = digitizer.measure.labels, units = digitizer.measure.units,
                        setpoints = tuple([setpoint]*self.n_ch), setpoint_names=tuple([names]*self.n_ch),
                        setpoint_labels=tuple([names]*self.n_ch), setpoint_units=(("mV",)*len(names),)*self.n_ch,
                        docstring='Scan parameter for digitizer')

    def get_raw(self):
        logging.info(f'Stop/flush')
        # clean up the digitizer
        for ch in range(1,5):
            self.dig.daq_stop(ch)
            self.dig.daq_flush(ch)

        # set digitizer
        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate, data_mode = self.data_mode, channels = self.channels)

        logging.info(f'Play')
        start = time.perf_counter()
        # play sequence
        self.my_seq.play([0], release = False)
        self.pulse_lib.uploader.wait_until_AWG_idle()
        logging.info(f'AWG idle after {(time.perf_counter()-start)*1000:3.1f} ms')

        data_out = []
        for i in self.channels:
            data_out.append(np.zeros(self.shape))

        # get the data
        data = list(self.dig.measure())

        # make sure that data is put in the right order.
        for i in range(len(data)):
            data[i] = data[i].reshape(self.shape)
            data[i] = data[i]
            if self.biasT_corr:
                data_out[i][:len(data[i][::2])] = data[i][::2]
                data_out[i][len(data[i][::2]):] = data[i][1::2][::-1]
            else:
                data_out[i] = data[i]

        logging.info(f'Done')
        return tuple(data_out)

    def stop(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.info('last play to cleanup')
            # remove pulse sequence from the AWG's memory.
            self.my_seq.play([0], release = True)
            # no blocking on HVI, so can just overwrite this.
            self.pulse_lib.uploader.release_memory()
            self.my_seq = None
            self.pulse_lib = None


    def __del__(self):
        if not self.my_seq is None and not self.pulse_lib is None:
            logging.error(f'Cleanup in __del__(); Call stop()!')
            self.stop()

if __name__ == '__main__':
    import V2_software.drivers.M3102A as M3102A
    from V2_software.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
    from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib_debug
    from qcodes.instrument_drivers.Keysight.SD_common.SD_AWG import SD_AWG


    dig = M3102A.SD_DIG("digitizer1", chassis = 0, slot = 6)
    firmware_loader(dig, M3102A_AVG)

    awg1 = SD_AWG("AWG1", chassis = 0, slot = 2, channels=4, triggers=8)
    awg2 = SD_AWG("AWG2", chassis = 0, slot = 3, channels=4, triggers=8)
    awg3 = SD_AWG("AWG3", chassis = 0, slot = 4, channels=4, triggers=8)
    awg4 = SD_AWG("AWG4", chassis = 0, slot = 5, channels=4, triggers=8)

    pulse, vg, fs = return_pulse_lib(awg1, awg2, awg3, awg4)

    param = construct_2D_scan_fast('P2', 10, 10, 'P5', 10, 10,50000, True, pulse, dig)
    data = param.get()
    print(data)

    param_1D = construct_1D_scan_fast("P2", 10,10,5000, True, pulse, dig)
    data_1D = param.get()
    print(data_1D)