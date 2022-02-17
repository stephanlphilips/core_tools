from typing import List, Callable
from dataclasses import dataclass
import numpy as np

@dataclass
class VirtualGateMatrixData:
    name:str
    real_gate_names: List[str]
    virtual_gate_names: List[str]
    r2v_matrix_no_norm: np.ndarray
    saver: Callable[['VirtualGateMatrixData'], None] = None

    def save(self):
        if not self.saver:
            raise Exception(f'Save not configured for VirtualGateMatrix {self.name}')
        self.saver(self)
