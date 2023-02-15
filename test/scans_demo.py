import core_tools as ct
from core_tools.sweeps.scans import Scan, sweep, Function, Break
import qcodes as qc
from qcodes import ManualParameter
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = qc.Station()

x = ManualParameter('x', initial_value=0)
y = ManualParameter('y', initial_value=9)

t = ElapsedTimeParameter('t')

#%%

ds1 = Scan(
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
        reset_param=True).run()


#%%
def check_x(last_values, dataset):
    max_x = max(dataset.m1.x())
    if max_x > 4:
        raise Break(f'max x = {max_x}. Last {last_values}')

ds3 = Scan(
        sweep(x, -20, 20, 11, delay=0.1),
        t,
        Function(check_x, add_dataset=True, add_last_values=True),
        name='test_break',
        reset_param=True).run()

#%%

t.reset_clock()

def check_t(last_values):
    # abort after 0.5 s
    t = last_values['t']
    if t > 0.5:
        raise Break(f't={t:5.2f} s')

ds4 = Scan(
        sweep(x, -20, 20, 11, delay=0.1),
        sweep(y, -1, 1, 3),
        t,
        Function(check_t, add_last_values=True),
        name='test_break_2D',
        reset_param=True).run()


#%%
ds5 = Scan(
        sweep(y, -20, 20, 21),
        sweep(x, -10, 10, 41, delay=0.001),
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
        sweep(y, -1, 1, 3, delay=0.2),
        Function(inner_scan_do1D),
        t,
        reset_param=True).run()

#%%

ds = Scan(
        sweep(y, [1, 2, 6, 7], delay=0.1),
        sweep(x, [-1, 1, 4, 12], delay=0.2),
        t,
        name='test_sweep_array').run()

