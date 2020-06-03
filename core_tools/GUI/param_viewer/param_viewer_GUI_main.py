from core_tools.GUI.param_viewer.param_viewer_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial

import numpy as np
from dataclasses import dataclass

@dataclass
class gate_data_obj:
    gate_parameter : any
    gui_input_param : any


class param_viewer(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, gates_object):
        self.real_gates = list()
        self.virtual_gates = list()
        self.gates_object = gates_object
        self._step_size = 1 #mV
        instance_ready = True
        
        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        
        # add real gates
        for gate_name in gates_object.hardware.dac_gate_map.keys():
            param = getattr(gates_object, gate_name)
            self._add_gate(param, False)

        # add virtual gates
        for virt_gate_set in gates_object.hardware.virtual_gates:
            for gate_name in virt_gate_set.virtual_gate_names:
                param = getattr(gates_object, gate_name)
                self._add_gate(param, True)

        self.step_size.valueChanged.connect(partial(self._update_step, self.step_size.value))
        self._finish_gates_GUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(partial(self._update_gates))
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
        voltage_input.valueChanged.connect(partial(self._set_gate, parameter, voltage_input.value))
        voltage_input.setKeyboardTracking(False)
        layout.addWidget(voltage_input, i, 1, 1, 1)

        gate_unit = QtWidgets.QLabel(self.virtualgates)
        gate_unit.setObjectName(name + "_unit")
        gate_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(gate_unit, i, 2, 1, 1)
        if virtual == False:
            self.real_gates.append(gate_data_obj(parameter,  voltage_input))
        else:
            self.virtual_gates.append(gate_data_obj(parameter,  voltage_input))

    def _set_gate(self, gate, value):
        # TODO add support if out of range.
        gate.set(value())

    def _finish_gates_GUI(self):
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

    def _update_gates(self):
        '''
        updates the values of all the gates in the parameterviewer periodically
        '''
        idx = self.tab_menu.currentIndex() 

        if idx == 0:
            gates = self.real_gates
        elif idx == 1:
            gates = self.virtual_gates
        else:
            return

        for gate in gates:
            # do not update when a user clicks on it.
            if not gate.gui_input_param.hasFocus():
                gate.gui_input_param.setValue(gate.gate_parameter())

        

if __name__ == "__main__":
    import sys
    import qcodes as qc
    from V2_software.drivers.virtual_gates.examples.hardware_example import hardware_example 
    from V2_software.drivers.virtual_gates.instrument_drivers.virtual_dac import virtual_dac
    from V2_software.drivers.virtual_gates.instrument_drivers.gates import gates

    my_dac_1 = virtual_dac("dac_a", "virtual")
    my_dac_2 = virtual_dac("dac_b", "virtual")
    my_dac_3 = virtual_dac("dac_c", "virtual")
    my_dac_4 = virtual_dac("dac_d", "virtual")

    hw =  hardware_example("hw")
    my_gates = gates("my_gates", hw, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])

    # app = QtWidgets.QApplication(sys.argv)
    # MainWindow = QtWidgets.QMainWindow()
    ui = param_viewer(my_gates)
    # MainWindow.show()
    # sys.exit(app.exec_())