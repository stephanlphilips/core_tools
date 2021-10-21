from core_tools.GUI.parameter_viewer_qml.model import gate_model
from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets, QtQml

import core_tools.GUI.parameter_viewer_qml as qml_in
import os, sys

from functools import partial
import qcodes as qc

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Material'

class param_viewer:
    def __init__(self, gates=None, allow_mouse_wheel_updates : bool = True):
        """ Parameter viewer for gates

        Args:
            gates: Gate instrument to use. If None, use qcodes.Station.default.gates
            allow_mouse_wheel_updates: If True, then allow changing parameter values using mouse scrolling
        """
        super().__init__()
        self.app = QtCore.QCoreApplication.instance()
        self.instance_ready = True

        if self.app is None:
            self.instance_ready = False
            self.app = QtWidgets.QApplication([])

        self.engine = QtQml.QQmlApplicationEngine()

        if gates is None:
            if hasattr(qc.Station.default, 'gates'):
                gates = qc.Station.default.gates
            else:
                raise ValueError('No gates Instrument found in the station, pleasse add manually.')

        self.real_gate_model = gate_model(gates, list(gates.hardware.dac_gate_map.keys()), allow_mouse_wheel_updates = allow_mouse_wheel_updates)
        self.engine.rootContext().setContextProperty("real_gate_model", self.real_gate_model)

        v_gates = list()
        for i in gates.v_gates.values():
            v_gates += i

        self.virtual_gate_model = gate_model(gates, v_gates, allow_mouse_wheel_updates = allow_mouse_wheel_updates)
        self.engine.rootContext().setContextProperty("virtual_gate_model", self.virtual_gate_model)

        self.engine.rootContext().setContextProperty("param_viewer", self)


        filename = os.path.join(qml_in.__file__[:-12], "param_viewer.qml")
        self.engine.load(QtCore.QUrl.fromLocalFile(filename))
        self.win = self.engine.rootObjects()[0]

        self.timer_real = QtCore.QTimer()
        self.timer_real.timeout.connect(self.real_gate_model.update_model)
        self.timer_real.start(500)
        self.timer_virt = QtCore.QTimer()
        self.timer_virt.timeout.connect(self.virtual_gate_model.update_model)
        self.timer_virt.start(500)

        if self.instance_ready == False:
            self.app.exec_()
            print('exec')

if __name__ == "__main__":
    import numpy as np


    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    from core_tools.drivers.hardware.hardware import hardware
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')

    from core_tools.drivers.virtual_dac import virtual_dac
    from core_tools.drivers.gates import gates
    import qcodes as qc

    my_dac_1 = virtual_dac("dac_a", "virtual")
    my_dac_2 = virtual_dac("dac_b", "virtual")
    my_dac_3 = virtual_dac("dac_c", "virtual")
    my_dac_4 = virtual_dac("dac_d", "virtual")


    h = hardware()
    h.dac_gate_map = {
        'B0': (0, 1), 'P1': (0, 2), 
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6), 
        'B3': (0, 7), 'P4': (0, 8), 
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13), 'S6' : (0,14,),
        'SD1_P': (1, 1), 'SD2_P': (1, 2), 
        'SD1_B1': (1, 3), 'SD2_B1': (1, 4),
        'SD1_B2': (1, 5), 'SD2_B2': (1, 6),}

    h.boundaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    h.awg2dac_ratios.add(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'S6', 'SD1_P', 'SD2_P'])
    h.virtual_gates.add('test', ['B0', 'P1', 'B1', 'P2', 'B2', 'P3', 'B3', 'P4', 'B4', 'P5', 'B5', 'P6', 'B6', 'S6', 'SD1_P', 'SD2_P', 'COMP1', 'COMP2', 'COMP3'])


    my_gates = gates("gates", h, [my_dac_1, my_dac_2, my_dac_3, my_dac_4])
    station=qc.Station(my_gates)

    # print(station.gates.hardware.dac_gate_map.keys())
    param_viewer()



    