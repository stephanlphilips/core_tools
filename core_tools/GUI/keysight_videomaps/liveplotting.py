import logging
import os
from collections.abc import Sequence
from typing import Callable

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui
from qcodes import MultiParameter

import core_tools.GUI.keysight_videomaps.GUI as gui_module
from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver
from core_tools.GUI.keysight_videomaps.data_saver.native import CoreToolsDataSaver
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_base import (
    FastScanParameterBase,
    FastScanGeneratorBase,
)
from core_tools.GUI.keysight_videomaps.data_getter.iq_modes import get_channel_map, get_channel_map_dig_4ch
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Virtual
from core_tools.GUI.keysight_videomaps.GUI.favorites import Favorites
from core_tools.GUI.keysight_videomaps.GUI.pulselib_settings import PulselibSettings
from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.GUI.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot
from core_tools.GUI.qt_util import qt_log_exception
from core_tools.utility.powerpoint import addPPTslide
from core_tools.GUI.keysight_videomaps.GUI.gui_components import (
    Settings, CheckboxList, OffsetsList
)


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
    except Exception:
        return None


class liveplotting(QtWidgets.QMainWindow, Ui_MainWindow):
    # class variable to keep the last instance alive and retrievable by other components.
    last_instance = None
    _all_instances = []
    auto_stop_other = True

    def __init__(self, pulse_lib, digitizer=None,
                 scan_type: str | None = None,
                 cust_defaults: dict[str, dict[str, any]] | None = None,
                 iq_mode: str | None = None,
                 channel_map: dict[str, tuple[int | str, Callable[[np.ndarray], np.ndarray]]] | None = None,
                 gates=None,
                 n_pulse_gates=5,
                 scan_generator: FastScanGeneratorBase | None = None,
                 title: str | None = None,
                 settings_dir: str | None = None,
                 settings_name: str | None = None,
                 ):
        '''
        Args:
            pulse_lib (pulselib) : provide the pulse library object. This is used to generate the sequences.
            digitizer (QCodes Instrument) : digitizer to use. If None uses digitizers configured in pulse-lib.
            scan_type (str) : AWG and digitizer used: 'Keysight', 'Qblox', 'Tektronix' or 'Virtual'.
            cust_defaults (dict of dicts):
                Dictionary to supply custom starting defaults.
                Any parameters/dicts that are not defined will resort to defaults.
                Format is {'1D': dict, '2D': dict, 'gen': dict}
                    1D = {'gate_name': str,
                       'V_swing': float,
                       'npt': int,
                       't_meas': float,
                       'biasT_corr': bool,
                       'average': int,
                       'diff': bool,
                       'offsets': dict[str, float]}
                    2D = {'gate1_name': str,
                       'gate2_name': str,
                       'V1_swing': float,
                       'V2_swing': float,
                       'npt': int,
                       't_meas': float,
                       'biasT_corr': bool,
                       'average': int,
                       'gradient': str, # 'Off', 'Magnitude', or 'Mag & angle'
                       'filter_background': bool,
                       'background_sigma': float,
                       'filter_noise': bool,
                       'noise_sigma': float,
                       'cross': bool,
                       'colorbar': bool,
                       'offsets': dict[str, float]}
                    gen = {
                       'enabled_channels': list[str],
                       'enabled_markers': list[str],
                       'n_columns': int,
                       'line_margin': int,
                       'bias_T_RC': float,
                       'acquisition_delay_ns': float, # ns between AWG output change and digitizer acquisition start.
                       'max_V_swing': float, # maximum voltage swing for 1D and 2D
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
            scan_generator: Custom scan generator to use.
            title: Text to add to window title bar
            settings_dir: Directory where favorite settings are stored.
            settings_name: Name of favorite settings to load.

        Note:
            If multiple settings are provided by a default settings file "videomode.Default.yaml",
            `cust_defaults`, and/or a `settings_name`, then the settings are applied in
            aforementioned order.
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
        self._set_channel_map(channel_map, iq_mode)
        self._pulselib_settings = PulselibSettings(pulse_lib)

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
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        if title is None:
            window_title = "Video Mode"
        else:
            window_title = f"Video Mode - {title}"
        self.setWindowTitle(window_title)

        self.setup_statusbar()
        self._favorites = Favorites(self, settings_dir)
        self.setupUI2()
        self._init_defaults(cust_defaults, settings_name)

        # update GUI state (for single step)
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.timeout.connect(self._update_active_state)
        self._update_timer.start(200)

        # only change if still default
        if pg.getConfigOption('foreground') == 'd' and pg.getConfigOption('background') == 'k':
            pg.setConfigOption('background', 'w')
            pg.setConfigOption('foreground', 'k')

        liveplotting.last_instance = self
        liveplotting._all_instances.append(self)

        self.show()
        if instance_ready is False:
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

    def setup_statusbar(self):
        self.statusbar.setContentsMargins(8, 0, 4, 4)
        self.bias_T_warning_label = QtWidgets.QLabel("")
        self.bias_T_warning_label.setMargin(2)
        self.bias_T_warning_label.setContentsMargins(QtCore.QMargins(6, 0, 6, 0))
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

    def setupUI2(self):
        gate_names = sorted(self.pulse_lib.channels, key=str.lower)
        self.gate_names = gate_names

        for name in gate_names:
            self._1D_gate_name.addItem(name)
            self._2D_gate1_name.addItem(name)
            self._2D_gate2_name.addItem(name)

        self._gen_settings = Settings("gen", lambda: None)
        self._1D_settings = Settings("1D", self.update_plot_properties_1D)
        self._2D_settings = Settings("2D", self.update_plot_properties_2D)

        sensor_checkboxes = CheckboxList(
            "enabled_channels",
            self._gen_settings,
            list(self.channel_map.keys()),
            self.horizontalLayout_channel_labels,
            self.horizontalLayout_channel_checkboxes,
            default=True,
        )

        marker_checkboxes = CheckboxList(
            "enabled_markers",
            self._gen_settings,
            sorted(self.pulse_lib.marker_channels, key=str.lower),
            self.horizontalLayout_markers,
            self.horizontalLayout_markers_checks,
            default=False,
        )

        self._gen_settings.add("acquisition_delay_ns", self._gen_acquisition_delay_ns)
        self._gen_settings.add("n_columns", self._gen_n_columns)
        self._gen_settings.add("line_margin", self._gen_line_margin)
        self._gen_settings.add("max_V_swing", self._gen_max_V_swing, plot_setting=True)
        self._gen_settings.add("bias_T_RC", self._gen_bias_T_RC, plot_setting=True)
        self._gen_settings.add("enabled_channels", sensor_checkboxes)
        self._gen_settings.add("enabled_markers", marker_checkboxes)
        self._gen_settings.add("virtual_matrix_auto_recompile", self._gen_vm_auto_recompile)

        offset_gate_voltages_1D = OffsetsList(
            "offsets",
            self._1D_settings,
            self.formLayout_1D,
            11,
            self.n_pulse_gates,
            gate_names)

        self._1D_settings.add("gate_name", self._1D_gate_name)
        self._1D_settings.add("V_swing", self._1D_V_swing)
        self._1D_settings.add("npt", self._1D_npt)
        self._1D_settings.add("t_meas", self._1D_t_meas)
        self._1D_settings.add("biasT_corr", self._gen_biasT_corr_1D)
        self._1D_settings.add("average", self._1D_average, plot_setting=True)
        self._1D_settings.add("diff", self._1D_diff, plot_setting=True)
        self._1D_settings.add("offsets", offset_gate_voltages_1D)

        offset_gate_voltages_2D = OffsetsList(
            "offsets",
            self._2D_settings,
            self.formLayout_2D,
            11,
            self.n_pulse_gates,
            gate_names)

        self._2D_settings.add("gate1_name", self._2D_gate1_name)
        self._2D_settings.add("V1_swing", self._2D_V1_swing)
        self._2D_settings.add("V2_swing", self._2D_V2_swing)
        self._2D_settings.add("gate2_name", self._2D_gate2_name)
        self._2D_settings.add("npt", self._2D_npt)
        self._2D_settings.add("t_meas", self._2D_t_meas)
        self._2D_settings.add("biasT_corr", self._gen_biasT_corr_2D)
        self._2D_settings.add("average", self._2D_average, plot_setting=True)
        self._2D_settings.add("gradient", self._2D_gradient, plot_setting=True)
        self._2D_settings.add("filter_background", self._2D_filter_background, plot_setting=True)
        self._2D_settings.add("background_sigma", self._2D_background_sigma, plot_setting=True)
        self._2D_settings.add("filter_noise", self._2D_filter_noise, plot_setting=True)
        self._2D_settings.add("noise_sigma", self._2D_noise_sigma, plot_setting=True)
        self._2D_settings.add("cross", self._gen_2D_cross)
        self._2D_settings.add("colorbar", self._gen_2D_colorbar)
        self._2D_settings.add("offsets", offset_gate_voltages_2D)

        self._1D_play.clicked.connect(lambda: self._start_1D())
        self._2D_play.clicked.connect(lambda: self._start_2D())
        self._1D_pause.clicked.connect(lambda: self._stop_1D())
        self._2D_pause.clicked.connect(lambda: self._stop_2D())
        self._1D_step.clicked.connect(lambda: self._step_1D())
        self._2D_step.clicked.connect(lambda: self._step_2D())
        self._1D_reload.clicked.connect(lambda: self.reload_1D())
        self._2D_reload.clicked.connect(lambda: self.reload_2D())
        self._flip_axes.clicked.connect(lambda: self.do_flip_axes())
        self.tabWidget.currentChanged.connect(lambda: self.tab_changed())

        self._1D_reset_average.clicked.connect(lambda: self._reset_1D_average())
        self._2D_reset_average.clicked.connect(lambda: self._reset_2D_average())

        self._1D_save_data.clicked.connect(lambda: self.save_data())
        self._2D_save_data.clicked.connect(lambda: self.save_data())

        self._1D_ppt_save.clicked.connect(lambda: self.copy_ppt())
        self._2D_ppt_save.clicked.connect(lambda: self.copy_ppt())

        self._1D_copy.clicked.connect(lambda: self.copy_to_clipboard())
        self._2D_copy.clicked.connect(lambda: self.copy_to_clipboard())

        self._1D_set_DC.setEnabled(self.gates is not None)
        self._1D_set_DC.setStyleSheet("QPushButton:checked { background-color: #ffc000; color: black }")
        self._2D_set_DC.setEnabled(self.gates is not None)
        self._2D_set_DC.setStyleSheet("QPushButton:checked { background-color: #ffc000; color: black }")

        self._shortcut_play = QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self)
        self._shortcut_play.activated.connect(self._play)
        self._shortcut_reload = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F5"), self)
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

        self._fav_save.clicked.connect(lambda: self._favorites.save())
        self._fav_save_default.clicked.connect(lambda: self._favorites.save_default())
        self._fav_apply.clicked.connect(lambda: self._apply_favorite())
        self._favorites_names.currentRowChanged.connect(self._load_selected_favorite)

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

    def _init_defaults(self, cust_defaults, settings_name: str = None):
        self.defaults_1D = {
            'gate_name': self.gate_names[0],
            'V_swing': 50,
            'npt': 200,
            't_meas': 50,
            'average': 1,
            'diff': False,
            'biasT_corr': False,
        }

        self.defaults_2D = {
            'gate1_name': self.gate_names[0],
            'gate2_name': self.gate_names[1],
            'V1_swing': 50,
            'V2_swing': 50,
            'npt': 75,
            't_meas': 5,
            'biasT_corr': True,
            'average': 1,
            'gradient': 'Off',
            'filter_background': False,
            'background_sigma': 0.2,
            'filter_noise': False,
            'noise_sigma': 1.0,
            'cross': False,
            'colorbar': False,
        }

        self.defaults_gen = {
            'acquisition_delay_ns': 500,
            'n_columns': 4,
            'line_margin': 1,
            'max_V_swing': 1000.0,
            'bias_T_RC': 100,
            'virtual_matrix_auto_recompile': False,
        }

        self._1D_settings.update(self.defaults_1D)
        self._2D_settings.update(self.defaults_2D)
        self._gen_settings.update(self.defaults_gen)

        settings = self._favorites.read_settings("Default", may_fail=True)
        self.apply_settings(settings)

        if cust_defaults is not None:
            defaults_1D = cust_defaults.get("1D", {}).copy()
            defaults_2D = cust_defaults.get("2D", {}).copy()
            defaults_gen = cust_defaults.get("gen", {}).copy()
            # convert old settings to new settings
            if "biasT_corr_1D" in defaults_gen:
                defaults_1D["biasT_corr"] = defaults_gen["biasT_corr_1D"]
            if "biasT_corr_2D" in defaults_gen:
                defaults_2D["biasT_corr"] = defaults_gen["biasT_corr_2D"]
            if "2D_cross" in defaults_gen:
                defaults_2D["cross"] = defaults_gen["2D_cross"]
            if "2D_colorbar" in defaults_gen:
                defaults_2D["colorbar"] = defaults_gen["2D_colorbar"]

            self._1D_settings.update(defaults_1D)
            self._2D_settings.update(defaults_2D)
            self._gen_settings.update(defaults_gen)

        if settings_name is not None:
            self.load_favorite_setting(settings_name)

        max_swing = self._gen_settings["max_V_swing"]
        for v_spinner in [self._1D_V_swing, self._2D_V1_swing, self._2D_V2_swing]:
            v_spinner.setRange(-max_swing, max_swing)

    def apply_settings(self, settings: dict[str, any]):
        self._1D_settings.update(settings.get("1D", {}))
        self._2D_settings.update(settings.get("2D", {}))
        self._gen_settings.update(settings.get("gen", {}))

    @qt_log_exception
    def _load_selected_favorite(self, index: int):
        active_settings = {
            "1D": self._1D_settings.to_dict(),
            "2D": self._2D_settings.to_dict(),
            "gen": self._gen_settings.to_dict(),
        }
        self._favorites.load_selected(active_settings)

    @qt_log_exception
    def _apply_favorite(self):
        self.apply_settings(self._favorites.current_settings())

    @qt_log_exception
    def update_plot_properties_1D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differentation of data)
        '''
        if self._plot1D is not None:
            settings = self._1D_settings
            self._plot1D.averaging = settings["average"]
            self._plot1D.gradient = settings["diff"]

    @qt_log_exception
    def update_plot_properties_2D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/gradient of data)
        '''
        if self._plot2D is not None:
            settings = self._2D_settings
            self._plot2D.averaging = settings["average"]
            self._plot2D.gradient = settings["gradient"]
            self._plot2D.set_background_filter(
                settings["filter_background"],
                settings["background_sigma"],
            )
            self._plot2D.set_noise_filter(
                settings["filter_noise"],
                settings["noise_sigma"],
            )

    def _update_gui_1D(self):
        settings = self._1D_settings

        if self.gates is not None:
            enable = True
            if settings["gate_name"] not in self.gates.parameters:
                logging.warning(f'{settings["gate_name"]} not in DC gates')
                enable = False
            self._1D_set_DC.setEnabled(enable)

        npt = settings["npt"]
        t_meas = settings["t_meas"]
        line_margin = self._gen_settings["line_margin"]
        if settings["biasT_corr"]:
            t_bias_charging = t_meas
        else:
            # total time of a line divided by 4, because ramp consists of '2 triangles'.
            t_bias_charging = (npt + 2*line_margin) * t_meas * 0.25
        self._update_bias_T_message(t_bias_charging, settings["V_swing"])

    def _update_gui_2D(self):
        settings = self._2D_settings

        if self.gates is not None:
            enable = True
            for gate_name in ["gate1_name", "gate2_name"]:
                if settings[gate_name] not in self.gates.parameters:
                    logging.warning(f'{settings[gate_name]} not in DC gates')
                    enable = False
            self._2D_set_DC.setEnabled(enable)

        npt = settings["npt"]
        t_meas = settings["t_meas"]
        line_margin = self._gen_settings["line_margin"]
        if settings["biasT_corr"]:
            # total time of a line divided by 2, because prepulse distributes error
            t_bias_charging = (npt + 2*line_margin) * t_meas * 0.5
        else:
            t_bias_charging = (npt + 2*line_margin) * t_meas * npt

        self._update_bias_T_message(t_bias_charging, settings["V2_swing"])

    def _update_bias_T_message(self, t_bias_charging, v_swing):
        biasTrc = self._gen_settings["bias_T_RC"] * 1000  # microseconds
        biasTerror = t_bias_charging/biasTrc
        v_error = biasTerror * v_swing / 2

        # max error is on y-value / gate2 voltage
        self.bias_T_warning_label.setText(f'max bias T error: {biasTerror:3.1%}, {v_error:3.1f} mV')
        style = 'QLabel {background-color : #F64; }' if biasTerror > 0.05 else ''
        self.bias_T_warning_label.setStyleSheet(style)

    def _recompile_sequence(self, param) -> bool:
        recompile = getattr(param, "recompile", None)
        # Abstract methods have a property __isabstractmethod__ returning True
        if recompile and not getattr(recompile, "__isabstractmethod__", False):
            recompile()
            return True
        return False

    def _requires_build(self, param: FastScanParameterBase, settings: Settings):
        build = param is None or settings.update_scan

        if not build and self._pulselib_settings.has_changes():
            if not self._recompile_sequence(param):
                build = True
        return build

    def _prepare_scan(self):
        settings = self._gen_settings
        active_channel_map = {
            name: self.channel_map[name]
            for name in settings["enabled_channels"]
        }
        self._scan_generator.configure(
            acquisition_delay_ns=settings["acquisition_delay_ns"],
            enabled_markers=settings["enabled_markers"],
            line_margin=settings["line_margin"])
        self._scan_generator.set_iq_mode(self.iq_mode)
        self._scan_generator.set_channel_map(active_channel_map)

    def _prepare_1D_scan(self):
        gen_settings = self._gen_settings
        if gen_settings.update_scan:
            self._1D_settings.update_scan = True
            self._2D_settings.update_scan = True
            gen_settings.update_scan = False
        settings = self._1D_settings
        self._stop_other()

        if self._requires_build(self._param1D, settings):
            logger.debug('Creating 1D scan')
            self._prepare_scan()
            self._param1D = self._scan_generator.create_1D_scan(
                settings["gate_name"],
                settings["V_swing"],
                settings["npt"],
                settings["t_meas"]*1000,
                pulse_gates=settings["offsets"],
                biasT_corr=settings["biasT_corr"])
            self._plot1D = _1D_live_plot(
                self._1D_plotter_layout,
                self._param1D,
                gen_settings["n_columns"],
                self._1D_av_progress,
                gates=self.gates,
                gate_values_label=self.gate_values_label,
                on_mouse_moved=self._on_mouse_moved_1D,
                on_mouse_clicked=self._on_mouse_clicked_1D)
            self.update_plot_properties_1D()
            self._set_metadata(1)
            settings.update_scan = False
            self._pulselib_settings.store()
        else:
            self._param1D.restart()

        self._update_gui_1D()
        self.vm_data_param_1D = vm_data_param(self._param1D, self._plot1D, self.metadata)

    @qt_log_exception
    def _start_1D(self):
        if self.is_running == "1D":
            self._stop_1D()
        logger.info('Starting 1D')
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
        gen_settings = self._gen_settings
        if gen_settings.update_scan:
            self._1D_settings.update_scan = True
            self._2D_settings.update_scan = True
            gen_settings.update_scan = False
        settings = self._2D_settings
        self._stop_other()
        if self._requires_build(self._param2D, settings):
            logger.debug('Creating 2D scan')
            self._prepare_scan()
            self._param2D = self._scan_generator.create_2D_scan(
                settings["gate1_name"],
                settings["V1_swing"],
                settings["npt"],
                settings["gate2_name"],
                settings["V2_swing"],
                settings["npt"],
                settings["t_meas"]*1000,
                pulse_gates=settings["offsets"],
                biasT_corr=settings["biasT_corr"])
            self._plot2D = _2D_live_plot(
                self._2D_plotter_layout,
                self._param2D,
                gen_settings["n_columns"],
                self._2D_av_progress,
                gates=self.gates,
                gate_values_label=self.gate_values_label,
                on_mouse_moved=self._on_mouse_moved_2D,
                on_mouse_clicked=self._on_mouse_clicked_2D)
            self._plot2D.set_cross(settings["cross"])  # TODO make dynamic
            self._plot2D.set_colorbar(settings["colorbar"])  # TODO make dynamic
            self.update_plot_properties_2D()
            self._set_metadata(2)
            settings.update_scan = False
            self._pulselib_settings.store()
            logger.debug('Finished init currentplot and current_param')
        else:
            self._param2D.restart()

        self._update_gui_2D()
        self.vm_data_param_2D = vm_data_param(self._param2D, self._plot2D, self.metadata)

    @qt_log_exception
    def _start_2D(self):
        if self.is_running == "2D":
            self._stop_2D()
        logger.info('Starting 2D')
        try:
            self._2D_play.setEnabled(False)
            self._prepare_2D_scan()
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
        logger.info('Step 1D')
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
        logger.info('Step 2D')
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
        if self.tab_id == 0:  # 1D
            self._step_1D()
        elif self.tab_id == 1:  # 2D
            self._step_2D()

    def _update_active_state(self):
        """Updates the state after single step and checks
        whether recompile is required.
        """
        state = self.is_running
        if state == '1D' and not self._plot1D.active:
            self._stop_1D()
        elif state == '2D' and not self._plot2D.active:
            self._stop_2D()

        if (self._gen_settings["virtual_matrix_auto_recompile"]
                and self._pulselib_settings.has_changes()):
            state = self.is_running
            param = None
            if state == "1D":
                param = self._param1D
            elif state == "2D":
                param = self._param2D
            else:
                # not running
                pass
            if param:
                if self._recompile_sequence(param):
                    self._pulselib_settings.store()

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

    def _play(self):
        if self.tab_id == 0:  # 1D
            self._start_1D()
        elif self.tab_id == 1:  # 2D
            self.start_2D()

    def _reload(self):
        if self.tab_id == 0:  # 1D
            self.reload_1D()
        elif self.tab_id == 1:  # 2D
            self.reload_2D()

    @qt_log_exception
    def reload_1D(self):
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
        except Exception:
            logger.error('Update plot failed', exc_info=True)

    @qt_log_exception
    def reload_2D(self):
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
        except Exception:
            logger.error('Update plot failed', exc_info=True)

    @qt_log_exception
    def do_flip_axes(self):
        settings = self._2D_settings
        old_x_axis = settings["gate1_name"]
        old_y_axis = settings["gate2_name"]
        old_x_swing = settings["V1_swing"]
        old_y_swing = settings["V2_swing"]
        settings.set_value("gate1_name", old_y_axis)
        settings.set_value("gate2_name", old_x_axis)
        settings.set_value("V1_swing", old_y_swing)
        settings.set_value("V1_swing", old_x_swing)
        if self._run_state == "2D":
            self.update_plot_settings_2D()

    @qt_log_exception
    def tab_changed(self):
        self.stop()
        self.cursor_value_label.setText('')
        self.gate_values_label.setText('')
        max_swing = self._gen_settings["max_V_swing"]
        for v_spinner in [self._1D_V_swing, self._2D_V1_swing, self._2D_V2_swing]:
            v_spinner.setRange(-max_swing, max_swing)
        if self.tab_id == 3:  # favorites
            self._favorites._load_favorites()

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
            # TODO improve HVI2 scheduler. Make it a qcodes instrument
            from core_tools.HVI2.scheduler_hardware import default_scheduler_hardware
            default_scheduler_hardware.release_schedule()
        except Exception:
            pass

        if liveplotting.last_instance == self:
            liveplotting.last_instance = None
        try:
            liveplotting._all_instances.remove(self)
        except ValueError:
            logger.error("Oops! Error in liveplotting administration")
        logger.info('Window closed')

    def _set_metadata(self, dim: int):
        metadata = {}
        if dim == 1:
            metadata['measurement_type'] = '1D_scan'
            metadata.update(self._1D_settings.to_dict())
        elif dim == 2:
            metadata['measurement_type'] = '2D_scan'
            metadata.update(self._2D_settings.to_dict())
        metadata.update(self._gen_settings.to_dict())
        self.metadata = metadata

    @property
    def vm_data_param(self):
        if self.tab_id == 0:  # 1D
            return self.vm_data_param_1D
        if self.tab_id == 1:  # 2D
            return self.vm_data_param_2D
        return None

    @qt_log_exception
    def copy_ppt(self, inp_title=''):
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

        if self.tab_id == 0:  # 1D
            figure_hand = self._plot1D.plot_widgets[0].plot_widget.parent()
            settings = self._1D_settings
            gate_x = settings["gate_name"]
            range_x = settings["V_swing"]
            channels = ','.join(self._param1D.channel_names)
            title = f'{gate_x} ({range_x:.0f} mV), m:{channels}'
        elif self.tab_id == 1:  # 2D
            figure_hand = self._plot2D.plot_widgets[0].plot_widget.parent()
            settings = self._2D_settings
            gate_y = settings["gate2_name"]
            gate_x = settings["gate1_name"]
            range_y = settings["V2_swing"]
            range_x = settings["V1_swing"]
            channels = ','.join(self._param2D.channel_names)
            title = f'{inp_title} {gate_y} ({range_y:.0f} mV) vs. {gate_x} ({range_x:.0f} mV), m:{channels}'
        else:
            title = 'Oops, unknown tab'

        addPPTslide(title=title, fig=figure_hand, notes=str(notes), verbose=-1)

    @qt_log_exception
    def copy_to_clipboard(self):
        if self.vm_data_param is None:
            return
        if self.tab_id == 0:  # 1D
            frame = self._1D_plotter_frame
        elif self.tab_id == 1:  # 2D
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
        if self.tab_id == 0:  # 1D
            label = self._1D_settings["gate_name"]
        elif self.tab_id == 1:  # 2D
            settings = self._2D_settings
            label = settings["gate1_name"] + '_vs_' + settings["gate2_name"]
        else:
            raise Exception(f"Cannot save data from tab {self.tab_id}")

        update = {
            "average": self.vm_data_param.plot.average_scans,
            "differentiate":  self.vm_data_param.plot.gradient
        }
        self.metadata.update(update)
        self.vm_data_param.load_metadata(update)

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
            gate_name = self._1D_settings["gate_name"]
            vx = self._plot1D.gate_x_voltage + x
            self.gates.set(gate_name, vx)
            msg = (f'Set {gate_name}:{vx:6.3f} mV')
            print(msg)
            self.cursor_value_label.setText(msg)
            self._plot1D.clear_buffers()

    @qt_log_exception
    def _on_mouse_moved_1D(self, x, ch, v):
        dc_x = self._plot1D.gate_x_voltage
        if dc_x is not None:
            x_total = f' ({dc_x+x:7.2f})'
        else:
            x_total = ''
        gate_name = self._1D_settings["gate_name"]
        self.cursor_value_label.setText(
            f'{gate_name}:{x:7.2f}{x_total} mV, '
            f'{ch}:{v:7.2f} mV')

    @qt_log_exception
    def _on_mouse_clicked_2D(self, x, y):
        if self._2D_set_DC.isChecked():
            settings = self._2D_settings
            vx = self._plot2D.gate_x_voltage + x
            vy = self._plot2D.gate_y_voltage + y
            self.gates.set(settings["gate1_name"], vx)
            self.gates.set(settings["gate2_name"], vy)
            msg = (f'Set {settings["gate1_name"]}:{vx:6.3f} mV, '
                   f'{settings["gate2_name"]}:{vy:6.3f} mV')
            print(msg)
            self.cursor_value_label.setText(msg)
            self._plot2D.clear_buffers()

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
        settings = self._2D_settings
        self.cursor_value_label.setText(
            f'{settings["gate1_name"]}:{x:7.2f}{x_total} mV, '
            f'{settings["gate2_name"]}:{y:7.2f}{y_total} mV, '
            f'{ch}:{v:7.2f} mV')


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
