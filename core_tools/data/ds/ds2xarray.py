import xarray as xr
import numpy as np
import json
import qcodes as qc

def _add_coord(ds, param):
    name = param.param_name
    data = param()
    attrs = {
            'units':param.unit,
            'long_name':param.label,
            }

    if name in ds.coords:
        if (np.array_equal(data , ds.coords[name].data, equal_nan=True)
            and attrs == ds.coords[name].attrs):
            # coord already added
            return
        raise Exception('Cannot handle conversion with duplicate coordinate names that are not equal. '
                        f'(coord={name})')

    ds.coords[name] = data
    ds.coords[name].attrs = attrs

def _add_data_var(ds, var, dims, param_index):
    name = var.param_name
    ds[name] = (dims, var())
    ds[name].attrs = {
            'units':var.unit,
            'long_name':var.label,
            '_param_index':param_index,
            }

def ds2xarray(ct_ds):
    snapshot_json = json.dumps(ct_ds.snapshot, cls=qc.utils.helpers.NumpyJSONEncoder)
    metadata_json = json.dumps(ct_ds.metadata, cls=qc.utils.helpers.NumpyJSONEncoder)

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
                    dims.append(coord.param_name)
                    _add_coord(ds, coord)
                if param.ndim > 1:
                    coord = param.y
                    dims.append(coord.param_name)
                    _add_coord(ds, coord)
            else:
                if param.ndim > 0:
                    coord = param.i
                    dims.append(coord.param_name)
                    _add_coord(ds, coord)
                if param.ndim > 1:
                    coord = param.j
                    dims.append(coord.param_name)
                    _add_coord(ds, coord)
                if param.ndim > 2:
                    coord = param.k
                    dims.append(coord.param_name)
                    _add_coord(ds, coord)
            _add_data_var(ds, param, dims, param_index)

    return ds

