from .xarray2ds import xarray2ds
from .ds2xarray import ds2xarray
import xarray as xr
import os

def _get_fname(uuid):
    return f'ds_{uuid}.hdf5'

def _load_xr_hdf5(fname):
    # Check existence. xarray gives a very confusing error when the file does not exist.
    if not os.path.exists(fname):
        raise FileNotFoundError(fname)
    xds = xr.open_dataset(fname)
    xds.close()
    return xds

def save_hdf5(ds, fname):
    xds = ds2xarray(ds)
    comp = {"compression": "gzip", "compression_opts": 9}
    encoding = {var: comp for var in list(xds.data_vars)+list(xds.coords)}
    xds.to_netcdf(fname, engine='h5netcdf', encoding=encoding)

def load_hdf5(fname):
    xs = _load_xr_hdf5(fname)
    ds = xarray2ds(xs)
    return ds

def save_hdf5_uuid(ds, path):
    os.makedirs(path, exist_ok=True)
    name = _get_fname(ds.exp_uuid)
    fname = os.path.join(path, name)
    save_hdf5(ds, fname)

def load_hdf5_uuid(uuid, path):
    name = _get_fname(uuid)
    fname = os.path.join(path, name)
    return load_hdf5(fname)

def load_xr_by_uuid(uuid, path):
    name = _get_fname(uuid)
    fname = os.path.join(path, name)
    return _load_xr_hdf5(fname)

def save_hdf5_id(ds, path):
    os.makedirs(path, exist_ok=True)
    name = _get_fname(ds.exp_id)
    fname = os.path.join(path, name)
    save_hdf5(ds, fname)

def load_hdf5_id(id, path):
    name = _get_fname(id)
    fname = os.path.join(path, name)
    return load_hdf5(fname)

def load_xr_by_id(id, path):
    name = _get_fname(id)
    fname = os.path.join(path, name)
    return _load_xr_hdf5(fname)

