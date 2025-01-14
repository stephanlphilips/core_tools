import core_tools as ct
import numpy as np

ct.configure("./setup_config/ct_config_measurement.yaml")

# %%

from core_tools.data.data_writer import write_data, Axis, Data

write_data(
    'Demo_WriteData',
    Axis('x', 'x-array', 'a.u.', [1, 2, 3, 4]),
    Data('y', 'y-array', 'a.u.', [3, 1, 4, 6]),
)

write_data(
    'Demo_WriteData2D',
    Axis('f', 'frequency', 'Hz', np.linspace(100e6, 200e6, 11)),
    Axis('e12', 'detuning', 'mv', np.linspace(-10, 10, 5)),
    Data('SD1', 'Sensor 1', 'mV', np.linspace(10, 20, 55).reshape((11, 5))),
    Data('SD2', 'Sensor 2', 'mV', np.linspace(0, -20, 55).reshape((11, 5))),
)


#%%