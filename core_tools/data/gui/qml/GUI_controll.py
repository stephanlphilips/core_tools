from PyQt5 import QtCore, QtQuick
# import os, sys
# import core_tools.data.gui.qml as qml_in

from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote
from core_tools.data.SQL.queries.dataset_gui_queries import (
        alter_dataset, query_for_samples, query_for_measurement_results)

from core_tools.data.ds.data_set import load_by_uuid
from core_tools.data.gui.plot_mgr import data_plotter
from core_tools.data.gui.data_browser_models.result_table_data_class import m_result_overview

def if_any_to_none(arg):
    if arg == "any":
        return None
    return arg

def default(arg, default):
    return arg if arg is not None else default


class DataFilter:
    def __init__(self, project_model, set_up_model, sample_model):
        self.project = None
        self.set_up = None
        self.sample = None
        self._project_model = project_model
        self._set_up_model = set_up_model
        self._sample_model = sample_model
        self._update_lists()

    def _update_lists(self):
        self._projects = ['any'] + query_for_samples.get_projects(sample=self.sample, set_up=self.set_up)
        self._set_ups = ['any'] + query_for_samples.get_set_ups(sample=self.sample, project=self.project)
        self._samples = ['any'] + query_for_samples.get_samples(set_up=self.set_up, project=self.project)
        self._project_model.reset_data(self._projects)
        self._set_up_model.reset_data(self._set_ups)
        self._sample_model.reset_data(self._samples)

    def set_indices(self, index_project, index_set_up, index_sample):
        self.project = if_any_to_none(self._project_model[index_project])
        self.set_up = if_any_to_none(self._set_up_model[index_set_up])
        self.sample = if_any_to_none(self._sample_model[index_sample])
        self._update_lists()

    def set_project(self, project):
        project = if_any_to_none(project)
        if project is None or project in self._projects:
            self.project = project
        else:
            print(f'Project {project} not in list')
            self.project = None
        self._update_lists()

    def set_set_up(self, set_up):
        set_up = if_any_to_none(set_up)
        if set_up is None or set_up in self._set_ups:
            self.set_up = set_up
        else:
            print(f'Set-up {set_up} not in list')
            self.set_up = None
        self._update_lists()

    def set_sample(self, sample):
        sample = if_any_to_none(sample)
        if sample is None or sample in self._samples:
            self.sample = sample
        else:
            print(f'Sample {sample} not in list')
            self.sample = None
        self._update_lists()

    @property
    def project_index(self):
        return self._projects.index(default(self.project, 'any'))

    @property
    def set_up_index(self):
        return self._set_ups.index(default(self.set_up, 'any'))

    @property
    def sample_index(self):
        return self._samples.index(default(self.sample, 'any'))


class signale_handler(QtQuick.QQuickView):
    def __init__(self, data_filter, date_model, data_overview_model):
        super().__init__()
        self.live_plotting_enabled = True
        self._data_filter = data_filter

        self.date_model = date_model
        self.data_overview_model = data_overview_model

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

        self.pro_set_sample_info_state_change_loc(
                self._data_filter.project_index,
                self._data_filter.set_up_index,
                self._data_filter.sample_index)

        _, self.measurement_count = query_for_measurement_results.detect_new_meaurements(self.measurement_count)

        self.updating = False
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
        self._data_filter.set_indices(index_project, index_set_up, index_sample)

        obj = self.win.findChild(QtCore.QObject, "combobox_project")
        obj.setProperty("currentIndex", self._data_filter.project_index)

        obj = self.win.findChild(QtCore.QObject, "combobox_set_up")
        obj.setProperty("currentIndex", self._data_filter.set_up_index)

        obj = self.win.findChild(QtCore.QObject, "combobox_sample")
        obj.setProperty("currentIndex", self._data_filter.sample_index)

        self.update_date_model()
        self.update_date_selection(0)

    def update_date_model(self):
        dates = query_for_measurement_results.get_all_dates_with_meaurements(
                self._data_filter.project,
                self._data_filter.set_up,
                self._data_filter.sample)

        self.date_model.reset_data(dates)
        obj = self.win.findChild(QtCore.QObject, "date_list_view")
        obj.setProperty("currentIndex", 0)

    @QtCore.pyqtSlot(int)
    def update_date_selection(self, idx):
        date = self.date_model[idx] if self.date_model.rowCount() else None
        self.load_data_table(date)

    def load_data_table(self, date):
        data = query_for_measurement_results.get_results_for_date(
                date,
                project=self._data_filter.project,
                set_up=self._data_filter.set_up,
                sample=self._data_filter.sample)
        model_data = m_result_overview(data)
        self.data_overview_model.reset_data(model_data)

    def check_for_updates(self):
        if self.updating:
            return
        try:
            self.updating = True
            update, self.measurement_count = query_for_measurement_results.detect_new_meaurements(self.measurement_count)

            if update==True:
                self.update_date_model()

                if self.live_plotting_enabled == True:
                    self.plot_ds(self.data_overview_model._data[0].uuid)
        finally:
            self.updating = False

    def plot_ds(self, uuid):
        # let the garbage collector collect the old plots
        try:
            ds = load_by_uuid(uuid)
        except Exception as ex:
            print(ex)
            return
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