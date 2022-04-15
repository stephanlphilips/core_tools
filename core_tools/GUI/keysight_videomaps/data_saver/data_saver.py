from core_tools.GUI.keysight_videomaps.data_saver import qcodes, quantify

_DATA_SAVING_MAP = {'qcodes': qcodes.save_data, 'quantify': quantify.save_data}


def save_data(vm_data_parameter, label, backend='qcodes'):
    data_saving_func = _DATA_SAVING_MAP.get(backend, None)
    if data_saving_func is None:
        raise ValueError(f'Invalid backend \"{backend}\" selected as data saving backend. Please use one of: {_DATA_SAVING_MAP.keys()}')

    data, metadata = data_saving_func(vm_data_parameter=vm_data_parameter, label=label)
    metadata['data_saving_backend'] = backend
    return data, metadata
