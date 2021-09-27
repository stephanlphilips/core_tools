import xarray as xr

def _add_coord(ds, param):
    # @@@ TODO: check duplicate coordinates
    ds.coords[param.param_name] = param()
    ds.coords[param.param_name].attrs = {
            'units':param.unit,
            'long_name':param.label,
            }

def _add_data_var(ds, var, dims):
    ds[var.param_name] = (dims, var())
    ds[var.param_name].attrs = {
            'units':var.unit,
            'long_name':var.label,
            }

def ds2xarray(ct_ds):

    attrs = {
        'title':ct_ds.name,
        'uuid':ct_ds.exp_uuid,
        'id':ct_ds.exp_id,
        'sample_name':ct_ds.sample_name,
        'project':ct_ds.project,
        'set_up':ct_ds.set_up,
        'measurement_time':ct_ds.run_timestamp,
        }

    ds = xr.Dataset(attrs=attrs)

    for m_param_set in ct_ds:
        for m_param in m_param_set:
            param = m_param[1]
            dims = []
            if param.ndim > 0:
                coord = param.x
                dims.append(coord.param_name)
                _add_coord(ds, coord)
            if param.ndim > 1:
                coord = param.y
                dims.append(coord.param_name)
                _add_coord(ds, coord)
            _add_data_var(ds, param, dims)

    return ds

