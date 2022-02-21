# -*- coding: utf-8 -*-
from typing import Optional
from core_tools.GUI.param_viewer.param_viewer_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets
import qcodes as qc
from dataclasses import dataclass
from ..qt_util import qt_log_exception

import logging

@dataclass
class param_data_obj:
    param_parameter : any
    gui_input_param : any
    division : any


class param_viewer(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, gates_object: Optional[object] = None,
                 max_diff : float = 1000):
        self.real_gates = list()
        self.virtual_gates = list()
        self.rf_settings = list()
        self.station = qc.Station.default
        self.max_diff = max_diff
        self.locked = False

        if gates_object:
            self.gates_object = gates_object
        else:
            try:
                self.gates_object = self.station.gates
            except:
                raise ValueError('`gates` must be set in qcodes.station or supplied as argument')
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
        if hasattr(self.gates_object.hardware, 'RF_source_names'):
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
        for gate_name in self.gates_object.v_gates:
            param = getattr(self.gates_object, gate_name)
            self._add_gate(param, True)

        self.lock.stateChanged.connect(lambda: self._update_lock(self.lock.isChecked()))
        self.step_size.valueChanged.connect(lambda: self.update_step(self.step_size.value()))
        self._finish_gates_GUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda:self._update_parameters())
        self.timer.start(500)

        self.show()
        if instance_ready == False:
            self.app.exec()

    @qt_log_exception
    def closeEvent(self, event):
        self.timer.stop()

    @qt_log_exception
    def update_step(self, value : float):
        """ Update step size of the parameter GUI elements with the specified value """
        self._step_size = value
        for gate in self.real_gates:
            gate.gui_input_param.setSingleStep(value)
        for gate in self.virtual_gates:
            gate.gui_input_param.setSingleStep(value)

        self.step_size.setValue(value)

    @qt_log_exception
    def _update_lock(self, locked):
        print('Locked:', locked)
        self.locked = locked

    @qt_log_exception
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
        set_input.valueChanged.connect(lambda:self._set_set(parameter, set_input.value, division))
        set_input.setKeyboardTracking(False)
        set_input.setSingleStep(step_size)

        layout.addWidget(set_input, i, 1, 1, 1)

        set_unit = QtWidgets.QLabel(self.RFsettings)
        set_unit.setObjectName(name + "_unit")
        set_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(set_unit, i, 2, 1, 1)
        self.rf_settings.append(param_data_obj(parameter,  set_input, division))

    @qt_log_exception
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
        voltage_input.setValue(parameter())
        voltage_input.valueChanged.connect(lambda:self._set_gate(parameter, voltage_input.value, voltage_input))
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

    @qt_log_exception
    def _set_gate(self, gate, value, voltage_input):
        if self.locked:
            logging.warning(f'Not changing voltage, ParameterViewer is locked!')
            # Note value will be restored by _update_parameters
            return

        delta = abs(value() - gate())
        if delta > self.max_diff:
            logging.warning(f'Not setting {gate} to {value():.1f}mV. '
                            f'Difference {delta:.0f} mV > {self.max_diff:.0f} mV')
            return

        try:
            last_value = gate.get()
            new_text = voltage_input.text()
            current_text = voltage_input.textFromValue(last_value)
            if new_text != current_text:
                logging.info(f'GUI value changed: set gate {gate.name} {current_text} -> {new_text}')
                gate.set(value())
        except Exception as ex:
            logging.error(f'Failed to set gate {gate} to {value()}: {ex}')


    @qt_log_exception
    def _set_set(self, setting, value, division):
        logging.info(f'setting {setting} to {value():.1f} times {division:.1f}')
        setting.set(value()*division)
        self.gates_object.hardware.RF_settings[setting.full_name] = value()*division
        self.gates_object.hardware.sync_data()

    @qt_log_exception
    def _finish_gates_GUI(self):

        for items, layout_widget in [ (self.real_gates, self.layout_real), (self.virtual_gates, self.layout_virtual),
                              (self.rf_settings, self.layout_RF)]:
            i = len(items) + 1

            spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            layout_widget.addItem(spacerItem, i, 0, 1, 1)

            spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            layout_widget.addItem(spacerItem1, 0, 3, 1, 1)

        self.setWindowTitle(f'Parameter Viewer for {self.gates_object}')

    @qt_log_exception
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
            try:
                # do not update when a user clicks on it.
                gui_input = param.gui_input_param
                if not gui_input.hasFocus():
                    new_value = param.param_parameter()/param.division
                    current_text = gui_input.text()
                    new_text = gui_input.textFromValue(new_value)
                    if current_text != new_text:
                        logging.info(f'Update GUI {param.param_parameter.name} {current_text} -> {new_text}')
                        gui_input.setValue(new_value)
            except:
                logging.error(f'Error updating {param}', exc_info=True)



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
