from core_tools.GUI.virt_gate_matrix.virt_gate_matrix_window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial

import numpy as np


def inv_cap_to_cap_mat(inv_cap):
    '''
    convert the normalized inverted capacitance matrix to the capacitance matrix.

    Args:
        inv_cap (np.ndarray) : matrix representing the inverse of the capacitance of the dots.
    '''
    inv_cap_no_view = np.asarray(inv_cap)
    cap = np.linalg.inv(inv_cap_no_view)
    return cap

def cap_to_inv_cap_mat(cap):
    '''
    convert capacitance matrix to the normalized inverted capacitance matrix.

    Args:
        inv_cap (np.ndarray) : matrix representing the inverse of the capacitance of the dots (normalized).
    '''
    cap_no_view = np.asarray(cap)
    return np.linalg.inv(cap_no_view)

class virt_gate_matrix_GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, gates_object, pulse_lib):
        self.gates = []
        self.gates_object = gates_object
        self.AWG_attentuation_local_data = dict()
        self.timers =list()
        self.stepsize = 0.001
        instance_ready = True

        self.pulse_lib = pulse_lib
        # Use attenuation table from the hardware object
        # hardware object is now data owner. Where needed changes should be reloaded to pulse_lib
        hardware = self.gates_object.hardware
        self.pulse_lib.load_hardware(hardware)
        self._old_harware_class = not hasattr(hardware, 'awg2dac_ratios')
        if self._old_harware_class:
            # old harware class
            self._awg_attenuation = hardware.AWG_to_dac_conversion
        else:
            # new hardware class
            self._awg_attenuation = hardware.awg2dac_ratios

        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)

        gates = self._awg_attenuation.keys()

        for gate in gates:
            if gate not in pulse_lib.marker_channels:
                self.add_gate(gate)

        self.add_spacer()

        for virtual_gate_set in hardware.virtual_gates:
            self._add_matrix(virtual_gate_set)

        self.show()
        if instance_ready == False:
            self.app.exec()

    def add_gate(self, gate_name):
        gate = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(gate.sizePolicy().hasHeightForWidth())
        gate.setSizePolicy(sizePolicy)
        gate.setMinimumSize(QtCore.QSize(0, 26))
        font = QtGui.QFont()
        font.setPointSize(11)
        gate.setFont(font)
        gate.setLayoutDirection(QtCore.Qt.RightToLeft)
        gate.setAutoFillBackground(False)
        gate.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        gate.setObjectName(gate_name)
        self.verticalLayout_2.addWidget(gate)
        _translate = QtCore.QCoreApplication.translate
        gate.setText(_translate("MainWindow", gate_name))
        self.gates.append(gate)

        v_ratio_value = self._awg_attenuation[gate_name]

        v_ratio = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        v_ratio.setObjectName("v_ratio")
        v_ratio.setDecimals(3)
        v_ratio.setMaximum(1.0)
        v_ratio.setSingleStep(0.01)
        v_ratio.setMinimumSize(QtCore.QSize(0, 26))

        v_ratio.setValue(v_ratio_value)

        v_ratio.valueChanged.connect(partial(self.update_v_ratio, gate_name))
        self.verticalLayout_4.addWidget(v_ratio)

        db_ratio = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        db_ratio.setObjectName("db_ratio")
        db_ratio.setMaximum(0.0)
        db_ratio.setMinimum(-100.0)
        db_ratio.setMinimumSize(QtCore.QSize(0, 26))

        db_ratio.setValue(20*np.log10(v_ratio_value))
        db_ratio.valueChanged.connect(partial(self.update_db_ratio, gate_name))
        self.verticalLayout_3.addWidget(db_ratio)

        self.AWG_attentuation_local_data[gate_name] = (v_ratio, db_ratio)

    def update_db_ratio(self, gate_name):
        '''
        On change of the db ratio, update the voltage ratio to the corresponding value + update in the virtual gate matrixes.

        Args:
            gate_name (str) : name of the gate the is being updated
        '''

        v_ratio, db_ratio = self.AWG_attentuation_local_data[gate_name]
        v_ratio_value = 10**(db_ratio.value()/20)
        v_ratio.setValue(v_ratio_value)
        self.update_awg_attenuation(gate_name, v_ratio_value)

    def update_v_ratio(self, gate_name):
        '''
        On change of the voltage ratio, update the db ratio to the corresponding value + update in the virtual gate matrixes.

        Args:
            gate_name (str) : name of the gate the is being updated
        '''

        v_ratio, db_ratio = self.AWG_attentuation_local_data[gate_name]
        db_ratio_value = 20*np.log10(v_ratio.value())
        db_ratio.setValue(db_ratio_value)

        self.update_awg_attenuation(gate_name, v_ratio.value())

    def update_awg_attenuation(self, gate_name, v_ratio):
        self._awg_attenuation[gate_name] = v_ratio
        hardware = self.gates_object.hardware
        if self._old_harware_class:
            hardware.sync_data()
        self.pulse_lib.load_hardware(hardware)

    def add_spacer(self):
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        spacerItem1 = QtWidgets.QSpacerItem(30, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_2.addItem(spacerItem1)

        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem2)
        spacerItem3 = QtWidgets.QSpacerItem(30, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_4.addItem(spacerItem3)


        spacerItem4 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem4)
        spacerItem5 = QtWidgets.QSpacerItem(30, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_3.addItem(spacerItem5)

    def _add_matrix(self, virtual_gate_set):
        '''
        add a matrix to the gui.

        Args:
            virtual_gate_set (virtual_gate) : virtual gate object where to fetch the data from
        '''
        Virtual_gates_matrix = QtWidgets.QWidget()
        # Virtual_gates_matrix.setObjectName("Virtual_gates_matrix")
        gridLayout = QtWidgets.QGridLayout(Virtual_gates_matrix)
        # gridLayout_3.setObjectName("gridLayout_3")
        self.tabWidget.addTab(Virtual_gates_matrix, virtual_gate_set.name)

        _translate = QtCore.QCoreApplication.translate
        tableWidget = QtWidgets.QTableWidget(Virtual_gates_matrix)
        self.tablewid = tableWidget
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(tableWidget.sizePolicy().hasHeightForWidth())
        tableWidget.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(12)
        tableWidget.setFont(font)
        tableWidget.setColumnCount(len(virtual_gate_set))
        tableWidget.setObjectName("virtgates")
        tableWidget.setRowCount(len(virtual_gate_set))
        for i in range(len(virtual_gate_set)):
            item = QtWidgets.QTableWidgetItem()
            tableWidget.setHorizontalHeaderItem(i, item)
            item.setText(_translate("MainWindow", virtual_gate_set.virtual_gate_names[i]))

            item = QtWidgets.QTableWidgetItem()
            tableWidget.setVerticalHeaderItem(i, item)
            item.setText(_translate("MainWindow", virtual_gate_set.real_gate_names[i]))

        tableWidget.horizontalHeader().setDefaultSectionSize(45)
        tableWidget.horizontalHeader().setMaximumSectionSize(100)
        tableWidget.horizontalHeader().setMinimumSectionSize(30)
        tableWidget.verticalHeader().setDefaultSectionSize(20)
        gridLayout.addWidget(tableWidget, 0, 0, 1, 1)

        update_list = []
        for i in range(len(virtual_gate_set)):
            for j in range(len(virtual_gate_set)):
                doubleSpinBox = QtWidgets.QDoubleSpinBox()
                sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(doubleSpinBox.sizePolicy().hasHeightForWidth())
                font = QtGui.QFont()
                font.setPointSize(10)
                doubleSpinBox.setFont(font)
                doubleSpinBox.setSizePolicy(sizePolicy)
                doubleSpinBox.setMinimumSize(QtCore.QSize(30, 0))
                doubleSpinBox.setMaximumSize(QtCore.QSize(100, 50))
                doubleSpinBox.setWrapping(False)
                doubleSpinBox.setFrame(False)
                doubleSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                doubleSpinBox.setPrefix("")
                doubleSpinBox.setMaximum(5.0)
                doubleSpinBox.setMinimum(-5.0)
                doubleSpinBox.setSingleStep(0.001)
                doubleSpinBox.setDecimals(3)
                doubleSpinBox.setContentsMargins(0,0,0,0)
                inverted_matrix = np.linalg.inv(virtual_gate_set.virtual_gate_matrix_no_norm)
                doubleSpinBox.setValue(inverted_matrix[i,j])
                doubleSpinBox.setObjectName("doubleSpinBox")
                doubleSpinBox.valueChanged.connect(partial(self.linked_result, virtual_gate_set.virtual_gate_matrix_no_norm, i, j, doubleSpinBox))
                update_list.append((i,j, doubleSpinBox))
                tableWidget.setCellWidget(i, j, doubleSpinBox)
        # make a timer to refresh the data in the plot when the matrix is changed externally.
        timer = QtCore.QTimer()
        timer.timeout.connect(partial(self.update_v_gates, virtual_gate_set.virtual_gate_matrix_no_norm, update_list))
        timer.start(2000)
        self.timers.append(timer)


    def linked_result(self, matrix, i, j, spin_box):
        matrix_no_view = matrix
        inv_cap = cap_to_inv_cap_mat(matrix)
        inv_cap[i,j] = spin_box.value()
        cap_mat = inv_cap_to_cap_mat(inv_cap)
        matrix_no_view[:, :] = cap_mat
        if self._old_harware_class:
            self.gates_object.hardware.sync_data()

    def update_v_gates(self, matrix, update_list):
        """ Update the virtual gate matrix elements

        Args:
            matrix: Array with new values
            update_list: List with GUI boxes
        """
        inv_cap = cap_to_inv_cap_mat(matrix)

        for i,j, spin_box in update_list:
            if not spin_box.hasFocus():
                # print(f'setting {i},{j} to {inv_cap[i,j]}')
                spin_box.setValue(inv_cap[i,j])


if __name__ == "__main__":

    from pulse_templates.demo_pulse_lib.virtual_awg import get_demo_lib
    from hardware_example import hardware6dot
    from core_tools.drivers.virtual_dac import virtual_dac
    from core_tools.drivers.gates import gates

    my_dac_1 = virtual_dac("dac_a", "virtual")
    my_dac_2 = virtual_dac("dac_b", "virtual")
    my_dac_3 = virtual_dac("dac_c", "virtual")
    my_dac_4 = virtual_dac("dac_d", "virtual")

    hw =  hardware6dot('test1')
    my_gates = gates("my_gates", hw, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])
    pulse = get_demo_lib('six')

    ui = virt_gate_matrix_GUI(my_gates, pulse)
