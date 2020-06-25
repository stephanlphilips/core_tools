# -*- coding: utf-8 -*-
from core_tools.GUI.param_viewer.param_viewer_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
from qcodes import Station
import numpy as np
from dataclasses import dataclass
import logging

@dataclass
class param_data_obj:
    param_parameter : any
    gui_input_param : any
    division : any


class param_viewer(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, station, gates_object = None, max_diff = 100):
        if type(station) is not Station:
            raise Exception('Syntax changed, to support RF_settings now supply station')
        self.real_gates = list()
        self.virtual_gates = list()
        self.rf_settings = list()
        self.station = station
        self.max_diff = max_diff
        self.locked = False
        
        if gates_object:
            self.gates_object = gates_object
        else:
            try:
                self.gates_object = self.station.gates
            except:
                raise ValueError('Default guess for gates object wrong, please supply manually')    
        self._step_size = 1 #mV
        instance_ready = True
        
        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        
        # add RF parameters
        for src_name in self.gates_object.hardware.RF_source_names:
            inst = getattr(station, src_name)
            for RFpar in self.gates_object.hardware.RF_params:
                param = getattr(inst, RFpar)
                self._add_RFset(param)

        # add real gates
        for gate_name in self.gates_object.hardware.dac_gate_map.keys():
            param = getattr(self.gates_object, gate_name)
            self._add_gate(param, False)

        # add virtual gates
        for virt_gate_set in self.gates_object.hardware.virtual_gates:
            for gate_name in virt_gate_set.virtual_gate_names:
                param = getattr(self.gates_object, gate_name)
                self._add_gate(param, True)
        
        self.lock.stateChanged.connect(lambda: self._update_lock(self.lock.isChecked()))
        self.step_size.valueChanged.connect(partial(self._update_step, self.step_size.value))
        self._finish_gates_GUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(partial(self._update_parameters))
        self.timer.start(500)

        self.show()
        if instance_ready == False:
            self.app.exec()
    
    def _update_step(self, value):
        self.update_step(value())

    def update_step(self, value):
        self._step_size = value
        for gate in self.real_gates:
            gate.gui_input_param.setSingleStep(value)
        for gate in self.virtual_gates:
            gate.gui_input_param.setSingleStep(value)

        self.step_size.setValue(value)

    def _add_RFset(self, parameter):
        '''
        add a new gate.

        Args:
            parameter (QCoDeS parameter object) : parameter to add.
            virtual (bool) : True in case this is a virtual gate.
        '''

        i = len(self.rf_settings)
        layout = self.layout_RF
        
        name = parameter.full_name
        unit = parameter.unit
        step_size = 0.5
        division = 1
        
        if parameter.name[0:10] == 'frequency':
            division = 1e6
            step_size = 0.1
            unit = f'M{unit}'

        _translate = QtCore.QCoreApplication.translate

        set_name = QtWidgets.QLabel(self.RFsettings)
        set_name.setObjectName(name)
        set_name.setMinimumSize(QtCore.QSize(100, 0))
        set_name.setText(_translate("MainWindow", name))
        layout.addWidget(set_name, i, 0, 1, 1)

        set_input = QtWidgets.QDoubleSpinBox(self.RFsettings)
        set_input.setObjectName(name + "_input")
        set_input.setMinimumSize(QtCore.QSize(100, 0))
        
        # TODO collect boundaries out of the harware
        set_input.setRange(-1e9,1e9)
        set_input.setValue(parameter()/division)
        set_input.valueChanged.connect(partial(self._set_set, parameter, set_input.value,division))
        set_input.setKeyboardTracking(False)
        set_input.setSingleStep(step_size)
        
        layout.addWidget(set_input, i, 1, 1, 1)

        set_unit = QtWidgets.QLabel(self.RFsettings)
        set_unit.setObjectName(name + "_unit")
        set_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(set_unit, i, 2, 1, 1)
        self.rf_settings.append(param_data_obj(parameter,  set_input, division))

    def _add_gate(self, parameter, virtual):
        '''
        add a new gate.

        Args:
            parameter (QCoDeS parameter object) : parameter to add.
            virtual (bool) : True in case this is a virtual gate.
        '''

        i = len(self.real_gates)
        layout = self.layout_real

        if virtual == True:
            i = len(self.virtual_gates)
            layout = self.layout_virtual
        
        name = parameter.name
        unit = parameter.unit

        _translate = QtCore.QCoreApplication.translate

        gate_name = QtWidgets.QLabel(self.virtualgates)
        gate_name.setObjectName(name)
        gate_name.setMinimumSize(QtCore.QSize(100, 0))
        gate_name.setText(_translate("MainWindow", name))
        layout.addWidget(gate_name, i, 0, 1, 1)

        voltage_input = QtWidgets.QDoubleSpinBox(self.virtualgates)
        voltage_input.setObjectName( name + "_input")
        voltage_input.setMinimumSize(QtCore.QSize(100, 0))
        
        # TODO collect boundaries out of the harware
        voltage_input.setRange(-4000,4000.0)
        voltage_input.setValue(parameter())
        voltage_input.valueChanged.connect(partial(self._set_gate, parameter, voltage_input.value))
        voltage_input.setKeyboardTracking(False)
        layout.addWidget(voltage_input, i, 1, 1, 1)

        gate_unit = QtWidgets.QLabel(self.virtualgates)
        gate_unit.setObjectName(name + "_unit")
        gate_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(gate_unit, i, 2, 1, 1)
        if virtual == False:
            self.real_gates.append(param_data_obj(parameter,  voltage_input, 1))
        else:
            self.virtual_gates.append(param_data_obj(parameter,  voltage_input, 1))

    def _set_gate(self, gate, value):
        # TODO add support if out of range.
        logging.info(f'setting {gate} to {value():.1f}')
        if value() - gate() < self.max_diff:
            if not self.locked:
                gate.set(value())
            else:
                logging.warning(f'not changing voltage, PV is locked!')
        else:
            logging.warning(f'not setting {gate} to {value():.1f}, difference {value() - gate():.0f} mV larger than allowed (self.max_diff:.0f) mV')

    def _set_set(self, setting, value, division):
        # TODO add support if out of range.
        setting.set(value()*division)
        logging.info(f'setting {setting} to {value():.1f} times {division:.1f}')
        self.gates_object.hardware.RF_settings[setting.full_name] = value()*division
        self.gates_object.hardware.sync_data()

    def _finish_gates_GUI(self):
        # MAKE THIS INTO A FOR LOOP
        i = len(self.real_gates) + 1

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout_real.addItem(spacerItem, i, 0, 1, 1)

        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout_real.addItem(spacerItem1, 0, 3, 1, 1)

        i = len(self.virtual_gates) + 1

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout_virtual.addItem(spacerItem, i, 0, 1, 1)

        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout_virtual.addItem(spacerItem1, 0, 3, 1, 1)
        
        i = len(self.rf_settings) + 1

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout_RF.addItem(spacerItem, i, 0, 1, 1)

        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout_RF.addItem(spacerItem1, 0, 3, 1, 1)

    def _update_parameters(self):
        '''
        updates the values of all the gates in the parameterviewer periodically
        '''
        idx = self.tab_menu.currentIndex() 

        if idx == 0:
            params = self.real_gates
        elif idx == 1:
            params = self.virtual_gates
        elif idx == 2:
            params = self.rf_settings
        else:
            return

        for param in params:
            # do not update when a user clicks on it.
            if not param.gui_input_param.hasFocus():
                param.gui_input_param.setValue(param.param_parameter()/param.division)
            
    def _update_lock(self, locked):
        self.locked = locked