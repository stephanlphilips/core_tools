from typing import Dict, Any, Tuple

import logging

from qcodes import MultiParameter
from qcodes.measure import Measure
from qcodes.data.data_set import DataSet

from core_tools.sweeps.sweeps import do0D
from core_tools.data.SQL.connect import sample_info


def _create_metadata(dataset: DataSet) -> Dict[str, Any]:
    """
    Creates a metadata dict with information about the dataset.

    Args:
        dataset: The dataset object.

    Returns:
        A metadata dict containing the location on disk of the dataset and if available the experiment id and uuid.
    """
    metadata = dict()
    if hasattr(dataset, 'exp_id'):
        metadata['dataset_id'] = dataset.exp_id
        metadata['dataset_uuid'] = dataset.exp_uuid
    else:
        metadata['location'] = dataset.location
    return metadata


def save_data(vm_data_parameter: MultiParameter, label: str) -> Tuple[DataSet, Dict[str, Any]]:
    """
    Performs a measurement using qcodes and writes the data to disk.

    Args:
        vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and setpoints.
        label: a string that is used to label the dataset.

    Returns:
        A Tuple (ds, metadata) containing the created dataset ds and a metadata dict with information about the dataset.
    """
    is_ds_configured = False
    try:
        is_ds_configured = isinstance(sample_info.project, str)
    except:
        pass

    try:
        if is_ds_configured:
            logging.info('Save')
            job = do0D(vm_data_parameter, name=label)
            data = job.run()
            return data, _create_metadata(data)
        else:
            # use qcodes measurement
            measure = Measure(vm_data_parameter)
            data = measure.run(quiet=True, name=label)
            data.finalize()
            return data, _create_metadata(data)
    except:
        logging.error(f'Error during save data', exc_info=True)
