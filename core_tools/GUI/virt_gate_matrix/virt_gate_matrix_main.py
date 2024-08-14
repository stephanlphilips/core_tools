from core_tools.GUI.virt_gate_matrix.virt_gate_matrix_window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from ..qt_util import qt_log_exception

import logging
import numpy as np

logger = logging.getLogger(__name__)

class virt_gate_matrix_GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, gates_object, pulse_lib, coloring=True):
        self.gates = []
        self.gates_object = gates_object
        self.AWG_attentuation_local_data = dict()
        self.timers =list()
        instance_ready = True
        self._updating = False
        self._coloring = coloring

        self.pulse_lib = pulse_lib
        # Use attenuation table from the hardware object
        # hardware object is now data owner. Where needed changes should be reloaded to pulse_lib
        hardware = self.gates_object.hardware
        self._old_harware_class = not hasattr(hardware, 'awg2dac_ratios')
        if self._old_harware_class:
            # old harware class
            self._awg_attenuation = hardware.AWG_to_dac_conversion
        else:
            # new hardware class
            self._awg_attenuation = hardware.awg2dac_ratios
        # write attenuation to pulselib
        self.pulse_lib.set_channel_attenuations(self._awg_attenuation)

        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Virtual Matrix Editor")

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

    @qt_log_exception
    def closeEvent(self, event):
        for timer in self.timers:
            timer.stop()

    @qt_log_exception
    def add_gate(self, gate_name):
        gate = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(gate.sizePolicy().hasHeightForWidth())
        gate.setSizePolicy(sizePolicy)
        gate.setMinimumSize(QtCore.QSize(0, 26))
        gate.setMaximumSize(QtCore.QSize(200, 26))
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
        v_ratio.setMaximumSize(QtCore.QSize(120, 26))

        v_ratio.setValue(v_ratio_value)

        v_ratio.valueChanged.connect(lambda:self.update_v_ratio(gate_name))
        self.verticalLayout_4.addWidget(v_ratio)

        db_ratio = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        db_ratio.setObjectName("db_ratio")
        db_ratio.setMaximum(0.0)
        db_ratio.setMinimum(-100.0)
        db_ratio.setMinimumSize(QtCore.QSize(0, 26))
        db_ratio.setMaximumSize(QtCore.QSize(120, 26))

        db_ratio.setValue(20*np.log10(v_ratio_value))
        db_ratio.valueChanged.connect(lambda:self.update_db_ratio(gate_name))
        self.verticalLayout_3.addWidget(db_ratio)

        self.AWG_attentuation_local_data[gate_name] = (v_ratio, db_ratio)

    @qt_log_exception
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

    @qt_log_exception
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

    @qt_log_exception
    def update_awg_attenuation(self, gate_name, v_ratio):
        self._awg_attenuation[gate_name] = v_ratio
        hardware = self.gates_object.hardware
        if self._old_harware_class:
            hardware.sync_data()
        self.pulse_lib.set_channel_attenuations(self._awg_attenuation)

    @qt_log_exception
    def add_spacer(self):
        spacerItem = QtWidgets.QSpacerItem(140, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        spacerItem1 = QtWidgets.QSpacerItem(200, 1, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_2.addItem(spacerItem1)

        spacerItem2 = QtWidgets.QSpacerItem(140, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem2)
        spacerItem3 = QtWidgets.QSpacerItem(180, 1, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_4.addItem(spacerItem3)


        spacerItem4 = QtWidgets.QSpacerItem(140, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem4)
        spacerItem5 = QtWidgets.QSpacerItem(180, 1, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_3.addItem(spacerItem5)

    @qt_log_exception
    def _add_matrix(self, virtual_gate_set):
        '''
        add a matrix to the gui.

        Args:
            virtual_gate_set (virtual_gate) : virtual gate object where to fetch the data from
        '''
        Virtual_gates_matrix = QtWidgets.QWidget()
        # Virtual_gates_matrix.setObjectName("Virtual_gates_matrix")
        gridLayout = QtWidgets.QGridLayout(Virtual_gates_matrix)
        gridLayout.setSpacing(4)
        gridLayout.setContentsMargins(2, 2, 2, 2)
        # gridLayout_3.setObjectName("gridLayout_3")
        self.tabWidget.addTab(Virtual_gates_matrix, virtual_gate_set.name)

        tableWidget = QtWidgets.QTableWidget(Virtual_gates_matrix)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(tableWidget.sizePolicy().hasHeightForWidth())
        tableWidget.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(11)
        tableWidget.setFont(font)
        tableWidget.setColumnCount(len(virtual_gate_set.virtual_gate_names))
        tableWidget.setObjectName("virtgates")
        tableWidget.setRowCount(len(virtual_gate_set.real_gate_names))
        for i,name in enumerate(virtual_gate_set.virtual_gate_names):
            item = QtWidgets.QTableWidgetItem()
            tableWidget.setHorizontalHeaderItem(i, item)
            item.setText(name)

        for i,name in enumerate(virtual_gate_set.real_gate_names):
            item = QtWidgets.QTableWidgetItem()
            tableWidget.setVerticalHeaderItem(i, item)
            item.setText(name)

        tableWidget.horizontalHeader().setDefaultSectionSize(45)
        tableWidget.horizontalHeader().setMaximumSectionSize(100)
        tableWidget.horizontalHeader().setMinimumSectionSize(30)
        tableWidget.verticalHeader().setDefaultSectionSize(20)
        gridLayout.addWidget(tableWidget, 0, 0, 1, 1)

        state = {'v2r':True}
        update_list = []
        for i in range(len(virtual_gate_set.real_gate_names)):
            for j in range(len(virtual_gate_set.virtual_gate_names)):
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
                doubleSpinBox.setMaximumSize(QtCore.QSize(150, 50))
                doubleSpinBox.setWrapping(False)
                doubleSpinBox.setFrame(False)
                doubleSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                doubleSpinBox.setPrefix("")
                doubleSpinBox.setMaximum(99.999)
                doubleSpinBox.setMinimum(-99.999)
                doubleSpinBox.setSingleStep(0.001)
                doubleSpinBox.setDecimals(3)
                doubleSpinBox.setContentsMargins(0,0,0,0)
                value = virtual_gate_set.get_element(i, j, v2r=True)
                doubleSpinBox.setValue(value)
                doubleSpinBox.setObjectName("doubleSpinBox")
                doubleSpinBox.valueChanged.connect(self._get_link(virtual_gate_set, i, j,
                                                                  doubleSpinBox, state))
                update_list.append((i,j, doubleSpinBox))
                tableWidget.setCellWidget(i, j, doubleSpinBox)

        controlBar = QtWidgets.QWidget()
        barLayout = QtWidgets.QHBoxLayout(controlBar)

        directionBtn = QtWidgets.QPushButton('Invert matrix')
        directionBtn.clicked.connect(lambda:self.invert(virtual_gate_set, refresh, tableWidget, state))
        directionBtn.setMinimumSize(QtCore.QSize(150, 28))
        barLayout.addWidget(directionBtn)

        barLayout.addWidget(QtWidgets.QLabel("Matrix determinant:"))
        label_determinant = QtWidgets.QLabel()
        barLayout.addWidget(label_determinant)

        if virtual_gate_set.normalization:
            normalizeBtn = QtWidgets.QPushButton('Normalize')
            normalizeBtn.clicked.connect(lambda:self.normalize(virtual_gate_set, refresh))
            normalizeBtn.setMinimumSize(QtCore.QSize(150, 28))
            barLayout.addWidget(normalizeBtn)
            reverseNormalizeBtn = QtWidgets.QPushButton('Reverse normalize')
            reverseNormalizeBtn.clicked.connect(lambda:self.reverse_normalize(virtual_gate_set, refresh))
            reverseNormalizeBtn.setMinimumSize(QtCore.QSize(150, 28))
            barLayout.addWidget(reverseNormalizeBtn)

        horizontalSpacer = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        barLayout.addItem(horizontalSpacer)
        barLayout.setContentsMargins(2, 2, 2, 2)
        gridLayout.addWidget(controlBar, 1, 0, 1, 1)

        # Timer to refresh the data in the plot when the matrix is changed externally.
        refresh = lambda:self.update_v_gates(virtual_gate_set, update_list, state, label_determinant)
        timer = QtCore.QTimer()
        timer.timeout.connect(refresh)
        timer.start(2000)
        self.timers.append(timer)

    def _get_link(self, virtual_gate_set, i, j, doubleSpinBox, state):
        '''
        Creates a lambda expression to update the matrix.
        NOTES:
            Lambda cannot be used directly in a for-loop. All calls will be reduced to 1 call.
            functools.partial doesn't work properly with decorators.
        '''
        return lambda:self.linked_result(virtual_gate_set, i, j, doubleSpinBox, state)

    @qt_log_exception
    def normalize(self, virtual_gate_set, refresh):
        logger.info(f'Normalize {virtual_gate_set.name}')
        virtual_gate_set.normalize()
        refresh()

    @qt_log_exception
    def reverse_normalize(self, virtual_gate_set, refresh):
        logger.info(f'Reverse normalize {virtual_gate_set.name}')
        virtual_gate_set.reverse_normalize()
        refresh()

    @qt_log_exception
    def linked_result(self, virtual_gate_set, i, j, spin_box, state):
        if not self._updating:
            value = spin_box.value()
            virtual_gate_set.set_element(i, j, value, v2r=state['v2r'])
            self.set_color(spin_box, value)

    @qt_log_exception
    def update_v_gates(self, virtual_gate_set, update_list, state, label_determinant):
        """ Update the virtual gate matrix elements

        Args:
            matrix: Array with new values
            update_list: List with GUI boxes
        """
        self._updating = True
        for i,j, spin_box in update_list:
            if not spin_box.hasFocus():
                value = virtual_gate_set.get_element(i, j, v2r=state['v2r'])
                spin_box.setValue(value)
                self.set_color(spin_box, value)
        determinant = np.linalg.det(virtual_gate_set.matrix)
        if state['v2r']:
            determinant = 1/determinant
        label_determinant.setText(f"{determinant:6.3f}")
        if abs(determinant) < 0.01 or abs(determinant) > 100.0:
            label_determinant.setStyleSheet("color: red; font-weight: bold;")
        else:
            label_determinant.setStyleSheet("")
        self._updating = False


    def set_color(self, spin_box, value):
        if abs(value) > 99.0:
            spin_box.setStyleSheet("color: red; font-weight: bold;")
            return
        spin_box.setStyleSheet("font-weight: normal;")

        if not self._coloring:
            return
        if value == 0.0:
            r,g,b = 255,255,255
        elif value > 0:
            # blue
            b = 255
            r = max(150, int(255 - value * 200))
            g = r
        elif value < 0:
            # red
            r = 255
            b = max(150, int(255 - abs(value) * 200))
            g = b
        spin_box.setStyleSheet(f'background-color:rgb({r},{g},{b});')

    @qt_log_exception
    def invert(self, virtual_gate_set, refresh, tableWidget, state):
        state['v2r'] = not state['v2r']
        if state['v2r']:
            for i,name in enumerate(virtual_gate_set.virtual_gate_names):
                tableWidget.horizontalHeaderItem(i).setText(name)

            for i,name in enumerate(virtual_gate_set.real_gate_names):
                tableWidget.verticalHeaderItem(i).setText(name)
        else:
            for i,name in enumerate(virtual_gate_set.real_gate_names):
                tableWidget.horizontalHeaderItem(i).setText(name)

            for i,name in enumerate(virtual_gate_set.virtual_gate_names):
                tableWidget.verticalHeaderItem(i).setText(name)
        refresh()


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
