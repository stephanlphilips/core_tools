import io
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pyqtgraph as pg

from PyQt5 import QtCore, QtWidgets, QtGui

from qcodes import MultiParameter
from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver
from core_tools.GUI.keysight_videomaps.data_saver.native import CoreToolsDataSaver
from core_tools.GUI.keysight_videomaps.data_getter.iq_modes import iq_mode2numpy
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Virtual
from core_tools.GUI.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot
from core_tools.utility.powerpoint import addPPTslide
from ..qt_util import qt_log_exception

logger = logging.getLogger(__name__)

_data_saver: Optional[IDataSaver] = None
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

@dataclass
class plot_content:
    _1D: _1D_live_plot
    _2D: _2D_live_plot


@dataclass
class param_getter:
    _1D: object()
    _2D: object()


class liveplotting(QtWidgets.QMainWindow, Ui_MainWindow):
    # class variable to keep the last instance alive and retrievable by other components.
    last_instance = None

    """
    VideoMode GUI.
    """
    def __init__(self, pulse_lib, digitizer, scan_type = 'Virtual', cust_defaults = None,
                 iq_mode=None, channel_map=None, gates=None):
        '''
        init of the class

        Args:
            pulse_lib (pulselib) : provide the pulse library object. This is used to generate the sequences.
            digitizer (QCodes Instrument) : provide the digitizer driver of the card. In this case the one put in V2 software.
            scan_type (str) : type of the scan, will point towards a certain driver for getting the data (e.g. 'Virtual', 'Keysight')
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
        '''
        logger.info('initialising vm')
        self.pulse_lib = pulse_lib
        self.digitizer = digitizer
        self.scan_type = scan_type
        if gates is None:
            gates = _try_get_gates()
        self.gates = gates

        if scan_type == 'Virtual':
            self.construct_1D_scan_fast = scan_generator_Virtual.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Virtual.construct_2D_scan_fast
        elif scan_type == "Keysight":
            from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Keysight
            self.construct_1D_scan_fast = scan_generator_Keysight.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Keysight.construct_2D_scan_fast
        elif scan_type == "Tektronix":
            from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Tektronix
            self.construct_1D_scan_fast = scan_generator_Tektronix.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Tektronix.construct_2D_scan_fast
        elif scan_type == "Qblox":
            from .data_getter import scan_generator_Qblox
            if digitizer is not None:
                logger.error('liveplotting parameter digitizer should be None for Qblox. '
                              'QRM must be added to pulse_lib with  `add_digitizer`.')
            self.construct_1D_scan_fast = scan_generator_Qblox.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Qblox.construct_2D_scan_fast
        else:
            raise ValueError("Unsupported argument for scan type.")
        self.current_plot = plot_content(None, None)
        self.current_param_getter = param_getter(None, None)
        self.vm_data_param = None
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

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.start_1D.clicked.connect(lambda:self._1D_start_stop())
        self.start_2D.clicked.connect(lambda:self._2D_start_stop())
        self._1D_update_plot.clicked.connect(lambda:self.update_plot_settings_1D())
        self._2D_update_plot.clicked.connect(lambda:self.update_plot_settings_2D())
        self._flip_axes.clicked.connect(lambda:self.do_flip_axes())
        self.tabWidget.currentChanged.connect(lambda:self.tab_changed())

        self._1D_reset_average.clicked.connect(lambda:self._reset_1D_average())
        self._2D_reset_average.clicked.connect(lambda:self._reset_2D_average())

        self.init_defaults(pulse_lib.channels, cust_defaults)

        self._1D_save_data.clicked.connect(lambda:self.save_data())
        self._2D_save_data.clicked.connect(lambda:self.save_data())

        self._1D_ppt_save.clicked.connect(lambda:self.copy_ppt())
        self._2D_ppt_save.clicked.connect(lambda:self.copy_ppt())

        self._1D_copy.clicked.connect(lambda:self.copy_to_clipboard())
        self._2D_copy.clicked.connect(lambda:self.copy_to_clipboard())

        self._1D_set_DC.setEnabled(gates is not None)
        self._1D_set_DC.clicked.connect(lambda:self._1D_set_DC_button_state())
        self._2D_set_DC.setEnabled(gates is not None)
        self._2D_set_DC.clicked.connect(lambda:self._2D_set_DC_button_state())

        liveplotting.last_instance = self

        self.show()
        if instance_ready == False:
            print('APP EXEC')
            self.app.exec()

    def setupUI2(self):
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

    @property
    def tab_id(self):
        return self.tabWidget.currentIndex()

    @property
    def is_running(self):
        if self.start_1D.text() == 'Stop':
            return '1D'
        elif self.start_2D.text() == 'Stop':
            return '2D'
        else:
            return False

    def turn_off(self):
        if self.is_running == '1D':
            self._1D_start_stop()
        elif self.is_running == '2D':
            self._2D_start_stop()

    def _set_channel_map(self, channel_map, iq_mode):
        if channel_map is not None:
            if iq_mode is not None:
                logger.warning('iq_mode is ignored when channel_map is specified')
            self.channel_map = channel_map
            return

        if isinstance(iq_mode, dict):
            for ch, mode in iq_mode.items():
                self.channel_map[f'ch{ch}'] = (ch, iq_mode2numpy[mode])
            return

        if self.digitizer is None:
            channels = [(name, name) for name in self.pulse_lib.digitizer_channels]
        else:
            channels = [(f'ch{i}', i) for i in range(1,5)]

        if iq_mode is None:
            func = np.real
        else:
            func = iq_mode2numpy[iq_mode]

        self.channel_map = {}
        for name,channel in channels:
            if isinstance(func, list):
                for suffix,f in func:
                    self.channel_map[name+suffix] = (channel, f)
            else:
                self.channel_map[name] = (channel, func)


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
            for i in [1,2,3]:
                cb_offset = getattr(self, f'_{dim}_offset{i}_name')
                cb_offset.addItem('<None>')
                for gate in sorted(gates, key=str.lower):
                    cb_offset.addItem(gate)
            try:
                init_offsets = cust_defaults[dim]['offsets']
            except Exception:
                continue
            if len(init_offsets) > 3:
                raise Exception('Only 3 offsets supported')
            for i,(gate,value) in enumerate(init_offsets.items()):
                getattr(self, f'_{dim}_offset{i+1}_name').setCurrentText(gate)
                getattr(self, f'_{dim}_offset{i+1}_voltage').setValue(value)

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
            'background_sigma': 0.2,
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

        self._1D_average.valueChanged.connect(lambda:self.update_plot_properties_1D())
        self._1D_diff.stateChanged.connect(lambda:self.update_plot_properties_1D())

        self._2D_average.valueChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_gradient.currentTextChanged.connect(lambda:self.update_plot_properties_2D())
        self._2D_filter_background.stateChanged.connect(lambda:self.update_plot_properties_2D())

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

    def set_digitizer_settings(self, sample_rate=None, channels=None, dig_vmax=None):
        if sample_rate is not None:
            if int(sample_rate/1e6) not in [100, 500]:
                raise Exception(f'sample rate {sample_rate} is not valid. Valid values: 100, 500 MHz')
            self._gen_sample_rate.setCurrentText(str(int(sample_rate/1e6)))

        if channels is not None:
            for check_box in self.channel_check_boxes.values():
                check_box.setChecked(False)
            for channel in channels:
                ch = str(channel)
                self.channel_check_boxes[ch].setChecked(True)

            self._channels = self.get_activated_channels()
        if dig_vmax is not None:
            print(f'Parameter dig_vmax is deprecated. Digitizer input should be configured directly on instrument.')

    @qt_log_exception
    def update_plot_properties_1D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differentation of data)
        '''
        if self.current_plot._1D  is not None:
            self.current_plot._1D.averaging = self._1D_average.value()
            self.current_plot._1D.gradient = self._1D_diff.isChecked()
            # store for metadata
            self._1D__average = self._1D_average.value()
            self._1D__diff = self._1D_diff.isChecked()

    @qt_log_exception
    def update_plot_properties_2D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/gradient of data)
        '''
        if self.current_plot._2D  is not None:
            self.current_plot._2D.averaging = self._2D_average.value()
            self.current_plot._2D.gradient = self._2D_gradient.currentText()
            self.current_plot._2D.set_background_filter(
                    self._2D_filter_background.isChecked(),
                    self._gen_background_sigma.value()
                    )
            # store for metadata
            self._2D__average = self._2D_average.value()
            self._2D__gradient = self._2D_gradient.currentText()
            self._2D__filter_background = self._2D_filter_background.isChecked()
            self._gen__background_sigma = self._gen_background_sigma.value()

    @qt_log_exception
    def get_offsets(self, dimension='1D'):
        offsets = {}
        for i in range(1,4):
            gate = getattr(self, f'_{dimension}_offset{i}_name').currentText()
            voltage = getattr(self, f'_{dimension}_offset{i}_voltage').value()
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


    @qt_log_exception
    def _1D_start_stop(self):
        '''
        Starts/stops the data acquisition and plotting.
        '''
        if self.start_1D.text() == "Start":
            self._start_1D()
        elif self.start_1D.text() == "Stop":
            self._stop_1D()

    def _start_1D(self):
        try:
            if self.current_plot._1D is None:
                logger.info('Creating 1D scan')
                self.get_plot_settings(1)
                self.start_1D.setEnabled(False)
                self.current_param_getter._1D = self.construct_1D_scan_fast(
                        self._1D__gate_name, self._1D__V_swing, self._1D__npt, self._1D__t_meas*1000,
                        self._1D__biasT_corr, self.pulse_lib, self.digitizer, self._channels,
                        acquisition_delay_ns=self._gen__acquisition_delay_ns,
                        enabled_markers=self._gen__enabled_markers,
                        channel_map=self._active_channel_map,
                        pulse_gates=self._1D__offsets,
                        line_margin=self._gen__line_margin)
                self.current_plot._1D = _1D_live_plot(
                        self._1D_plotter_layout, self.current_param_getter._1D,
                        self._1D_average.value(), self._1D_diff.isChecked(),
                        self._gen__n_columns, self._1D_av_progress,
                        gates=self.gates, gate_values_label=self.gate_values_label,
                        on_mouse_moved=self._on_mouse_moved_1D,
                        on_mouse_clicked=self._on_mouse_clicked_1D)
                self.start_1D.setEnabled(True)
                self.set_metadata()
                logger.info('Finished init currentplot and current_param')
            else:
                self.current_param_getter._1D.restart()

            self.vm_data_param = vm_data_param(self.current_param_getter._1D, self.current_plot._1D, self.metadata)
            self.start_1D.setText("Stop")
            self.current_plot._1D.start()
        except Exception as e:
            logger.error(e, exc_info=True)

    def _stop_1D(self):
        self.current_plot._1D.stop()
        self.start_1D.setText("Start")

    @qt_log_exception
    def _2D_start_stop(self):
        '''
        Starts/stops the data acquisition and plotting.
        '''
        if self.start_2D.text() == "Start":
            self._start_2D()
        elif self.start_2D.text() == "Stop":
            self._stop_2D()

    def _start_2D(self):
        try:
            logger.info('Starting 2D')
            if self.current_plot._2D is None:
                logger.info('Creating 2D scan')
                self.get_plot_settings(2)
                self.start_2D.setEnabled(False)
                self.current_param_getter._2D = self.construct_2D_scan_fast(
                        self._2D__gate1_name, self._2D__V1_swing, int(self._2D__npt),
                        self._2D__gate2_name, self._2D__V2_swing, int(self._2D__npt),
                        self._2D__t_meas*1000, self._2D__biasT_corr,
                        self.pulse_lib, self.digitizer, self._channels,
                        acquisition_delay_ns=self._gen__acquisition_delay_ns,
                        enabled_markers=self._gen__enabled_markers,
                        channel_map=self._active_channel_map,
                        pulse_gates=self._2D__offsets,
                        line_margin=self._gen__line_margin,
                        )
                logger.info('Finished Param, now plot')
                self.current_plot._2D = _2D_live_plot(
                        self._2D_plotter_layout, self.current_param_getter._2D,
                        self._2D_average.value(), self._2D_gradient.currentText(),
                        self._gen__n_columns, self._2D_av_progress,
                        gates=self.gates, gate_values_label=self.gate_values_label,
                        on_mouse_moved=self._on_mouse_moved_2D,
                        on_mouse_clicked=self._on_mouse_clicked_2D)
                self.current_plot._2D.set_cross(self._2D__cross)
                self.current_plot._2D.set_colorbar(self._2D__colorbar)
                self.current_plot._2D.set_background_filter(
                        self._2D_filter_background.isChecked(),
                        self._gen_background_sigma.value()
                        )
                self.start_2D.setEnabled(True)
                self.set_metadata()
                logger.info('Finished init currentplot and current_param')
            else:
                self.current_param_getter._2D.restart()

            logger.info('Defining vm_data_param')
            self.vm_data_param = vm_data_param(self.current_param_getter._2D, self.current_plot._2D, self.metadata)

            self.start_2D.setText("Stop")
            logger.info('Starting the plot')
            self.current_plot._2D.start()
        except Exception as e:
            logger.error(e, exc_info=True)

    def _stop_2D(self):
        logger.info('Stopping 2D')
        self.current_plot._2D.stop()
        self.start_2D.setText("Start")

    def stop(self):
        state = self.is_running
        if state == '1D':
            self._stop_1D()
        elif state == '2D':
            self._stop_2D()

    @qt_log_exception
    def update_plot_settings_1D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data.
        '''
        try:
            if self.current_plot._1D is not None:
                self.current_plot._1D.stop()
                self.current_plot._1D.remove()
                self.current_plot._1D = None
                self.current_param_getter._1D.stop()
                self.current_param_getter._1D = None

            self.start_1D.setText("Start")
            self._1D_start_stop()
        except:
            logger.error('Update plot failed', exc_info=True)

    @qt_log_exception
    def update_plot_settings_2D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data. ~
        '''
        try:
            if self.current_plot._2D is not None:
                self.current_plot._2D.stop()
                self.current_plot._2D.remove()
                self.current_plot._2D = None
                self.current_param_getter._2D.stop()
                self.current_param_getter._2D = None

            self.start_2D.setText("Start")
            self._2D_start_stop()
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
        if self.start_2D.text() == "Stop":
            self.update_plot_settings_2D()

    @qt_log_exception
    def tab_changed(self):
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.start_1D.setText("Start")
        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.start_2D.setText("Start")
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
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.current_plot._1D.remove()
            self.current_plot._1D = None
            self.current_param_getter._1D.stop()
            self.current_param_getter._1D = None

        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.current_plot._2D.remove()
            self.current_plot._2D = None
            self.current_param_getter._2D.stop()
            self.current_param_getter._2D = None

        try:
            # TODO @@@ improve HVI2 scheduler. Make it a qcodes instrument
            from core_tools.HVI2.scheduler_hardware import default_scheduler_hardware
            default_scheduler_hardware.release_schedule()
        except: pass

        if liveplotting.last_instance == self:
            liveplotting.last_instance = None
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

    @qt_log_exception
    def copy_ppt(self, inp_title = ''):
        """
        ppt the data
        """
        if self.vm_data_param is None:
            print('no data to plot')
            return

        _, dataset_metadata = self.save_data()
        notes = self.metadata.copy()
        notes.update(dataset_metadata)
        if self.gates:
            try:
                notes['gates'] = self.gates.get_gate_voltages()
            except Exception as ex:
                logger.warning(f'Cannot add gates to PPT notes ({ex})')

        if type(inp_title) is not str:
            inp_title = ''

        if self.tab_id == 0: # 1D
            figure_hand = self.current_plot._1D.plot_widgets[0].plot_widget.parent()
            gate_x = self._1D__gate_name
            range_x = self._1D__V_swing
            channels = ','.join(self.current_param_getter._1D.channel_names)
            title = f'{gate_x} ({range_x:.0f} mV), m:{channels}'
        elif self.tab_id == 1: # 2D
            figure_hand = self.current_plot._2D.plot_widgets[0].plot_widget.parent()
            gate_y = self._2D__gate2_name
            gate_x = self._2D__gate1_name
            range_y = self._2D__V2_swing
            range_x = self._2D__V1_swing
            channels = ','.join(self.current_param_getter._2D.channel_names)
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
            raise RuntimeError(f"Attempting to save data, but liveplotting could not determine whether 1D or 2D is "
                               f"selected (self.tab_id=={self.tab_id}).")

        self.vm_data_param.update_metadata()
        self.metadata['average'] = self.vm_data_param.plot.average_scans
        self.metadata['differentiate'] = self.vm_data_param.plot.gradient

        try:
            return data_saver.save_data(self.vm_data_param, label)
        except Exception:
            logger.error(f'Error during save data', exc_info=True)

    @qt_log_exception
    def _reset_1D_average(self):
        self.current_plot._1D.clear_buffers = True

    @qt_log_exception
    def _reset_2D_average(self):
        self.current_plot._2D.clear_buffers = True

    @qt_log_exception
    def _on_mouse_clicked_1D(self, x):
        if self._1D_set_DC.isChecked():
            vx = self.current_plot._1D.gate_x_voltage + x
            self.gates.set(self._1D__gate_name, vx)
            msg = (f'Set {self._1D__gate_name}:{vx:6.3f} mV')
            print(msg)
            self.cursor_value_label.setText(msg)
            self.current_plot._1D.clear_buffers = True

    @qt_log_exception
    def _on_mouse_moved_1D(self, x, ch, v):
        dc_x = self.current_plot._1D.gate_x_voltage
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
            vx = self.current_plot._2D.gate_x_voltage + x
            vy = self.current_plot._2D.gate_y_voltage + y
            self.gates.set(self._2D__gate1_name, vx)
            self.gates.set(self._2D__gate2_name, vy)
            msg = (f'Set {self._2D__gate1_name}:{vx:6.3f} mV, {self._2D__gate2_name}:{vy:6.3f}')
            print(msg)
            self.cursor_value_label.setText(msg)
            self.current_plot._2D.clear_buffers = True

    @qt_log_exception
    def _on_mouse_moved_2D(self, x, y, ch, v):
        dc_x = self.current_plot._2D.gate_x_voltage
        dc_y = self.current_plot._2D.gate_y_voltage
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
            self._1D_set_DC.setStyleSheet("QPushButton{ background-color: yellow }");
        else:
            self._1D_set_DC.setStyleSheet("");

    @qt_log_exception
    def _2D_set_DC_button_state(self):
        if self._2D_set_DC.isChecked():
            self._2D_set_DC.setStyleSheet("QPushButton{ background-color: yellow }");
        else:
            self._2D_set_DC.setStyleSheet("");


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
        self.plot = plot
        super().__init__(name='vm_data_parameter', instrument=None,
             names=names, labels=labels, units=units,
             shapes=shapes, setpoints=setpoints, setpoint_names=setpoint_names,
             setpoint_labels=setpoint_labels, setpoint_units=setpoint_units,
             metadata=metadata)

    def update_metadata(self):
        self.load_metadata({'average':self.plot.average_scans})


    def get_raw(self):
        current_data = self.plot.buffer_data
        av_data = [np.sum(cd, 0).T/len(cd) for cd in current_data]
        return av_data


if __name__ == '__main__':
    class test(object):
        """docstring for test"""
        def __init__(self, arg):
            super(test, self).__init__()
            self.channels = arg

    # from V2_software.LivePlotting.data_getter.scan_generator_Virtual import construct_1D_scan_fast, construct_2D_scan_fast, fake_digitizer

    # dig = fake_digitizer("fake_digitizer")
    t= test(['P1','P2', 'P3', 'P4'])

    # V2_liveplotting(t,dig)

    from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import fake_digitizer
    # from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib

    # load a virtual version of the digitizer.
    dig = fake_digitizer("fake_digitizer")

    # load the AWG library (without loading the awg's)
    # pulse, _ = return_pulse_lib()

    liveplotting(t,dig)