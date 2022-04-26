from typing import Dict, Any, Tuple, Union, Optional

import logging
from pathlib import Path

from qcodes import MultiParameter
from qcodes.data.data_set import DataSet

from core_tools.sweeps.sweeps import do0D
from core_tools.data.SQL.connect import sample_info

from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver


class CoreToolsDataSaver(IDataSaver):
    def __init__(self, path: Optional[Union[Path, str]] = None):
        """
        Instantiates the core tools native data saver.

        Args:
            path: Not supported for this data saver. The user should connect to the database first.
        """
        if path is not None:
            raise ValueError(f'Specifying a custom path is not supported for this data-saving backend. Please connect '
                             f'to the database manually.')

    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> Tuple[DataSet, Dict[str, Any]]:
        """
        Performs a measurement using core tools and writes the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict with information about the dataset.
        """
        assert hasattr(sample_info, 'project')

        logging.info('Save')
        job = do0D(vm_data_parameter, name=label)
        dataset = job.run()

        return dataset, {"dataset_id": dataset.exp_id, "dataset_uuid": dataset.exp_uuid}
