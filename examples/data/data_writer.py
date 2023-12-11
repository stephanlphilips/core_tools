import numpy as np
import pulse_lib.segments.utility.looping as lp

from core_tools.data.ds.data_writer import DataWriter

frequency = lp.linspace(100e6, 200e6, 11, 'frequency', unit='Hz')
amplitude = lp.array([1, 3, 5, 12], 'amplitude', unit='mV')


with DataWriter('WriterTest') as dw:
    # add references and metadata....
    # dw.add_ds_reference(ds_uuid, 'raw data')
    # dw.add_metadata('abc', dict_x)

    dw.add_gridded('x', unit='a.u.', label='x data',
                   axes=[frequency, amplitude],
                   data=np.arange(44).reshape(11, 4))

    y = dw.grid_stream('y', unit='a.u.', label='x data', axes=[amplitude])

    for i in range(4):
        y.append(i + 5)

    # --- scattered ---

    dw.add_scattered('x', unit='a.u.', label='x data', axes=[frequency, amplitude],
                     data=dict(x=np.arange(44).reshape(11, 4),
                               amplitude=[1] * 44,
                               frequency=[2] * 44))

    y = dw.scattered_stream('y', unit='a.u.', label='x data', axes=[amplitude])
    for i in range(4):
        y.append(i + 5, amplitude=amplitude[4 - i])


dw.write_data(
    Var('x', unit='a.u.', label='x data', data=np.arange(44).reshape(11, 4)),
    Var('y', unit='a.u.', label='y data', data=np.arange(44).reshape(11, 4)),
    axes=(frequency, amplitude))


'''
wrap/extend Dataset.
ds = xr.Dataset()

ds.add(nane, label=, unit=, axes=[], data=)

x = ds.add_stream(nane, label=, unit=, axes=[])

ds.close()

Also save to file? database?

'''
