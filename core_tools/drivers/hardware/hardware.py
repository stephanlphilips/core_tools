from core_tools.drivers.hardware.hardware_SQL_backend import AWG_2_dac_ratio_queries
from core_tools.drivers.hardware.virtual_gate_matrix import load_virtual_gate
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

import qcodes as qc
import numpy as np
import json
from typing import List, Optional

class boundaries_mgr():
    def __init__(self):
        self.key_vals = dict()

    def __getitem__(self, gate):
        if gate in hardware().dac_gate_map.keys():
            return self.key_vals[gate]
        else:
            raise ValueError('Gate {} is not defined (gates present are : {})'.format(gate, hardware().dac_gate_map.keys()))

    def __setitem__(self, gate, value):
        if gate in hardware().dac_gate_map.keys():
            self.key_vals[gate] = value
        else:
            raise ValueError('Gate {} is not defined (gates present are : {})'.format(gate, hardware().dac_gate_map.keys()))

class virtual_gates_mgr():
    def __init__(self):
        self.virtual_gate_names = []

    def add(self, name, gates : List[str], virtual_gates : Optional[List[str]] = None):
        if name not in self.virtual_gate_names:
            self.virtual_gate_names += [name]

        setattr(self, name, load_virtual_gate(name , gates, virtual_gates))

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
        for gate, val  in self._ratios.items():
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
    instanciated = False
    _dac_gate_map = dict()
    _boundaries = boundaries_mgr()
    virtual_gates = virtual_gates_mgr()
    awg2dac_ratios = awg2dac_ratios_mgr()

    def __init__(self, name : str ='hardware'):
        """ Collection of hardware related settings

        The `hardware` is effectively a singleton class, so only one instance created in each session.
        """
        if hardware.instanciated == False: # this should happen in the station
            super().__init__(name)
        hardware.instanciated = True

    @property
    def dac_gate_map(self):
        return hardware._dac_gate_map

    @dac_gate_map.setter
    def dac_gate_map(self, val):
        hardware._dac_gate_map = val

    @property
    def boundaries(self):
        return self._boundaries.key_vals

    @boundaries.setter
    def boundaries(self, boundary_dict):
        for key, value in boundary_dict.items():
            self._boundaries[key] = value

    def snapshot_base(self, update=False, params_to_skip_update =None):
        vg_snap = {}
        for vg in self.virtual_gates:
            vg_snap[vg.name] = {
                    'real_gate_names' : vg.gates,
                    'virtual_gate_names' : vg.v_gates,
                    'virtual_gate_matrix' : json.dumps(np.asarray(vg.matrix).tolist())}

        return {'awg2dac_ratios': self.awg2dac_ratios._ratios,
                 'dac_gate_map': self.dac_gate_map,
                 'virtual_gates': vg_snap                     }

if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')

    h = hardware('6dotHW')
    h.dac_gate_map = {
        # dacs for creating the quantum dots -- syntax, "gate name": (dac module number, dac index)
        'B0': (0, 1), 'P1': (0, 2),
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6),
        'B3': (0, 7), 'P4': (0, 8),
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13)}
    print(h.dac_gate_map)

    h.boundaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    h.virtual_gates.add('test', ['B0', 'B1', 'B2'])
    h.awg2dac_ratios.add(['B0', 'B1', 'B2', 'B3'])

    # h.rf_sources.add(param)

    # h.awg2dac_ratios['B0'] = 0.78
    # print(h.virtual_gates.test[0, 1])
    print(h.awg2dac_ratios)
    # h.virtual_gates.test[0, 1] = 0.1

    print(h.virtual_gates)

    # print(h.snapshot_base())
