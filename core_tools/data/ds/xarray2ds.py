from datetime import datetime
import gzip
import json

from core_tools.data.SQL.buffer_writer import buffer_reference
from core_tools.data.ds.data_set_raw import data_set_raw, m_param_raw
from core_tools.data.ds.data_set_core import  data_set

def to_raw_param(xr_param, param_id,
                 dependencies,
                 setpoint=False):
    attrs = xr_param.attrs
    data = xr_param.data
    try:
        m_param_id, nth_set = attrs['_param_index']
        param_id = m_param_id
        nth_dim = -1
    except:
        m_param_id = 0
        nth_set = 0
        nth_dim = 0

    # Use param_name from attributes, otherwise name of xarray
    # Note: In the original dataset there can be multiple variable with the same name.
    name = attrs.get('param_name', xr_param.name)

    raw_param = m_param_raw(
        param_id=param_id, # required for dependencies Could just be a number in de data set.
        nth_set=nth_set, # required for slicing / averaging
        nth_dim=nth_dim, # required for slicing / averaging
        param_id_m_param=m_param_id,
        setpoint=setpoint, # required for data access
        setpoint_local=False, # has no specific meaning compared to setpoint
        name_gobal='_',
        name=name,
        label=attrs['long_name'],
        unit=attrs['units'],
        dependency=dependencies, # required for population
        shape=str(data.shape),
        size=-1,
        oid=-1,
        )
    raw_param.data_buffer = buffer_reference(data)
    return raw_param

def get_coord_param_id(coord_names, name):
    return 1000 + coord_names.index(name)

def xarray2ds(xr_ds):
    attrs = xr_ds.attrs
    if 'snapshot-gzip' in attrs:
        snapshot = json.loads(gzip.decompress(attrs['snapshot-gzip']))
    else:
        snapshot = json.loads(attrs['snapshot'])
    try:
        metadata = json.loads(attrs['metadata'])
    except KeyError:
        metadata = None

    ds_raw = data_set_raw(
            exp_id=attrs['id'],
            exp_uuid=attrs['uuid'],
            exp_name=attrs['title'],
            # Note: old incorrect attribute was 'set_up'.
            set_up = attrs.get('setup', attrs.get('set_up')),
            project = attrs['project'],
            sample = attrs['sample_name'],
            UNIX_start_time=datetime.fromisoformat(attrs['measurement_time']).timestamp(),
            UNIX_stop_time=datetime.fromisoformat(attrs['completed_time']).timestamp(),
            SQL_datatable='',
            snapshot=snapshot,
            metadata=metadata,
            keywords=attrs['keywords'],
            completed=bool(attrs['completed']),
            )

    coord_names = [name for name in xr_ds.coords]
    data_names = [name for name in xr_ds.data_vars]
    m_params = []
    # loop over data vars and coords.
    for name, param in xr_ds.data_vars.items():
        dependencies = [get_coord_param_id(coord_names, par_name) for par_name in param.dims]
        m_param = to_raw_param(param,
                               param_id=data_names.index(name),
                               dependencies=dependencies)
        m_params.append(m_param)

    for name, param in xr_ds.coords.items():
#        dependencies = [get_coord_param_id(coord_names, par_name) for par_name in param.coords]
#        print(name, dependencies, [n for n in param.coords])
        dependencies = []
        m_param = to_raw_param(param,
                               param_id=get_coord_param_id(coord_names, name),
                               setpoint=True,
                               dependencies=dependencies)
        m_params.append(m_param)

    ds_raw.measurement_parameters_raw = m_params

    return data_set(ds_raw)
