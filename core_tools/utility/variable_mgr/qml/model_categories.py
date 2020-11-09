from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets
import core_tools.utility.variable_mgr.qml as qml_in
from dataclasses import dataclass

import numpy as np
import os, sys

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'

@dataclass
class var_raw:
    name : str
    value : float
    step : int

class categories_model(QtCore.QAbstractListModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, QModelIndex, role):
        row = QModelIndex.row()
        return self._data[row]
    def roleNames(self):
        return {
            QtCore.Qt.UserRole + 1: b'category',
        }
    def reset_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class name_value_model(QtCore.QAbstractListModel):
    Name =QtCore.Qt.UserRole + 1
    Value = QtCore.Qt.UserRole + 2
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.keys())

    def data(self, QModelIndex, role):
        row = QModelIndex.row()
        if role == self.Name:
            return list(self._data.keys())[row]
        if role == self.Value:
            return "{}".format((list(self._data.values())[row].value))

    def roleNames(self):
        return {
            QtCore.Qt.UserRole + 1: b'name',
            QtCore.Qt.UserRole + 2: b'value'
        }

    def reset_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def update_all_data(self):
        self.dataChanged.emit(self.index(0), self.index(self.rowCount()), self.roleNames())

    def update_data(self, name, value, force=False):
        try:
            if float(value) == self._data[name].value and force==False:
                return
            print('updating {} to {}'.format(name, float(value)))
            self._data[name].value = float(value)
            idx = list(self._data.keys()).index(name)
            idx_qt = self.index(idx)
            self.dataChanged.emit(idx_qt, idx_qt, self.roleNames())
        except ValueError:
            print('Error {} could not be converted into a number.'.format(str(value)))

    def __getitem__(self, item):
        idx = list(self._data.keys()).index(item)
        return list(self._data.values())[idx]

class singal_hander_4_variable_exporer(QtQuick.QQuickView):
    def __init__(self, model_4_categories, model_4_name_values, data):
        super().__init__()
        self.model_4_categories = model_4_categories
        self.model_4_name_values = model_4_name_values
        self.data = data
        self.categories = model_4_categories._data
        self.selected_tab = 0

    @QtCore.pyqtSlot('QString','QString')
    def outputStr(self, name, number):
        self.model_4_name_values.update_data(name, number)

    @QtCore.pyqtSlot('QString', 'int')
    def add_step(self, name, sign):
        val_step_pair = self.model_4_name_values[name]
        val_step_pair.value = val_step_pair.value + sign*val_step_pair.step

        precision = 0  
        if val_step_pair.step != 0:
            precision = int(-np.log10(val_step_pair.step) + 5)
        if precision > 0:
            val_step_pair.value = np.round(val_step_pair.value, precision)

        self.model_4_name_values.update_data(name, val_step_pair.value, True)

    @QtCore.pyqtSlot('int')
    def update_tab(self, tab):
        self.selected_tab = tab
        self.model_4_name_values.reset_data(self.data[self.categories[tab]])

    def set_categories(self, categories):
        self.categories = categories
        self.model_4_categories.reset_data(self.categories)
    
    def set_data(self):
        self.categories = list(self.data.keys())
        self.model_4_categories.reset_data(self.categories)
        self.model_4_name_values.reset_data(self.data[self.categories[self.selected_tab]])
    
    # external_updates
    @QtCore.pyqtSlot()
    def update_data(self):
        self.model_4_name_values.update_all_data()