from core_tools import __version__ as ct_version
from core_tools.drivers.hardware.hardware_SQL_backend import AWG_2_dac_ratio_queries
from core_tools.drivers.hardware.virtual_gate_matrix_db import load_virtual_gate
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

import qcodes as qc
import numpy as np
import json


class boundaries_mgr():
    def __init__(self, dac_gate_map):
        self._dac_gate_map = dac_gate_map
        self.key_vals = dict()

    def __getitem__(self, gate):
        all_gates = self._dac_gate_map.keys()
        if gate in all_gates:
            return self.key_vals[gate]
        else:
            raise ValueError(f'Gate {gate} is not defined')

    def __setitem__(self, gate, value):
        all_gates = self._dac_gate_map.keys()
        if gate in all_gates:
            self.key_vals[gate] = value
        else:
            raise ValueError(f'Gate {gate} is not defined')


class virtual_gates_mgr():
    def __init__(self):
        self.virtual_gate_names = []

    def add(self, name, gates: list[str], virtual_gates: list[str] | None = None,
            matrix=None, normalization=False):
        if name not in self.virtual_gate_names:
            self.virtual_gate_names += [name]

        virtual_gate_matrix = load_virtual_gate(name, gates, virtual_gates, matrix,
                                                normalization=normalization)
        setattr(self, name, virtual_gate_matrix)
        return virtual_gate_matrix

    def __len__(self):
        return len(self.virtual_gate_names)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return getattr(self, self.virtual_gate_names[idx])
        return getattr(self, idx)

    def __repr__(self):
        content = f'Found {len(self)} virtual gate matrix :\n'

        for vg in self:
            content += f'\tname :: {vg.name} \t(size = {vg.matrix.shape[0]}x{vg.matrix.shape[1]})'

        return content + '\n'


class awg2dac_ratios_mgr():
    def __init__(self):
        self._ratios = dict()

    def add(self, gates):
        conn = SQL_database_manager().conn_local
        AWG_2_dac_ratio_queries.generate_table(conn)
        ratios_db = AWG_2_dac_ratio_queries.get_AWG_2_dac_ratios(conn, 'general')

        for gate in gates:
            if gate in ratios_db:
                self._ratios[gate] = ratios_db[gate]
            else:
                self._ratios[gate] = 1

    def keys(self):
        return self._ratios.keys()

    def values(self):
        return self._ratios.values()

    def items(self):
        return self._ratios.items()

    def __getitem__(self, gate):
        return self._ratios[gate]

    def __setitem__(self, gate, value):
        if isinstance(gate, int):
            gate = list(self.keys())[gate]

        if gate not in self._ratios.keys():
            raise ValueError('Gate {} not defined in AWG2dac ratios. Please add first.'.format(gate))

        self._ratios[gate] = value

        conn = SQL_database_manager().conn_local
        ratios_db = AWG_2_dac_ratio_queries.get_AWG_2_dac_ratios(conn, 'general')
        ratios_db[gate] = value
        AWG_2_dac_ratio_queries.set_AWG_2_dac_ratios(conn, 'general', ratios_db)

    def __len__(self):
        return len(self._ratios.keys())

    def __repr__(self):
        doc = 'AWG to dac ratios :: \n\n'
        for gate, val in self._ratios.items():
            doc += '{}\t:  {}\n'.format(gate, val)

        return doc


class rf_source():
    def __init__(self, parameter):
        self.source_param = parameter

    @property
    def power(self):
        return self.source_param.power


class rf_source_mgr():
    def __init__(self):
        self.rf_source_names = []

    def add(self, parameter):
        self.rf_source_names += [parameter.name]
        setattr(self, parameter.name, rf_source(parameter))


class hardware(qc.Instrument):

    def __init__(self, name: str = 'hardware'):
        """ Collection of hardware related settings

        The `hardware` is effectively a singleton class. This is enforced by qcodes.
        """
        super().__init__(name)
        self._dac_gate_map = dict()
        self._boundaries = boundaries_mgr(self._dac_gate_map)
        self._virtual_gates = virtual_gates_mgr()
        self._awg2dac_ratios = awg2dac_ratios_mgr()

    def get_idn(self):
        return dict(vendor='CoreTools',
                    model='hardware',
                    serial='',
                    firmware=ct_version)

    @property
    def dac_gate_map(self):
        return self._dac_gate_map

    @dac_gate_map.setter
    def dac_gate_map(self, val):
        self._dac_gate_map.clear()
        self._dac_gate_map.update(val)

    @property
    def boundaries(self):
        return self._boundaries.key_vals

    @boundaries.setter
    def boundaries(self, boundary_dict):
        for key, value in boundary_dict.items():
            self._boundaries[key] = value

    @property
    def virtual_gates(self):
        return self._virtual_gates

    @property
    def awg2dac_ratios(self):
        return self._awg2dac_ratios

    def snapshot_base(self, update=False, params_to_skip_update=None):
        vg_snap = {}
        for vg in self.virtual_gates:
            vg_snap[vg.name] = {
                'real_gate_names': vg.gates,
                'virtual_gate_names': vg.v_gates,
                'virtual_gate_matrix': json.dumps(np.asarray(vg.matrix).tolist())}

        return {'awg2dac_ratios': self.awg2dac_ratios._ratios,
                'dac_gate_map': self.dac_gate_map,
                'virtual_gates': vg_snap}
