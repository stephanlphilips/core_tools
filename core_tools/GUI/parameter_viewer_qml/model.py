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
        for gate in self.gates:
            self.current_vals += [self._data.get(gate)]

    def rowCount(self, parent=None):
        return len(self.gates)

    def data(self, QModelIndex, role):
        row = QModelIndex.row()
        if role == self.gate:
            return self.gates[row]
        if role == self.voltage:
            number =  self._data.get(self.gates[row])
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

        for i,gate_name in enumerate(self.gates):
            gv = self._data.get(gate_name)

            if self.current_vals[i] != gv:
                print(f'updating {i}, {gv}')
                to_update = True

            self.current_vals[i] = gv

        if to_update == True:
            self.setData(0, 0, QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(result=bool)
    def allow_mouse_wheel_updates(self) -> bool:
        return self._allow_mouse_wheel_updates

    @QtCore.pyqtSlot('QString','QString')
    def set_voltage(self, name, voltage):
        voltage = float(voltage)
        print(f'setting {name} to {voltage}')
        self.current_vals[self.gates.index(name)] = voltage
        self._data.set(name, voltage)