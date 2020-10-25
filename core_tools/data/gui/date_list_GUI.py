from PyQt5 import QtCore, QtGui, QtWidgets

class data_list_model(QtCore.QAbstractListModel):
    def __init__(self):
        super().__init__()

        self.data_list = []
        self.items_displayed = 0    

    def rowCount(self, index):
        return self.items_displayed

    def data(self, index, role):
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return self.data_list[index.row()].strftime("%d/%m/%Y")
        
        return None

    def canFetchMore(self, index):
        return self.items_displayed < len(self.data_list)

    def fetchMore(self, index):
        remainder = len(self.data_list) - self.items_displayed
        itemsToFetch = min(50, remainder)

        self.beginInsertRows(QtCore.QModelIndex(), self.items_displayed,
                self.items_displayed + itemsToFetch)
        self.items_displayed += itemsToFetch
        self.endInsertRows()

    def update_content(self, data):
        import numpy as np
        self.beginResetModel()
        self.items_displayed = 0 
        self.data_list = data
        self.endResetModel()

if __name__ == '__main__':
    from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
    from core_tools.data.SQL.SQL_measurment_queries import query_for_measurement_results
    import sys
    import datetime
    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')

    class test_window(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()

            data = query_for_measurement_results.get_all_dates_with_meaurements(None, None, 'Intel Project')
            self.model = data_list_model()
            self.model.update_content(data)

            self.view = QtWidgets.QListView()
            self.view.setModel(self.model)
            self.view.clicked.connect(self.print_date)

            self.setCentralWidget(self.view)

        def print_date(self, *args):
            print(args)
            print(args[0].row())

    app = QtWidgets.QApplication(sys.argv)

    window = test_window()
    window.show()

    sys.exit(app.exec_())
