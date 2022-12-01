import time
import core_tools as ct
from core_tools.sweeps.scans import Scan, sweep, Function, Break
import qcodes as qc
from qcodes import ManualParameter
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

from core_tools.job_mgnt.job_mgmt import queue_mgr

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = qc.Station()

x = ManualParameter('x', initial_value=0)
y = ManualParameter('y', initial_value=9)

t = ElapsedTimeParameter('t')

#%%

for i in range(10):
    ds1 = Scan(
            Function(print, 'scan', i, flush=True),
            sweep(x, -20, 20, 11, delay=0.01),
            t,
            name=f'test_scan_{i}',
            silent=True,
            ).put()

print("ALL PUT", flush=True)
for i in range(20):
    print('.', end='')
    time.sleep(0.05)

queue_mgr().killall()

