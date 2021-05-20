import core_tools.data.gui.ui_files.plotter_basic_autgen as plotter_basic_autgen
from core_tools.data.gui.generate_mparam_ui_box import single_m_param_m_descriptor
from PyQt5 import QtCore, QtGui, QtWidgets
import sys

from core_tools.data.gui.plots._1D_plotting import _1D_plot
from core_tools.data.gui.plots._2D_plotting import _2D_plot


class data_plotter(QtWidgets.QMainWindow, plotter_basic_autgen.Ui_MainWindow):
    def __init__(self, ds):
        self.ds = ds
        self.alive = True
        self.app = QtCore.QCoreApplication.instance()
        self.instance_ready = True
        if self.app is None:
            self.instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        self.ui_box_mgr = ui_box_mgr(self.app, self.ds, self.data_plot_layout)
        # add gui for dataset selection
        for m_param_set in self.ds:
            for m_param in m_param_set:
                param =m_param[1]
                layout = single_m_param_m_descriptor(param, self.scrollAreaWidgetContents_4)
                self.ui_box_mgr.add_m_param_plot_mgr(layout.plot_data_mgr)
                self.data_content_layout.addLayout(layout)

        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.data_content_layout.addItem(verticalSpacer)
        
        # render plots
        self.ui_box_mgr.draw_plots()

        self.show()

        if self.instance_ready == False:
            self.app.exec()

    def closeEvent(self, event):
        self.alive = False
    
class ui_box_mgr():
    def __init__(self, app, ds, plot_layout):
        '''
        Manager that will generate the plots (connecting the selected settings from the user with the pyqtgraph plotting library

        Args:
            app
            plot_layout (tbd) : qt layout where the pyqt windows can be inserted in. 
        '''
        self.plot_layout = plot_layout
        self.m_param_plot_mgr = []
        self.timer=QtCore.QTimer()
        self.plot_widgets = []
        self.app  = app
        self.ds = ds

    def add_m_param_plot_mgr(self, mgr):
        '''
        type:data_mgr_4_plot
        '''
        self.m_param_plot_mgr.append(mgr)
        mgr.parent = self

    def draw_plots(self):
        self.timer.stop()
        
        # clear all
        plot_widgets = []
        for item in self.m_param_plot_mgr:
            if item.n_dim == 1 and item.enable == True:
                plot_widget = _1D_plot([item.ds], {'x':item.x_log, 'y':item.y_log})
                plot_widgets.append(plot_widget)
            if item.n_dim == 2 and item.enable == True:
                plot_widget = _2D_plot(item.ds, {'z':item.z_log})
                plot_widgets.append(plot_widget)

        for i in reversed(range(self.plot_layout.count())): 
            widgetToRemove = self.plot_layout.itemAt(i).widget()
            self.plot_layout.removeWidget(widgetToRemove)
            widgetToRemove.setParent(None)
        
        self.plot_widgets = plot_widgets
        for plot_widget in self.plot_widgets:
            self.plot_layout.addWidget(plot_widget.widget)
        # update plot every 300 ms for a smooth plottin experience
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(300)


    def update_plots(self):
        if self.ds.completed==True:
            self.timer.stop()
        self.ds.sync()

        for plot in self.plot_widgets:
            plot.update()


if __name__ == '__main__':
    from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage, set_up_remote_storage
    from core_tools.data.ds.data_set import load_by_uuid, load_by_id
    import sys
    import datetime
    # set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
    set_up_remote_storage('131.180.205.81', 5432, 'xld_measurement_pc', 'XLDspin001', 'spin_data', "6dot", "XLD", "6D3S - SQ20-20-5-18-4")

    ds = load_by_id(307)
    p = data_plotter(ds)
