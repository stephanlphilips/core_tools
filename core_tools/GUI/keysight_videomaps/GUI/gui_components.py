from abc import abstractmethod
import copy
from functools import partial
import logging

from PyQt5 import QtCore, QtWidgets

from core_tools.GUI.qt_util import qt_show_error, qt_log_exception

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self, group_name: str, update_plot):
        self.update_scan = False
        self._group_name = group_name
        self._update_plot = update_plot
        self._gui_elements: dict[str, GuiElement] = {}
        self._values: dict[str, any] = {}

    def add(self, name: str, widget, plot_setting: bool = False):
        if isinstance(widget, QtWidgets.QCheckBox):
            gui_element = CheckboxElement(name, self, widget)
        elif isinstance(widget, QtWidgets.QDoubleSpinBox | QtWidgets.QSpinBox):
            gui_element = NumberElement(name, self, widget)
        elif isinstance(widget, QtWidgets.QComboBox):
            gui_element = TextElement(name, self, widget)
        elif isinstance(widget, GuiElement):
            gui_element = widget
        else:
            raise Exception(f"unknown widget type {type(widget)}")

        gui_element.plot_setting = plot_setting
        self._gui_elements[name] = gui_element
        self._values[name] = gui_element.get_value()

    def update_value(self, name: str, value: any):
        self._values[name] = value
        if self._gui_elements[name].plot_setting:
            self._update_plot()
        else:
            self.update_scan = True

    def __getitem__(self, name: str):
        return self._values[name]

    def set_value(self, name: str, value: any):
        self._gui_elements[name].set_value(value)

    def update(self, values: dict[str, any]):
        for name, value in values.items():
            if name not in self._values:
                logger.warning(f"Setting {self._group_name}:{name} does not exist")
                continue
            if self._values[name] != value:
                self.set_value(name, value)

    def to_dict(self) -> dict[str, any]:
        return copy.deepcopy(self._values)


class GuiElement:
    def __init__(self,
                 name: str,
                 settings: Settings):
        self._name = name
        self._settings = settings
        self.plot_setting = False

    def _value_changed(self, new_value):
        self._settings.update_value(self._name, new_value)

    @abstractmethod
    def set_value(self, value):
        raise NotImplementedError()

    @abstractmethod
    def get_value(self):
        raise NotImplementedError()


class CheckboxElement(GuiElement):
    def __init__(self,
                 name: str,
                 settings: Settings,
                 widget: QtWidgets.QCheckBox,
                 ):
        super().__init__(name, settings)
        self._widget = widget
        widget.stateChanged.connect(self._changed)

    @qt_log_exception
    def _changed(self, state: int):
        self._value_changed(bool(state))

    def set_value(self, value: bool):
        self._widget.setChecked(value)

    def get_value(self) -> bool:
        return self._widget.isChecked()


class NumberElement(GuiElement):
    def __init__(self,
                 name: str,
                 settings: Settings,
                 widget: QtWidgets.QSpinBox | QtWidgets.QDoubleSpinBox,
                 ):
        super().__init__(name, settings)
        self._widget = widget
        widget.valueChanged.connect(self._changed)

    @qt_log_exception
    def _changed(self, value: int | float):
        self._value_changed(value)

    def set_value(self, value: int | float):
        self._widget.setValue(value)

    def get_value(self) -> int | float:
        return self._widget.value()


class TextElement(GuiElement):
    def __init__(self,
                 name: str,
                 settings: Settings,
                 widget: QtWidgets.QComboBox,
                 ):
        super().__init__(name, settings)
        self._widget = widget
        widget.currentTextChanged.connect(self._changed)

    @qt_log_exception
    def _changed(self, value: str):
        self._value_changed(value)

    def set_value(self, value: str):
        self._widget.setCurrentText(value)
        if self._widget.currentText() != value:
            qt_show_error(
                "VideoMode: Invalid value",
                f"{self._name} cannot be set to '{value}'")

    def get_value(self) -> str:
        return self._widget.currentText()


class CheckboxList(GuiElement):
    def __init__(self,
                 name: str,
                 settings: Settings,
                 names: list[str],
                 layout_labels: QtWidgets.QLayout,
                 layout_check_boxes: QtWidgets.QLayout,
                 default: bool,
                 ):
        super().__init__(name, settings)
        self._checked = set()
        if default:
            self._checked |= set(names)
        self._check_boxes = {}
        for name in names:
            label = QtWidgets.QLabel(name)
            layout_labels.addWidget(label, 0, QtCore.Qt.AlignHCenter)
            check_box = QtWidgets.QCheckBox()
            check_box.setText("")
            check_box.setChecked(default)
            check_box.stateChanged.connect(partial(self._changed, name=name))
            layout_check_boxes.addWidget(check_box, 0, QtCore.Qt.AlignHCenter)
            self._check_boxes[name] = check_box

    @qt_log_exception
    def _changed(self, state: int, name: str):
        if state:
            self._checked.add(name)
        else:
            self._checked.discard(name)
        self._value_changed(sorted(self._checked))

    def set_value(self, value: list[str]):
        self._checked = set(value)
        for name, check_box in self._check_boxes.items():
            check_box.setChecked(name in self._checked)

    def get_value(self) -> list[str]:
        return sorted(self._checked)


class OffsetsList(GuiElement):
    def __init__(self,
                 name: str,
                 settings: Settings,
                 layout: QtWidgets.QFormLayout,
                 layout_offset: int,
                 n_pulse_gates: int,
                 gate_names: list[str],
                 ):
        super().__init__(name, settings)

        self._gates: list[str] = ["<None>"] * n_pulse_gates
        self._voltages: list[float] = [0.0] * n_pulse_gates

        self._gate_boxes = []
        self._voltage_boxes = []
        for i in range(n_pulse_gates):
            cb_gate = QtWidgets.QComboBox()
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            cb_gate.setSizePolicy(sizePolicy)
            cb_gate.setMinimumSize(QtCore.QSize(107, 0))
            self._gate_boxes.append(cb_gate)
            layout.setWidget(layout_offset+i, QtWidgets.QFormLayout.LabelRole, cb_gate)

            box_voltage = QtWidgets.QDoubleSpinBox()
            box_voltage.setRange(-1000.0, +1000.0)
            self._voltage_boxes.append(box_voltage)
            layout.setWidget(layout_offset+i, QtWidgets.QFormLayout.FieldRole, box_voltage)

            cb_gate.addItem("<None>")
            for gate_name in gate_names:
                cb_gate.addItem(gate_name)
            cb_gate.currentTextChanged.connect(partial(self._gate_changed, index=i))
            box_voltage.valueChanged.connect(partial(self._voltage_changed, index=i))

    @qt_log_exception
    def _gate_changed(self, text: str, index: int):
        self._gates[index] = text
        self._value_changed(self.get_value())

    @qt_log_exception
    def _voltage_changed(self, value: float, index: int):
        self._voltages[index] = value
        self._value_changed(self.get_value())

    def set_value(self, offsets: dict[str, float]):
        if len(offsets) >= len(self._gate_boxes):
            raise Exception(f"Only {len(self._gate_boxes)} offsets configured. "
                            "Specify larger n_pulse_gates")
        for i, (gate, value) in enumerate(offsets.items()):
            self._gate_boxes[i].setCurrentText(gate)
            self._voltage_boxes[i].setValue(value)

        for i in range(len(offsets), len(self._gate_boxes)):
            self._gate_boxes[i].setCurrentIndex(0)
            self._voltage_boxes[i].setValue(0.0)

    def get_value(self):
        result = {}
        for gate, voltage in zip(self._gates, self._voltages):
            if gate != "<None>" and voltage != 0.0:
                result[gate] = voltage
        return result

