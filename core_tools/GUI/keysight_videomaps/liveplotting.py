import qdarkstyle
import numpy as np
from functools import partial
import pyqtgraph as pg
from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.sweeps.sweeps import do0D
from core_tools.data.SQL.connect import sample_info

from dataclasses import dataclass
from PyQt5 import QtCore, QtWidgets
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Virtual
from core_tools.GUI.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot
from qcodes import MultiParameter
from qcodes.measure import Measure
from core_tools.utility.powerpoint import addPPTslide
import logging
from qtpy.QtCore import Signal, Slot

#TODO: Fix the measurement codes, to transpose the data properly (instead of fixing it in the plot)

@dataclass
class plot_content:
    _1D: _1D_live_plot
    _2D: _2D_live_plot

@dataclass
class param_getter:
    _1D: object()
    _2D: object()

class liveplotting(QtWidgets.QMainWindow, Ui_MainWindow):
    """
    Liveplotting designed for the V2 system.

    This is a quick implementation of VideoMode for the Keysight system including digitizer.
    To generate the GUI, QT designer is used. The code in the ui file is directly ported into python code.

    The code for this classes is multithreaded in order to make sure everything keeps smoots during aquisition of the data.
    """
    @property
    def tab_id(self):
        return self.tabWidget.currentIndex()

    # signal emitted on a mouse click in one of the plotting windows. signature: event, index if plot, handle to live_plot object
    signalPlotWindowMouseClicked = Signal(object, int, object)

    def __init__(self, pulse_lib, digitizer, scan_type = 'Virtual', cust_defaults = None,
                 iq_mode=None, channel_map=None):
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
                           'biasT_corr': bool,
                           'average': int,
                           'diff': bool}
                        2D = {'gate1_name': str,
                           'gate2_name': str,
                           'V1_swing': float,
                           'V2_swing': float,
                           'npt': int,
                           't_meas': float,
                           'biasT_corr': bool,
                           'average': int,
                           'gradient': str} # 'Off', 'Magnitude', or 'Mag & angle'
                        gen = {'ch1': bool,
                           'ch2': bool,
                           'ch3': bool,
                           'ch4': bool,
                           'sample_rate': float, # (currently only 100 or 500 allowed)
                           'dig_vmax: float, # allowed: 4.0, 2.0, 1.0, 0.5, 0.25, 0.125
                           'enabled_markers': list[str],
                           'n_columns': int,
                           'line_margin': int,
                           'bias_T_RC': float,
                           'acquisition_delay_ns': float, # Time in ns between AWG output change and digitizer acquisition start.
                           }
            iq_mode (str or dict): when digitizer is in MODE.IQ_DEMODULATION then this parameter specifies how the
                    complex I/Q value should be plotted: 'I', 'Q', 'abs', 'angle', 'angle_deg'. A string applies to
                    all channels. A dict can be used to specify selection per channel, e.g. {1:'abs', 2:'angle'}
            channel_map (Dict[str, Tuple(int, Callable[[np.ndarray], np.ndarray])]):
                defines new list of derived channels to display. Dictionary entries name: (channel_number, func).
                E.g. {(ch1-I':(1, np.real), 'ch1-Q':(1, np.imag), 'ch3-Amp':(3, np.abs), 'ch3-Phase':(3, np.angle)}
                The default channel_map is:
                    {'ch1':(1, np.real), 'ch2':(2, np.real), 'ch3':(3, np.real), 'ch4':(4, np.real)}
        '''
        logging.info('initialising vm')
        self.pulse_lib = pulse_lib
        self.digitizer = digitizer

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
        else:
            raise ValueError("Unsupported agrument for scan type.")
        self.current_plot = plot_content(None, None)
        self.current_param_getter = param_getter(None, None)
        instance_ready = True

        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self._init_channels(channel_map, iq_mode)
        self._init_markers(pulse_lib)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.start_1D.clicked.connect(self._1D_start_stop)
        self.start_2D.clicked.connect(self._2D_start_stop)
        self._1D_update_plot.clicked.connect(self.update_plot_settings_1D)
        self._2D_update_plot.clicked.connect(self.update_plot_settings_2D)
        self._flip_axes.clicked.connect(self.do_flip_axes)
        self.tabWidget.currentChanged.connect(self.tab_changed)

        self.init_defaults(pulse_lib.channels, cust_defaults)

        self._1D_save_data.clicked.connect(self.save_data)
        self._2D_save_data.clicked.connect(self.save_data)

        self._1D_ppt_save.clicked.connect(self.copy_ppt)
        self._2D_ppt_save.clicked.connect(self.copy_ppt)

        self.show()
        if instance_ready == False:
            self.app.exec()

    def _init_channels(self, channel_map, iq_mode):
        self.channel_map = (
                channel_map if channel_map is not None
                else {f'ch{i}':(i, np.real) for i in range(1,5)})

        # backwards compatibility with older iq_mode parameter
        iq_mode2numpy = {'I': np.real, 'Q': np.imag, 'abs': np.abs,
                    'angle': np.angle, 'angle_deg': lambda x:np.angle(x, deg=True)}
        if iq_mode is not None:
            if channel_map is not None:
                logging.warning('iq_mode is ignored when channel_map is also specified')
            elif isinstance(iq_mode, str):
                self.channel_map = {f'ch{i}':(i, iq_mode2numpy[iq_mode]) for i in range(1,5)}
            else:
                for ch, mode in iq_mode.items():
                    self.channel_map[f'ch{ch}'] = (ch, iq_mode2numpy[mode])

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

        # 1D defaults
        self.defaults_1D = {'gate_name': self._1D_gate_name.currentText(),
                           'V_swing': 50,
                           'npt': 200,
                           't_meas': 50,
                           'biasT_corr': False,
                           'average': 1,
                           'diff': False}

        # 2D defaults
        self.defaults_2D = {'gate1_name': self._2D_gate1_name.currentText(),
                           'gate2_name': self._2D_gate2_name.currentText(),
                           'V1_swing': 50,
                           'V2_swing': 50,
                           'npt': 75,
                           't_meas': 5,
                           'biasT_corr': True,
                           'average': 1,
                           'gradient': 'Off'}

        self.defaults_gen = {'sample_rate': 100,
                           'dig_vmax': 2.0,
                           'acquisition_delay_ns': 500,
                           'n_columns': 4,
                           'line_margin': 1,
                           'bias_T_RC': 100,
                           'enabled_markers': []}

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

        self._1D_average.valueChanged.connect(self.update_plot_properties_1D)
        self._1D_diff.stateChanged.connect(self.update_plot_properties_1D)

        self._2D_average.valueChanged.connect(self.update_plot_properties_2D)
        self._2D_gradient.currentTextChanged.connect(self.update_plot_properties_2D)
        self._2D_enh_contrast.stateChanged.connect(self.update_plot_properties_2D)

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
            self._gen_dig_vmax.setCurrentText(str(dig_vmax))

    def update_plot_properties_1D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differentation of data)
        '''
        if self.current_plot._1D  is not None:
            self.current_plot._1D.averaging = self._1D_average.value()
            self.current_plot._1D.differentiate = self._1D_diff.isChecked()

    def update_plot_properties_2D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/gradient of data)
        '''
        if self.current_plot._2D  is not None:
            self.current_plot._2D.averaging = self._2D_average.value()
            self.current_plot._2D.gradient = self._2D_gradient.currentText()
            self.current_plot._2D.enhanced_contrast = self._2D_enh_contrast.isChecked()

    def get_offsets(self, dimension='1D'):
        offsets = {}
        for i in range(1,4):
            gate = getattr(self, f'_{dimension}_offset{i}_name').currentText()
            voltage = getattr(self, f'_{dimension}_offset{i}_voltage').value()
            if gate != '<None>' and voltage != 0.0:
                offsets[gate] = voltage

        return offsets

    def get_plot_settings(self):
        '''
        write the values of the input into the the class
        '''
        self._1D__gate_name = self._1D_gate_name.currentText()
        self._1D__V_swing = self._1D_V_swing.value()
        self._1D__npt = self._1D_npt.value()
        self._1D__t_meas = self._1D_t_meas.value()
        self._1D__biasT_corr = self._1D_biasT_corr.isChecked()

        self._2D__gate1_name = self._2D_gate1_name.currentText()
        self._2D__gate2_name = self._2D_gate2_name.currentText()
        self._2D__V1_swing = self._2D_V1_swing.value()
        self._2D__V2_swing = self._2D_V2_swing.value()
        self._2D__npt = self._2D_npt.value()
        self._2D__t_meas = self._2D_t_meas.value()
        self._2D__biasT_corr = self._2D_biasT_corr.isChecked()

        self._gen__sample_rate = int(self._gen_sample_rate.currentText())*1e6
        self._channels = self.get_activated_channels()
        self._active_channel_map = {
                name:settings for name, settings in self.channel_map.items()
                if self.channel_check_boxes[name].isChecked()
                }
        self._gen__dig_vmax = float(self._gen_dig_vmax.currentText())
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

        biasTerror2D = t_bias_charging_2D/biasTrc
        # max error is on y-value / gate2 voltage
        self._2D_biasTwarning.setText(f'max bias T error: {biasTerror2D:3.1%}, {biasTerror2D*self._2D__V2_swing/2:3.1f} mV')
        style = 'QLabel {color : red; }' if biasTerror2D > 0.05 else ''
        self._2D_biasTwarning.setStyleSheet(style)

        if self._1D__biasT_corr:
            t_bias_charging_1D = self._1D__t_meas
        else:
            # total time of a line divided by 4, because ramp consists of '2 triangles'.
            t_bias_charging_1D = (self._1D__npt + 2*self._gen__line_margin) * self._1D__t_meas * 0.25

        biasTerror1D = t_bias_charging_1D/biasTrc
        self._1D_biasTwarning.setText(f'max bias T error: {biasTerror1D:3.1%}, {biasTerror1D*self._1D__V_swing/2:3.1f} mV')
        style = 'QLabel {color : red; }' if biasTerror1D > 0.05 else ''
        self._1D_biasTwarning.setStyleSheet(style)

    def _1D_start_stop(self):
        '''
        Starts/stops the data acquisition and plotting.
        '''
        if self.start_1D.text() == "Start":
            if self.current_plot._1D is None:
                logging.info('Creating 1D scan')
                try:
                    self.get_plot_settings()
                    self.start_1D.setEnabled(False)
                    self.current_param_getter._1D = self.construct_1D_scan_fast(
                            self._1D__gate_name, self._1D__V_swing, self._1D__npt, self._1D__t_meas*1000,
                            self._1D__biasT_corr, self.pulse_lib, self.digitizer, self._channels, self._gen__sample_rate,
                            dig_vmax=self._gen__dig_vmax, acquisition_delay_ns=self._gen__acquisition_delay_ns,
                            enabled_markers=self._gen__enabled_markers,
                            channel_map=self._active_channel_map,
                            pulse_gates=self._1D__offsets,
                            line_margin=self._gen__line_margin)
                    self.current_plot._1D = _1D_live_plot(
                            self.app, self._1D_plotter_frame, self._1D_plotter_layout, self.current_param_getter._1D,
                            self._1D_average.value(), self._1D_diff.isChecked(),
                            self._gen__n_columns)
                    self.start_1D.setEnabled(True)
                    self.set_metadata()
                    self.attach_mouse_click_callback(self.current_plot._1D )
                    logging.info('Finished init currentplot and current_param')
                except Exception as e:
                    logging.error(e, exc_info=True)
            else:
                self.current_param_getter._1D.restart()

            self.vm_data_param = vm_data_param(self.current_param_getter._1D, self.current_plot._1D, self.metadata)
            self.start_1D.setText("Stop")
            self.current_plot._1D.start()

        elif self.start_1D.text() == "Stop":
            self.current_plot._1D.stop()
            self.start_1D.setText("Start")

    @Slot(object, int, object)
    def _signalPlotWindowMouseClicked(self, event, plot_index, live_plot_object):
        self.signalPlotWindowMouseClicked.emit(event, plot_index, live_plot_object)
        
    def attach_mouse_click_callback(self, plot_handle ):
        for plot_index, pd in enumerate(plot_handle.plot_widgets):
            pw = pd.plot_widget
            img=pd.plot_items[0]
            print(f'attach_mouse_click_callback: plot {plot_handle} widget {plot_index}')
                       
            pw.scene().sigMouseClicked.connect(partial(self._signalPlotWindowMouseClicked, plot_index=plot_index, live_plot_object = plot_handle))
        
    def _2D_start_stop(self):
        '''
        Starts/stops the data acquisition and plotting.
        '''
        if self.start_2D.text() == "Start":
            logging.info('Starting 2D')
            if self.current_plot._2D is None:
                logging.info('Creating 2D scan')
                self.get_plot_settings()
                self.start_2D.setEnabled(False)
                try:
                    self.current_param_getter._2D = self.construct_2D_scan_fast(
                            self._2D__gate1_name, self._2D__V1_swing, int(self._2D__npt),
                            self._2D__gate2_name, self._2D__V2_swing, int(self._2D__npt),
                            self._2D__t_meas*1000, self._2D__biasT_corr,
                            self.pulse_lib, self.digitizer, self._channels, self._gen__sample_rate,
                            dig_vmax=self._gen__dig_vmax,
                            acquisition_delay_ns=self._gen__acquisition_delay_ns,
                            enabled_markers=self._gen__enabled_markers,
                            channel_map=self._active_channel_map,
                            pulse_gates=self._2D__offsets,
                            line_margin=self._gen__line_margin,
                            )
                    logging.info('Finished Param, now plot')
                    self.current_plot._2D = _2D_live_plot(
                            self, self._2D_plotter_frame, self._2D_plotter_layout, self.current_param_getter._2D,
                            self._2D_average.value(), self._2D_gradient.currentText(), self._gen__n_columns,
                            self._2D_av_progress)
                    self.current_plot._2D.enhanced_contrast = self._2D_enh_contrast.isChecked()
                    self.start_2D.setEnabled(True)
                    self.set_metadata()                    
                    self.attach_mouse_click_callback(self.current_plot._2D )                    
                    logging.info('Finished init currentplot and current_param')
                except Exception as e:
                    logging.error(e, exc_info=True)
            else:
                self.current_param_getter._2D.restart()

            logging.info('Defining vm_data_param')
            self.vm_data_param = vm_data_param(self.current_param_getter._2D, self.current_plot._2D, self.metadata)

            self.start_2D.setText("Stop")
            logging.info('Starting the plot')
            self.current_plot._2D.start()

        elif self.start_2D.text() == "Stop":
            logging.info('Stopping 2D')
            self.current_plot._2D.stop()
            self.start_2D.setText("Start")


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
            logging.error('Update plot failed', exc_info=True)

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
            logging.error('Update plot failed', exc_info=True)

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

    def tab_changed(self):
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.start_1D.setText("Start")

        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.start_2D.setText("Start")

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
        logging.info('Window closed')


    def get_activated_channels(self):
        channels = set()
        for name, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channel_nr = self.channel_map[name][0]
                channels.add(channel_nr)
        return list(channels)

    def set_metadata(self):
        metadata = {}
        if self.tab_id == 0: # 1D
            metadata['measurement_type'] = '1D_sweep'
            for key in self.defaults_1D.keys():
                metadata[key] = getattr(self,f'_1D__{key}')
        elif self.tab_id == 1: # 2D
            metadata['measurement_type'] = '2D_sweep'
            for key in self.defaults_2D.keys():
                metadata['measurement_type'] = '2D_sweep'
                metadata[key] = getattr(self,f'_2D__{key}')

        for key in self.defaults_gen.keys():
            metadata[key] = getattr(self,f'_gen__{key}')

        self.metadata = metadata

    def copy_ppt(self):
        """
        ppt the data
        """
        if self.tab_id == 0: # 1D
            figure_hand = self.current_plot._1D.plot_widgets[0].plot_widget.parent()
        elif self.tab_id == 1: # 2D
            figure_hand = self.current_plot._2D.plot_widgets[0].plot_widget.parent()

        try:
            ds = self.save_data()
            self.metadata['dataset_id'] = ds.exp_id
            self.metadata['dataset_uuid'] = ds.exp_uuid
            addPPTslide(fig=figure_hand, notes=str(self.metadata), verbose=-1)
        except:
            print('could not add slide')
            pass


    def save_data(self):
        """
        save the data
        """
        if self.tab_id == 0: # 1D
            label = self._1D__gate_name
        elif self.tab_id == 1: # 2D
            label = self._2D__gate1_name + '_vs_' + self._2D__gate2_name

        is_ds_configured = False
        try:
            is_ds_configured = isinstance(sample_info.project, str)
        except: pass

        try:
            if is_ds_configured:
                logging.info('Save')
                job = do0D(self.vm_data_param, name=label)
                ds = job.run()
                return ds
            else:
                # use qcodes measurement
                measure = Measure(self.vm_data_param)
                data = measure.get_data_set(location=None,
                                            loc_record={
                                            'name': 'vm_data',
                                            'label': label})
                data = measure.run(quiet=True)
                data.finalize()
        except:
            logging.error(f'Error during save data', exc_info=True)

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