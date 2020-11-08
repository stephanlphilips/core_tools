from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets
import core_tools.utility.variable_mgr.qml as qml_in
from dataclasses import dataclass

import numpy as np
import os, sys

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'

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

@dataclass
class var_raw:
    name : str
    value : float
    step : int

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
    # external_updates
    def set_data(self, data):
        self.data = data
        self.model_4_name_values.reset_data(self.data[self.selected_tab])

class GUI_controller:
    def __init__(self, data):
        super().__init__()
        self.app =  QtGui.QGuiApplication(sys.argv)
#        self.app = QtCore.QCoreApplication.instance()
#        self.instance_ready = True
#        if self.app is None:
#            self.instance_ready = False
#            self.app = QtWidgets.QApplication([])

        self.engine = QtQml.QQmlApplicationEngine()
        self.categories_model = categories_model(list(data.keys()))
        self.data = data
        if len(data)==0:
            self.data_model = name_value_model({})
        else:
            self.data_model = name_value_model(data[list(data.keys())[0]])
        self.singal_hander =singal_hander_4_variable_exporer(self.categories_model, self.data_model, data)

        self.engine.rootContext().setContextProperty("cat_model", self.categories_model)
        self.engine.rootContext().setContextProperty("variable_name_value_pair_list", self.data_model)
        self.engine.rootContext().setContextProperty("test_function", self.singal_hander)

        # grab directory from the import!
        filename = os.path.join(qml_in.__file__[:-11], "variable_mgr_window.qml")
        self.engine.load(QtCore.QUrl.fromLocalFile(filename))
        self.win = self.engine.rootObjects()[0]

        self.app.exec()

#        if self.instance_ready == False:
#            print('exec')
    def update_entry(self, category, raw_value):
        self.data[category] = raw_value
        self.singal_hander.update_entry(category,raw_value)

    def add_entry(self, data):
        '''just update all...'''
        self.data = data

if __name__ == "__main__":
    
    import sys
    from PyQt5.QtCore import QObject
    from PyQt5 import QtGui, QtQml, QtCore
    import time

    data = {'SD voltages':{'SD1_on_11':var_raw('SD1_on_11', 0.1, 0.1), 'SD1_on_11':var_raw('SD1_on_11', 0.4, 0.1), 'SD1_off':var_raw('SD1_off', -5, 0.1), 'SD2_on':var_raw('SD2_on', 3.5, 0.1), 'SD2_off':var_raw('SD2_off', 0, 0.1)},
            'dot properties':{'U1':var_raw('U1',45,1), 'U2':var_raw('U2',50,1), 'U3':var_raw('U3',70,1), 'U4':var_raw('U4',40,1), 'U5':var_raw('U5',50,1), 'U6':var_raw('U6',50,1)},
            'qubit properties':{'f_qubit_1':var_raw('f_qubit_1',18.219e9,0.1e5), 'f_qubit_2':var_raw('f_qubit_2',18.312e9,0.1e5)}}

    g =GUI_controller(data)

    # if not g.engine.rootObjects():
    #     sys.exit(-1)

    # sys.exit(g.app.exec_())
    # print('donesys.argv')