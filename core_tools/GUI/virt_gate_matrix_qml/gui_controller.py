from core_tools.GUI.virt_gate_matrix_qml.models import attenuation_model, table_header_model, vg_matrix_model
from core_tools.drivers.hardware.hardware import hardware

from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets, QtQml

import core_tools.GUI.virt_gate_matrix_qml  as qml_in
import os, sys

class GUI_controller:
    def __init__(self):
        super().__init__()
        # self.app =  QtGui.QGuiApplication(sys.argv)
        self.app = QtCore.QCoreApplication.instance()
        self.instance_ready = True
        if self.app is None:
            self.instance_ready = False
            self.app = QtWidgets.QApplication([])

        hw = hardware()
        self.engine = QtQml.QQmlApplicationEngine()

        self.attenuation_model = attenuation_model(hw.awg2dac_ratios)
        self.engine.rootContext().setContextProperty("attenuation_model", self.attenuation_model)
        
        if len(hw.virtual_gates) > 0:
            self.row_header_model = table_header_model(hw.virtual_gates[0].gates)
            self.column_header_model = table_header_model(hw.virtual_gates[0].v_gates)
            self.vg_matrix_model = vg_matrix_model(hw.virtual_gates[0])

            self.engine.rootContext().setContextProperty('row_header_model', self.row_header_model)
            self.engine.rootContext().setContextProperty('column_header_model', self.column_header_model)
            self.engine.rootContext().setContextProperty('vg_matrix_model', self.vg_matrix_model)
        # grab directory from the import!

        filename = os.path.join(qml_in.__file__[:-12], "virt_gate_matrix_gui.qml")
        self.engine.load(QtCore.QUrl.fromLocalFile(filename))
        self.win = self.engine.rootObjects()[0]

        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)

        if self.instance_ready == False:
            self.app.exec_()
            print('exec')
        

    def update_data(self):
        self.singal_hander.update_data()

    def set_data(self):
        '''just update all...'''
        self.singal_hander.set_data()


if __name__ == "__main__":
    import numpy as np


    from core_tools.data.SQL.connect import set_up_local_storage, set_up_remote_storage, set_up_local_and_remote_storage
    from core_tools.drivers.hardware.hardware import hardware
    set_up_local_storage('stephan', 'magicc', 'test', 'test_project1', 'test_set_up', 'test_sample')

    h = hardware()
    h.dac_to_gate = {
        # dacs for creating the quantum dots -- syntax, "gate name": (dac module number, dac index)
        'B0': (0, 1), 'P1': (0, 2), 
        'B1': (0, 3), 'P2': (0, 4),
        'B2': (0, 5), 'P3': (0, 6), 
        'B3': (0, 7), 'P4': (0, 8), 
        'B4': (0, 9), 'P5': (0, 10),
        'B5': (0, 11),'P6': (0, 12),
        'B6': (0, 13)}

    h.boudaries = {'B0' : (0, 2000), 'B1' : (0, 2500)}
    h.awg2dac_ratios.add(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'S6', 'SD1_P', 'SD2_P'])
    h.virtual_gates.add('test', ['B0', 'P1', 'B1', 'P2', 'B2', 'P3', 'B3', 'P4', 'B4', 'P5', 'B5', 'P6', 'B6', 'S6', 'SD1_P', 'SD2_P', 'COMP1', 'COMP2', 'COMP3'])
    
    a = np.array([[ 1.00000000e+00,  0.00000000e+00,  0.00000000e+00,0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00],
            [ 6.49707806e-02,  2.82481655e-01,  4.90827766e-02, 7.81982372e-02,  3.10296188e-02,  3.77927331e-02, 2.04070954e-02,  1.92595334e-02,  5.77896842e-03, 5.23641473e-03,  1.07451230e-03,  1.20437539e-03, 1.08393785e-04,  4.03374906e-01, -5.72633650e-18,-1.75608355e-18],
            [ 0.00000000e+00,  0.00000000e+00,  1.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00],
            [ 2.02412952e-02,  8.80056311e-02,  3.92602899e-02, 1.95568069e-01,  7.67383245e-02,  8.68695232e-02, 1.71876988e-02,  3.15420382e-02,  1.04634263e-02, 8.57586683e-03,  1.75976787e-03,  1.97244937e-03, 1.77520443e-04,  4.21638099e-01, -6.07292953e-18,-1.83177706e-18],
            [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  1.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00],
            [ 8.60939992e-03,  3.74321735e-02,  1.66989085e-02, 8.31826079e-02,  6.54671507e-02,  2.13066308e-01, 3.27095776e-02,  7.33179851e-02,  2.47674300e-02, 1.99341993e-02,  4.09049770e-03,  4.58486584e-03, 4.12637926e-04,  4.15726257e-01, -6.28931174e-18,-1.80691524e-18],
            [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 1.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00,  0.00000000e+00,  0.00000000e+00, 0.00000000e+00],
            [ 4.58831882e-03,  1.99492123e-02,  8.89956525e-03, 4.43315828e-02,  2.80054449e-02,  1.13552183e-01, 3.98079716e-02,  2.11194559e-01,  5.13356355e-02, 5.74210329e-02,  1.17827960e-02,  1.32068376e-02, 1.18861538e-03,  3.94736245e-01, -6.75019910e-18,-1.87957376e-18],
            [-1.13747604e-18, -2.83748185e-18, -7.02765838e-18,-4.57657416e-18, -4.04289212e-18,  2.25759347e-18, 6.47263042e-19,  9.97668597e-19,  1.00000000e+00, 1.73576902e-18,  3.49023532e-18,  1.32946821e-19, 7.14528222e-19, -5.41853938e-18, -1.12757026e-17, 7.80625564e-18],
            [ 2.21371708e-03,  9.62485689e-03,  4.29375560e-03, 2.13885709e-02,  1.35117315e-02,  5.47852965e-02, 1.92060731e-02,  1.01894620e-01,  7.54102430e-02, 1.96511948e-01,  4.03242517e-02,  4.51977480e-02, 4.06779732e-03,  4.11569391e-01, -8.93461466e-18,-3.14152001e-18],
            [-8.35738386e-19, -6.33704886e-19,  4.92852218e-18, 1.05218305e-18,  7.04962177e-19, -5.48017677e-18,-5.04760983e-18, -4.34445449e-18, -4.09613329e-18, 6.19746588e-18,  1.00000000e+00, -1.69256457e-18, 1.76562364e-18, -2.67784151e-17, -1.60461922e-17,-3.46944695e-18],
            [ 6.76113171e-04,  2.93962248e-03,  1.31139825e-03, 6.53249440e-03,  4.12675119e-03,  1.67325178e-02, 5.86591624e-03,  3.11206410e-02,  3.44094639e-02, 9.79442448e-02,  7.65184375e-02,  2.57611670e-01, 2.31850503e-02,  4.41025679e-01, -1.22523239e-17,-5.10733335e-18],
            [-2.36436087e-18, -5.90153867e-18, -1.45662517e-17,-9.52365278e-18, -8.66682292e-18,  4.83219219e-18,-1.51760539e-18, -6.44912262e-18, -1.31916453e-18,-6.73012624e-18, -1.09864362e-18, -4.47246990e-19, 1.00000000e+00, -2.79469603e-17, -2.34187669e-17,-2.60208521e-18],
            [-3.66373083e-17, -2.93006203e-17, -2.40292394e-17,-7.56924908e-17, -2.66398315e-17,  4.13863597e-17, 4.98254165e-18, -7.91675124e-18, -1.66866457e-16, 1.46595361e-16,  7.40710493e-16,  3.33829987e-17,-1.01078939e-16,  1.00000000e+00, -1.38777878e-17,-4.33680869e-18],
            [ 3.94710178e-02,  4.92640444e-02,  4.00235624e-03, 9.13044283e-03,  3.35657030e-03,  3.06239735e-03, 3.05006789e-03,  2.15866106e-03,  6.00781938e-04, 5.86911653e-04,  1.20434271e-04,  1.34989680e-04, 1.21490712e-05,  2.30623884e-01,  6.54425292e-01,-2.13653863e-18],
            [ 1.66746471e-04,  7.24984657e-04,  3.23423711e-04, 1.61107701e-03,  1.01776038e-03,  4.12665870e-03, 1.44668212e-03,  7.67513087e-03,  5.87574735e-03, 1.54538756e-02,  1.14956970e-02,  5.93898666e-02, 7.06073317e-02,  9.49489762e-02, -1.25916980e-17, 7.25136042e-01]])
    
    # h.virtual_gates.test.matrix = a #np.linalg.inv(a)


    g = GUI_controller()





    