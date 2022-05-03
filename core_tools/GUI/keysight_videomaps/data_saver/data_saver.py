from typing import Any, Tuple, Dict
from abc import ABC, abstractmethod

from qcodes import MultiParameter


class IDataSaver(ABC):
    """Specifies the interface data savers are to adhere to."""

    @abstractmethod
    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> Tuple[Any, Dict[str, str]]:
        """
        Saves the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and
            setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict that uniquely identifies the
            dataset.
        """
