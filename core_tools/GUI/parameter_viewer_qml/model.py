from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets

import numpy as np
import os, sys


class gate_model(QtCore.QAbstractListModel):
    gate  = QtCore.Qt.UserRole + 1
    voltage = QtCore.Qt.UserRole + 2

    def __init__(self, gates_obj, gates, parent=None, allow_mouse_wheel_updates : bool = True):
        super().__init__(parent)
        self._data = gates_obj
        self.gates = gates
        self._allow_mouse_wheel_updates = allow_mouse_wheel_updates

        self.current_vals = list()
        self.virtual_gate_updates = list()
        for gate in self.gates:
            self.current_vals += [getattr(self._data, gate)()]
        for v_gate in self._data.hardware.virtual_gates:
            self.virtual_gate_updates += [v_gate.last_update]

    def rowCount(self, parent=None):
        return len(self.gates)

    def data(self, QModelIndex, role):
        row = QModelIndex.row()
        if role == self.gate:
            return self.gates[row]
        if role == self.voltage:
            number =  getattr(self._data, self.gates[row])()
            return f'{number:.2f}'

    def roleNames(self):
        return {
            QtCore.Qt.UserRole + 1: b'gate',
            QtCore.Qt.UserRole + 2: b'voltage',
        }

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            idx0 = QtCore.QModelIndex()
            idx0.child(0,0)
            idx1  = QtCore.QModelIndex()
            idx1.child(0,0)
            self.dataChanged.emit(idx0, idx1, [QtCore.Qt.EditRole])
            self.beginResetModel()
            self.endResetModel()

            return True

    def update_model(self):
        to_update = False

        for i in range(len(self.gates)):
            gv = getattr(self._data, self.gates[i])()
            
            if self.current_vals[i] != gv:
                to_update = True

            self.current_vals[i] = gv

        for i in range(len(self.virtual_gate_updates)):
            if self.virtual_gate_updates[i] != self._data.hardware.virtual_gates[i].last_update:
                to_update = True
                self.virtual_gate_updates[i] = self._data.hardware.virtual_gates[i].last_update

        if to_update == True:
            self.setData(0, 0, QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(result=bool)
    def allow_mouse_wheel_updates(self) -> bool:
        return self._allow_mouse_wheel_updates

    @QtCore.pyqtSlot('QString','QString')
    def set_voltage(self, name, voltage):
        voltage = float(voltage)

        self.current_vals[self.gates.index(name)] = voltage
        getattr(self._data, name)(voltage)