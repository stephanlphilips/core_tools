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


def construct_1D_scan_fast(gate, swing, n_pt, t_step, mod_gates, f_center, f_step, pulse_lib, digitizer):
    """
    1D fast scan object for V2.

    Args:
        gate (str, list) : gate/gates that you want to sweep.
        swing (double) : swing to apply on the AWG gates.
        n_pt (int) : number of points to measure (current firmware limits to 1000)
        t_step (double) : time in ns to measure per point.
        mod_gates (list<str>) : list of gates that need to be modulated troughout the sweep
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

    # 2us needed to rearm digitizer
    # 100ns HVI waiting time
    step_eff = 2000 + 120 + t_step
    for my_gate in gate:
        for  voltage in np.linspace(-vp,vp,n_pt):
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
    
    return _digitzer_1D_scan_parameter(digitizer, my_seq, pulse_lib, t_step, n_pt, gate, np.linspace(-vp,vp,n_pt), 500e6)



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
                            setpoints = digitizer.measure.setpoints, setpoint_names=tuple([tuple([str(gates[0])],)]*len(digitizer.measure.names)),
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
            data = self.dig.measure()

            return data

        def __del__(self):
            # remove pulse sequence from the AWG's memory.
            self.my_seq.play([0], release = True)
            # no blocking a HVI can just overwrite this.
            self.pulse_lib.uploader.release_memory()


if __name__ == '__main__':
    param = construct_1D_scan_fast('vP4', 1000, 200, 50000, station.pulse, station.dig)
    param.get()
