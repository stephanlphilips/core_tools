import numpy as np

class VirtualGateMatrixView:
    '''
    Data to convert real gate voltages to virtual gate voltages and v.v.

    Args:
        name (str): name of the matrix
        real_gates (list[str]): names of real gates
        virtual_gates (list[str]): names of virtual gates
        r2v_matrix (2D array-like): matrix to convert voltages of real gates to voltages of virtual gates.
    '''
    def __init__(self, name, real_gates, virtual_gates, r2v_matrix, indices):
        self.name = name
        self._real_gates = real_gates
        self._virtual_gates = virtual_gates
        self._r2v_matrix = r2v_matrix
        self._indices = indices

    @property
    def real_gates(self):
        '''
        Names of real gates
        '''
        return self._real_gates

    @property
    def virtual_gates(self):
        '''
        Names of virtual gates
        '''
        return self._virtual_gates

    @property
    def r2v_matrix(self):
        # note: self._r2v_matrix may be changed externally. Create indexed copy here.
        r2v_matrix = self._r2v_matrix[self._indices][:,self._indices]
        return r2v_matrix


class VirtualGateMatrix:

    def __init__(self, persistent_object, normalization=False):
        '''
        generate a virtual gate object.
        Args:
            real_gate_names (list<str>) : list with the names of real gates
            virtual_gate_names (list<str>) :
                (optional) names of the virtual gates set. If not provided a "v" is inserted before the gate name.
            normalization (bool or str): normalize matrix.
        '''
        self._persistent_object = persistent_object
        self._normalization = normalization
        # store matrix and inverse to minimize conversions back and forth during editing.
        self._r2v_matrix = self._persistent_object.r2v_matrix_no_norm
        self._v2r_matrix = np.linalg.inv(self._r2v_matrix)
        # object shared with outside world reflecting the 'normalized' r2v matrix.
        self._norm_r2v_matrix = np.zeros(self._r2v_matrix.shape)
        self._calc_normalized()

    @property
    def name(self):
        return self._persistent_object.name

    @property
    def real_gate_names(self):
        '''
        Names of real gates
        '''
        return self._persistent_object.real_gate_names

    @property
    def virtual_gate_names(self):
        '''
        Names of virtual gates
        '''
        return self._persistent_object.virtual_gate_names

    @property
    def normalization(self):
        return self._normalization

    @property
    def virtual_gate_matrix(self):
        return self._norm_r2v_matrix

    @property
    def virtual_gate_matrix_no_norm(self):
        return self._r2v_matrix

    @property
    def matrix(self):
        # read-only view of matrix
        matrix = self._r2v_matrix[:]
        matrix.setflags(write=False)
        return matrix

    @matrix.setter
    def matrix(self, value):
        self._r2v_matrix[:] = value
        self._v2r_matrix[:] = np.linalg.inv(self._r2v_matrix)
        self._calc_normalized()
        self._persistent_object.save()

    @property
    def gates(self):
        return self.real_gate_names

    @property
    def v_gates(self):
        return self.virtual_gate_names

    def get_element(self, i, j, v2r=True):
        if v2r:
            return self._v2r_matrix[i,j]
        else:
            return self._r2v_matrix[i,j]

    def set_element(self, i, j, value, v2r=True):
        if v2r:
            self._v2r_matrix[i,j] = value
            self._r2v_matrix[:] = np.linalg.inv(self._v2r_matrix)
        else:
            self._r2v_matrix[i,j] = value
            self._v2r_matrix[:] = np.linalg.inv(self._r2v_matrix)

        self._calc_normalized()
        self._persistent_object.save()

    def normalize(self):
        if self._normalization:
            self._r2v_matrix[:] = self._norm_r2v_matrix
            self._v2r_matrix[:] = np.linalg.inv(self._r2v_matrix)
            self._persistent_object.save()

    def reverse_normalize(self):
        if self._normalization:
            # divide columns of v2r by diagonal value
            self._v2r_matrix[:] = self._v2r_matrix / np.diag(self._v2r_matrix)
            self._r2v_matrix[:] = np.linalg.inv(self._v2r_matrix)
            self._persistent_object.save()

    def _calc_normalized(self):
        no_norm = self._r2v_matrix

        if self._normalization:
            # divide rows by diagonal value
            norm = no_norm/np.diag(no_norm)[:,None]
        else:
            norm = no_norm

        self._norm_r2v_matrix[:] = norm

    def get_view(self, available_gates):
        gate_indices = []
        real_gate_names = []
        virtual_gate_names = []

        for i,name in enumerate(self.real_gate_names):
            if name in available_gates:
                gate_indices.append(i)
                real_gate_names.append(name)
                virtual_gate_names.append(self.virtual_gate_names[i])

        return VirtualGateMatrixView(self.name,
                                     real_gate_names,
                                     virtual_gate_names,
                                     self._norm_r2v_matrix,
                                     gate_indices)

