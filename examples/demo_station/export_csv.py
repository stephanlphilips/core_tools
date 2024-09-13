import os
import json
from typing import List, Union
from core_tools.data.ds.ds2xarray import ds2xarray

def _save_metadata(xds, fname):
    coordinates = []
    for name,coord in xds.coords.items():
        coord_data = {
            'name':name,
            'units':coord.attrs['units'],
            }
        coordinates.append(coord_data)
    variables = []
    for name,xa in xds.variables.items():
        var_data = {
            'name': name,
            'units': xa.attrs['units'],
            'dims': list(xa.dims)
            }
        variables.append(var_data)
    attrs = xds.attrs
    data = {
        'experiment_name': attrs['title'],
        'project': attrs['project'],
        'setup': attrs['set_up'],
        'sample': attrs['sample_name'],
        'uuid': attrs['uuid'],
        'measured_at': attrs['measurement_time'],
        'coordinates': coordinates,
        'variables': variables,
        }

    with open(fname, 'w') as fp:
        json.dump(data, fp, indent=2)

def save_csv(ds, path,
             vars: Union[None, List[str], str, int] = None,
             metadata: bool = False):
    xds = ds2xarray(ds)
    if vars is not None:
        if isinstance(vars, list):
            xds = xds[vars]
        if isinstance(vars, str):
            xds = xds[[vars]]
        elif isinstance(vars, int):
            name = list(xds.variables)[vars]
            xds = xds[[name]]

    os.makedirs(path, exist_ok=True)
    name = f'ds_{ds.exp_uuid}.csv'
    fname = os.path.join(path, name)
    df = xds.to_dataframe()
    df.to_csv(fname)

    if metadata:
        name = f'ds_{ds.exp_uuid}.json'
        fname = os.path.join(path, name)
        _save_metadata(xds, fname)