import numpy as np

from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager
from core_tools.drivers.hardware.hardware_SQL_backend import virtual_gate_queries

from .virtual_gate_matrix_data import VirtualGateMatrixData
from .virtual_gate_matrix import VirtualGateMatrix


def load_virtual_gate(name, real_gates, virtual_gates=None, matrix=None, normalization=False):
    conn = SQL_database_manager().conn_local
    virtual_gate_queries.generate_table(conn)

    if virtual_gates is None:
        virtual_gates = ['v'+gate_name for gate_name in real_gates]

    if matrix is None:
        matrix = np.eye(len(real_gates))
    else:
        matrix = np.asarray(matrix)

    if virtual_gate_queries.check_var_in_table_exist(conn, name):
        real_gate_db, virtual_gate_db, matrix_db = virtual_gate_queries.get_virtual_gate_matrix(conn, name)

        # indices of rows/columns that exist in stored matrix.
        n = len(real_gates)
        indices = [None]*n
        for i,gate_name in enumerate(real_gates):
            if gate_name in real_gate_db:
                indices[i] = real_gate_db.index(gate_name)

        for i in range(n):
            for j in range(n):
                if indices[i] is not None and indices[j] is not None:
                    matrix[i,j] = matrix_db[indices[i], indices[j]]

    data = VirtualGateMatrixData(name, real_gates, virtual_gates, matrix)
    data.saver = save_virtual_gate
    data.save()

    return VirtualGateMatrix(data, normalization=normalization)


def save_virtual_gate(vg_matrix):
    conn = SQL_database_manager().conn_local

    if virtual_gate_queries.check_var_in_table_exist(conn, vg_matrix.name):
        # merge in case there are more entries
        real_gate_db, virtual_gate_db, matrix_db = virtual_gate_queries.get_virtual_gate_matrix(conn, vg_matrix.name)

        # copy gate names to new lists
        all_real_gates = list(vg_matrix.real_gate_names)
        all_virtual_gates = list(vg_matrix.virtual_gate_names)

        for real_db, virtual_db in zip(real_gate_db, virtual_gate_db):
            if real_db not in vg_matrix.real_gate_names:
                all_real_gates.append(real_db)
                all_virtual_gates.append(virtual_db)

        matrix = np.eye(len(all_real_gates))
        # copy data from db in matrix
        for i_db, i_name in enumerate(real_gate_db):
            for j_db, j_name in enumerate(real_gate_db):
                try:
                    i_new = all_real_gates.index(i_name)
                    j_new = all_real_gates.index(j_name)
                    matrix[i_new, j_new] = matrix_db[i_db, j_db]
                except:
                    pass

        # overwrite with data from current matrix
        n = len(vg_matrix.real_gate_names)
        matrix[:n,:n] = vg_matrix.r2v_matrix_no_norm

        virtual_gate_queries.set_virtual_gate_matrix(conn, vg_matrix.name,
            all_real_gates, all_virtual_gates, matrix)
    else:
        virtual_gate_queries.set_virtual_gate_matrix(conn, vg_matrix.name,
            vg_matrix.real_gate_names, vg_matrix.virtual_gate_names, vg_matrix.r2v_matrix_no_norm)
