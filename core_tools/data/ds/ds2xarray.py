import gzip
import json
import string

import numpy as np
import xarray as xr

from qcodes.utils.helpers import NumpyJSONEncoder

from core_tools import __version__

def _add_coord(ds, param):
    data = param()
    attrs = {
            'units':param.unit,
            'long_name':param.label,
            }

    dup = 0
    param_name = param.param_name
    name = param_name
    if not name:
        name = param.name
    while name in ds.coords:
        if (np.array_equal(data , ds.coords[name].data, equal_nan=True)
            and attrs == ds.coords[name].attrs):
            # coord already added and identical
            return name
        dup += 1
        name = f'{param_name}-{dup}'

    ds.coords[name] = data
    ds.coords[name].attrs = attrs
    return name

def _add_data_var(ds, var, dims, param_index):
    var_name = var.param_name
    if not var_name:
        # Just in case the param name is not set.
        var_name = var.name
    name = var_name
    dup = 1
    while name in ds:
        # Duplicate variable name. Add sequence number
        dup += 1
        name = f'{var_name}-{dup}'
    ds[name] = (dims, var())
    ds[name].attrs = {
            'units':var.unit,
            'long_name':var.label,
            '_param_index':param_index,
            'param_name':var_name,
            }

def ds2xarray(ct_ds, snapshot='gzip'):
    metadata_json = json.dumps(ct_ds.metadata, cls=NumpyJSONEncoder)

    if len(ct_ds) == 0:
        raise Exception(f'Dataset has no data ({ct_ds.exp_uuid})')

    attrs = {
        'title':ct_ds.name,
        'uuid':ct_ds.exp_uuid,
        'id':ct_ds.exp_id,
        'sample_name':ct_ds.sample_name,
        'project':ct_ds.project,
        'set_up':ct_ds.set_up,
        'measurement_time':str(ct_ds.run_timestamp),
        'completed_time': str(ct_ds.completed_timestamp),
        'metadata': metadata_json,
        'keywords':ct_ds.keywords,
        'completed':int(ct_ds.completed),
        'application': f"core-tools:{__version__}"
        }
    if snapshot == 'gzip':
        snapshot_json = json.dumps(ct_ds.snapshot, cls=NumpyJSONEncoder)
        attrs['snapshot-gzip'] = np.array(bytearray(gzip.compress(bytearray(snapshot_json, 'utf-8'))))
    elif snapshot == 'dict':
        attrs['snapshot'] = ct_ds.snapshot
    elif snapshot == 'json':
        snapshot_json = json.dumps(ct_ds.snapshot, cls=NumpyJSONEncoder)
        attrs['snapshot'] = snapshot_json

    ds = xr.Dataset(attrs=attrs)

    for i_param,m_param_set in enumerate(ct_ds):
        for i_set,m_param in enumerate(m_param_set):
            param_index = (i_param, i_set)
            param = m_param[1]
            dims = []
            if param.ndim <= 2:
                if param.ndim > 0:
                    coord = param.x
                    dim_name = _add_coord(ds, coord)
                    dims.append(dim_name)
                if param.ndim > 1:
                    coord = param.y
                    dim_name = _add_coord(ds, coord)
                    dims.append(dim_name)
            else:
                for i in range(param.ndim):
                    dim_name  = string.ascii_lowercase[8+i]

                    coord = getattr(param, dim_name)
                    dim_name = _add_coord(ds, coord)
                    dims.append(dim_name)

            _add_data_var(ds, param, dims, param_index)

    return ds

