from core_tools.drivers.hardware.hardware_SQL_backend import AWG_2_dac_ratio_queries
from core_tools.drivers.hardware.virtual_gate_matrix import load_virtual_gate
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

class boudaries_mgr():
    def __init__(self):
        self.key_vals = dict()

    def __getitem__(self, gate):
        if gate in hardware().dac_to_gate.keys():
            return self.key_vals[gate]
        else:
            raise ValueError('Gate {} is not defined (gates present are : {})'.format(gate, hardware().dac_to_gate.keys()))
    
    def __setitem__(self, gate, value):
        if gate in hardware().dac_to_gate.keys():
            self.key_vals[gate] = value
        else:
            raise ValueError('Gate {} is not defined (gates present are : {})'.format(gate, hardware().dac_to_gate.keys()))

class virtual_gates_mgr():
    def __init__(self):
        self.virtual_gate_names = []

    def add(self, name, gates, virtual_gates=None):
        self.virtual_gate_names += [name]
        setattr(self, name, load_virtual_gate(name , gates, virtual_gates))

class awg2dac_ratios_mgr():
    def __init__(self):
        self.__ratios = dict()
    
    def add(self, gates):
        conn = SQL_database_manager().conn_local
        AWG_2_dac_ratio_queries.generate_table(conn)
        ratios_db = AWG_2_dac_ratio_queries.get_AWG_2_dac_ratios(conn, 'general')

        for gate in gates:
            if gate in ratios_db:
                self.__ratios[gate] = ratios_db[gate]
            else:
                self.__ratios[gate] = 1 

    def __getitem__(self, gate):
        return self.__ratios[gate]

    def __setitem__(self, gate, value):
        if gate not in self.__ratios.keys():
            raise ValueError('Gate {} not defined in AWG2dac ratios. Please add first.'.format(gate))

        self.__ratios[gate] = value

        conn = SQL_database_manager().conn_local
        ratios_db = AWG_2_dac_ratio_queries.get_AWG_2_dac_ratios(conn, 'general')
        ratios_db[gate] = value
        AWG_2_dac_ratio_queries.set_AWG_2_dac_ratios(conn, 'general', ratios_db)

    def __repr__(self):
        doc = 'AWG to dac ratios :: \n\n'
        for gate, val  in self.__ratios.items():
            doc += '{}\t:  {}\n'.format(gate, val)

        return doc

class rf_source():
    def __init__(self, parameter):
        self.source_param = paramter

    @property
    def power(self):
        return self.source_param.power 
    
class rf_source_mgr():
    def __init__(self):
        self.rf_source_names = []

    def add(self, parameter):
        self.rf_source_names += [paramter.name]
        setattr(self, name, rf_source(parameter)) 

class hardware():
    _dac_to_gate = dict()
    _boudaries = boudaries_mgr()   
    virtual_gates = virtual_gates_mgr()
    awg2dac_ratios = awg2dac_ratios_mgr()

    @property
    def dac_to_gate(self):
        return hardware._dac_to_gate

    @dac_to_gate.setter
    def dac_to_gate(self, val):
        hardware._dac_to_gate = val

    @property
    def boudaries(self):
        return self._boudaries.key_vals

    @boudaries.setter
    def boudaries(self, boundary_dict):
        for key, value in boundary_dict.items():
            self._boudaries[key] = value

if __name__ == '__main__':
    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')

    h = hardware()
    h.dac_to_gate = {
        # dacs for creating the quantum dots -- syntax, "gate name": (dac module number, dac index)
        'B0': (0, 1), 'P1': (0, 2), 
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6), 
        'B3': (0, 7), 'P4': (0, 8), 
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13)}
    print(h.dac_to_gate)

    h.boudaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    h.virtual_gates.add('test', ['B0', 'B1', 'B2'])
    h.awg2dac_ratios.add(['B0', 'B1', 'B2', 'B3'])

    # h.rf_sources.add(param)
    
    # h.awg2dac_ratios['B0'] = 0.78
    # print(h.virtual_gates.test[0, 1])
    print(h.awg2dac_ratios)
    # h.virtual_gates.test[0, 1] = 0.1
    
    print(h.virtual_gates.test[0, 1])
