import core_tools.data.gui.ui_files.data_browser_autogen as data_browser_autogen

from core_tools.data.gui.result_table_gui import result_table_model
from core_tools.data.gui.date_list_GUI import data_list_model

from core_tools.data.SQL.SQL_measurment_queries import query_for_samples, query_for_measurement_results
from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage

from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial

import sys

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

		self.app.exec_()

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
				self.load_data_table(self.dates_overview_model.data_list[0])

	def load_meas_data(self, idx):
		self.load_data_table(self.dates_overview_model.data_list[idx.row()])
	
	def load_data_table(self, date):
		data = query_for_measurement_results.get_results_for_date(date, **self.sample_info)
		self.data_table_model.overwrite_data(data)

	def load_measurement(self, index):
		print('loading measurment window for uuid {}'.format(self.data_table_model._data[index.row()].uuid))

if __name__ == '__main__':

	set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')

	db = data_browser()
