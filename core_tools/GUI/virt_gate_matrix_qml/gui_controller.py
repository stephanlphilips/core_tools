from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets, QtQml
import core_tools.GUI.virt_gate_matrix_qml  as qml_in
from core_tools.GUI.virt_gate_matrix_qml.models import attenuation_model, singal_hander_4_vg_matrix
import os, sys

class GUI_controller:
    def __init__(self, data):
        super().__init__()
        # self.app =  QtGui.QGuiApplication(sys.argv)
        self.app = QtCore.QCoreApplication.instance()
        self.instance_ready = True
        if self.app is None:
            self.instance_ready = False
            self.app = QtWidgets.QApplication([])

        self.engine = QtQml.QQmlApplicationEngine()
        self.attenuation_model = attenuation_model(data)

        self.singal_hander =singal_hander_4_vg_matrix(self.attenuation_model)

        self.engine.rootContext().setContextProperty("attenuation_model", self.attenuation_model)
        self.engine.rootContext().setContextProperty("singal_hander", self.singal_hander)

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
    mock_data = {'P1': 0.215,
 'P2': 0.088,
 'P3': 0.099,
 'P4': 0.083,
 'P5': 0.088,
 'P6': 0.088,
 'B0': 0.091,
 'B1': 0.143,
 'B2': 0.15,
 'B3': 0.153,
 'B4': 0.153,
 'B5': 0.153,
 'SD1_P': 0.052,
 'SD2_P': 0.067,
 'I_MW': 1,
 'Q_MW': 1,
 'S6': 0.1,
 'misc': 1}

    g =GUI_controller(mock_data)

    # if not g.engine.rootObjects():
    #     sys.exit(-1)

    # sys.exit(g.app.exec_())
    # print('donesys.argv')