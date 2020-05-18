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


def construct_1D_scan_fast(gate, swing, n_pt, t_step, biasT_corr, pulse_lib, digitizer):
    """
    1D fast scan object for V2.

    Args:
        gate (str, list) : gate/gates that you want to sweep.
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
    if isinstance(gate, str):
        gate = [gate]
    
    vp = swing/2

    getattr(charge_st_1D, gate[0]).add_HVI_variable("t_measure", int(t_step))
    getattr(charge_st_1D, gate[0]).add_HVI_variable("digitizer", digitizer)
    getattr(charge_st_1D, gate[0]).add_HVI_variable("number_of_points", int(n_pt))
    getattr(charge_st_1D, gate[0]).add_HVI_variable("averaging", True)

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


    for my_gate in gate:
        for  voltage in voltages:
            getattr(charge_st_1D,my_gate).add_block(0, step_eff, voltage)
            getattr(charge_st_1D,my_gate).reset_time()
            
    
    # 100 time points per step to make sure that everything looks good (this is more than needed).
    awg_t_step = t_step /10
    sample_rate = 1/(awg_t_step*1e-9)

    # generate the sequence and upload it.
    my_seq = pulse_lib.mk_sequence([charge_st_1D])
    my_seq.add_HVI(HVI_ID, load_HVI, set_and_compile_HVI, excute_HVI)
    my_seq.n_rep = 1
    my_seq.sample_rate = sample_rate

    my_seq.upload([0])
    
    return _digitzer_1D_scan_parameter(digitizer, my_seq, pulse_lib, t_step, n_pt, gate, voltages, 500e6)



class _digitzer_1D_scan_parameter(MultiParameter):
        def __init__(self, digitizer, my_seq, pulse_lib, t_measure, n_rep, gates, setpoint, sample_rate, data_mode = DATA_MODE.AVERAGE_TIME, channels = [1,2]):
            """
            args:
                digitizer : digizer driver:
                my_seq : sequence of the 1D scan
                pulse_lib : pulse library object
                t_step : time to measure per step
                n_rep : number of points to measure
                gates : name of the gate(s) that are measured.
                sample_rate : sample rate of the digitizer card that should be used.
                data mode : data mode of the digizer
                channel : channels to measure
            """
            digitizer.set_digitizer_HVI(t_measure, n_rep, sample_rate = sample_rate, data_mode = data_mode, channels =  channels)
            print(tuple([tuple([str(gates[0])],)]*len(digitizer.measure.names)))
            super().__init__(name=digitizer.name, names = digitizer.measure.names, shapes = digitizer.measure.shapes,
                            labels = digitizer.measure.labels, units = digitizer.measure.units,
                            setpoints = tuple([tuple([tuple(np.sort(setpoint))],)]*len(digitizer.measure.names)), setpoint_names=tuple([tuple([str(gates[0])],)]*len(digitizer.measure.names)),
                            setpoint_labels=tuple([tuple([str(gates[0])],)]*len(digitizer.measure.names)), setpoint_units=tuple([tuple(["mV"],)]*len(digitizer.measure.names)),
                            docstring='1D scan parameter for digitizer')
            self.dig = digitizer
            self.my_seq = my_seq
            self.pulse_lib = pulse_lib
            self.t_measure = t_measure
            self.n_rep = n_rep
            self.sample_rate =sample_rate
            self.data_mode = data_mode
            self.channels = channels
            self.data_sorting = np.argsort(setpoint)

        def get_raw(self):
            # clean up the digitizer
            self.dig.daq_flush(1)
            self.dig.daq_flush(2)
            self.dig.daq_flush(3)
            self.dig.daq_flush(4)

            # set digitizer
            self.dig.set_digitizer_HVI(self.t_measure, self.n_rep, sample_rate = self.sample_rate, data_mode = self.data_mode, channels =  self.channels)

            # play sequence
            self.my_seq.play([0], release = False)
            self.pulse_lib.uploader.wait_until_AWG_idle()

            # get the data
            data = list(self.dig.measure())

            # make sure that data is put in the right order.
            for i in range(len(data)):
                data[i] = data[i][self.data_sorting]

            return tuple(data)

        def __del__(self):
            # remove pulse sequence from the AWG's memory.
            self.my_seq.play([0], release = True)
            # no blocking on HVI, so can just overwrite this.
            self.pulse_lib.uploader.release_memory()


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

    param = construct_1D_scan_fast('P2', 1000, 200, 50000, True, pulse, dig)
    param.get()
