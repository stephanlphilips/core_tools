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


class attenuation_model(QtCore.QAbstractListModel):
    Name  = QtCore.Qt.UserRole + 1
    Ratio = QtCore.Qt.UserRole + 2
    DB = QtCore.Qt.UserRole + 3

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.keys())

    def data(self, QModelIndex, role):
        row = QModelIndex.row()
        if role == self.Name:
            return list(self._data.keys())[row]
        if role == self.Ratio:
            return "{}".format(round((list(self._data.values())[row]),3))
        if role == self.DB:
            return "{}".format(round(20*np.log10(list(self._data.values())[row]),1))

    def roleNames(self):
        return {
            QtCore.Qt.UserRole + 1: b'name',
            QtCore.Qt.UserRole + 2: b'ratio',
            QtCore.Qt.UserRole + 3: b'db',
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
        print(item)
        idx = list(self._data.keys()).index(item)
        return list(self._data.values())[idx]

class singal_hander_4_vg_matrix(QtQuick.QQuickView):
    def __init__(self, attentuation_ratios_model):
        super().__init__()
        self.attentuation_ratios_model = attentuation_ratios_model
        self.selected_tab = 0

    @QtCore.pyqtSlot('int','QString', result=str)
    def process_attenuation_update_nrml(self, name, number):
        number = float(number)
        print('NORM', name, number)
        if number >= 1:
            return '1.000'
        elif number <= 0.001 :
            return '0.001'
        else:
            return f'{number:.3f}'

    @QtCore.pyqtSlot('int','QString', result=str)
    def process_attenuation_update_db(self, name, number):
        number = float(number)
        print(name, number)
        if number >= 0:
            return '0.0'
        elif number <= -60 :
            return '-60.0'
        else:
            return f'{number:.1f}'

    @QtCore.pyqtSlot('QString', 'int')
    def add_step(self, name, sign):
        val_step_pair = self.model_4_name_values[name]
        val_step_pair.value = val_step_pair.value + sign*val_step_pair.step

        precision = int(-np.log10(val_step_pair.step) + 5)
        if precision > 0:
            val_step_pair.value = np.round(val_step_pair.value, precision)

        self.model_4_name_values.update_data(name, val_step_pair.value, True)

    @QtCore.pyqtSlot('int')
    def update_tab(self, tab):
        self.selected_tab = tab
        self.model_4_name_values.reset_data(self.data[self.categories[tab]])

    @QtCore.pyqtSlot()
    def update_data(self):
        self.model_4_name_values.update_all_data()

    def set_categories(self, categories):
        self.categories = categories
        self.model_4_categories.reset_data(self.categories)
    
    # external_updates
    def set_data(self):
        tab = self.selected_tab
        self.model_4_name_values.reset_data(self.data[self.categories[tab]])