from typing import Dict, Any, Tuple, Union, Optional

from pathlib import Path

from qcodes import MultiParameter
from qcodes.measure import Measure
from qcodes.data.data_set import DataSet

from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver


class QCodesDataSaver(IDataSaver):
    def __init__(self, path: Optional[Union[Path, str]] = None):
        self._path = path

    @property
    def path(self):
        if isinstance(self._path, Path):
            return str(self._path)
        else:
            return self._path

    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> Tuple[DataSet, Dict[str, Any]]:
        """
        Performs a measurement using qcodes and writes the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict with information about the dataset.
        """
        measure = Measure(vm_data_parameter)
        data = measure.run(quiet=True, name=label, location=self.path)
        data.finalize()
        return data, {'location': data.location}
