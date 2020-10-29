import sys
import qdarkstyle
import numpy as np
import threading as th
import pyqtgraph as pg
from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.sweeps.sweeps import do0D, do1D, do2D

from dataclasses import dataclass
from PyQt5.QtCore import QThread
from PyQt5 import QtCore, QtGui, QtWidgets
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Keysight
from core_tools.GUI.keysight_videomaps.data_getter import scan_generator_Virtual
from core_tools.GUI.keysight_videomaps.plotter.plotting_functions import _1D_live_plot, _2D_live_plot
from qcodes import MultiParameter
from qcodes.measure import Measure
from core_tools.utility.powerpoint import addPPTslide
import time
import logging

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

    def __init__(self, pulse_lib, digitizer, scan_type = 'Virtual'):
        '''
        init of the class

        Args:
            pulse_lib (pulselib) : provide the pulse library object. This is used to generate the sequences.
            digitizer (QCodes Instrument) : provide the digitizer driver of the card. In this case the one put in V2 software.
            scan_type (str) : type of the scan, will point towards a certain driver for getting the data (e.g. 'Virtual', 'Keysight')
        '''
        # super(QThread, self).__init__()
        logging.info('initialising vm')
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
#        self._1D_update_plot.setEnabled(False)
        self._2D_update_plot.clicked.connect(self.update_plot_settings_2D)
#        self._2D_update_plot.setEnabled(False)
        self.tabWidget.currentChanged.connect(self.tab_changed)
        self.init_defaults(pulse_lib.channels)

        self._1D_save_data.clicked.connect(self.save_data)
        self._1Dm_save_data.clicked.connect(self.save_data)
        self._2D_save_data.clicked.connect(self.save_data)

        self._1D_ppt_save.clicked.connect(self.copy_ppt)
        self._1Dm_ppt_save.clicked.connect(self.copy_ppt)
        self._2D_ppt_save.clicked.connect(self.copy_ppt)

        self.quit = QtWidgets.QAction("Quit", self)
        self.quit.triggered.connect(self.closeEvent)

        self.show()
        if instance_ready == False:
            self.app.exec()

    def init_defaults(self, gates):
        '''
        inititialize defaults for the 1D plot. Also configure listeners to check when values are changed.

        Args:
            gates (list<str>) : names of the gates that are available in the AWG.
        '''
        for i in sorted(gates, key=str.lower):
            self._1D_gate_name.addItem(str(i))
            self._2D_gate1_name.addItem(str(i))
            self._2D_gate2_name.addItem(str(i))

        # 1D stuff
        self._1D__gate = self._1D_gate_name.currentText()
        self._1D__vswing = 50
        self._1D__npt = 200
        self._1D__t_meas = 50
        self._1D__biasT_corr = False

        self._1D_V_swing.setValue(self._1D__vswing)
        self._1D_npt.setValue(self._1D__npt)
        self._1D_t_meas.setValue(self._1D__t_meas)


        self._1D__averaging = 1
        self._1D__differentiate = False

        self._1D_average.setValue(self._1D__averaging)
        self._1D_average.valueChanged.connect(self.update_plot_properties_1D)
        self._1D_diff.stateChanged.connect(self.update_plot_properties_1D)

        # 2D stuff
        self._2D__gate1_name =  self._2D_gate1_name.currentText()
        self._2D__gate2_name =  self._2D_gate2_name.currentText()
        self._2D__V1_swing = 25
        self._2D__V2_swing = 25
        self._2D__npt = 75
        self._2D__t_meas = 5
        self._2D__biasT_corr = False

        self._2D_gate1_name.setCurrentText(self._2D__gate1_name)
        self._2D_gate2_name.setCurrentText(self._2D__gate2_name)
        self._2D_V1_swing.setValue(self._2D__V1_swing)
        self._2D_V2_swing.setValue(self._2D__V2_swing)
        self._2D_npt.setValue(self._2D__npt)
        self._2D_t_meas.setValue(self._2D__t_meas)


        self._2D__averaging = 1
        self._2D__differentiate = False

        self._2D_average.setValue(self._1D__averaging)
        self._2D_average.valueChanged.connect(self.update_plot_properties_2D)
        self._2D_diff.stateChanged.connect(self.update_plot_properties_2D)

        self._sample_rate_val = 100
        self._ch1_val = True
        self._ch2_val = True
        self._ch3_val = False
        self._ch4_val = False

        self._channels = self.get_activated_channels()

        self._sample_rate.setCurrentText(str(self._sample_rate_val)) # Update later to setValue on a universal box
        self._ch1.setChecked(self._ch1_val)
        self._ch2.setChecked(self._ch2_val)
        self._ch3.setChecked(self._ch3_val)
        self._ch4.setChecked(self._ch4_val)


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

        self._sample_rate_val = int(self._sample_rate.currentText())*1e6
        self._ch1_val = self._ch1.isChecked()
        self._ch2_val = self._ch2.isChecked()
        self._ch3_val = self._ch3.isChecked()
        self._ch4_val = self._ch4.isChecked()
        self._channels = self.get_activated_channels()

    def _1D_start_stop(self):
        '''
        define behevior when pressing start/stop
        '''
        if self.start_1D.text() == "Start":
            if self.current_plot._1D is None:
                self.get_plot_settings()
                self.start_1D.setEnabled(False)
                self.current_param_getter._1D = self.construct_1D_scan_fast(self._1D__gate, self._1D__vswing, self._1D__npt, self._1D__t_meas*1000, self._1D__biasT_corr, self.pulse_lib, self.digitizer, self._channels, self._sample_rate_val)
                self.current_plot._1D = _1D_live_plot(self.app, self._1D_plotter_frame, self._1D_plotter_layout, self.current_param_getter._1D, self._1D_average.value(), self._1D_diff.isChecked())
                self.start_1D.setEnabled(True)
                self.set_metadata()

            self.vm_data_param = vm_data_param(self.current_param_getter._1D, self.current_plot._1D, self.metadata)
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
            logging.info('Starting 2D')
            if self.current_plot._2D is None:
                logging.info('Current plot is None')
                self.get_plot_settings()
                self.start_2D.setEnabled(False)
                try:
                    self.current_param_getter._2D = self.construct_2D_scan_fast(self._2D__gate1_name, self._2D__V1_swing, int(self._2D__npt),
                                    self._2D__gate2_name, self._2D__V2_swing, int(self._2D__npt),
                                    self._2D__t_meas*1000, self._2D__biasT_corr,
                                    self.pulse_lib, self.digitizer, self._channels, self._sample_rate_val)
                except Exception as e:
                    print(e)
                try:
                    self.current_plot._2D = _2D_live_plot(self.app, self._2D_plotter_frame, self._2D_plotter_layout, self.current_param_getter._2D, self._2D_average.value(), self._2D_diff.isChecked())
                except Exception as e:
                    print(e)
                self.start_2D.setEnabled(True)
                self.set_metadata()
                logging.info('Finished init currentplot and current_param')
                time.sleep(0.5)

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
        if self.current_plot._1D is not None:
            self.current_plot._1D.stop()
            self.current_plot._1D.remove()
            self.current_plot._1D = None
            self.current_param_getter._1D.stop()
            self.current_param_getter._1D = None


#        self._1D_update_plot.setEnabled(False)
        self.start_1D.setText("Start")
        self._1D_start_stop()

    def update_plot_settings_2D(self):
        '''
        update settings of the plot -- e.g. switch gate, things that require a re-upload of the data. ~
        '''
        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            time.sleep(0.5)
            self.current_plot._2D.remove()
            self.current_plot._2D = None
            self.current_param_getter._2D.stop()
            self.current_param_getter._2D = None


#        self._2D_update_plot.setEnabled(False)
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
            self.current_param_getter._1D.stop()
            self.current_param_getter._1D = None

        if self.current_plot._2D is not None:
            self.current_plot._2D.stop()
            self.current_plot._2D.remove()
            self.current_plot._2D = None
            self.current_param_getter._2D.stop()
            self.current_param_getter._2D = None

    def get_activated_channels(self):
        channels = []
        for channel in range(1,5):
            if getattr(self, '_ch%i_val' % channel):
                channels.append(channel)
        return channels

    def set_metadata(self):
        metadata = {}
        if self.tab_id == 0 or self.tab_id == 1: # 1D
            metadata['measurement_type'] = '1D_sweep'
            metadata['gate'] = self._1D__gate
            metadata['Vswing'] = self._1D__vswing
            metadata['Npt'] = self._1D__npt
            metadata['t_meas'] = self._1D__t_meas
            metadata['biasT_corr'] = self._1D__biasT_corr
            metadata['averaging'] = self._1D__averaging
            metadata['differentiate'] = self._1D__differentiate
        elif self.tab_id == 2: # 2D
            metadata['measurement_type'] = '2D_sweep'
            metadata['gate_x'] = self._2D__gate1_name
            metadata['Vswing_x'] = self._2D__V1_swing
            metadata['gate_y'] = self._2D__gate2_name
            metadata['Vswing_y'] = self._2D__V2_swing
            metadata['Npt'] = self._2D__npt
            metadata['t_meas'] = self._2D__t_meas
            metadata['biasT_corr'] = self._2D__biasT_corr
            metadata['averaging'] = self._2D__averaging
            metadata['differentiate'] = self._2D__differentiate
        self.metadata = metadata

    def copy_ppt(self):
        """
        ppt the data
        """
        if self.tab_id == 0 or self.tab_id == 1: # 1D
            figure_hand = self.current_plot._1D.plot_widgets[0].plot_widget.parent()
        elif self.tab_id == 2: # 2D
            figure_hand = self.current_plot._2D.plot_widgets[0].plot_widget.parent()

        try:
            addPPTslide(fig=figure_hand, notes=str(self.metadata), verbose=-1)
        except:
            print('could not add slide')
            pass


    def save_data(self):
        """
        save the data
        """
        print('saving data')
        if self.tab_id == 0 or self.tab_id == 1: # 1D
            label = self._1D__gate
        elif self.tab_id == 2: # 2D
            label = self._2D__gate1_name + 'vs' + self._2D__gate2_name
        try:
            measure = Measure(self.vm_data_param)
            data = measure.get_data_set(location=None,
                                        loc_record={
                                        'name': 'vm_data',
                                        'label': label})
            data = measure.run(quiet=True)
            data.finalize()
            print(data)
            do0D(self.vm_data_param).run()
        except Exception as e:
            print(e)
        print('done')

class vm_data_param(MultiParameter):
    def __init__(self, param, plot, metadata):
        param = param
        shapes = param.shapes
        labels = param.labels
        units = param.units
        setpoints = param.setpoints
        setpoint_names = param.setpoint_names
        setpoint_units = param.setpoint_units

        self.plot = plot
        super().__init__(name='vm_data_parameter',instrument=None,names=param.names, labels=labels, units=units,
             shapes=shapes, setpoints=setpoints, setpoint_names = setpoint_names,
             setpoint_units = setpoint_units, metadata=metadata)

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