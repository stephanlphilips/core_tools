from typing import Union, Any, Tuple, Dict, Optional

from abc import ABC, abstractmethod

from pathlib import Path

from qcodes import MultiParameter


class IDataSaver(ABC):
    """Specifies the interface data savers are to adhere to."""

    @abstractmethod
    def __init__(self, path: Optional[Union[Path, str]] = None):
        """
        Constructor.

        Args:
            path: Specifies where to store the data. If left None, the default for the data saver is used.
        """

    @abstractmethod
    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Saves the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict with information about the dataset.
        """
