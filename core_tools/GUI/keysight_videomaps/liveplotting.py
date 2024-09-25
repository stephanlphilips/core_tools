import logging
import os
from collections.abc import Sequence
from typing import Callable

import numpy as np
import pyqtgraph as pg

from PyQt5 import QtCore, QtWidgets, QtGui

from qcodes import MultiParameter
import core_tools.GUI.keysight_videomaps.GUI as gui_module
from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver
from core_tools.GUI.keysight_videomaps.data_saver.native import CoreToolsDataSaver
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_base import FastScanGeneratorBase
from core_tools.GUI.keysight_videomaps.data_getter.iq_modes import get_channel_map, get_channel_map_dig_4ch
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Virtual
from core_tools.GUI.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot
from core_tools.GUI.qt_util import qt_log_exception
from core_tools.utility.powerpoint import addPPTslide

logger = logging.getLogger(__name__)

_data_saver: IDataSaver | None = None
_DEFAULT_DATA_SAVER = CoreToolsDataSaver


def set_data_saver(data_saver: IDataSaver):
    """
    Sets the data saver object to use.
    """
    assert isinstance(data_saver, IDataSaver)
    global _data_saver
    _data_saver = data_saver


def get_data_saver():
    """
    Returns the data saver that is set. If the data saver is not specified, this sets the default.
    """
    if _data_saver is None:
        logger.warning(f"No data saver specified. Using {_DEFAULT_DATA_SAVER.__name__} as default.")
        set_data_saver(_DEFAULT_DATA_SAVER())
    return _data_saver


def _try_get_gates():
    try:
        from qcodes import Station
        return Station.default.gates
    except:
        return None



class liveplotting(QtWidgets.QMainWindow, Ui_MainWindow):
    # class variable to keep the last instance alive and retrievable by other components.
    last_instance = None
    _all_instances = []
    auto_stop_other = True

    """
    VideoMode GUI.
    """
    def __init__(self, pulse_lib, digitizer=None,
                 scan_type: str | None = None,
                 cust_defaults: dict[str, dict[str, any]] | None = None,
                 iq_mode: str | None = None,
                 channel_map: dict[str, tuple[int | str, Callable[[np.ndarray], np.ndarray]]] | None = None,
                 gates=None,
                 n_pulse_gates=5,
                 scan_generator: FastScanGeneratorBase | None = None):
        '''
        Args:
            pulse_lib (pulselib) : provide the pulse library object. This is used to generate the sequences.
            digitizer (QCodes Instrument) : digitizer to use. If None uses digitizers configured in pulse-lib.
            scan_type (str) : AWG and digitizer used: 'Keysight', 'Qblox', 'Tektronix' or 'Virtual'.
            cust_defaults (dict of dicts): Dictionary to supply custom starting defaults. Any parameters/dicts that are not defined will resort to defaults.
                        Format is {'1D': dict, '2D': dict, 'gen': dict}
                        1D = {'gate_name': str,
                           'V_swing': float,
                           'npt': int,
                           't_meas': float,
                           'average': int,
                           'diff': bool,
                           'offsets': dict[str, float]}
                        2D = {'gate1_name': str,
                           'gate2_name': str,
                           'V1_swing': float,
                           'V2_swing': float,
                           'npt': int,
                           't_meas': float,
                           'average': int,
                           'gradient': str, # 'Off', 'Magnitude', or 'Mag & angle'
                           'filter_background': bool,
                           'background_sigma': float,
                           'filter_noise': bool,
                           'noise_sigma': float,
                           'offsets': dict[str, float]}
                        gen = {'ch1': bool,
                           'ch2': bool,
                           'ch3': bool,
                           'ch4': bool,
                           'enabled_markers': list[str],
                           'n_columns': int,
                           'line_margin': int,
                           'bias_T_RC': float,
                           'acquisition_delay_ns': float, # Time in ns between AWG output change and digitizer acquisition start.
                           'max_V_swing': float, # maximum voltage swing for 1D and 2D
                           'biasT_corr_1D': bool,
                           'biasT_corr_2D': bool,
                           '2D_cross': bool,
                           '2D_colorbar': bool,
                           }
            iq_mode (str): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                    complex I/Q value should be plotted: 'I', 'Q', 'amplitude', 'phase', 'phase_deg', 'I+Q',
                    'amplitude+phase'. In the latter two cases 2 charts will be shown for each channel.
            channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray])]):
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
                E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
                The default channel_map is:
                    {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
            gates (gates):
                Optional gates object with real and virtual DC gate values.
                If gates is specified it can be used to change the DC voltages with a click in
                the 2D chart. The 1D and 2D charts can also show the absolute voltages.
            n_pulse_gates (int): number of pulse_gates to show in GUI.
        '''
        logger.info('initialising video mode')
        self.pulse_lib = pulse_lib
        self.digitizer = digitizer
        if gates is None:
            gates = _try_get_gates()
        self.gates = gates
        if n_pulse_gates > 15:
            raise Exception("Maximum number of pulse gates is 15")
        self.n_pulse_gates = n_pulse_gates

        if scan_generator is not None:
            self._scan_generator = scan_generator
        else:
            self._scan_generator = self._get_scan_generator(scan_type)
        self._scan_generator.set_pulse_lib(pulse_lib)
        self._scan_generator.set_digitizer(digitizer)

        self._plot1D = None
        self._plot2D = None
        self._param1D = None
        self._param2D = None

        self.vm_data_param_1D = None
        self.vm_data_param_2D = None
        self._run_state = "Idle"
        instance_ready = True

        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
            self.app = QtWidgets.QApplication([])

        self.app.setFont(QtGui.QFont("Sans Serif", 8))
        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        self.setupUI2()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self._set_channel_map(channel_map, iq_mode)
        self._init_channels()
        self._init_markers(pulse_lib)
        self.init_defaults(pulse_lib.channels, cust_defaults)
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.timeout.connect(self._update_active_state)
        self._update_timer.start(200)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        liveplotting.last_instance = self
        liveplotting._all_instances.append(self)

        self.show()
        if instance_ready == False:
            print('APP EXEC')
            self.app.exec()

    def _get_scan_generator(self, scan_type):
        if scan_type is None:
            scan_type = self.pulse_lib._backend
            if scan_type in ['Keysight_QS', 'M3202A']:
                scan_type = 'Keysight'
            elif scan_type == 'Tektronix_5014':
                scan_type = 'Tektronix'

        if scan_type == 'Virtual':
            scan_generator = scan_generator_Virtual.FastScanGenerator()
        elif scan_type == "Keysight":
            from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Keysight
            scan_generator = scan_generator_Keysight.FastScanGenerator()
        elif scan_type == "Tektronix":
            from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Tektronix
            scan_generator = scan_generator_Tektronix.FastScanGenerator()
        elif scan_type == "Qblox":
            from .data_getter import scan_generator_Qblox
            if self.digitizer is not None:
                logger.error('liveplotting parameter digitizer should be None for Qblox. '
                              'QRM must be added to pulse_lib with  `add_digitizer`.')
            scan_generator = scan_generator_Qblox.FastScanGenerator()
        else:
            raise ValueError("Unsupported argument for scan type.")

        return scan_generator

    def setupUI2(self):
        self.setWindowTitle("Video Mode")
        self.statusbar.setContentsMargins(8,0,4,4)
        self.bias_T_warning_label = QtWidgets.QLabel("")
        self.bias_T_warning_label.setMargin(2)
        self.bias_T_warning_label.setContentsMargins(QtCore.QMargins(6,0,6,0))
        self.bias_T_warning_label.setMinimumWidth(300)
        self.statusbar.addWidget(self.bias_T_warning_label)

        self.gate_values_label = QtWidgets.QLabel("DC gates")
        self.gate_values_label.setMargin(2)
        self.gate_values_label.setMinimumWidth(250)
        self.statusbar.addWidget(self.gate_values_label)
        if self.gates is None:
            self.gate_values_label.setText("DC gates not known")
        self.cursor_value_label = QtWidgets.QLabel(" --.-, --.-: ---.- mV")
        self.cursor_value_label.setMargin(2)
        self.cursor_value_label.setMinimumWidth(300)
        self.statusbar.addWidget(self.cursor_value_label)

        self._1D_offset_gate_voltages = []
        self._2D_offset_gate_voltages = []
        for dim in ['1D', '2D']:
            frame = getattr(self, f"frame_{dim}")
            layout = getattr(self, f"formLayout_{dim}")
            offset_gate_voltages = getattr(self, f"_{dim}_offset_gate_voltages")
            for i in range(self.n_pulse_gates):
                cb_gate = QtWidgets.QComboBox(frame)
                sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                cb_gate.setSizePolicy(sizePolicy)
                cb_gate.setMinimumSize(QtCore.QSize(107, 0))
                layout.setWidget(11+i, QtWidgets.QFormLayout.LabelRole, cb_gate)

                box_voltage = QtWidgets.QDoubleSpinBox(frame)
                box_voltage.setMinimum(-1000.0)
                box_voltage.setMaximum(1000.0)
                layout.setWidget(11+i, QtWidgets.QFormLayout.FieldRole, box_voltage)

                offset_gate_voltages.append((cb_gate, box_voltage))

        self._1D_average.valueChanged.connect(lambda:self.update_plot_properties_1D())
        self._1D_diff.stateChanged.connect(lambda:self.update_plot_properties_1D())

        self._2D_average.valueChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_gradient.currentTextChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_filter_background.stateChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_background_sigma.valueChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_filter_noise.stateChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_noise_sigma.valueChanged.connect(lambda:self.update_plot_properties_2D())

        self._1D_play.clicked.connect(lambda:self._start_1D())
        self._2D_play.clicked.connect(lambda:self._start_2D())
        self._1D_pause.clicked.connect(lambda:self._stop_1D())
        self._2D_pause.clicked.connect(lambda:self._stop_2D())
        self._1D_step.clicked.connect(lambda:self._step_1D())
        self._2D_step.clicked.connect(lambda:self._step_2D())
        self._1D_reload.clicked.connect(lambda:self.update_plot_settings_1D())
        self._2D_reload.clicked.connect(lambda:self.update_plot_settings_2D())
        self._flip_axes.clicked.connect(lambda:self.do_flip_axes())
        self.tabWidget.currentChanged.connect(lambda:self.tab_changed())

        self._1D_reset_average.clicked.connect(lambda:self._reset_1D_average())
        self._2D_reset_average.clicked.connect(lambda:self._reset_2D_average())

        self._1D_save_data.clicked.connect(lambda:self.save_data())
        self._2D_save_data.clicked.connect(lambda:self.save_data())

        self._1D_ppt_save.clicked.connect(lambda:self.copy_ppt())
        self._2D_ppt_save.clicked.connect(lambda:self.copy_ppt())

        self._1D_copy.clicked.connect(lambda:self.copy_to_clipboard())
        self._2D_copy.clicked.connect(lambda:self.copy_to_clipboard())

        self._1D_set_DC.setEnabled(self.gates is not None)
        self._1D_set_DC.clicked.connect(lambda:self._1D_set_DC_button_state())
        self._2D_set_DC.setEnabled(self.gates is not None)
        self._2D_set_DC.clicked.connect(lambda:self._2D_set_DC_button_state())

        self._shortcut_reload = QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self)
        self._shortcut_reload.activated.connect(self._reload)
        self._shortcut_stop = QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self)
        self._shortcut_stop.activated.connect(self.stop)
        self._shortcut_step = QtWidgets.QShortcut(QtGui.QKeySequence("F9"), self)
        self._shortcut_step.activated.connect(self._step)
        self._shortcut_save = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self._shortcut_save.activated.connect(self.save_data)
        self._shortcut_copy = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+C"), self)
        self._shortcut_copy.activated.connect(self.copy_to_clipboard)
        self._shortcut_copy = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+P"), self)
        self._shortcut_copy.activated.connect(self.copy_ppt)

        self._set_icon(self._1D_play, "play.png")
        self._set_icon(self._1D_pause, "pause.png")
        self._set_icon(self._1D_reload, "refresh.png")
        self._set_icon(self._1D_step, "image.png")
        self._set_icon(self._1D_copy, "copy.png")
        self._set_icon(self._1D_ppt_save, "presentation.png")
        self._set_icon(self._1D_save_data, "save.png")

        self._set_icon(self._2D_play, "play.png")
        self._set_icon(self._2D_pause, "pause.png")
        self._set_icon(self._2D_reload, "refresh.png")
        self._set_icon(self._2D_step, "image.png")
        self._set_icon(self._2D_copy, "copy.png")
        self._set_icon(self._2D_ppt_save, "presentation.png")
        self._set_icon(self._2D_save_data, "save.png")

        self._1D_av_progress.setAlignment(QtCore.Qt.AlignCenter)
        self._2D_av_progress.setAlignment(QtCore.Qt.AlignCenter)

    def _set_icon(self, button, name):
        icon_path = os.path.dirname(gui_module.__file__)
        button.setIcon(QtGui.QIcon(os.path.join(icon_path, name)))
        button.setIconSize(QtCore.QSize(24, 24))

    @property
    def tab_id(self):
        return self.tabWidget.currentIndex()

    @property
    def is_running(self):
        return self._run_state if self._run_state != "Idle" else False

    def turn_off(self):
        self.stop()

    def _set_channel_map(self, channel_map, iq_mode):
        self.iq_mode = iq_mode
        if channel_map is not None:
            if iq_mode is not None:
                logger.warning('iq_mode is ignored when channel_map is specified')
            self.channel_map = channel_map
            return

        if self.digitizer is None:
            self.channel_map = get_channel_map(self.pulse_lib, iq_mode)
        else:
            self.channel_map = get_channel_map_dig_4ch(iq_mode)

    def _init_channels(self):
        # add to GUI
        self.channel_check_boxes = {}
        for name in self.channel_map:
            label = QtWidgets.QLabel(self.verticalLayoutWidget)
            label.setObjectName(f"label_channel_{name}")
            label.setText(name)
            self.horizontalLayout_channel_labels.addWidget(label, 0, QtCore.Qt.AlignHCenter)
            check_box = QtWidgets.QCheckBox(self.verticalLayoutWidget)
            check_box.setText("")
            check_box.setChecked(True)
            check_box.setObjectName(f"check_channel_{name}")
            self.horizontalLayout_channel_checkboxes.addWidget(check_box, 0, QtCore.Qt.AlignHCenter)
            self.channel_check_boxes[name] = check_box

    def _init_markers(self, pulse_lib):
        self.marker_check_boxes = {}
        for m in pulse_lib.marker_channels:
            label = QtWidgets.QLabel(self.verticalLayoutWidget)
            label.setObjectName(f"label_marker_{m}")
            label.setText(m)
            self.horizontalLayout_markers.addWidget(label, 0, QtCore.Qt.AlignHCenter)
            check_box = QtWidgets.QCheckBox(self.verticalLayoutWidget)
            check_box.setText("")
            check_box.setChecked(False)
            check_box.setObjectName(f"check_box_marker_{m}")
            self.horizontalLayout_markers_checks.addWidget(check_box, 0, QtCore.Qt.AlignHCenter)
            self.marker_check_boxes[m] = check_box

    def init_defaults(self, gates, cust_defaults):
        '''
        inititialize defaults for the 1D plot. Also configure listeners to check when values are changed.

        Args:
            gates (list<str>) : names of the gates that are available in the AWG.
        '''

        for i in sorted(gates, key=str.lower):
            self._1D_gate_name.addItem(str(i))
            self._2D_gate1_name.addItem(str(i))
            self._2D_gate2_name.addItem(str(i))

        for dim in ['1D', '2D']:
            offset_gate_voltages = getattr(self, f"_{dim}_offset_gate_voltages")
            for cb_gate, box_voltage in offset_gate_voltages:
                cb_gate.addItem('<None>')
                for gate in sorted(gates, key=str.lower):
                    cb_gate.addItem(gate)
            try:
                init_offsets = cust_defaults[dim]['offsets']
            except Exception:
                continue
            if len(init_offsets) >= len(offset_gate_voltages):
                raise Exception(f'Only {len(offset_gate_voltages)} offsets configured. '
                                'Specify larger n_pulse_gates')
            for i, (gate, value) in enumerate(init_offsets.items()):
                cb_gate, box_voltage = offset_gate_voltages[i]
                cb_gate.setCurrentText(gate)
                box_voltage.setValue(value)

        # 1D defaults
        self.defaults_1D = {
            'gate_name': self._1D_gate_name.currentText(),
            'V_swing': 50,
            'npt': 200,
            't_meas': 50,
            'average': 1,
            'diff': False}

        # 2D defaults
        self.defaults_2D = {
            'gate1_name': self._2D_gate1_name.currentText(),
            'gate2_name': self._2D_gate2_name.currentText(),
            'V1_swing': 50,
            'V2_swing': 50,
            'npt': 75,
            't_meas': 5,
            'average': 1,
            'gradient': 'Off',
            'filter_background': False,
            'background_sigma': 0.2,
            'filter_noise': False,
            'noise_sigma': 1.0,
            }

        self.defaults_gen = {
            'acquisition_delay_ns': 500,
            'n_columns': 4,
            'line_margin': 1,
            'max_V_swing': 1000.0,
            'bias_T_RC': 100,
            'biasT_corr_1D': False,
            'biasT_corr_2D': True,
            '2D_cross': False,
            '2D_colorbar': False,
            'enabled_markers': [],
            }

        try:
            val = cust_defaults['gen']['dig_vmax']
            print(f"setting 'gen':{{ 'dig_vmax': {val} }} is deprecated.")
        except:
            pass

        # General defaults

        default_tabs = ['1D', '2D','gen']
        default_dicts = [self.defaults_1D, self.defaults_2D, self.defaults_gen]
        exclude = ['_gen_enabled_markers']

        for (tab,defaults) in zip(default_tabs,default_dicts):
            for (key,val) in defaults.items():
                try:
                    val = cust_defaults[tab][key]
                except:
                    pass
                setattr(self,f'_{tab}__{key}', val)
                if f'_{tab}_{key}' not in exclude:
                    GUI_element = getattr(self,f'_{tab}_{key}')
                    if type(GUI_element) == QtWidgets.QComboBox:
                        GUI_element.setCurrentText(str(val))
                    elif type(GUI_element) == QtWidgets.QDoubleSpinBox or type(GUI_element) == QtWidgets.QSpinBox:
                        GUI_element.setValue(val)
                    elif type(GUI_element) == QtWidgets.QCheckBox:
                        GUI_element.setChecked(val)

        for channel_name, check_box in self.channel_check_boxes.items():
            try:
                if channel_name in cust_defaults['gen']:
                    check_box.setChecked(cust_defaults['gen'][channel_name])
            except: pass

        for marker, check_box in self.marker_check_boxes.items():
            check_box.setChecked(marker in self._gen__enabled_markers)

        for v_spinner in [self._1D_V_swing, self._2D_V1_swing, self._2D_V2_swing]:
            v_spinner.setRange(-self._gen__max_V_swing, self._gen__max_V_swing)

        self._channels = self.get_activated_channels()

    def set_1D_settings(self, gate=None, vswing=None, npt=None, t_meas=None, biasT_corr=None,
                        averaging=None, differentiate=None):
        if gate is not None:
            self._1D_gate_name.setCurrentText(gate)
        if vswing is not None:
            self._1D_V_swing.setValue(vswing)
        if npt is not None:
            self._1D_npt.setValue(npt)
        if t_meas is not None:
            self._1D_t_meas.setValue(t_meas)
        if biasT_corr is not None:
            self._1D_biasT_corr.setChecked(biasT_corr)
        if averaging is not None:
            self._1D_average.setValue(averaging)
        if differentiate is not None:
            self._1D_diff.setChecked(differentiate)

    def set_2D_settings(self, gate1=None, vswing1=None, gate2=None, vswing2=None, npt=None, t_meas=None,
                        biasT_corr=None, averaging=None, gradient=None):
        if gate1 is not None:
            self._2D_gate1_name.setCurrentText(gate1)
        if vswing1 is not None:
            self._2D_V1_swing.setValue(vswing1)
        if gate2 is not None:
            self._2D_gate2_name.setCurrentText(gate2)
        if vswing2 is not None:
            self._2D_V2_swing.setValue(vswing2)
        if npt is not None:
            self._2D_npt.setValue(npt)
        if t_meas is not None:
            self._2D_t_meas.setValue(t_meas)
        if biasT_corr is not None:
            self._2D_biasT_corr.setChecked(biasT_corr)
        if averaging is not None:
            self._2D_average.setValue(averaging)
        if gradient is not None:
            self._2D_gradient.setCurrentText(gradient)

    def set_digitizer_settings(self, sample_rate=None, channels=None):
        if sample_rate is not None:
            logger.warning("Argument sample_rate is not used anymore")

        if channels is not None:
            for check_box in self.channel_check_boxes.values():
                check_box.setChecked(False)
            for channel in channels:
                ch = str(channel)
                self.channel_check_boxes[ch].setChecked(True)

            self._channels = self.get_activated_channels()

    @qt_log_exception
    def update_plot_properties_1D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differentation of data)
        '''
        if self._plot1D  is not None:
            self._plot1D.averaging = self._1D_average.value()
            self._plot1D.gradient = self._1D_diff.isChecked()
            # store for metadata
            self._1D__average = self._1D_average.value()
            self._1D__diff = self._1D_diff.isChecked()

    @qt_log_exception
    def update_plot_properties_2D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/gradient of data)
        '''
        if self._plot2D  is not None:
            self._plot2D.averaging = self._2D_average.value()
            self._plot2D.gradient = self._2D_gradient.currentText()
            self._plot2D.set_background_filter(
                    self._2D_filter_background.isChecked(),
                    self._2D_background_sigma.value()
                    )
            self._plot2D.set_noise_filter(
                    self._2D_filter_noise.isChecked(),
                    self._2D_noise_sigma.value()
                    )
            # store for metadata
            self._2D__average = self._2D_average.value()
            self._2D__gradient = self._2D_gradient.currentText()
            self._2D__filter_background = self._2D_filter_background.isChecked()
            self._2D__background_sigma = self._2D_background_sigma.value()
            self._2D__filter_noise = self._2D_filter_noise.isChecked()
            self._2D__noise_sigma = self._2D_noise_sigma.value()

    @qt_log_exception
    def get_offsets(self, dim: str):
        offsets = {}
        offset_gate_voltages = getattr(self, f"_{dim}_offset_gate_voltages")
        for cb_gate, box_voltage in offset_gate_voltages:
            gate = cb_gate.currentText()
            voltage = box_voltage.value()
            if gate != '<None>' and voltage != 0.0:
                offsets[gate] = voltage

        return offsets

    @qt_log_exception
    def get_plot_settings(self, ndim):
        '''
        write the values of the input into the the class
        '''
        self._1D__gate_name = self._1D_gate_name.currentText()
        self._1D__V_swing = self._1D_V_swing.value()
        self._1D__npt = self._1D_npt.value()
        self._1D__t_meas = self._1D_t_meas.value()
        self._1D__biasT_corr = self._gen_biasT_corr_1D.isChecked()

        self._2D__gate1_name = self._2D_gate1_name.currentText()
        self._2D__gate2_name = self._2D_gate2_name.currentText()
        self._2D__V1_swing = self._2D_V1_swing.value()
        self._2D__V2_swing = self._2D_V2_swing.value()
        self._2D__npt = self._2D_npt.value()
        self._2D__t_meas = self._2D_t_meas.value()
        self._2D__biasT_corr = self._gen_biasT_corr_2D.isChecked()
        self._2D__cross = self._gen_2D_cross.isChecked()
        self._2D__colorbar = self._gen_2D_colorbar.isChecked()

        self._channels = self.get_activated_channels()
        self._active_channel_map = {
                name:settings for name, settings in self.channel_map.items()
                if self.channel_check_boxes[name].isChecked()
                }
        self._gen__acquisition_delay_ns = self._gen_acquisition_delay_ns.value()
        self._gen__enabled_markers = []
        for marker, cb in self.marker_check_boxes.items():
            if cb.isChecked():
                self._gen__enabled_markers.append(marker)

        self._2D__offsets = self.get_offsets('2D')
        self._1D__offsets = self.get_offsets('1D')
        self._gen__line_margin = self._gen_line_margin.value()
        self._gen__n_columns = self._gen_n_columns.value()
        biasTrc = self._gen_bias_T_RC.value() * 1000 # microseconds

        if self._2D__biasT_corr:
            # total time of a line divided by 2, because prepulse distributes error
            t_bias_charging_2D = (self._2D__npt + 2*self._gen__line_margin) * self._2D__t_meas * 0.5
        else:
            t_bias_charging_2D = (self._2D__npt + 2*self._gen__line_margin) * self._2D__t_meas * self._2D__npt

        if self._1D__biasT_corr:
            t_bias_charging_1D = self._1D__t_meas
        else:
            # total time of a line divided by 4, because ramp consists of '2 triangles'.
            t_bias_charging_1D = (self._1D__npt + 2*self._gen__line_margin) * self._1D__t_meas * 0.25

        t_bias_charging = t_bias_charging_1D if ndim == 1 else t_bias_charging_2D

        biasTerror = t_bias_charging/biasTrc
        v_error = biasTerror * (self._1D__V_swing if ndim == 1 else self._2D__V2_swing) / 2

        # max error is on y-value / gate2 voltage
        self.bias_T_warning_label.setText(f'max bias T error: {biasTerror:3.1%}, {v_error:3.1f} mV')
        style = 'QLabel {background-color : #F64; }' if biasTerror > 0.05 else ''
        self.bias_T_warning_label.setStyleSheet(style)

        if self.gates is not None and ndim == 2:
            enable = True
            if self._2D__gate1_name not in self.gates.parameters:
                logging.warning(f'{self._2D__gate1_name} not in DC gates')
                enable = False
            if self._2D__gate2_name not in self.gates.parameters:
                logging.warning(f'{self._2D__gate2_name} not in DC gates')
                enable = False
            self._2D_set_DC.setEnabled(enable)

    def _prepare_1D_scan(self):
        logger.info('Starting 1D')
        self._stop_other()
        if self._param1D is None: # @@@@ or anything changed...
            logger.debug('Creating 1D scan')
            self.get_plot_settings(1)
            # @@@ Move to get_plot_settings...
            self._scan_generator.configure(
                    acquisition_delay_ns=self._gen__acquisition_delay_ns,
                    enabled_markers=self._gen__enabled_markers,
                    line_margin=self._gen__line_margin)
            self._scan_generator.set_iq_mode(self.iq_mode)
            self._scan_generator.set_channel_map(self._active_channel_map)

            self._param1D = self._scan_generator.create_1D_scan(
                    self._1D__gate_name, self._1D__V_swing, self._1D__npt, self._1D__t_meas*1000,
                    pulse_gates=self._1D__offsets,
                    biasT_corr=self._1D__biasT_corr)
            self._plot1D = _1D_live_plot(
                    self._1D_plotter_layout, self._param1D,
                    self._1D_average.value(), self._1D_diff.isChecked(),
                    self._gen__n_columns, self._1D_av_progress,
                    gates=self.gates, gate_values_label=self.gate_values_label,
                    on_mouse_moved=self._on_mouse_moved_1D,
                    on_mouse_clicked=self._on_mouse_clicked_1D)
            self.set_metadata()
            logger.debug('Finished init currentplot and current_param')
        else:
            self._param1D.restart()

        self.vm_data_param_1D = vm_data_param(self._param1D, self._plot1D, self.metadata)

    @qt_log_exception
    def _start_1D(self):
        try:
            self._1D_play.setEnabled(False)
            self._prepare_1D_scan()
            self._plot1D.start()
            self._run_state = "1D"
            self._set_icon(self._1D_play, r"playing.png")
        except Exception as e:
            logger.error(repr(e), exc_info=True)
            self._stop_1D()
        finally:
            self._1D_play.setEnabled(True)

    @qt_log_exception
    def _stop_1D(self):
        if self._plot1D:
            logger.info('Stopping 1D')
            self._run_state = "Idle"
            self._set_icon(self._1D_play, "play.png")
            self._set_icon(self._1D_step, "image.png")
            self._plot1D.stop()

    def _prepare_2D_scan(self):
        logger.info('Prepare 2D scan')
        self._stop_other()
        if self._plot2D is None:
            logger.debug('Creating 2D scan')
            self.get_plot_settings(2)
            self._scan_generator.configure(
                    acquisition_delay_ns=self._gen__acquisition_delay_ns,
                    enabled_markers=self._gen__enabled_markers,
                    line_margin=self._gen__line_margin)
            self._scan_generator.set_iq_mode(self.iq_mode)
            self._scan_generator.set_channel_map(self._active_channel_map)
            self._param2D = self._scan_generator.create_2D_scan(
                    self._2D__gate1_name, self._2D__V1_swing, int(self._2D__npt),
                    self._2D__gate2_name, self._2D__V2_swing, int(self._2D__npt),
                    self._2D__t_meas*1000,
                    pulse_gates=self._2D__offsets,
                    biasT_corr=self._2D__biasT_corr)
            self._plot2D = _2D_live_plot(
                    self._2D_plotter_layout, self._param2D,
                    self._2D_average.value(), self._2D_gradient.currentText(),
                    self._gen__n_columns, self._2D_av_progress,
                    gates=self.gates, gate_values_label=self.gate_values_label,
                    on_mouse_moved=self._on_mouse_moved_2D,
                    on_mouse_clicked=self._on_mouse_clicked_2D)
            self._plot2D.set_cross(self._2D__cross)
            self._plot2D.set_colorbar(self._2D__colorbar)
            self._plot2D.set_background_filter(
                    self._2D_filter_background.isChecked(),
                    self._2D_background_sigma.value()
                    )
            self._plot2D.set_noise_filter(
                    self._2D_filter_noise.isChecked(),
                    self._2D_noise_sigma.value()
                    )
            self.set_metadata()
            logger.debug('Finished init currentplot and current_param')
        else:
            self._param2D.restart()

        self.vm_data_param_2D = vm_data_param(self._param2D, self._plot2D, self.metadata)

    @qt_log_exception
    def _start_2D(self):
        try:
            self._2D_play.setEnabled(False)
            self._prepare_2D_scan()
            logger.debug('Starting the plot')
            self._plot2D.start()
            self._run_state = "2D"
            self._set_icon(self._2D_play, r"playing.png")
        except Exception as e:
            logger.error(repr(e), exc_info=True)
            self._stop_2D()
        finally:
            self._2D_play.setEnabled(True)

    @qt_log_exception
    def _stop_2D(self):
        if self._plot2D:
            logger.info('Stopping 2D')
            self._plot2D.stop()
            self._set_icon(self._2D_play, "play.png")
            self._set_icon(self._2D_step, "image.png")
            self._run_state = "Idle"

    def stop(self):
        state = self.is_running
        if state == '1D':
            self._stop_1D()
        elif state == '2D':
            self._stop_2D()

    @qt_log_exception
    def _step_1D(self):
        try:
            self._prepare_1D_scan()
            self._plot1D.start(single_step=True)
            # Note: plot goes to not active state when ready
            # If play is pressed before ready, then it becomes playing...
            self._set_icon(self._1D_step, "capturing.png")
            self._run_state = "1D"
        except Exception as e:
            logger.error(repr(e), exc_info=True)
            self._stop_1D()

    @qt_log_exception
    def _step_2D(self):
        try:
            self._prepare_2D_scan()
            self._plot2D.start(single_step=True)
            # Note: plot goes to not active state when ready
            # If play is pressed before ready, then it becomes playing...
            self._set_icon(self._2D_step, "capturing.png")
            self._run_state = "2D"
        except Exception as e:
            logger.error(repr(e), exc_info=True)
            self._stop_1D()

    def _step(self):
        if self.tab_id == 0: # 1D
            self._step_1D()
        elif self.tab_id == 1: # 2D
            self._step_2D()

    def _update_active_state(self):
        state = self.is_running
        if state == '1D' and not self._plot1D.active:
            self._stop_1D()
        elif state == '2D' and not self._plot2D.active:
            self._stop_2D()

    def _stop_other(self):
        if not liveplotting.auto_stop_other:
            return
        liveplotting.stop_all(exclude=self)

    @staticmethod
    def stop_all(exclude=None):
        for gui in liveplotting._all_instances:
            if gui == exclude:
                continue
            try:
                if gui.is_running:
                    logger.info("Stopping other Video Mode GUI")
                    gui.stop()
            except Exception:
                logger.error("Failure stopping other Video Mode GUI", exc_info=True)

    @staticmethod
    def is_any_running():
        for gui in liveplotting._all_instances:
            if gui.is_running:
                return True
        return False

    def _reload(self):
        if self.tab_id == 0: # 1D
            self.update_plot_settings_1D()
        elif self.tab_id == 1: # 2D
            self.update_plot_settings_2D()

    @qt_log_exception
    def update_plot_settings_1D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data.
        '''
        try:
            if self._plot1D is not None:
                self._plot1D.stop()
                self._plot1D.remove()
                self._plot1D = None
                self._param1D.stop()
                self._param1D = None

            self._start_1D()
        except:
            logger.error('Update plot failed', exc_info=True)

    @qt_log_exception
    def update_plot_settings_2D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data. ~
        '''
        try:
            if self._plot2D is not None:
                self._plot2D.stop()
                self._plot2D.remove()
                self._plot2D = None
                self._param2D.stop()
                self._param2D = None

            self._start_2D()
        except:
            logger.error('Update plot failed', exc_info=True)

    @qt_log_exception
    def do_flip_axes(self):
        old_x_axis = self._2D_gate1_name.currentText()
        old_y_axis = self._2D_gate2_name.currentText()
        old_x_swing = self._2D_V1_swing.value()
        old_y_swing = self._2D_V2_swing.value()
        self._2D_gate1_name.setCurrentText(old_y_axis)
        self._2D_gate2_name.setCurrentText(old_x_axis)
        self._2D_V1_swing.setValue(old_y_swing)
        self._2D_V2_swing.setValue(old_x_swing)
        if self._run_state == "2D":
            self.update_plot_settings_2D()

    @qt_log_exception
    def tab_changed(self):
        self.stop()
        self.cursor_value_label.setText('')
        self.gate_values_label.setText('')
        self._gen__max_V_swing = self._gen_max_V_swing.value()
        for v_spinner in [self._1D_V_swing, self._2D_V1_swing, self._2D_V2_swing]:
            v_spinner.setRange(-self._gen__max_V_swing, self._gen__max_V_swing)

    @qt_log_exception
    def closeEvent(self, event):
        """
        overload the Qt close funtion. Make sure that all references in memory are fully gone,
        so the memory on the AWG is properly released.
        """
        self._update_timer.stop()
        if self._plot1D is not None:
            self._plot1D.stop()
            self._plot1D.remove()
            self._plot1D = None
            self._param1D.stop()
            self._param1D = None

        if self._plot2D is not None:
            self._plot2D.stop()
            self._plot2D.remove()
            self._plot2D = None
            self._param2D.stop()
            self._param2D = None

        try:
            # TODO @@@ improve HVI2 scheduler. Make it a qcodes instrument
            from core_tools.HVI2.scheduler_hardware import default_scheduler_hardware
            default_scheduler_hardware.release_schedule()
        except: pass

        if liveplotting.last_instance == self:
            liveplotting.last_instance = None
        try:
            liveplotting._all_instances.remove(self)
        except ValueError:
            logger.error("Oops! Error in liveplotting administration")
        logger.info('Window closed')

    @qt_log_exception
    def get_activated_channels(self):
        channels = set()
        for name, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channel_nr = self.channel_map[name][0]
                channels.add(channel_nr)
        return list(channels)

    @qt_log_exception
    def set_metadata(self):
        metadata = {}
        if self.tab_id == 0: # 1D
            metadata['measurement_type'] = '1D_sweep'
            for key in self.defaults_1D.keys():
                metadata[key] = getattr(self,f'_1D__{key}')
            metadata['offsets'] = self._1D__offsets
        elif self.tab_id == 1: # 2D
            metadata['measurement_type'] = '2D_sweep'
            for key in self.defaults_2D.keys():
                metadata['measurement_type'] = '2D_sweep'
                metadata[key] = getattr(self,f'_2D__{key}')
            metadata['offsets'] = self._2D__offsets

        for key in self.defaults_gen.keys():
            metadata[key] = getattr(self,f'_gen__{key}')

        self.metadata = metadata

    @property
    def vm_data_param(self):
        if self.tab_id == 0: # 1D
            return self.vm_data_param_1D
        if self.tab_id == 1: # 2D
            return self.vm_data_param_2D
        return None

    @qt_log_exception
    def copy_ppt(self, inp_title = ''):
        """
        ppt the data
        """
        if self.vm_data_param is None:
            print('no data to plot')
            return

        _, dataset_descriptor = self.save_data()
        notes = self.metadata.copy()
        notes.update(dataset_descriptor)
        if self.gates:
            try:
                notes['gates'] = self.gates.get_gate_voltages()
            except Exception as ex:
                logger.warning(f'Cannot add gates to PPT notes ({ex})')

        if type(inp_title) is not str:
            inp_title = ''

        if self.tab_id == 0: # 1D
            figure_hand = self._plot1D.plot_widgets[0].plot_widget.parent()
            gate_x = self._1D__gate_name
            range_x = self._1D__V_swing
            channels = ','.join(self._param1D.channel_names)
            title = f'{gate_x} ({range_x:.0f} mV), m:{channels}'
        elif self.tab_id == 1: # 2D
            figure_hand = self._plot2D.plot_widgets[0].plot_widget.parent()
            gate_y = self._2D__gate2_name
            gate_x = self._2D__gate1_name
            range_y = self._2D__V2_swing
            range_x = self._2D__V1_swing
            channels = ','.join(self._param2D.channel_names)
            title = f'{inp_title} {gate_y} ({range_y:.0f} mV) vs. {gate_x} ({range_x:.0f} mV), m:{channels}'
        else:
            title = 'Oops, unknown tab'

        addPPTslide(title=title, fig=figure_hand, notes=str(notes), verbose=-1)

    @qt_log_exception
    def copy_to_clipboard(self):
        if self.vm_data_param is None:
            return
        if self.tab_id == 0: # 1D
            frame = self._1D_plotter_frame
        elif self.tab_id == 1: # 2D
            frame = self._2D_plotter_frame
        else:
            return
        QtWidgets.QApplication.clipboard().setPixmap(frame.grab())

    @qt_log_exception
    def save_data(self):
        """
        save the data
        """
        data_saver = get_data_saver()

        if self.vm_data_param is None:
            print('no data to save')
            return
        if self.tab_id == 0: # 1D
            label = self._1D__gate_name
        elif self.tab_id == 1: # 2D
            label = self._2D__gate1_name + '_vs_' + self._2D__gate2_name
        else:
            raise Exception(f"Cannot save data from tab {self.tab_id}")

        self.vm_data_param.update_metadata()
        self.metadata['average'] = self.vm_data_param.plot.average_scans
        self.metadata['differentiate'] = self.vm_data_param.plot.gradient

        try:
            return data_saver.save_data(self.vm_data_param, label)
        except Exception:
            logger.error('Error during save data', exc_info=True)

    @qt_log_exception
    def _reset_1D_average(self):
        self._plot1D.clear_buffers()

    @qt_log_exception
    def _reset_2D_average(self):
        self._plot2D.clear_buffers()

    @qt_log_exception
    def _on_mouse_clicked_1D(self, x):
        if self._1D_set_DC.isChecked():
            vx = self._plot1D.gate_x_voltage + x
            self.gates.set(self._1D__gate_name, vx)
            msg = (f'Set {self._1D__gate_name}:{vx:6.3f} mV')
            print(msg)
            self.cursor_value_label.setText(msg)
            self._plot1D.clear_buffers = True

    @qt_log_exception
    def _on_mouse_moved_1D(self, x, ch, v):
        dc_x = self._plot1D.gate_x_voltage
        if dc_x is not None:
            x_total = f' ({dc_x+x:7.2f})'
        else:
            x_total = ''
        self.cursor_value_label.setText(
                f'{self._1D__gate_name}:{x:7.2f}{x_total} mV, '
                f'{ch}:{v:7.2f} mV')

    @qt_log_exception
    def _on_mouse_clicked_2D(self, x, y):
        if self._2D_set_DC.isChecked():
            vx = self._plot2D.gate_x_voltage + x
            vy = self._plot2D.gate_y_voltage + y
            self.gates.set(self._2D__gate1_name, vx)
            self.gates.set(self._2D__gate2_name, vy)
            msg = (f'Set {self._2D__gate1_name}:{vx:6.3f} mV, {self._2D__gate2_name}:{vy:6.3f}')
            print(msg)
            self.cursor_value_label.setText(msg)
            self._plot2D.clear_buffers = True

    @qt_log_exception
    def _on_mouse_moved_2D(self, x, y, ch, v):
        dc_x = self._plot2D.gate_x_voltage
        dc_y = self._plot2D.gate_y_voltage
        if dc_x is not None:
            x_total = f' ({dc_x+x:7.2f})'
        else:
            x_total = ''
        if dc_y is not None:
            y_total = f' ({dc_y+y:7.2f})'
        else:
            y_total = ''
        self.cursor_value_label.setText(
                f'{self._2D__gate1_name}:{x:7.2f}{x_total} mV, '
                f'{self._2D__gate2_name}:{y:7.2f}{y_total} mV, '
                f'{ch}:{v:7.2f} mV')

    @qt_log_exception
    def _1D_set_DC_button_state(self):
        if self._1D_set_DC.isChecked():
            self._1D_set_DC.setStyleSheet("QPushButton{ background-color: yellow }")
        else:
            self._1D_set_DC.setStyleSheet("")

    @qt_log_exception
    def _2D_set_DC_button_state(self):
        if self._2D_set_DC.isChecked():
            self._2D_set_DC.setStyleSheet("QPushButton{ background-color: yellow }")
        else:
            self._2D_set_DC.setStyleSheet("")


class vm_data_param(MultiParameter):
    def __init__(self, param, plot, metadata):
        param = param
        names = param.names
        shapes = param.shapes
        labels = param.labels
        units = param.units
        setpoints = param.setpoints
        setpoint_names = param.setpoint_names
        setpoint_labels = param.setpoint_labels
        setpoint_units = param.setpoint_units
        self.param = param
        self.plot = plot
        super().__init__(name='video_mode_data', instrument=None,
             names=names, labels=labels, units=units,
             shapes=shapes, setpoints=setpoints, setpoint_names=setpoint_names,
             setpoint_labels=setpoint_labels, setpoint_units=setpoint_units,
             metadata=metadata)

    def update_metadata(self):
        self.load_metadata({'average':self.plot.average_scans})

    def snapshot_base(self,
                      update: bool | None = True,
                      params_to_skip_update: Sequence[str] | None = None
                      ) -> dict[any, any]:
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot["parameters"] = self.param.snapshot().get("parameters", {})
        return snapshot

    def get_raw(self):
        current_data = self.plot.buffer_data
        av_data = [np.sum(cd, 0).T/len(cd) for cd in current_data]
        return av_data
