from PyQt5 import QtCore, QtQuick
from core_tools.data.gui.qml.models import date_model, data_overview_model
# import os, sys
# import core_tools.data.gui.qml as qml_in

from core_tools.data.SQL.connect import sample_info, SQL_conn_info_local, SQL_conn_info_remote
from core_tools.data.SQL.queries.dataset_gui_queries import (
        alter_dataset, query_for_samples, query_for_measurement_results)

from core_tools.data.ds.data_set import load_by_uuid
from core_tools.data.gui.plot_mgr import data_plotter
from core_tools.data.gui.data_browser_models.result_table_data_class import m_result_overview

def if_any_to_none(arg):
    if arg == "any":
        return None
    return arg

class signale_handler(QtQuick.QQuickView):
    def __init__(self, project_model, set_up_model, sample_model, date_model, data_overview_model):
        super().__init__()
        self.live_plotting_enabled = True
        self.project_model = project_model
        self.set_up_model = set_up_model
        self.sample_model = sample_model

        self.date_model = date_model
        self.data_overview_model = data_overview_model

        self.sample_info = dict()
        self.sample_info['project'] = sample_info.project
        self.sample_info['sample'] = sample_info.set_up
        self.sample_info['set_up'] = sample_info.sample

        self.measurement_count =0
        self.plots = []


    def init_gui_variables(self, win):
        self.win = win

        obj = self.win.findChild(QtCore.QObject, "local_conn")
        if SQL_conn_info_local.host == 'localhost':
            obj.setProperty("local_conn_status", True)
        else:
            obj.setProperty("local_conn_status", False)

        obj = self.win.findChild(QtCore.QObject, "remote_conn")
        if SQL_conn_info_remote.host != 'localhost':
            obj.setProperty("remote_conn_status", True)
        else:
            obj.setProperty("remote_conn_status", False)

        self.pro_set_sample_info_state_change_loc(1,1,1)

        _, self.measurement_count = query_for_measurement_results.detect_new_meaurements(self.measurement_count)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start()

    @QtCore.pyqtSlot(bool)
    def enable_liveplotting(self, state):
        self.live_plotting_enabled = state

    @QtCore.pyqtSlot(int, int, int)
    def pro_set_sample_info_state_change(self, index_project, index_set_up, index_sample):
        self.pro_set_sample_info_state_change_loc(index_project, index_set_up, index_sample)

    def pro_set_sample_info_state_change_loc(self, index_project, index_set_up, index_sample):
        self.sample_info['project'] = if_any_to_none(self.project_model[index_project])
        self.sample_info['set_up'] = if_any_to_none(self.set_up_model[index_set_up])
        self.sample_info['sample'] = if_any_to_none(self.sample_model[index_sample])

        projects = ['any'] + query_for_samples.get_projects(sample=self.sample_info['sample'], set_up=self.sample_info['set_up'])
        set_ups = ['any'] + query_for_samples.get_set_ups(sample=self.sample_info['sample'], project=self.sample_info['project'])
        samples = ['any'] + query_for_samples.get_samples(set_up=self.sample_info['set_up'], project=self.sample_info['project'])

        idx_project = projects.index(self.project_model[index_project])
        idx_set_up = set_ups.index(self.set_up_model[index_set_up])
        idx_sample = samples.index(self.sample_model[index_sample])

        self.project_model.reset_data(projects)
        self.set_up_model.reset_data(set_ups)
        self.sample_model.reset_data(samples)

        obj = self.win.findChild(QtCore.QObject, "combobox_project")
        obj.setProperty("currentIndex", idx_project)

        obj = self.win.findChild(QtCore.QObject, "combobox_set_up")
        obj.setProperty("currentIndex", idx_set_up)

        obj = self.win.findChild(QtCore.QObject, "combobox_sample")
        obj.setProperty("currentIndex", idx_sample)

        self.update_date_model()
        self.update_date_selection(0)

    def update_date_model(self):
        dates = query_for_measurement_results.get_all_dates_with_meaurements(
                        self.sample_info['project'],self.sample_info['set_up'],
                        self.sample_info['sample'])

        self.date_model.reset_data(dates)
        obj = self.win.findChild(QtCore.QObject, "date_list_view")
        obj.setProperty("currentIndex", 0)

    @QtCore.pyqtSlot(int)
    def update_date_selection(self, idx):
        date = self.date_model[idx] if self.date_model.rowCount() else None
        self.load_data_table(date)

    def load_data_table(self, date):
        data = query_for_measurement_results.get_results_for_date(date, **self.sample_info)
        model_data = m_result_overview(data)
        self.data_overview_model.reset_data(model_data)

    def check_for_updates(self):
        update, self.measurement_count = query_for_measurement_results.detect_new_meaurements(self.measurement_count)

        if update==True:
            self.update_date_model()

            if self.live_plotting_enabled == True:
                self.plot_ds(self.data_overview_model._data[0].uuid)

    def plot_ds(self, uuid):
        # let the garbage collector collect the old plots

        ds = load_by_uuid(uuid)
        p = data_plotter(ds)
        self.plots.append(p)

        for i in range(len(self.plots)-1, -1, -1):
            if self.plots[i].alive == False:
                self.plots.pop(i)

    @QtCore.pyqtSlot('QString')
    def plot_ds_qml(self, uuid):
        self.plot_ds(int(uuid))

    @QtCore.pyqtSlot('QString', bool)
    def star_measurement(self, uuid, state):
        alter_dataset.star_measurement(uuid, state)

    @QtCore.pyqtSlot('QString', 'QString')
    def update_name_meaurement(self, uuid, name):
        alter_dataset.update_name(uuid, name)