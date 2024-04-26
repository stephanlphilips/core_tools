import time
import numpy as np
import core_tools as ct
from core_tools.sweeps.scans import Scan, sweep, Function, Break
import qcodes as qc
from qcodes import ManualParameter
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = qc.Station()

# Scan.verbose = True

#%%
x = ManualParameter('x', initial_value=0)
y = ManualParameter('y', initial_value=9)

t = ElapsedTimeParameter('t')

#%%
# ct.set_sample_info('CoreTools', 'Demo', 'Magic')

ds1 = Scan(
        sweep(y, np.geomspace(1, 100, 7), delay=1.0),
        sweep(x, -20, 20, 11, delay=0.01),
        t,
        name='test_scan',
        silent=True,
        ).run()


#%%
t.reset_clock()

ds_inner = []
def inner_scan():
    ds = Scan(
        sweep(x, -20, 20, 11, delay=0.01),
        t,
        name='test_inner_scan',
        silent=True,
        ).run()
    ds_inner.append(ds)

ds2 = Scan(
        sweep(y, -1, 1, 3, delay=0.2),
        Function(inner_scan),
        t,
        reset_param=True,
        name='outer_scan').run()


#%%
def check_x(last_values, dataset):
    max_x = max(dataset.m1.x())
    if max_x > 4:
        raise Break(f'max x = {max_x}. Last {last_values}')

ds3 = Scan(
        sweep(x, -20, 20, 11, delay=0.1),
        t,
        Function(check_x, add_dataset=True, add_last_values=True),
        name='test_break').run()

#%%
def check_t(last_values):
    # abort after 0.5 s
    t = last_values['t']
    if t > 0.5:
        raise Break(f't={t:5.2f} s')

t.reset_clock()

ds4 = Scan(
        sweep(x, -20, 20, 11, delay=0.1),
        sweep(y, -1, 1, 3),
        t,
        Function(check_t, add_last_values=True),
        name='test_break_2D').run()


#%%
ds5 = Scan(
        sweep(x, -20, 20, 21),
        sweep(y, -10, 10, 41, delay=0.001),
        t,
        name='test_2D').run()

#%%
from core_tools.sweeps.sweeps import do1D

t.reset_clock()

ds_inner2 = []
def inner_scan_do1D():
    ds = do1D(
        x, -20, 20, 11, 0.01,
        t,
        name='test_inner_do1D',
        silent=True,
        ).run()
    ds_inner2.append(ds)

ds6 = Scan(
        sweep(y, -1, 1, 5, delay=0.2),
        Function(inner_scan_do1D),
        t,
        name='Scan with inner scan',
        reset_param=True).run()

# %%

from qcodes import DelegateParameter

i1 = ManualParameter('i1', initial_value=0)
i2 = ManualParameter('i2', initial_value=0)
v1 = ManualParameter('v1', initial_value=0)

current = ManualParameter('I', initial_value=0)
current1 = DelegateParameter('I1', current, label='I1')

ds11 = Scan(
        sweep(i1, range(1, 3)),
        sweep(i2, range(1, 5)),
        current,
        sweep(v1, -500, -1100, 30),
        current1,
        name='Scan with delegate parameter',
        reset_param=True).run()


# %%
from core_tools.sweeps.scans import Section
from qcodes import DelegateParameter, Parameter

i1 = ManualParameter('i1', initial_value=0)
i2 = ManualParameter('i2', initial_value=0)
v1 = ManualParameter('v1', initial_value=0)
v2 = ManualParameter('v2', initial_value=0)
v3 = ManualParameter('v3', initial_value=0)

def get_current():
    return -0.001 * (v1() + v2() + v3())

meas_param = Parameter('I', unit='uA', get_cmd=get_current)

def param_alias(param, name):
    return DelegateParameter(name, param, label=name)

def break_at(param_name, Imax, resume_at):
    def check_break(last_values):
        I = last_values[param_name]
        if I > Imax:
            raise Break(f"I: {I}", resume_at_label=resume_at)
    return Function(check_break, add_last_values=True)

def reset_voltage():
    v1(0.0)

ds11 = Scan(
        sweep(i1, range(1, 16)),
        sweep(i2, range(1, 10), label="i2"),
        Section(
            sweep(v1, -500, -1100, 100, delay=0.001),
            param_alias(meas_param, "I1"),
            break_at("I1", Imax=0.8, resume_at="v2"),
        ),
        Section(
            sweep(v2, -500, -1100, 100, value_after='start', delay=0.01, label="v2"),
            param_alias(meas_param, "I2"),
        ),
        Section(
            sweep(v3, -500, -1100, 100, value_after='start', delay=0.01),
            param_alias(meas_param, "I3"),
        ),
        Function(reset_voltage),
        name='Scan with sections',
        reset_param=True).run()


ds11

# %%
from core_tools.data.ds.data_set import load_by_uuid

ds12 = load_by_uuid(ds11.exp_uuid)

ds12

#%%
from core_tools.data.ds.ds2xarray import ds2xarray
dsx = ds2xarray(ds12)
dsx