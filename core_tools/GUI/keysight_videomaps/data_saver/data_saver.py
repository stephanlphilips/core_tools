from core_tools.GUI.keysight_videomaps.data_saver import qcodes, quantify

_DATA_SAVING_MAP = {'qcodes': qcodes.save_data, 'quantify': quantify.save_data}
"""Maps the name of the backend to a function that actually performs the saving."""


def save_data(vm_data_parameter, label, backend='qcodes'):
    """
    Save the data to disk, using a user specified backend.

    Args:
        vm_data_parameter: MultiParameter containing the data to store to disk.
        label: The label to give to the data.
        backend: The data saving backend to use. Must be present in _DATA_SAVING_MAP.

    Returns:
        The dataset produced by the data saving backend as well as additional metadata that can be logged.

    Raises:
        KeyError: An unknown backend is provided.
    """
    data_saving_func = _DATA_SAVING_MAP.get(backend, None)
    if data_saving_func is None:
        raise KeyError(f'Invalid backend \"{backend}\" selected as data saving backend. Please use one of: {_DATA_SAVING_MAP.keys()}')

    data, metadata = data_saving_func(vm_data_parameter=vm_data_parameter, label=label)
    metadata['data_saving_backend'] = backend
    return data, metadata
