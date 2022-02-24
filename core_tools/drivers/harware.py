from dataclasses import dataclass
import qcodes as qc
import numpy as np
import shelve
from typing import Sequence
import json

from .hardware.virtual_gate_matrix_data import VirtualGateMatrixData
from .hardware.virtual_gate_matrix import VirtualGateMatrix


# NOTE: class used for loading from and saving to shelve. Do not change name or attributes.
@dataclass
class virtual_gate(VirtualGateMatrixData):

    def __init__(self, name, real_gate_names, virtual_gate_names=None):
        '''
        generate a virtual gate object.
        Args:
            real_gate_names (list<str>) : list with the names of real gates
            virtual_gate_names (list<str>) : (optional) names of the virtual gates set. If not provided a "v" is inserted before the gate name.
        '''
        self.name = name
        self.real_gate_names = real_gate_names
        self.r2v_matrix_no_norm = np.eye(len(real_gate_names))
        if virtual_gate_names !=  None:
            self.virtual_gate_names = virtual_gate_names
        else:
            self.virtual_gate_names = []
            for name in real_gate_names:
                self.virtual_gate_names.append("v" + name)
        self.sync_engine = None

    def __getstate__(self):
        return {
            'name': self.name,
            'real_gate_name_names': self.real_gate_names,
            'virtual_gate_names': self.virtual_gate_names,
            'r2v_matrix_no_norm': self.r2v_matrix_no_norm,
                }

    def __setstate__(self, new_state):
        '''
        overwrite state methods so object becomes pickable.
        '''
        if "r2v_matrix_no_norm" not in new_state:
            # retrieving old version
            new_state["r2v_matrix_no_norm"] = np.asarray(new_state["virtual_gate_matrix_no_norm"])
        if "real_gate_names" not in new_state:
            new_state["real_gate_names"] = new_state["real_gate_name_names"]
        self.__dict__.update(new_state)


class virtual_gates_mgr(list):
    def __init__(self, sync_engine):
        super().__init__()
        self.sync_engine = sync_engine

    def add(self, name, real_gate_names, virtual_gate_names=None,
            matrix=None, normalization=False):
        if virtual_gate_names is not None:
            if len(real_gate_names) != len(virtual_gate_names):
                raise ValueError("number of real gates and virtual gates is not equal.")
        else:
            virtual_gate_names = ["v" + name for name in real_gate_names]

        vg = virtual_gate(name, real_gate_names, virtual_gate_names)
        self.append(vg, matrix=matrix, normalization=normalization)

    def append(self, item, matrix=None, normalization=False):
        if not isinstance(item, virtual_gate):
            raise ValueError("Virtual gates should be specified with the virtual_gate class. "
                             f"Got class {type(item)}")

        self._check_virtual_gate_names(item.name, item.virtual_gate_names)

        if item.name in list(self.sync_engine.keys()):
            item_in_ram = self.sync_engine[item.name]
            if item_in_ram.real_gate_names == item.real_gate_names:
                item.r2v_matrix_no_norm[:] = item_in_ram.r2v_matrix_no_norm
            else:
                # TODO implement conversion
                print('WARNING: Gates have changed. The values of the old virtual matrix are lost.')
                if matrix is not None:
                    item.r2v_matrix_no_norm[:] = matrix
        elif matrix is not None:
            item.r2v_matrix_no_norm[:] = matrix

        item.saver = self._save_vgm
        item.save()

        vgm = VirtualGateMatrix(item, normalization=normalization)

        return super().append(vgm)

    def _save_vgm(self, vgm):
        self.sync_engine[vgm.name]=vgm

    def _check_virtual_gate_names(self, name, virtual_gate_names):
        # check for uniqueness of the virtual gate names.
        for gate_name in virtual_gate_names:
            for vg in self:
                if gate_name in vg.virtual_gate_names:
                    raise ValueError(f"Duplicate virtual gate {gate_name}. "
                                     f"Defined in {vg.name} and {name}")

    def __getitem__(self, row):
        if isinstance(row, int):
            return super(virtual_gates_mgr, self).__getitem__(row)
        if isinstance(row, str):
            row = self.index(row)
            return super(virtual_gates_mgr, self).__getitem__(row)

        raise ValueError(f"Invalid key/name {row} provided for the virtual gate matrix.")

    def index(self, name):
        if len(self) == 0:
            raise ValueError("No virtual matrix is defined.")
        for i, virtual_gate_matrix in enumerate(self):
            if virtual_gate_matrix.name == name:
                return i
        raise ValueError(f"Virtual gate matrix {name} not registered in hardware")


class harware_parent(qc.Instrument):
    """docstring for harware_parent -- init a empy hardware object"""
    def __init__(self, sample_name, storage_location):
        super(harware_parent, self).__init__(sample_name)
        self.storage_location = storage_location
        self.sync = shelve.open(storage_location + sample_name, flag='c', writeback=True)
        self.dac_gate_map = dict()
        self.boundaries = dict()
        self.RF_source_names = []
        self.RF_params = ['frequency_stepsize', 'frequency', 'power']
        self._RF_settings = dict()

        # set this one in the GUI.
        self._AWG_to_dac_conversion = dict()
        if 'AWG2DAC' in list(self.sync.keys()):
            self._AWG_to_dac_conversion = self.sync['AWG2DAC']

        self._virtual_gates = virtual_gates_mgr(self.sync)

    @property
    def virtual_gates(self):
        return self._virtual_gates

    @property
    def RF_settings(self):
        return self._RF_settings

    @RF_settings.setter
    def RF_settings(self, RF_settings):
        if self._RF_settings.keys() == RF_settings.keys():
            RF_settings = self._RF_settings
        else:
            self._RF_settings = RF_settings

    @property
    def AWG_to_dac_conversion(self):
        return self._AWG_to_dac_conversion

    @AWG_to_dac_conversion.setter
    def AWG_to_dac_conversion(self, AWG_to_dac_ratio):
        if self._AWG_to_dac_conversion.keys() == AWG_to_dac_ratio.keys():
            AWG_to_dac_ratio = self._AWG_to_dac_conversion
        else:
            self._AWG_to_dac_conversion = AWG_to_dac_ratio

    def setup_RF_settings(self, sources):
        #TODO: If a module is added, the settings of the previous module are discarded
        RF_generated, qc_params = self.gen_RF_settings(sources)
        if 'RFsettings' in list(self.sync.keys()) and self.sync['RFsettings'].keys() == RF_generated.keys():
            self.RF_settings = self.sync['RFsettings']
            for (param,val) in zip(qc_params,self.RF_settings.values()):
                param(val)
        else:
            self.RF_settings = self.gen_RF_settings(sources = sources)

    def gen_RF_settings(self, sources):
        RF_settings = dict()
        qc_params = []
        for src in sources:
            name = src.name
            self.RF_source_names.append(name)
            for param in self.RF_params:
                qc_param = getattr(src,param)
                RF_settings[f'{name}_{param}'] = qc_param()
                qc_params.append(qc_param)
        return RF_settings,qc_params

    def sync_data(self):
        print("SYNC")
#        for item in self.virtual_gates:
#            self.sync[item.name] = item._persistent_object
        self.sync['AWG2DAC'] = self._AWG_to_dac_conversion
        self.sync['RFsettings'] = self._RF_settings
        self.sync.sync()

    def snapshot_base(self, update: bool=False,
                  params_to_skip_update: Sequence[str]=None):
        vg_snap = {}
        for vg in self.virtual_gates:
            vg_meta = {}
            vg_meta['real_gate_names'] = vg.real_gate_names
            vg_meta['virtual_gate_names'] = vg.virtual_gate_names
            vg_meta['virtual_gate_matrix'] = json.dumps(np.asarray(vg.virtual_gate_matrix).tolist())
            vg_meta['virtual_gate_matrix_no_norm'] = json.dumps(np.asarray(vg.virtual_gate_matrix_no_norm).tolist())
            vg_snap[vg.name] = vg_meta
        self.snap = {
                'AWG_to_DAC': self.AWG_to_dac_conversion,
                'dac_gate_map': self.dac_gate_map,
                'virtual_gates': vg_snap
                }
        return self.snap

