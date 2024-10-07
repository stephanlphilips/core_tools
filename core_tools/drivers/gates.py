from functools import partial
from core_tools import __version__ as ct_version
from core_tools.drivers.hardware.hardware import hardware as hw_parent

import qcodes as qc
import numpy as np
import copy
import logging

logger = logging.getLogger(__name__)


class gates(qc.Instrument):
    """
    gates class, generate qcodes parameters for the real gates and the virtual gates
    It also manages the virtual gate matrix.
    """
    def __init__(self, name, hardware, dac_sources, dc_gain={}):
        '''
        gates object
        args:
            name (str) : name of the instrument
            hardware (class) : class describing the instrument
            dac_sources (list<virtual_dac>) : list with the dacs
            dc_gain (Dict[str,float]) : DC gain factors to compensate for.

        Notes:
            DC gain is the value of the external amplification factor.
            dc_gain = {'P1': 4.0} means P1 has an external amplification of 4.0.
            The DAC output will be set to v_gate/4.0.

            To avoid accidents, DC gain cannot be changed at run-time.
        '''
        super(gates, self).__init__(name)

        if not isinstance(hardware, hw_parent):
            logger.info('Detected old hardware class')

        self.hardware = hardware
        self.dc_gain = dc_gain.copy()

        self._dac_params = {}
        self._gv = dict()
        self._real_gates = list()
        self._virtual_gates = list()
        self._virt_gate_convertors = list()
        self._all_gate_names = list()

        # add gates:
        for gate_name, dac_location in self.hardware.dac_gate_map.items():
            source_index, ch_num = dac_location
            self._dac_params[gate_name] = dac_sources[source_index][f'dac{int(ch_num)}']
            self._all_gate_names.append(gate_name)
            self._real_gates.append(gate_name)
            self.add_parameter(gate_name, set_cmd = partial(self._set_voltage,  gate_name),
                               get_cmd=partial(self._get_voltage,  gate_name),
                               unit = "mV")

        # make virtual gates:
        for virt_gate_set in self.hardware.virtual_gates:
            virt_gate_convertor = virt_gate_set.get_view(available_gates=self._all_gate_names)
            self._virt_gate_convertors.append(virt_gate_convertor)
            self._all_gate_names += virt_gate_convertor.virtual_gates
            self._virtual_gates += virt_gate_convertor.virtual_gates
            for v_gate_name in virt_gate_convertor.virtual_gates:
                self.add_parameter(v_gate_name,
                                   set_cmd=partial(self._set_voltage_virt, v_gate_name, virt_gate_convertor),
                                   get_cmd=partial(self._get_voltage_virt, v_gate_name, virt_gate_convertor),
                                   unit="mV")

        self._projection_cache_matrices = []
        self._projection_cache_projection = None

    def get_idn(self):
        return dict(vendor='CoreTools',
                    model='gates',
                    serial='',
                    firmware=ct_version)

    @property
    def gates(self):
        return list(self._real_gates)

    @property
    def v_gates(self):
        return list(self._virtual_gates)

    def _set_voltage(self, gate_name, voltage):
        '''
        set a voltage to the dac
        Args:
            voltage (double) : voltage to set
            gate_name (str) : name of the gate to set
        '''
        if gate_name in self.hardware.boundaries.keys():
            min_voltage, max_voltage = self.hardware.boundaries[gate_name]
            if voltage < min_voltage or voltage > max_voltage:
                raise ValueError(f"Voltage boundaries violated, trying to set gate {gate_name} to {voltage:.1f} mV.\n"
                                 f"The limit is set to {min_voltage} to {max_voltage} mV.")

        if gate_name in self.dc_gain:
            dac_voltage = voltage / self.dc_gain[gate_name]
            logger.info(f'set {gate_name} {voltage:.1f} mV (DAC:{dac_voltage:.1f} mV)')
        else:
            dac_voltage = voltage
            logger.info(f'set {gate_name} {voltage:.1f} mV')
        self._dac_params[gate_name](dac_voltage)

    def _get_voltage(self, gate_name):
        '''
        get a voltage to the dac
        Args:
            gate_name (str) : name of the gate to set
        '''
        voltage = self._dac_params[gate_name].cache()
        if gate_name in self.dc_gain:
            return voltage * self.dc_gain[gate_name]
        else:
            return voltage

    def _set_voltage_virt(self, gate_name, virt_gate_convertor, voltage):
        '''
        set a voltage to the virtual dac
        Args:
            voltage (double) : voltage to set
            gate_name : name of the virtual gate
        '''
        old_voltages = self.get_all_gate_voltages()
        projection = self.get_virtual_gate_projection()
        delta = voltage - old_voltages[gate_name]
        logger.info(f'set {gate_name} {old_voltages[gate_name]:.1f} -> {voltage:.1f} mV')

        try:
            for real_gate, ratio in projection[gate_name].items():
                self.set(real_gate, old_voltages[real_gate] + ratio * delta)
        except Exception as ex:
            logger.warning(f'Failed to set virtual gate voltage to {voltage:.1f} mV; Reverting all voltages. '
                            f'Exception: {ex}')
            for real_gate, ratio in projection[gate_name].items():
                self.set(real_gate, old_voltages[real_gate])
            raise

    def _get_voltage_virt(self, gate_name, virt_gate_convertor):
        '''
        get a voltage to the virtual dac
        Args:
            gate_name : name of the virtual gate
        '''
        return self.get_all_gate_voltages()[gate_name]

    def _get_voltages(self, gates):
        return [self.get(gate_name) for gate_name in gates]

    def set_all_zero(self):
        '''
        set all dacs in the gate set to 0. Is ramped down 1 per 1
        '''
        print("In progress ..")
        for gate_name, dac_location in self.hardware.dac_gate_map.items():
            self.set(gate_name, 0)
        print("All gates set to 0!")

    @property
    def gv(self):
        '''
        get a dict with all the gate value of dacs (real values).
        Return:
            real_voltages (dict<str, double>): dict with gate name as key and the corresponding voltage as value
        '''
        for gate_name, my_dac_location in self.hardware.dac_gate_map.items():
            self._gv[gate_name] = self._get_voltage(gate_name)

        return copy.copy(self._gv)

    @gv.setter
    def gv(self, my_gv):
        '''
        setter for voltages
        '''
        names = list(my_gv.keys())
        voltages = list(my_gv.values())

        for i in range(len(names)):
            self._set_voltage(names[i], voltages[i])

    def get_gate_voltages(self):
        res = {}
        for gate_name in self._all_gate_names:
            res[gate_name] = f'{self.get(gate_name):.2f}'
        return res

    def get_all_gate_voltages(self):
        # NOTE: also set all cached values for snapshot!
        v = {}
        for name in self._real_gates:
            v_real = self._get_voltage(name)
            v[name] = v_real
            self[name].cache.set(v_real)

        for virt_gate_convertor in self._virt_gate_convertors:
            real_voltages = [v[name] for name in virt_gate_convertor.real_gates]
            virtual_voltages =  np.matmul(virt_gate_convertor.r2v_matrix, real_voltages)
            for vg_name, vg_voltage in zip(virt_gate_convertor.virtual_gates, virtual_voltages):
                v[vg_name] = vg_voltage
                self[vg_name].cache.set(vg_voltage)

        return v

    def get_virtual_gate_projection(self):
        '''
        Returns a dictionary with per virtual gate name a dictionary
        with real gate names and multipliers.
        Example:
             'vP1': {'P1': 1.0, 'P2': -0.12},
             'vP2': {'P1': -0.10, 'P2': 1.0},
        '''
        # cache physical channels and matrices. Do not recompute if nothing changed.
        if (len(self._virt_gate_convertors) == len(self._projection_cache_matrices)):
            for i, vm in enumerate(self._virt_gate_convertors):
                if not np.array_equal(vm.r2v_matrix, self._projection_cache_matrices[i]):
                    break
            else:
                # nothing has changed.
                return self._projection_cache_projection

        gates = list(self._real_gates)
        projection_matrix = np.eye(len(gates))

        for vm in self._virt_gate_convertors:

            real_gates = vm.real_gates
            v2r = np.linalg.inv(vm.r2v_matrix)
            # select real gate columns from projection matrix
            col_indices = [gates.index(gate) for gate in real_gates]
            m = projection_matrix[:, col_indices]
            # multiply and concatenate
            p_new = m @ v2r

            projection_matrix = np.concatenate([projection_matrix, p_new], axis=-1)
            # add virtual gates to gate list
            gates += vm.virtual_gates

        # return map
        result = {}
        for i, gate in enumerate(gates):
            if gate in self._real_gates:
                # Only project virtual gates to physical gates. Skip real gates.
                continue
            gate_values = {}
            result[gate] = gate_values
            for j, real_gate in enumerate(self._real_gates):
                value = projection_matrix[j, i]
                if np.abs(value) > 1e-5:
                    gate_values[real_gate] = value

        self._projection_cache_matrices = []
        for vm in self._virt_gate_convertors:
            self._projection_cache_matrices.append(vm.r2v_matrix.copy())
        self._projection_cache_projection = result

        return result

    def snapshot_base(self, update=False, params_to_skip_update=None):
        # update real and virtual gates cached values by getting them.
        self.get_all_gate_voltages()

        return super().snapshot_base(update, params_to_skip_update)
