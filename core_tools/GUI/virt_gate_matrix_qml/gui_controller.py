from core_tools.GUI.virt_gate_matrix_qml.models import attenuation_model, table_header_model, vg_matrix_model

from PyQt5 import QtCore, QtWidgets, QtQml, QtGui

import core_tools.GUI.virt_gate_matrix_qml as qml_in
import os
import logging

import qcodes as qc

logger = logging.getLogger(__name__)


class virt_gate_matrix_GUI:
    def __init__(self, virtual_gate_name: str | int = 0,
                 invert: bool = False):
        """
        Args:
            virtual_gate_name: Name or index of virtual gate to display
            invert: Show inverted matrix.
        """
        super().__init__()

        self.app = QtCore.QCoreApplication.instance()
        self.instance_ready = True
        if self.app is None:
            self.instance_ready = False
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
            self.app = QtWidgets.QApplication([])

        self.app.setFont(QtGui.QFont("Sans Serif", 8))

        hw = qc.Station.default.hardware
        self.engine = QtQml.QQmlApplicationEngine()

        self.attenuation_model = attenuation_model(hw.awg2dac_ratios)
        self.engine.rootContext().setContextProperty("attenuation_model", self.attenuation_model)

        if isinstance(virtual_gate_name, int):
            self.virtual_gate_index = virtual_gate_name
        else:
            self.virtual_gate_index = (hw.virtual_gates.virtual_gate_names).index(virtual_gate_name)

        if len(hw.virtual_gates) > self.virtual_gate_index:
            vg = hw.virtual_gates[self.virtual_gate_index]
            logger.info(f'creating objects for index {self.virtual_gate_index}')
            self.vg_matrix_model = vg_matrix_model(vg)
            self.vg_matrix_model._manipulate_callback = self.set_table_headers

            self.gates_header_model = table_header_model(vg.gates)
            self.vgates_header_model = table_header_model(vg.v_gates)

            root_context = self.engine.rootContext()
            root_context.setContextProperty('virt_gate_matrix_GUI', self)
            root_context.setContextProperty('vg_matrix_model', self.vg_matrix_model)
            root_context.setContextProperty('row_header_model', self.gates_header_model)
            root_context.setContextProperty('column_header_model', self.vgates_header_model)
        else:
            print('virtual gate name {virtual_gate_name} could not be found')

        # grab directory from the import!
        filename = os.path.join(qml_in.__file__[:-12], "virt_gate_matrix_gui.qml")
        logger.info(f'loading qml from {filename}')
        self.engine.load(QtCore.QUrl.fromLocalFile(filename))
        self.win = self.engine.rootObjects()[0]

        normalize_button = self.win.findChild(QtCore.QObject, "normalize_button")
        normalize_button.setProperty('enabled', vg.normalization)
        reverse_normalize_button = self.win.findChild(QtCore.QObject, "reverse_normalize_button")
        reverse_normalize_button.setProperty('enabled', vg.normalization)

        self._mat_inv_switch = self.win.findChild(QtCore.QObject, "mat_inv_switch")
        self._mat_inv_switch.setProperty('checked', invert)
        self.vg_matrix_model.set_virtual_2_real(self._mat_inv_switch.property('checked'))
        self.set_table_headers()

        if self.instance_ready is False:
            self.app.exec_()
            print('exec')

    def set_table_headers(self):
        root_context = self.engine.rootContext()
        inverted = self._mat_inv_switch.property('checked')
        logger.info(f'set_table_headers: mat_inv {inverted}')

        if inverted:
            root_context.setContextProperty('row_header_model', self.gates_header_model)
            root_context.setContextProperty('column_header_model', self.vgates_header_model)
        else:
            root_context.setContextProperty('row_header_model', self.vgates_header_model)
            root_context.setContextProperty('column_header_model', self.gates_header_model)
