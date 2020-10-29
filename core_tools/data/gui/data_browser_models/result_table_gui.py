from PyQt5 import QtCore, QtGui, QtWidgets

class result_table_model(QtCore.QAbstractTableModel):
	def __init__(self):
		super().__init__()
		self._data = [[]]
		self.items_displayed = 0

	def overwrite_data(self, data):
		self._data = data
		self.items_displayed = 0
		self.layoutChanged.emit()

	def data(self, index, role):
		if index.isValid() and role == QtCore.Qt.DisplayRole:
			return self._data[index.row()][index.column()]
		
		return None

	def headerData(self, section, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return ("ID", "UUID", 'Name', 'date', 'Project', 'Set up', 'Sample', 'Keywords', 'location')[section]
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.InitialSortOrderRole:
			if section == 3:
				return QtCore.Qt.DescendingOrder
			return None

		return None

	def rowCount(self, index):
		return self.items_displayed

	def columnCount(self, index):
		return len(self._data[0])

	def canFetchMore(self, index):
		return self.items_displayed < len(self._data)

	def fetchMore(self, index):
		remainder = len(self._data) - self.items_displayed
		itemsToFetch = min(50, remainder)
		self.beginInsertRows(QtCore.QModelIndex(), self.items_displayed,
				self.items_displayed + itemsToFetch-1)
		self.items_displayed += itemsToFetch
		self.endInsertRows()

	def sort(self, column, direction):
		self.layoutAboutToBeChanged.emit()
		self._data.sort(column, direction)
		self.layoutChanged.emit()


if __name__ == '__main__':
	from core_tools.data.SQL.SQL_measurment_queries import query_for_measurement_results

	class MainWindow(QtWidgets.QMainWindow):
		def __init__(self):
			super().__init__()

			self.table = QtWidgets.QTableView()
			self.table.setSortingEnabled(True);
			self.table.sortByColumn(3, QtCore.Qt.DescendingOrder)
			self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);

			self.table.doubleClicked.connect(self.test)
			
			test_date = datetime.datetime.now()- datetime.timedelta(20)
			data = query_for_measurement_results.get_results_for_date(test_date, sample=None, set_up=None, project='Intel Project', limit=1000)
			
			self.model = result_table_model()
			self.table.setModel(self.model)
			self.model.overwrite_data(data)


			self.setCentralWidget(self.table)

		def test(self, index):
			print('loading measurment window for uuid {}'.format(self.model._data[index.row()].uuid))

	from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
	import sys
	import datetime

	set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
	app=QtWidgets.QApplication(sys.argv)
	window=MainWindow()
	window.show()
	app.exec_()