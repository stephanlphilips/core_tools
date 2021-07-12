# -*- coding: utf-8 -*-
from typing import Optional
from core_tools.GUI.param_viewer.param_viewer_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
import qcodes as qc
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
    def __init__(self, gates_object: Optional[object] = None, keysight_rf: Optional[object] = None):
        self.real_gates = list()
        self.virtual_gates = list()
        self.rf_settings = list()
        self.station = qc.Station.default
        self.keysight_rf = keysight_rf
        self.last_param_value = {}
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
        try:
            for src_name in self.gates_object.hardware.RF_source_names:
                inst = getattr(station, src_name)
                for RFpar in self.gates_object.hardware.RF_params:
                    param = getattr(inst, RFpar)
                    self._add_RFset(param)
        except:
            pass
        try:
            for ks_param in self.keysight_rf.all_params:
                self._add_RFset(ks_param)
        except Exception as e:
            print(e)

        # add real gates
        for gate_name in self.gates_object.hardware.dac_gate_map.keys():
            param = getattr(self.gates_object, gate_name)
            self._add_gate(param, False)

        # add virtual gates
        for virtual_gates_names in self.gates_object.v_gates.values():
            for gate_name in virtual_gates_names:
                param = getattr(self.gates_object, gate_name)
                self._add_gate(param, True)

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

    def update_step(self, value : float):
        """ Update step size of the parameter GUI elements with the specified value """
        self._step_size = value
        for gate in self.real_gates:
            gate.gui_input_param.setSingleStep(value)
        for gate in self.virtual_gates:
            gate.gui_input_param.setSingleStep(value)

        self.step_size.setValue(value)

    def _add_RFset(self, parameter : qc.Parameter):
        ''' Add a new RF.

        Args:
            parameter (QCoDeS parameter object) : parameter to add.
        '''

        i = len(self.rf_settings)
        layout = self.layout_RF

        name = parameter.full_name
        unit = parameter.unit
        step_size = 0.5
        division = 1

        name = name.replace('keysight_rfgen_','')

        if 'freq' in parameter.name:
            division = 1e6
            step_size = 0.1
            unit = f'M{unit}'

        _translate = QtCore.QCoreApplication.translate

        set_name = QtWidgets.QLabel(self.RFsettings)
        set_name.setObjectName(name)
        set_name.setMinimumSize(QtCore.QSize(100, 0))
        set_name.setText(_translate("MainWindow", name))
        layout.addWidget(set_name, i, 0, 1, 1)

        if 'enable' in name:
            set_input = QtWidgets.QCheckBox(self.RFsettings)
            set_input.setObjectName(name + "_input")
            set_input.stateChanged.connect(partial(self._set_bool, parameter, set_input.isChecked))
            layout.addWidget(set_input, i, 1, 1, 1)
        else:
            set_input = QtWidgets.QDoubleSpinBox(self.RFsettings)
            set_input.setObjectName(name + "_input")
            set_input.setMinimumSize(QtCore.QSize(100, 0))

            # TODO collect boundaries out of the harware
            set_input.setRange(-1e9,1e9)
            set_input.valueChanged.connect(partial(self._set_set, parameter, set_input.value,division))
            set_input.setKeyboardTracking(False)
            set_input.setSingleStep(step_size)

            layout.addWidget(set_input, i, 1, 1, 1)

        set_unit = QtWidgets.QLabel(self.RFsettings)
        set_unit.setObjectName(name + "_unit")
        set_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(set_unit, i, 2, 1, 1)
        self.rf_settings.append(param_data_obj(parameter,  set_input, division))

    def _add_gate(self, parameter : qc.Parameter, virtual : bool):
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
        logging.info(f'set_gate {gate.name} = {value()}')
        gate.set(value())

    def _set_set(self, setting, value, division):
        # TODO add support if out of range.
        setting.set(value()*division)
        self.gates_object.hardware.RF_settings[setting.full_name] = value()*division
        self.gates_object.hardware.sync_data()

    def _set_bool(self, setting, value):
        setting.set(value())
        self.gates_object.hardware.RF_settings[setting.full_name] = value()
        self.gates_object.hardware.sync_data()

    def _finish_gates_GUI(self):

        for items, layout_widget in [ (self.real_gates, self.layout_real), (self.virtual_gates, self.layout_virtual),
                              (self.rf_settings, self.layout_RF)]:
            i = len(items) + 1

            spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            layout_widget.addItem(spacerItem, i, 0, 1, 1)

            spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            layout_widget.addItem(spacerItem1, 0, 3, 1, 1)

        self.setWindowTitle(f'Viewer for {self.gates_object}')

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
                if type(param.gui_input_param) == QtWidgets.QDoubleSpinBox:
                    last_value = self.last_param_value.get(param.param_parameter.name, None)
                    new_value = param.param_parameter()/param.division
                    if new_value != last_value:
                        logging.info(f'Update GUI {param.param_parameter.name} {last_value} -> {new_value}')
                        self.last_param_value[param.param_parameter.name] = new_value
                    param.gui_input_param.setValue(new_value)
                elif type(param.gui_input_param) == QtWidgets.QCheckBox:
                    param.gui_input_param.setChecked(param.param_parameter())



if __name__ == "__main__":
    import sys
    import qcodes as qc

    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')
    from core_tools.drivers.hardware.hardware import hardware
    from core_tools.drivers.virtual_dac import virtual_dac
    from core_tools.drivers.gates import gates

    my_dac_1 = virtual_dac("dac_a", "virtual")
    my_dac_2 = virtual_dac("dac_b", "virtual")
    my_dac_3 = virtual_dac("dac_c", "virtual")
    my_dac_4 = virtual_dac("dac_d", "virtual")

    hw =  hardware()
    hw.RF_source_names = []
    hw.dac_gate_map = {
        'B0': (0, 1), 'P1': (0, 2),
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6),
        'B3': (0, 7), 'P4': (0, 8),
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13), 'S6' : (0,14,),
        'SD1_P': (1, 1), 'SD2_P': (1, 2),
        'SD1_B1': (1, 3), 'SD2_B1': (1, 4),
        'SD1_B2': (1, 5), 'SD2_B2': (1, 6),}

    hw.boundaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    hw.virtual_gates.add('test', ['B0', 'P1', 'B1', 'P2', 'B2', 'P3', 'B3', 'P4', 'B4', 'P5', 'B5', 'P6', 'B6', 'S6', 'SD1_P', 'SD2_P', 'COMP1'])
    hw.awg2dac_ratios.add(hw.virtual_gates.test.gates)


    my_gates = gates("gates", hw, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])
    station=qc.Station(my_gates)
    ui = param_viewer()
    from core_tools.GUI.virt_gate_matrix_qml.gui_controller import virt_gate_matrix_GUI
    # virt_gate_matrix_GUI()
