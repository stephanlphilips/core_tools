import core_tools.data.gui.ui_files.data_browser_autogen as data_browser_autogen
from core_tools.data.ds.data_set import load_by_uuid, load_by_id

from core_tools.data.gui.plot_mgr import data_plotter
from core_tools.data.gui.data_browser_models.result_table_gui import result_table_model
from core_tools.data.gui.data_browser_models.date_list_GUI import data_list_model

from core_tools.data.SQL.SQL_measurment_queries import query_for_samples, query_for_measurement_results
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage

from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial

import sys
import datetime

def if_any_to_none(arg):
    if arg == "any":
        return None
    return arg

class data_browser(data_browser_autogen.Ui_MainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        MainWindow = QtWidgets.QMainWindow()
        self.setupUi(MainWindow)
        MainWindow.show()

        ##################
        # overiew window #
        ##################
        self.sample_info = dict()
        self.sample_info['project'] = sample_info.project
        self.sample_info['sample'] = sample_info.set_up
        self.sample_info['set_up'] = sample_info.sample

        self.dates_overview_model = data_list_model()
        self.dates_overview.setModel(self.dates_overview_model)
        self.dates_overview.clicked.connect(self.load_meas_data)
        
        self.data_table_model = result_table_model()
        self.data_table.setSortingEnabled(True);
        self.data_table.sortByColumn(3, QtCore.Qt.DescendingOrder)
        self.data_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);
        self.data_table.doubleClicked.connect(self.load_measurement)
        self.data_table.setModel(self.data_table_model)

        self.selected_date = None
        self.init_index(self.set_up_scroll_box, ['any', sample_info.set_up])
        self.init_index(self.Sample_scroll_box, ['any', sample_info.sample])
        self.init_index(self.Project_scroll_box, ['any', sample_info.project])
        self.update_index(('set_up',self.set_up_scroll_box),
            ('project', self.Project_scroll_box), ('sample', self.Sample_scroll_box))
        self.update_index(('sample', self.Sample_scroll_box),
            ('set_up',self.set_up_scroll_box), ('project', self.Project_scroll_box))
        self.update_index(('project', self.Project_scroll_box),
            ('set_up',self.set_up_scroll_box), ('sample', self.Sample_scroll_box), True)

        self.set_up_scroll_box.activated.connect(partial(self.update_index, ('set_up',self.set_up_scroll_box),
            ('project', self.Project_scroll_box), ('sample', self.Sample_scroll_box), True))
        self.Sample_scroll_box.activated.connect(partial(self.update_index, ('sample', self.Sample_scroll_box),
            ('set_up',self.set_up_scroll_box), ('project', self.Project_scroll_box), True))
        self.Project_scroll_box.activated.connect(
            partial(self.update_index, 
                        ('project', self.Project_scroll_box),
                        ('set_up',self.set_up_scroll_box),
                        ('sample', self.Sample_scroll_box),
                        True))

        ##############
        # search tab #
        ##############

        self.enable_min_date.stateChanged.connect(partial(self.enable_date, self.min_date_field))
        self.enable_max_date.stateChanged.connect(partial(self.enable_date, self.max_date_field))

        self.set_up_search.activated.connect(partial(self.update_index, ('set_up',self.set_up_search),
            ('project', self.project_search), ('sample', self.sample_search)))
        self.sample_search.activated.connect(partial(self.update_index, ('sample', self.sample_search),
            ('set_up',self.set_up_search), ('project', self.project_search)))
        self.project_search.activated.connect(partial(self.update_index, 
            ('project', self.project_search), ('set_up',self.set_up_search),('sample', self.sample_search)))

        self.reset_search_box()

        self.reset_search.clicked.connect(self.reset_search_box)

        self.search_table_data_model = result_table_model()
        self.search_table_data.setSortingEnabled(True);
        self.search_table_data.sortByColumn(3, QtCore.Qt.DescendingOrder)
        self.search_table_data.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);
        self.search_table_data.doubleClicked.connect(self.load_measurement_search)
        self.search_table_data.setModel(self.search_table_data_model)

        self.search_bottom.clicked.connect(self.search_data)

        self.plots = []

        self.count_measurements = 0
        self.check_for_updates()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(200)
        
        
        self.app.exec_()

    def enable_date(self, item, state):
        item.setVisible(state)

    def init_index(self, index, values, idx = 1):
        index.clear()
        index.addItems(values)
        index.setCurrentIndex(idx)

    def update_index(self, current, other_1, other_2, update_date=False, *args):
        current_val = current[1].currentText()
        other_1_val = other_1[1].currentText()
        other_2_val = other_2[1].currentText()

        vals_1 = ['any'] + query_for_samples.get_x_given_yz(other_1[0], (other_2[0],if_any_to_none(other_2_val)), 
                                    (current[0], if_any_to_none(current_val)))
        vals_2 = ['any'] + query_for_samples.get_x_given_yz(other_2[0], (other_1[0],if_any_to_none(other_1_val)), 
                                    (current[0], if_any_to_none(current_val)))

        self.init_index(other_1[1], vals_1, vals_1.index(other_1_val))
        self.init_index(other_2[1], vals_2, vals_2.index(other_2_val))

        if update_date == True:
            self.sample_info[current[0]] = if_any_to_none(current[1].currentText())
            self.sample_info[other_1[0]] = if_any_to_none(other_1[1].currentText())
            self.sample_info[other_2[0]] = if_any_to_none(other_2[1].currentText())
            data = query_for_measurement_results.get_all_dates_with_meaurements(self.sample_info['project'],
                self.sample_info['set_up'], self.sample_info['sample'])

            self.dates_overview_model.update_content(data)
            
            if len(self.dates_overview_model.data_list) > 0:
                self.selected_date = self.dates_overview_model.data_list[0]
                self.load_data_table(self.selected_date)

    def load_meas_data(self, idx):
        self.selected_date = self.dates_overview_model.data_list[idx.row()]
        self.load_data_table(self.selected_date)
    
    def load_data_table(self, date):
        data = query_for_measurement_results.get_results_for_date(date, **self.sample_info)
        self.data_table_model.overwrite_data(data)

    def load_measurement(self, index):
        self.plot_ds(self.data_table_model._data[index.row()].uuid)
    
    def load_measurement_search(self, index):
        self.plot_ds(self.search_table_data_model._data[index.row()].uuid)
        
    def plot_ds(self, uuid):
        ds = load_by_uuid(uuid)
        p = data_plotter(ds)
        self.plots.append(p)

    def check_for_updates(self):
        update, self.count_measurements = query_for_measurement_results.detect_new_meaurements(self.count_measurements)
        if update==True:
            self.load_data_table(self.selected_date)

            if self.action_autoplot_new.isChecked() == True:
                self.plot_ds(self.data_table_model._data[0].uuid)

    def reset_search_box(self):
        self.min_date_field.hide()
        self.max_date_field.hide()

        self.enable_min_date.setCheckState(0)
        self.enable_max_date.setCheckState(0)

        max_date = datetime.datetime.now()
        min_date = max_date - datetime.timedelta(days=7)

        self.min_date_field.setDate(min_date.date())
        self.max_date_field.setDate(max_date.date())

        self.description_search.clear()
        self.id_uuid_search.clear()

        self.init_index(self.project_search, ['any', sample_info.project])
        self.init_index(self.set_up_search, ['any', sample_info.set_up])
        self.init_index(self.sample_search, ['any', sample_info.sample])

        self.update_index(('set_up',self.set_up_search), ('project', self.project_search), ('sample', self.sample_search))
        self.update_index(('sample', self.sample_search), ('set_up',self.set_up_search), ('project', self.project_search))
        self.update_index(('project', self.project_search), ('set_up',self.set_up_search), ('sample', self.sample_search))

    def search_data(self):
        exp_id = None
        exp_uuid = None
        id_uuid = self.id_uuid_search.text()
        seach_type_id_uuid = self.id_uuid_search_type.currentText()
        if seach_type_id_uuid == 'id' and id_uuid!="":
            exp_id = id_uuid
        elif seach_type_id_uuid == 'uuid' and id_uuid!="":
            exp_uuid = id_uuid
        
        project = if_any_to_none(self.project_search.currentText())
        set_up = if_any_to_none(self.set_up_search.currentText())
        sample = if_any_to_none(self.sample_search.currentText())
        words = self.description_search.text()

        start_date = None
        stop_date = None
        if self.enable_min_date.checkState() == 2:
            start_date = self.min_date_field.date()
        if self.enable_max_date.checkState() == 2:
            stop_date = self.max_date_field.date()

        data = query_for_measurement_results.search_query(exp_id, exp_uuid, words, start_date, stop_date, project, set_up, sample)

        self.search_table_data_model.overwrite_data(data)

if __name__ == '__main__':

    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')

    db = data_browser()
