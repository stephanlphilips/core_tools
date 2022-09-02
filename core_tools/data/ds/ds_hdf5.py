from .xarray2ds import xarray2ds
from .ds2xarray import ds2xarray
import xarray as xr
import os

def save_hdf5(ds, fname):
    xds = ds2xarray(ds)
    xds.to_netcdf(fname, engine='h5netcdf')

def load_hdf5(fname):
    xs = xr.open_dataset(fname)
    ds = xarray2ds(xs)
    xs.close()
    return ds

def save_hdf5_uuid(ds, path):
    os.makedirs(path, exist_ok=True)
    name = f'ds_{ds.exp_uuid}.hdf5'
    fname = os.path.join(path, name)
    save_hdf5(ds, fname)

def load_hdf5_uuid(uuid, path):
    name = f'ds_{uuid}.hdf5'
    fname = os.path.join(path, name)
    return load_hdf5(fname)

