import core_tools as ct
from core_tools.sweeps.scans import Scan, SequenceFunction
import qcodes as qc

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = qc.Station()

#%%
from pulse_lib.base_pulse import pulselib
from pulse_lib.tests.mock_m3202a import MockM3202A
from pulse_lib.tests.mock_m3102a import MockM3102A

# create station with AWG, Dig
awg = MockM3202A('AWG1', 1, 2)
digitizer = MockM3102A('Digitizer', 1, 2)
station.add_component(awg)
station.add_component(digitizer)

# create pulselib with P1, P2, PSD1
pulse = pulselib('Keysight')
pulse.add_awg(awg)
pulse.define_channel('P1', awg.name, 1)
pulse.define_channel('P2', awg.name, 2)
pulse.define_channel('PSD1', awg.name, 3)
pulse.add_digitizer(digitizer)
pulse.define_digitizer_channel('SD1', digitizer.name, 1)
pulse.configure_digitizer = True
pulse.finish_init()

#%%
from pulse_lib.tests.hw_schedule_mock import HardwareScheduleMock
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import construct_1D_scan_fast
import pulse_lib.segments.utility.looping as lp

v_sweep = 20.0 # mV
n_pt = 100
t_measure = 20_000 # ns
channels = [1,2]
sensor_scan_param = construct_1D_scan_fast('PSD1', v_sweep, n_pt, t_measure, False,
                                           pulse, digitizer, channels)

def inner_scan_calibration():
    data = sensor_scan_param()
    # process data and set sensor voltage.

    # NOTE: Wait at least 2x bias-T time after changing sensor voltage
    # Bias-T acts as a low-pass filter for the DAC.
    # After 2x bias-T time 87% of difference has been transfered to device
    # After 3x bias-T time 95% of difference has been transfered to device
    # After 4x bias-T time 98% of difference has been transfered to device


amplitude = lp.linspace(20, 200, 10, name='amplitude', unit='mV', axis=0)
duration = lp.linspace(10, 20, 3, name='duration', unit='ns', axis=1)

seg = pulse.mk_segment()
seg['P1'].add_block(0, duration, amplitude)
seg['SD1'].acquire(0, 1000, wait=True)

sequence = pulse.mk_sequence([seg])
sequence.set_hw_schedule(HardwareScheduleMock())
m_param = sequence.get_measurement_param()

ds = Scan(
        sequence,
        SequenceFunction(inner_scan_calibration, axis='duration'),
        m_param,
        name='Scan with calibration demo',
        silent=True).run()

ds = Scan(
        sequence,
        SequenceFunction(inner_scan_calibration, axis=1),
        m_param,
        name='Scan with calibration demo',
        silent=True).run()

# Call stop on the fast scan parameter to release AWG memory.
sensor_scan_param.stop()
