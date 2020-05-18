# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 16:50:02 2019

@author: V2
"""
from qcodes import MultiParameter
from V2_software.HVI_files.charge_stability_diagram.HVI_charge_stability_diagram import load_HVI, set_and_compile_HVI, excute_HVI, HVI_ID
from V2_software.drivers.M3102A import DATA_MODE
import matplotlib.pyplot as plt
import numpy as np


def construct_2D_scan_fast(gate1, swing1, n_pt1, gate2, swing2, n_pt2, t_step, biasT_corr, pulse_lib, digitizer):
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
    
    charge_st_2D  = pulse_lib.mk_segment()
    
    getattr(charge_st_2D, gate1).add_HVI_variable("t_measure", int(t_step))
    getattr(charge_st_2D, gate1).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_2D, gate1).add_HVI_variable("number_of_points", int(n_pt1*n_pt2))
    getattr(charge_st_2D, gate1).add_HVI_variable("averaging", True)

    # set up timing for the scan
    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    step_eff = 2000 + 120 + t_step

    # set up sweep voltages (get the right order, to compenstate for the biasT).
    vp1 = swing1/2
    vp2 = swing2/2

    voltages1 = np.linspace(-vp1,vp1,n_pt1)
    voltages2 = np.zeros(n_pt2)
    if biasT_corr == True:
        voltages2[::2] = np.linspace(-vp2,vp2,n_pt2)[:len(voltages2[::2])]
        voltages2[1::2] = np.linspace(-vp2,vp2,n_pt2)[len(voltages2[1::2]):][::-1]
    else:
        voltages2 = np.linspace(-vp2,vp2,n_pt2)


    getattr(charge_st_2D, gate1).add_ramp_ss(0, step_eff*n_pt1, vp1, -vp1)
    getattr(charge_st_2D, gate1).repeat(n_pt1)

    i = 1
    for  voltage in voltages2:
        getattr(charge_st_2D,gate2).add_block(0, step_eff*n_pt1, voltage)
        getattr(charge_st_2D,gate2).reset_time()
            
    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_2D])
    # my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate
    # my_seq.upload([0])
    
    return _digitzer_scan_parameter(digitizer, my_seq, pulse_lib, t_step, (n_pt1, n_pt2), (gate1, gate2), (voltages1, np.sort(voltages2)), biasT_corr, 500e6)



class _digitzer_scan_parameter(MultiParameter):
    """
    generator for the parameter f
    """
    def __init__(self, digitizer, my_seq, pulse_lib, t_measure, shape, names, setpoint, biasT_corr, sample_rate, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2]):
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
        super().__init__(name=digitizer.name, names = digitizer.measure.names, shapes = tuple([shape]*len(digitizer.measure.names)),
                        labels = digitizer.measure.labels, units = digitizer.measure.units,
                        setpoints = tuple([setpoint]*len(digitizer.measure.names)), setpoint_names=tuple([names]*len(digitizer.measure.names)),
                        setpoint_labels=tuple([names]*len(digitizer.measure.names)), setpoint_units=tuple([tuple(["mV"]*len(names))]*len(digitizer.measure.names)),
                        docstring='1D scan parameter for digitizer')
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

    def get_raw(self):
        # clean up the digitizer
        self.dig.daq_flush(1)
        self.dig.daq_flush(2)
        self.dig.daq_flush(3)
        self.dig.daq_flush(4)

        # set digitizer
        self.dig.set_digitizer_HVI(self.t_measure, int(np.prod(self.shape)), sample_rate = self.sample_rate, data_mode = self.data_mode, channels = self.channels)

        # play sequence
        # self.my_seq.play([0], release = False)
        # self.pulse_lib.uploader.wait_until_AWG_idle()

        data_out = [np.zeros(self.shape)]*len(self.channels)
        # get the data
        data = list(self.dig.measure())

        # make sure that data is put in the right order.
        for i in range(len(data)):
            data[i] = data[i].reshape(self.shape)
            if self.biasT_corr:
                data_out[i][:len(data[i][::2])] = data[i][::2]
                data_out[i][len(data[i][::2]):] = data[i][1::2][::-1]

        return tuple(data)

    def __del__(self):
        # remove pulse sequence from the AWG's memory.
        # self.my_seq.play([0], release = True)
        # no blocking on HVI, so can just overwrite this.
        # self.pulse_lib.uploader.release_memory()
        pass

if __name__ == '__main__':
    import V2_software.drivers.M3102A as M3102A
    from V2_software.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
    from V2_software.pulse_lib_config.init_pulse_lib import return_pulse_lib
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