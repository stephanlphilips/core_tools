import logging
from qcodes import MultiParameter
from core_tools.data.ds.data_set_core import data_set

from core_tools.sweeps.sweeps import do0D
from core_tools.data.SQL.connect import sample_info

from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver

logger = logging.getLogger(__name__)


class CoreToolsDataSaver(IDataSaver):

    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> tuple[data_set, dict[str, str]]:
        """
        Performs a measurement using core tools and writes the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and
            setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict that uniquely identifies the
            dataset.
        """
        # Calling this before initializing the database will raise a ConnectionError.
        sample_info_str = str(sample_info)

        job = do0D(vm_data_parameter, name=label)
        dataset = job.run()
        logger.info(f'Saved {dataset.exp_uuid}')
        print(f'\nSaved {dataset.exp_uuid} ({label})')

        return (
            dataset,
            {
                "dataset_id": dataset.exp_id,
                "dataset_uuid": dataset.exp_uuid,
                "sample_info": sample_info_str,
            }
        )
