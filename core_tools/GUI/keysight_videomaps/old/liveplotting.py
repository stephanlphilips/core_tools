import sys
import qdarkstyle
import numpy as np
import threading as th
import pyqtgraph as pg
import projects.keysight_videomaps.GUI.videomode_gui

from dataclasses import dataclass
from PyQt5.QtCore import QThread
from PyQt5 import QtCore, QtGui, QtWidgets
import projects.keysight_videomaps.data_getter.scan_generator_Keysight as scan_generator_Keysight
import projects.keysight_videomaps.data_getter.scan_generator_Virtual as scan_generator_Virtual
from projects.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot

@dataclass
class plot_content:
    _1D: _1D_live_plot
    _2D: _2D_live_plot

@dataclass
class param_getter:
    _1D: object()
    _2D: object()

class liveplotting(QtWidgets.QMainWindow, projects.keysight_videomaps.GUI.videomode_gui.Ui_MainWindow):
    """
    Liveplotting designed for the V2 system.

    This is a quick implementation of VideoMode for the Keysight system including digitizer.
    To generate the GUI, QT designer is used. The code in the ui file is directly ported into python code.

    The code for this classes is multithreaded in order to make sure everything keeps smoots during aquisition of the data.
    """
    def __init__(self, pulse_lib, digitizer, scan_type = 'Virtual'):
        '''
        init of the class

        Args:
            pulse_lib (pulselib) : provide the pulse library object. This is used to generate the sequences.
            digitizer (QCodes Instrument) : provide the digitizer driver of the card. In this case the one put in V2 software.
            scan_type (str) : type of the scan, will point towards a certain driver for getting the data (e.g. 'Virtual', 'Keysight')
        '''
        # super(QThread, self).__init__()

        self.pulse_lib = pulse_lib
        self.digitizer = digitizer
        
        if scan_type == 'Virtual':
            self.construct_1D_scan_fast = scan_generator_Virtual.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Virtual.construct_2D_scan_fast
        elif scan_type == "Keysight":
            self.construct_1D_scan_fast = scan_generator_Keysight.construct_1D_scan_fast
            self.construct_2D_scan_fast = scan_generator_Keysight.construct_2D_scan_fast
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

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.start_1D.clicked.connect(self._1D_start_stop)
        self.start_2D.clicked.connect(self._2D_start_stop)
        self._1D_update_plot.clicked.connect(self.update_plot_settings_1D)
        self._1D_update_plot.setEnabled(False)
        self._2D_update_plot.clicked.connect(self.update_plot_settings_2D)
        self._2D_update_plot.setEnabled(False)
        self.tabWidget.currentChanged.connect(self.tab_changed)
        self.init_defaults(pulse_lib.channels)

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(self.closeEvent)

        self.show()
        if instance_ready == False:
            self.app.exec()

    def init_defaults(self, gates):
        '''
        inititialize defaults for the 1D plot. Also configure listeners to check when values are changed.

        Args:
            gates (list<str>) : names of the gates that are available in the AWG.
        '''
        for i in gates:
            self._1D_gate_name.addItem(str(i))
            self._2D_gate1_name.addItem(str(i))
            self._2D_gate2_name.addItem(str(i))

        # 1D stuff
        self._1D__gate = self._1D_gate_name.currentText()
        self._1D__vswing = 50
        self._1D__npt = 200
        self._1D__t_meas = 10
        self._1D__biasT_corr = False

        self._1D_V_swing.setValue(self._1D__vswing)
        self._1D_npt.setValue(self._1D__npt)
        self._1D_t_meas.setValue(self._1D__t_meas)

        self._1D_gate_name.currentIndexChanged.connect(self.settings_value_change_1D)
        self._1D_V_swing.valueChanged.connect(self.settings_value_change_1D)
        self._1D_npt.valueChanged.connect(self.settings_value_change_1D)
        self._1D_t_meas.valueChanged.connect(self.settings_value_change_1D)
        self._1D_biasT_corr.stateChanged.connect(self.settings_value_change_1D)

        self._1D__averaging = 1
        self._1D__differentiate = False
        self._1D__channels = [1,2]
        
        self._1D_average.setValue(self._1D__averaging)
        self._1D_average.valueChanged.connect(self.update_plot_properties_1D)
        self._1D_diff.stateChanged.connect(self.update_plot_properties_1D)

        # 2D stuff
        self._2D__gate1_name =  self._2D_gate1_name.currentText()
        self._2D__gate2_name =  self._2D_gate2_name.currentText()
        self._2D__V1_swing = 50
        self._2D__V2_swing = 50
        self._2D__npt = 75
        self._2D__t_meas = 10
        self._2D__biasT_corr = False

        self._2D_V1_swing.setValue(self._2D__V1_swing)
        self._2D_V2_swing.setValue(self._2D__V2_swing)
        self._2D_npt.setValue(self._2D__npt)
        self._2D_t_meas.setValue(self._2D__t_meas)

        self._2D_gate1_name.currentIndexChanged.connect(self.settings_value_change_2D)
        self._2D_gate2_name.currentIndexChanged.connect(self.settings_value_change_2D)
        self._2D_V1_swing.valueChanged.connect(self.settings_value_change_2D)
        self._2D_V2_swing.valueChanged.connect(self.settings_value_change_2D)
        self._2D_npt.valueChanged.connect(self.settings_value_change_2D)
        self._2D_t_meas.valueChanged.connect(self.settings_value_change_2D)
        self._2D_biasT_corr.stateChanged.connect(self.settings_value_change_2D)

        self._2D__averaging = 1
        self._2D__differentiate = False

        self._2D_average.setValue(self._1D__averaging)
        self._2D_average.valueChanged.connect(self.update_plot_properties_2D)
        self._2D_diff.stateChanged.connect(self.update_plot_properties_2D)


    def update_plot_properties_1D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differntation of data)
        '''
        self.averaging = self._1D_average.value()
        self.differentiate = self._1D_diff.isChecked()
        if self.current_plot._1D  is not None:
            self.current_plot._1D.averaging = self.averaging
            self.current_plot._1D.differentiate = self.differentiate

    def update_plot_properties_2D(self):
        '''
        update properties in the liveplot without reloading the sequences (e.g. averaging/differntation of data)
        '''
        self.averaging = self._2D_average.value()
        self.differentiate = self._2D_diff.isChecked()
        if self.current_plot._2D  is not None:
            self.current_plot._2D.averaging = self.averaging
            self.current_plot._2D.differentiate = self.differentiate

    def settings_value_change_1D(self):
        '''
        make sure you cannot click on the setting bottom when it is not needed
        '''
        # get is there is a difference with the current values.
        if self.current_plot._1D is not None:
            self._1D_update_plot.setEnabled(True)

    def settings_value_change_2D(self):
        '''
        make sure you cannot click on the setting bottom when it is not needed
        '''
        # get is there is a difference with the current values.
        if self.current_plot._2D is not None:
            self._2D_update_plot.setEnabled(True)


    def get_plot_settings(self):
        '''
        write the values of the input into the the class
        '''
        self._1D__gate = self._1D_gate_name.currentText()
        self._1D__vswing = self._1D_V_swing.value()
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

    def _1D_start_stop(self):
        '''
        define behevior when pressing start/stop
        '''
        if self.start_1D.text() == "Start":
            if self.current_plot._1D is None:
                self.get_plot_settings()
                self.start_1D.setEnabled(False)
                self.current_param_getter._1D = self.construct_1D_scan_fast(self._1D__gate, self._1D__vswing, self._1D__npt, self._1D__t_meas*1000, self._1D__biasT_corr, self.pulse_lib, self.digitizer, channels = [1,2,3,4])
                self.current_plot._1D = _1D_live_plot(self.app, self._1D_plotter_frame, self._1D_plotter_layout, self.current_param_getter._1D, self._1D__averaging, self._1D__differentiate)
                self.start_1D.setEnabled(True)

            self.start_1D.setText("Stop")
            self.current_plot._1D.start()

        elif self.start_1D.text() == "Stop":
            self.current_plot._1D.stop()
            self.start_1D.setText("Start")

    def _2D_start_stop(self):
        '''
        define behevior when pressing start/stop
        '''
        if self.start_2D.text() == "Start":
            if self.current_plot._2D is None:
                self.get_plot_settings()
                self.start_2D.setEnabled(False)
                self.current_param_getter._2D = self.construct_2D_scan_fast(self._2D__gate1_name, self._2D__V1_swing, int(self._2D__npt),
                                    self._2D__gate2_name, self._2D__V2_swing, int(self._2D__npt),
                                    self._2D__t_meas*1000, self._2D__biasT_corr,
                                    self.pulse_lib, self.digitizer, channels = [1,2,3,4])
                self.current_plot._2D = _2D_live_plot(self.app, self._2D_plotter_frame, self._2D_plotter_layout, self.current_param_getter._2D, self._2D__averaging, self._2D__differentiate)
                self.start_2D.setEnabled(True)

            self.start_2D.setText("Stop")
            self.current_plot._2D.start()
            print('Plot started!')

        elif self.start_2D.text() == "Stop":
            self.current_plot._2D.stop()
            self.start_2D.setText("Start")


    def update_plot_settings_1D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data. 
        '''
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.current_plot._1D.remove()
            self.current_plot._1D = None
            self.current_param_getter._1D = None


        self._1D_update_plot.setEnabled(False)
        self.start_1D.setText("Start")
        self._1D_start_stop()

    def update_plot_settings_2D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data. 
        '''
        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.current_plot._2D.remove()
            self.current_plot._2D = None
            self.current_param_getter._2D = None


        self._2D_update_plot.setEnabled(False)
        self.start_2D.setText("Start")
        self._2D_start_stop()

    def tab_changed(self):
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.start_1D.setText("Start")

        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.start_2D.setText("Start")

        # tab_name = self.tabWidget.tabText(self.tabWidget.currentIndex())
        # if tab_name == "1D" and self.current_plot._1D is not None:
        #     print("wanting to start the plot")
        #     self._1D_start_stop()
        # elif tab_name == "2D" and self.current_plot._2D is not None:
        #     self._2D_start_stop()

    def closeEvent(self, event):
        """
        overload the close funtion. Make sure that all references in memory are fully gone,
        so the memory on the AWG is properly released.
        """
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.current_plot._1D.remove()
            self.current_plot._1D = None
            self.current_param_getter._1D = None

        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.current_plot._2D.remove()
            self.current_plot._2D = None
            self.current_param_getter._2D = None


if __name__ == '__main__':
    # class test(object):
    #     """docstring for test"""
    #     def __init__(self, arg):
    #         super(test, self).__init__()
    #         self.channels = arg
    
    # from V2_software.LivePlotting.data_getter.scan_generator_Virtual import construct_1D_scan_fast, construct_2D_scan_fast, fake_digitizer
    
    # dig = fake_digitizer("fake_digitizer")
    # t= test(['P1','P2', 'P3', 'P4'])

    # V2_liveplotting(t,dig)

    from V2_software.LivePlotting.data_getter.scan_generator_Virtual import construct_1D_scan_fast, construct_2D_scan_fast, fake_digitizer
    from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib

    # load a virtual version of the digitizer.
    dig = fake_digitizer("fake_digitizer")

    # load the AWG library (without loading the awg's) 
    pulse, _ = return_pulse_lib()

    V2_liveplotting(pulse,dig)