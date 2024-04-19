import numpy as np
import core_tools as ct
from core_tools.sweeps.sweeps import do0D, do1D, do2D
import qcodes as qc
from qcodes import ManualParameter
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

ct.configure('./setup_config/ct_config_measurement.yaml')

# ct.launch_databrowser()

station = qc.Station()


#%%
p1 = ManualParameter('p1', initial_value=0)
p2 = ManualParameter('p2', initial_value=9)

t = ElapsedTimeParameter('t')
#%%
ds0 = do0D(t, name='do0D-t')

#%%
t.reset_clock()

ds1 = do1D(p1, 0, 5, 11, 0.02, t, name='x-t').run()

# %%
t.reset_clock()

ds2 = do2D(
    p2, 0, 5, 6, 0.0,
    p1, 0, -1, 3, 0.01,
    t, name='x,y->t').run()

print()
print('t:', ds2.m1())
print('t', ds2['m1']())
print(ds2['Elapsed time']())

m1 = ds2['m1']
print(f"m1 label: '{m1.label}', unit: '{m1.unit}'")

print('p1:', ds2.m1.x())
print('p2:', ds2.m1.y())

x = ds2.m1.x
print(f"x label: '{x.label}', unit: '{x.unit}'")

# %%
from core_tools.job_mgnt.job_mgmt import queue_mgr
import time

do2D(
    p2, 0, 5, 6, 0.0,
    p1, 0, -1, 3, 0.02,
    t, name='x,y->t').put()

time.sleep(0.2)
queue_mgr().killall()

