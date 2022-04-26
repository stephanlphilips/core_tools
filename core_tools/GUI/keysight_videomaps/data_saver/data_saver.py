from typing import Union, Any, Tuple, Dict, Optional

from abc import ABC, abstractmethod

from pathlib import Path

from qcodes import MultiParameter


class IDataSaver(ABC):

    @abstractmethod
    def __init__(self, path: Optional[Union[Path, str]] = None):
        pass

    @abstractmethod
    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> Tuple[Any, Dict[str, Any]]:
        pass
