import xarray as xr
import numpy as np
import json
import string
from qcodes.utils.helpers import NumpyJSONEncoder

def _add_coord(ds, param):
    data = param()
    attrs = {
            'units':param.unit,
            'long_name':param.label,
            }

    dup = 0
    param_name = param.param_name
    name = param_name
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
    name = var.param_name
    ds[name] = (dims, var())
    ds[name].attrs = {
            'units':var.unit,
            'long_name':var.label,
            '_param_index':param_index,
            }

def ds2xarray(ct_ds):
    snapshot_json = json.dumps(ct_ds.snapshot, cls=NumpyJSONEncoder)
    metadata_json = json.dumps(ct_ds.metadata, cls=NumpyJSONEncoder)

    attrs = {
        'title':ct_ds.name,
        'uuid':ct_ds.exp_uuid,
        'id':ct_ds.exp_id,
        'sample_name':ct_ds.sample_name,
        'project':ct_ds.project,
        'set_up':ct_ds.set_up,
        'measurement_time':str(ct_ds.run_timestamp),
        'completed_time': str(ct_ds.completed_timestamp),
        'snapshot': snapshot_json,
        'metadata': metadata_json,
        'keywords':ct_ds.keywords,
        'completed':int(ct_ds.completed),
        }

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

