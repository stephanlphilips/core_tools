import logging
from PyQt5 import QtCore, QtQuick
from PyQt5.QtWidgets import QMessageBox

from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote
from core_tools.data.SQL.queries.dataset_gui_queries import (
        alter_dataset, query_for_samples, query_for_measurement_results)

from core_tools.data.ds.data_set import load_by_uuid
try:
    from qt_dataviewer.core_tools import CoreToolsDatasetViewer
    from qt_dataviewer import DatasetList
    use_qt_dataviewer = True
except ImportError:
    from core_tools.data.gui.plot_mgr import data_plotter
    use_qt_dataviewer = False

from core_tools.data.gui.data_browser_models.result_table_data_class import m_result_overview
from core_tools.data.name_validation import validate_dataset_name

logger = logging.getLogger(__name__)


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
        self.name = None
        self.keywords = None
        self.starred = False
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
            logger.warning(f'Project {project} not in list')
            print(f'Project {project} not in list')
            self.project = None
        self._update_lists()

    def set_set_up(self, set_up):
        set_up = if_any_to_none(set_up)
        if set_up is None or set_up in self._set_ups:
            self.set_up = set_up
        else:
            logger.warning(f'Set-up {set_up} not in list')
            print(f'Set-up {set_up} not in list')
            self.set_up = None
        self._update_lists()

    def set_sample(self, sample):
        sample = if_any_to_none(sample)
        if sample is None or sample in self._samples:
            self.sample = sample
        else:
            logger.warning(f'Sample {sample} not in list')
            print(f'Sample {sample} not in list')
            self.sample = None
        self._update_lists()

    def set_name(self, name):
        if name == '':
            name = None
        self.name = name

    def set_keywords(self, keywords):
        if keywords == '':
            self.keywords = None
        else:
            self.keywords = [kw.strip() for kw in keywords.split(',')]

    def set_starred(self, starred):
        self.starred = starred

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
    def __init__(self, data_filter, date_model, data_overview_model,
                 live_plotting_enabled=True):
        super().__init__()
        self.live_plotting_enabled = live_plotting_enabled
        self._data_filter = data_filter

        self.date_model = date_model
        self.data_overview_model = data_overview_model

        self.max_measurement_id = 0
        self.selected_date = None
        self.ignore_date_selection_changes = False
        self.plots = []

    def init_gui_variables(self, win):
        self.win = win

        obj = self.win.findChild(QtCore.QObject, "local_conn")
        state = SQL_conn_info_local.host == 'localhost'
        obj.setProperty("local_conn_status", state)

        obj = self.win.findChild(QtCore.QObject, "remote_conn")
        state = SQL_conn_info_remote.host != 'localhost'
        obj.setProperty("remote_conn_status", state)

        obj = self.win.findChild(QtCore.QObject, "enable_liveplotting")
        obj.setProperty("checked", self.live_plotting_enabled)

        self.pro_set_sample_info_state_change_loc(
                self._data_filter.project_index,
                self._data_filter.set_up_index,
                self._data_filter.sample_index)

        self.updating = False
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start()

    @QtCore.pyqtSlot('QString')
    def message(self, message):
        print(message)

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

        _, self.max_measurement_id = query_for_measurement_results.detect_new_meaurements(
                0,
                project=self._data_filter.project,
                set_up=self._data_filter.set_up,
                sample=self._data_filter.sample)
        self.update_date_model()

    def update_date_model(self):
        dates = query_for_measurement_results.get_all_dates_with_meaurements(
                self._data_filter.project,
                self._data_filter.set_up,
                self._data_filter.sample,
                name=self._data_filter.name,
                keywords=self._data_filter.keywords,
                starred=self._data_filter.starred,
                )
        # avoid selected date being set to index 0.
        self.ignore_date_selection_changes = True
        self.date_model.reset_data(dates)
        self.ignore_date_selection_changes = False
        if not self.selected_date:
            index = 0 if len(dates) > 0 else -1
        else:
            try:
                index = dates.index(self.selected_date)
            except ValueError:
                index = -1
        obj = self.win.findChild(QtCore.QObject, "date_list_view")
        old_index = obj.property('currentIndex')
        obj.setProperty("currentIndex", index)
        if old_index == index or index == -1:
            # fresh measurements
            self.load_data_table(self.selected_date)

    @QtCore.pyqtSlot(int)
    def update_date_selection(self, idx):
        if self.ignore_date_selection_changes:
            return
        try:
            date = self.date_model[idx] if self.date_model.rowCount() and idx >= 0 else None
            self.selected_date = date
            self.load_data_table(date)
        except Exception:
            logger.error('Failed to set date', exc_info=True)

    def load_data_table(self, date):
        try:
            data = query_for_measurement_results.get_results_for_date(
                    date,
                    project=self._data_filter.project,
                    set_up=self._data_filter.set_up,
                    sample=self._data_filter.sample,
                    name=self._data_filter.name,
                    keywords=self._data_filter.keywords,
                    starred=self._data_filter.starred,
                    )
            model_data = m_result_overview(data)
            self.data_overview_model.reset_data(model_data)
        except Exception:
            logger.error('Failed to load datasets', exc_info=True)

    def check_for_updates(self):
        if self.updating:
            return
        try:
            self.updating = True
            update, self.max_measurement_id = query_for_measurement_results.detect_new_meaurements(
                    self.max_measurement_id,
                    project=self._data_filter.project,
                    set_up=self._data_filter.set_up,
                    sample=self._data_filter.sample)

            if update and self.max_measurement_id is not None:
                self.update_date_model()

                if self.live_plotting_enabled:
                    # NOTE: name, keywords and starred are ignored for live plotting.
                    #       It is assumed that one want to see all new measurements
                    #       for project/setup/sample.
                    new_ds = query_for_measurement_results.search_query(exp_id=self.max_measurement_id)
                    self.plot_ds(new_ds[0].uuid)
        except Exception:
            logging.error('Check for updates failed', exc_info=True)
        finally:
            self.updating = False

    def plot_ds(self, uuid):
        # let the garbage collector collect the old plots
        try:
            ds = load_by_uuid(uuid)
        except Exception:
            logger.error(f'Failed to load dataset {uuid}', exc_info=True)
            return
        try:
            if use_qt_dataviewer:
                datalist = DataList(self.data_overview_model, uuid)
                p = CoreToolsDatasetViewer(ds, datalist=datalist)
                datalist.viewer = p
            else:
                p = data_plotter(ds)
            self.plots.append(p)

            for i in range(len(self.plots)-1, -1, -1):
                if not self.plots[i].alive:
                    self.plots.pop(i)
        except Exception:
            logger.error(f'Failed to show dataset {uuid}', exc_info=True)

    @QtCore.pyqtSlot('QString')
    def plot_ds_qml(self, uuid):
        self.plot_ds(int(uuid))

    @QtCore.pyqtSlot('QString', bool)
    def star_measurement(self, uuid, state):
        if uuid == 'filter':
            self._data_filter.set_starred(state)
            self.update_date_model()
        else:
            try:
                alter_dataset.star_measurement(uuid.replace('_', ''), state)
            except Exception:
                logging.error('Failed to change starred', exc_info=True)

    @QtCore.pyqtSlot('QString', 'QString')
    def update_name_meaurement(self, uuid, name):
        try:
            validate_dataset_name(name)
        except Exception as ex:
            logging.error(f"Failed to change name to '{name}': {ex}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(str(ex))
            msg.setWindowTitle("Invalid dataset name")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return

        try:
            alter_dataset.update_name(uuid.replace('_', ''), name)
        except Exception:
            logging.error(f'Failed to change name to "{name}"', exc_info=True)

    @QtCore.pyqtSlot('QString')
    def update_name_filter(self, name):
        self._data_filter.set_name(name)
        self.update_date_model()

    @QtCore.pyqtSlot('QString')
    def update_keywords_filter(self, keywords):
        self._data_filter.set_keywords(keywords)
        self.update_date_model()

    @QtCore.pyqtSlot()
    def close_all_plots(self):
        for plot in self.plots:
            plot.close()
        self.plots = []


if use_qt_dataviewer:

    class DataList(DatasetList):
        def __init__(self, data_overview_model, uuid):
            self.data_overview_model = data_overview_model
            self.uuid = uuid

        def has_next(self):
            # Note: data is ordered in descending order.
            # So 'next' in time is lower index
            index = self._get_index()
            return index is not None and index > 0

        def has_previous(self):
            index = self._get_index()
            return index is not None and index + 1 < len(self.data_overview_model._data)

        def _get_index(self):
            uuid = self.uuid
            for i, row in enumerate(self.data_overview_model._data):
                if row.uuid == uuid:
                    return i
            return None

        def _load_ds(self, uuid):
            try:
                return load_by_uuid(uuid)
            except Exception:
                logger.error(f'Failed to load dataset {uuid}', exc_info=True)
                # TODO raise Exception
                return None

        def get_next(self):
            index = self._get_index()
            if index is not None and index > 0:
                self.uuid = self.data_overview_model._data[index-1].uuid
                return self._load_ds(self.uuid)
            logger.info(f"No next data (index = {index})")
            return None

        def get_previous(self):
            index = self._get_index()
            if index is not None and index + 1 < len(self.data_overview_model._data):
                self.uuid = self.data_overview_model._data[index+1].uuid
                return self._load_ds(self.uuid)
            logger.info(f"No previous data (index = {index})")
            return None

        # -------------------------------------
        # OLD interface qt-dataviewer v0.2.x
        # TODO remove after some releases.
        def select_next(self):
            index = self._get_index()
            if index is not None and index > 0:
                self.uuid = self.data_overview_model._data[index-1].uuid
                self._set_ds(self.uuid)

        def select_previous(self):
            index = self._get_index()
            if index is not None and index + 1 < len(self.data_overview_model._data):
                self.uuid = self.data_overview_model._data[index+1].uuid
                self._set_ds(self.uuid)

        def _set_ds(self, uuid):
            try:
                ds = self._load_ds(uuid)
                if ds is not None:
                    self.viewer.set_ds(ds)
            except Exception:
                logger.error(f'Failed to set dataset {uuid}', exc_info=True)

