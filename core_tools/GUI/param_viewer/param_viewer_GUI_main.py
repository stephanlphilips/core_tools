from core_tools.GUI.param_viewer.param_viewer_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets
import qcodes as qc
from dataclasses import dataclass
from ..qt_util import qt_log_exception

import logging

logger = logging.getLogger(__name__)


@dataclass
class param_data_obj:
    param_parameter: any
    gui_input_param: any
    division: any
    name: str


class param_viewer(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, gates_object: object | None = None,
                 max_diff: float = 1000,
                 keysight_rf: object | None = None,
                 locked=False):
        self.real_gates = list()
        self.virtual_gates = list()
        self.rf_settings = list()
        self.station = qc.Station.default
        self.max_diff = max_diff
        self.keysight_rf = keysight_rf
        self.locked = locked
        self._last_gui_values = {}

        if gates_object:
            self.gates_object = gates_object
        else:
            try:
                self.gates_object = self.station.gates
            except AttributeError:
                raise ValueError('`gates` must be set in qcodes.station or supplied as argument')
        self._step_size = 1  # [mV]
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
                inst = getattr(self.station, src_name)
                for RFpar in self.gates_object.hardware.RF_params:
                    param = getattr(inst, RFpar)
                    self._add_RFset(param)
        if self.keysight_rf is not None:
            try:
                for ks_param in self.keysight_rf.all_params:
                    self._add_RFset(ks_param)
            except Exception as e:
                logger.error(f'Failed to add keysight RF {e}')

        # add real gates
        for gate_name in self.gates_object.hardware.dac_gate_map.keys():
            param = getattr(self.gates_object, gate_name)
            self._add_gate(param, False)

        # add virtual gates
        for gate_name in self.gates_object.v_gates:
            param = getattr(self.gates_object, gate_name)
            self._add_gate(param, True)

        self.step_size.clear()
        items = [100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1]
        self.step_size.addItems(str(item) for item in items)
        self.step_size.setCurrentText("1")

        self.lock.setChecked(self.locked)
        self.lock.stateChanged.connect(lambda: self._update_lock(self.lock.isChecked()))
        self.step_size.currentIndexChanged.connect(lambda: self.update_step(float(self.step_size.currentText())))
        self._finish_gates_GUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: self._update_parameters())
        self.timer.start(500)

        self.show()
        if not instance_ready:
            self.app.exec()

    @qt_log_exception
    def closeEvent(self, event):
        self.timer.stop()

    @qt_log_exception
    def update_step(self, value: float):
        """ Update step size of the parameter GUI elements with the specified value """
        self._step_size = value
        for gate in self.real_gates:
            gate.gui_input_param.setSingleStep(value)
        for gate in self.virtual_gates:
            gate.gui_input_param.setSingleStep(value)

    @qt_log_exception
    def _update_lock(self, locked):
        print('Locked:', locked)
        self.locked = locked

    @qt_log_exception
    def _add_RFset(self, parameter: qc.Parameter):
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

        name = name.replace('keysight_rfgen_', '')

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
            set_input.stateChanged.connect(lambda: self._set_bool(parameter, set_input.isChecked))
        else:
            set_input = QtWidgets.QDoubleSpinBox(self.RFsettings)
            set_input.setObjectName(name + "_input")
            set_input.setMinimumSize(QtCore.QSize(100, 0))
            set_input.setRange(-1e9, 1e9)
            set_input.setValue(parameter()/division)
            set_input.valueChanged.connect(lambda: self._set_set(parameter, set_input.value, division))
            set_input.setKeyboardTracking(False)
            set_input.setSingleStep(step_size)

        layout.addWidget(set_input, i, 1, 1, 1)

        set_unit = QtWidgets.QLabel(self.RFsettings)
        set_unit.setObjectName(name + "_unit")
        set_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(set_unit, i, 2, 1, 1)
        self.rf_settings.append(param_data_obj(parameter,  set_input, division, name))

    @qt_log_exception
    def _add_gate(self, parameter: qc.Parameter, virtual: bool):
        '''
        add a new gate.

        Args:
            parameter (QCoDeS parameter object) : parameter to add.
            virtual (bool) : True in case this is a virtual gate.
        '''

        i = len(self.real_gates)
        layout = self.layout_real

        if virtual:
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
        voltage_input.setObjectName(name + "_input")
        voltage_input.setMinimumSize(QtCore.QSize(100, 0))

        if not virtual:
            voltage_input.setRange(-4000.0, 4000.0)
        else:
            # QDoubleSpinBox needs a limit. Set it high for virtual voltage
            voltage_input.setRange(-99999.99, 99999.99)
        voltage_input.setValue(parameter())
        voltage_input.valueChanged.connect(lambda: self._set_gate(parameter, voltage_input.value, voltage_input))
        voltage_input.setKeyboardTracking(False)
        layout.addWidget(voltage_input, i, 1, 1, 1)

        gate_unit = QtWidgets.QLabel(self.virtualgates)
        gate_unit.setObjectName(name + "_unit")
        gate_unit.setText(_translate("MainWindow", unit))
        layout.addWidget(gate_unit, i, 2, 1, 1)
        param_data = param_data_obj(parameter,  voltage_input, 1, name)
        if not virtual:
            self.real_gates.append(param_data)
        else:
            self.virtual_gates.append(param_data)

    @qt_log_exception
    def _set_gate(self, gate, value, voltage_input):
        if self.locked:
            new_text = voltage_input.text()
            current_value_text = voltage_input.textFromValue(gate())
            if new_text != current_value_text:
                logger.warning(f"ParameterViewer is locked! Voltage of {gate.name} not changed.")
                voltage_input.setValue(gate())
            return
        if not voltage_input.isEnabled():
            logger.info(f"Ignoring out of range value {gate.name}: {value()}")
            return
        delta = abs(value() - gate())
        if self.max_diff is not None and delta > self.max_diff:
            logger.warning(f"Not setting {gate} to {value():.1f}mV. "
                           f"Difference {delta:.0f} mV > {self.max_diff:.0f} mV")
            return

        try:
            last_value = gate()
            new_text = voltage_input.text()
            current_text = voltage_input.textFromValue(last_value)
            if new_text != current_text:
                logger.info(f"GUI value changed: set gate {gate.name} {current_text} -> {new_text}")
                gate.set(value())
        except Exception as ex:
            logger.error(f"Failed to set gate {gate} to {value()}: {ex}")

    @qt_log_exception
    def _set_set(self, setting, value, division):
        logger.info(f"setting {setting} to {value():.1f} times {division:.1f}")
        setting.set(value()*division)
        self.gates_object.hardware.RF_settings[setting.full_name] = value()*division
        self.gates_object.hardware.sync_data()

    @qt_log_exception
    def _set_bool(self, setting, value):
        setting.set(value())
        self.gates_object.hardware.RF_settings[setting.full_name] = value()
        self.gates_object.hardware.sync_data()

    @qt_log_exception
    def _finish_gates_GUI(self):

        for items, layout_widget in [
                (self.real_gates, self.layout_real),
                (self.virtual_gates, self.layout_virtual),
                (self.rf_settings, self.layout_RF)]:
            i = len(items) + 1

            spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            layout_widget.addItem(spacerItem, i, 0, 1, 1)

            spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            layout_widget.addItem(spacerItem1, 0, 3, 1, 1)

        self.setWindowTitle(f"Parameter Viewer for {self.gates_object}")

    @qt_log_exception
    def _update_parameters(self):
        '''
        updates the values of all the gates in the parameter viewer periodically
        '''
        idx = self.tab_menu.currentIndex()
        all_gate_voltages = {}
        if idx == 0:
            params = self.real_gates
        elif idx == 1:
            params = self.virtual_gates
            # if supported retrieve all voltages in 1 call. That's a lot faster.
            if hasattr(self.gates_object, "get_all_gate_voltages"):
                all_gate_voltages = self.gates_object.get_all_gate_voltages()
        elif idx == 2:
            params = self.rf_settings
        else:
            return

        for param in params:
            try:
                name = param.name
                if name in all_gate_voltages:
                    new_value = all_gate_voltages[name]/param.division
                else:
                    new_value = param.param_parameter()/param.division

                old_value = self._last_gui_values.get(name, None)

                if old_value == new_value:
                    continue

                # do not update when a user clicks on it.
                gui_input = param.gui_input_param
                if not gui_input.hasFocus():
                    if isinstance(gui_input, QtWidgets.QDoubleSpinBox):
                        if idx == 1 and (new_value < gui_input.minimum() or new_value > gui_input.maximum()):
                            gui_input.setEnabled(False)
                            gui_input.setStyleSheet("color : red;")
                            new_text = gui_input.textFromValue(new_value)
                            current_text = gui_input.text()
                            if current_text != new_text:
                                gui_input.setValue(new_value)
                        else:
                            if not gui_input.isEnabled():
                                gui_input.setEnabled(True)
                                gui_input.setStyleSheet("")

                            current_text = gui_input.text()
                            new_text = gui_input.textFromValue(new_value)
                            if current_text != new_text:
                                logger.info(f'Update GUI {param.param_parameter.name} {current_text} -> {new_text}')
                                gui_input.setValue(new_value)
                                # Note: additional check on 0.0, because "-0.00 " and "0.00" are numerically equal.
                                if gui_input.text() != new_text and gui_input.valueFromText(new_text) != 0.0:
                                    print(f'WARNING: {param.param_parameter.name} corrected from '
                                          f'{new_text} to {gui_input.text()}')
                    elif isinstance(gui_input, QtWidgets.QCheckBox):
                        gui_input.setChecked(bool(new_value))
                    self._last_gui_values[name] = new_value
            except Exception:
                logger.error(f'Error updating {param}', exc_info=True)
