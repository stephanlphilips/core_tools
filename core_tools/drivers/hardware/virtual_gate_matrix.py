from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager

from core_tools.drivers.hardware.hardware_SQL_backend import virtual_gate_queries
import numpy as np

def lamda_do_nothing(matrix):
    return matrix

class virtual_gate_matrix(): 
    def __init__(self, name, gates, v_gates, data,
            forward_conv_lamda = lamda_do_nothing, backward_conv_lamda = lamda_do_nothing):
        self.name = name
        self.gates = gates
        self.v_gates = v_gates
        self._matrix = data

        self.forward_conv_lamda = forward_conv_lamda
        self.backward_conv_lamda = backward_conv_lamda

    @property
    def matrix(self):
        return self.forward_conv_lamda(self._matrix)

    @property
    def inv(self):
        l_inv_f = combine_lamdas(self.forward_conv_lamda, lamda_invert)
        l_inv_b = combine_lamdas(self.backward_conv_lamda, lamda_invert)
        return virtual_gate_matrix(self.name, self.gates, self.v_gates, self._matrix, l_inv_f, l_inv_b)
    
    @property
    def norm(self):
        l_norm_f = combine_lamdas(self.forward_conv_lamda, lamda_norm)
        l_norm_b = combine_lamdas(self.backward_conv_lamda, lamda_unnorm)
        return virtual_gate_matrix(self.name, self.gates, self.v_gates, self._matrix, l_norm_f, l_norm_b)
    
    def __getitem__(self, index):
        if isinstance(index, tuple):
            idx_1, idx_2 = index
            idx_1 = self.__evaluate_index(idx_1, self.v_gates)
            idx_2 = self.__evaluate_index(idx_2, self.gates)
            
            return self.matrix[idx_1,idx_2]
        else:
            raise ValueError("wrong input foramt provided ['virtual_gate','gate'] expected).".format(v_gate))
        
    def __setitem__(self, index, value):
        if isinstance(index, tuple):
            idx_1, idx_2 = index
            idx_1 = self.__evaluate_index(idx_1, self.v_gates)
            idx_2 = self.__evaluate_index(idx_2, self.gates)

            self.matrix[idx_1,idx_2] = value
            self._matrix = self.backward_conv_lamda(self.matrix)

            if self.name != 'dummy':
                save(self)
        else:
            raise ValueError("wrong input foramt provided ['virtual_gate','gate'] expected).".format(v_gate))

    def __evaluate_index(self, idx, options):
        if isinstance(idx, int) >= len(options):
            raise ValueError("gate out of range ({}),  size of virtual matrix {}x{}".format(idx, len(options), len(options)))
         
        if isinstance(idx, str):
            if idx not in options: 
                raise ValueError("{} gate does not exist in virtual gate matrix".format(idx))
            else:
                idx = options.index(idx)
        
        return idx

    def __repr__(self):
        descr =  "Virtual gate matrix named {}\nContents:\n".format(self.name)

        content = "\nGates : {}\nVirtual gates : {}\nMatrix :\n".format(self.gates, self.v_gates, self.matrix)

        for row in self.matrix:
            content  += "{}\n".format(row)

        return descr + content

def lamda_invert(matrix):
    return np.linalg.inv(matrix)

def lamda_norm(matrix_no_norm):
    matrix_norm = np.empty(matrix_no_norm.shape)

    for i in range(matrix_norm.shape[0]):
        matrix_norm[i, :] = matrix_no_norm[i]/np.sum(np.abs(matrix_no_norm[i, :]))

    return matrix_norm

def lamda_unnorm(matrix_norm):
    matrix_no_norm = np.empty(matrix_norm.shape)

    for i in range(matrix_norm.shape[0]):
        matrix_no_norm[i, :] = matrix_norm[i, :]/matrix_norm[i, i]

    return matrix_no_norm

def combine_lamdas(l1, l2):
    def new_lamda(matrix):
        return l1(l2(matrix))
    return new_lamda

def load_virtual_gate(name, real_gates, virtual_gates=None):
    conn = SQL_database_manager().conn_local
        
    virtual_gates = name_virtual_gates(virtual_gates, real_gates)

    if virtual_gate_queries.check_exist(conn, name):
        real_gate_db, virtual_gate_db, matrix_db = virtual_gate_queries.get_virtual_gate_matrix(conn, name)

        entries_to_add = set(real_gates) - set(real_gate_db)

        gates = real_gate_db + list(entries_to_add)

        dummy_matrix = np.eye(len(gates))
        dummy_matrix[:len(real_gate_db) , :len(real_gate_db)] = matrix_db

        dummy_v_gates = virtual_gate_matrix('dummy', gates, name_virtual_gates(None, gates), dummy_matrix)

        v_gate_matrix = np.eye(len(real_gates))

        for i in range(len(real_gates)):
            for j in range(len(real_gates)):
                v_gate_matrix[i, j] = dummy_v_gates['v' + real_gates[i],real_gates[j]]

        return virtual_gate_matrix(name, real_gates, virtual_gates, v_gate_matrix)

    else:
        return virtual_gate_matrix(name, real_gates, virtual_gates, np.eye(len(real_gates)))

def save(vg_matrix):
    conn = SQL_database_manager().conn_local

    if virtual_gate_queries.check_exist(conn, vg_matrix.name):
        # merge in case there are more entries
        real_gate_db, virtual_gate_db, matrix_db = virtual_gate_queries.get_virtual_gate_matrix(conn, vg_matrix.name)
        all_gates = list(set(real_gate_db + vg_matrix.gates))

        dummy_v_gates = virtual_gate_matrix('dummy', all_gates, name_virtual_gates(None, all_gates), np.eye(len(all_gates)))

        for i in range(len(real_gate_db)):
            for j in range(len(real_gate_db)):
                dummy_v_gates['v' + real_gate_db[i], real_gate_db[j]] = matrix_db[i,j]
        
        for i in range(len(vg_matrix.gates)):
            for j in range(len(vg_matrix.gates)):
                dummy_v_gates['v' + vg_matrix.gates[i], vg_matrix.gates[j]] = vg_matrix._matrix[i,j]

        virtual_gate_queries.set_virtual_gate_matrix(conn, vg_matrix.name, 
            dummy_v_gates.gates, dummy_v_gates.v_gates, dummy_v_gates._matrix)

    else:
        virtual_gate_queries.set_virtual_gate_matrix(conn, vg_matrix.name, 
            vg_matrix.gates, vg_matrix.v_gates, vg_matrix._matrix)

def name_virtual_gates(v_gate_names, real_gates):
    if v_gate_names is None:
        v_gates = []
        for i in real_gates:
            v_gates += ['v' + i]
    else:
        v_gates = v_gate_names

    return v_gates
