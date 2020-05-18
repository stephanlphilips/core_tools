# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'liveplot_only.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.frame_plots = QtWidgets.QFrame(self.centralwidget)
        self.frame_plots.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_plots.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_plots.setObjectName("frame_plots")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.frame_plots)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.grid_plots = QtWidgets.QGridLayout()
        self.grid_plots.setObjectName("grid_plots")
        self.gridLayout_4.addLayout(self.grid_plots, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.frame_plots, 0, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.Close = QtWidgets.QPushButton(self.centralwidget)
        self.Close.setObjectName("Close")
        self.gridLayout_2.addWidget(self.Close, 1, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 20))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Close.setText(_translate("MainWindow", "Close"))
