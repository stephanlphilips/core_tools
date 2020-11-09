from PyQt5 import QtCore, QtQuick, QtGui, QtWidgets, QtQml
import core_tools.utility.variable_mgr.qml as qml_in
from core_tools.utility.variable_mgr.qml.model_categories import categories_model, name_value_model, var_raw, singal_hander_4_variable_exporer
import os, sys

class GUI_controller:
    def __init__(self, data):
        super().__init__()
        self.app =  QtGui.QGuiApplication(sys.argv)
        # self.app = QtCore.QCoreApplication.instance()
        # self.instance_ready = True
        # if self.app is None:
        #     self.instance_ready = False
        #     self.app = QtWidgets.QApplication([])

        self.engine = QtQml.QQmlApplicationEngine()
        self.categories_model = categories_model(list(data.keys()))
        self.data = data
        if len(data)==0:
            self.data_model = name_value_model({})
        else:
            self.data_model = name_value_model(data[list(data.keys())[0]])
        self.singal_hander =singal_hander_4_variable_exporer(self.categories_model, self.data_model, data)

        self.engine.rootContext().setContextProperty("cat_model", self.categories_model)
        self.engine.rootContext().setContextProperty("variable_name_value_pair_list", self.data_model)
        self.engine.rootContext().setContextProperty("test_function", self.singal_hander)

        # grab directory from the import!
        filename = os.path.join(qml_in.__file__[:-11], "variable_mgr_window.qml")
        self.engine.load(QtCore.QUrl.fromLocalFile(filename))
        self.win = self.engine.rootObjects()[0]

        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)

        self.app.exec()
        # if self.instance_ready == False:
        #     print('exec')
    def update_data(self):
        self.singal_hander.update_data()

    def set_data(self):
        '''just update all...'''
        self.singal_hander.set_data()

if __name__ == "__main__":
    data = {'SD voltages':{'SD1_on_11':var_raw('SD1_on_11', 0.1, 0.1), 'SD1_on_11':var_raw('SD1_on_11', 0.4, 0.1), 'SD1_off':var_raw('SD1_off', -5, 0.1), 'SD2_on':var_raw('SD2_on', 3.5, 0.1), 'SD2_off':var_raw('SD2_off', 0, 0.1)},
            'dot properties':{'U1':var_raw('U1',45,1), 'U2':var_raw('U2',50,1), 'U3':var_raw('U3',70,1), 'U4':var_raw('U4',40,1), 'U5':var_raw('U5',50,1), 'U6':var_raw('U6',50,1)},
            'qubit properties':{'f_qubit_1':var_raw('f_qubit_1',18.219e9,0.1e5), 'f_qubit_2':var_raw('f_qubit_2',18.312e9,0.1e5)}}

    g =GUI_controller(data)

    # if not g.engine.rootObjects():
    #     sys.exit(-1)

    # sys.exit(g.app.exec_())
    # print('donesys.argv')