# -*- coding: utf-8 -*-
from data_browser_GUI_window import Ui_dataviewer
from PyQt5 import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QWidget
from functools import partial
import pyqtgraph as pg
import qcodes
import numpy as np
import qdarkstyle
import logging
# import qtt
from core_tools.utility.powerpoint import addPPTslide, addPPT_dataset
import os
from qcodes.plots.pyqtgraph import QtPlot

class data_viewer(QtWidgets.QMainWindow, Ui_dataviewer):
    """docstring for virt_gate_matrix_GUI"""
    def __init__(self, datadir=None, window_title='Data browser'):         
        # set graphical user interface
        instance_ready = True
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])
        
        super(QtWidgets.QMainWindow, self).__init__()
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        self.setupUi(self)        
        
        if datadir is None:
            datadir = qcodes.DataSet.default_io.base_location
        
        # set-up tree view for data
        self._treemodel = QtGui.QStandardItemModel()
        self.data_view.setModel(self._treemodel)
        self.tabWidget.addTab(QtWidgets.QWidget(), 'metadata')
        
        self.qplot = QtPlot(remote=False)
        self.plotwindow = self.qplot.win
        self.qplot.max_len = 10
        
        self.horizontalLayout_4.addWidget(self.plotwindow)

        # Fix some initializations in the window
        self.splitter_2.setSizes([int(self.height()/2)]*2)
        self.splitter.setSizes([int(self.width() / 3), int(2 * self.width() / 3)])
        
        # connect callbacks
        self.data_view.doubleClicked.connect(self.logCallback)
        self.actionReload_data.triggered.connect(self.updateLogs)
        self.actionPreload_all_info.triggered.connect(self.loadInfo)
        self.actionAdd_directory.triggered.connect(self.selectDirectory)
        self.filter_button.clicked.connect(lambda: self.updateLogs(filter_str=self.filter_input.text()))
        self.send_ppt.clicked.connect(self.pptCallback)
        self.copy_im.clicked.connect(self.clipboardCallback)
        self.split_data.clicked.connect(self.split_dataset)
        
        # initialize defaults
        self.extensions =['dat', 'hdf5']
        self.dataset = None
        self.datatag = None
        self.datadirlist = []
        self.datadirindex = 0
        self.color_list = [pg.mkColor(cl) for cl in qcodes.plots.pyqtgraph.color_cycle]
        self.current_params = []
        self.subpl_ind = dict()
        self.splitted = False
        
        # add default directory
        self.addDirectory(datadir)
        self.updateLogs()
               
        # Launch app
        self.show()
        if instance_ready == False:
            self.app.exec()

    def find_datafiles(self,datadir, extensions=['dat', 'hdf5'], show_progress=True):
        """ Find all datasets in a directory with a given extension """
        dd = []
        for e in extensions:
            dd += self.findfiles(datadir, e)
        dd.sort()
        datafiles = sorted(dd)
        return datafiles

    def loadInfo(self):
        logging.debug('loading info')
        try:
            for row in range(self._treemodel.rowCount()):
                index = self._treemodel.index(row, 0)
                i = 0
                while (index.child(i, 0).data() is not None):
                    filename = index.child(i, 3).data()
                    loc =  os.path.dirname(filename)
                    tempdata = qcodes.DataSet(loc)
                    tempdata.read_metadata()
                    infotxt = self.getArrayStr(tempdata.metadata)
                    self._treemodel.setData(index.child(i, 1), infotxt)
                    i = i + 1
        except Exception as e:
            logging.warning(e)

    def setDatadir(self, newindex):
        logging.info(f'Setting datadir with index: {newindex}')
        oldindex = self.datadirindex
        self.datadirindex = newindex
        datadir = self.datadirlist[newindex]  
        
        self.io = qcodes.DiskIO(datadir)
        logging.info('DataViewer: data directory %s' % datadir)
        self.logfile.setText('Log files at %s' % datadir)

        self.menuFolder.actions()[oldindex + 1].setText(self.menuFolder.actions()[oldindex + 1].text()[2:])
        self.menuFolder.actions()[newindex + 1].setText('>>' + self.menuFolder.actions()[newindex + 1].text())
        self.updateLogs()
    
    def selectDirectory(self):
        from qtpy.QtWidgets import QFileDialog
        d = QtWidgets.QFileDialog(caption='Select data directory')
        d.setFileMode(QFileDialog.Directory)
        if d.exec():
            datadir = d.selectedFiles()[0]
            self.addDirectory(datadir)
            
    def addDirectory(self,datadir):
        newindex = len(self.datadirlist)
        self.datadirlist.append(datadir)
        if len(self.datadirlist) == 1:
            datadir = '>>' + datadir
        new_act = QtWidgets.QAction(datadir, self)
        new_act.triggered.connect(partial(self.setDatadir,newindex))
        self.menuFolder.addAction(new_act)
        self.setDatadir(newindex)
    
    def updateLogs(self, filter_str = None):
        ''' Update the list of measurements '''
        logging.info('updating logs')
        model = self._treemodel
        
        self.datafiles=self.find_datafiles(self.datadirlist[self.datadirindex], self.extensions)
        dd = self.datafiles
        
        if filter_str:
            dd = [s for s in dd if filter_str in s]
        
        logging.info(f'DataViewer: found {len(dd)} files')

        model.clear()
        model.setHorizontalHeaderLabels(
            ['Log', 'Arrays', 'location', 'filename'])

        logs = dict()
        for i, d in enumerate(dd):
            try:
                datetag, logtag = d.split(os.sep)[-3:-1]
                if datetag not in logs:
                    logs[datetag] = dict()
                logs[datetag][logtag] = d
            except Exception as e:
                print(e)
                pass
        self.logs = logs

        logging.debug('DataViewer: create gui elements')
        for i, datetag in enumerate(sorted(logs.keys())[::-1]):
            logging.debug(f'DataViewer: datetag {datetag}')

            parent1 = QtGui.QStandardItem(datetag)
            for j, logtag in enumerate(sorted(logs[datetag])):
                filename = logs[datetag][logtag]
                child1 = QtGui.QStandardItem(logtag)
                child2 = QtGui.QStandardItem('info about plot')
                logging.debug(f'datetag: {datetag}, logtag: {logtag}')
                child3 = QtGui.QStandardItem(os.path.join(datetag, logtag))
                child4 = QtGui.QStandardItem(filename)
                parent1.appendRow([child1, child2, child3, child4])
            model.appendRow(parent1)
            self.data_view.setColumnWidth(0, 240)
            self.data_view.setColumnHidden(2, True)
            self.data_view.setColumnHidden(3, True)

            logging.debug('DataViewer: updateLogs done')

    def logCallback(self, index):
        """ Function called when. a log entry is selected """
        logging.info('logCallback: index %s' % str(index))
        oldtab_index = self.tabWidget.currentIndex()
        pp = index.parent()
        row = index.row()
        tag = pp.child(row, 2).data()
        filename = pp.child(row, 3).data()
        self.filename = filename
        self.datatag = tag
        if tag is None:
            return
        logging.debug(f'DataViewer logCallback: tag {tag}, filename {filename}')
        
        try:
            logging.debug('DataViewer: load tag %s' % tag)
            data = self.loadData(filename, tag)
            if not data:
                raise ValueError('File invalid (%s) ...' % filename)
            self.dataset = data
            self.updateMetaTabs()
            try:
                self.tabWidget.setCurrentIndex(oldtab_index)
            except: pass
            data_keys = data.arrays.keys()
            infotxt = self.getArrayStr(data.metadata)
            q = pp.child(row, 1).model()
            q.setData(pp.child(row, 1), infotxt)
            self.resetComboItems(data, data_keys)
        except Exception as e:
            print('logCallback! error: %s' % str(e))
            logging.exception(e)

    def resetComboItems(self, data, keys):
        # Clearing old stuff
        self.clearLayout(self.data_select_lay)
        self.qplot.clear()
        self.boxes = dict()
        self.box_labels = dict()
        self.param_keys = list()
        to_plot = list()
        
        # Loop through keys and add graphics items
        for key in keys:
            if not getattr(data, key).is_setpoint:
                box = QtWidgets.QCheckBox()
                box.clicked.connect(self.checkbox_callback)
                box.setText(key)
                label = QtWidgets.QLabel()
                self.data_select_lay.addRow(box, label)
                self.boxes[key] = box
                self.box_labels[key] = label
                self.param_keys.append(key)
                if key in self.subpl_ind.keys():
                    self.boxes[key].setChecked(True)
                    to_plot.append(key)
        self.data_select_lay.setLabelAlignment(QtCore.Qt.AlignLeft)
        
        # If no old parameters can be plotted, defined first one
        if not to_plot:
            def_key = list(self.boxes.values())[0].text()
            to_plot.append(self.boxes[def_key].text())
            self.boxes[def_key].setChecked(True)
        
        # Update the parameter plots
        self.subpl_ind = dict()
        self.current_params = list()
        self.updatePlots(to_plot)
        if self.splitted:
            self.split_dataset()
    
    def clearPlots(self):
        self.qplot.clear()
        self.current_params = list(set(self.current_params) - set(self.subpl_ind.keys()))
        self.subpl_ind = dict()
        
    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def checkbox_callback(self, state):
        if self.splitted:
            self.clearPlots()
            self.splitted = False
        to_plot = []
        for param in self.param_keys:
            box = self.boxes[param]
            if box.isChecked():
                to_plot.append(box.text())
        self.updatePlots(to_plot)        
    
    def updatePlots(self, param_names):
        for param_name in set(param_names + self.current_params):
            param = getattr(self.dataset, param_name)
            if param_name not in param_names:
                self.current_params.remove(param_name)
                if param.shape == (1,):                
                    self.removeValue(param_name)
                elif len(param.shape) < 3:                
                    self.removePlot(param_name)
            elif param_name not in self.current_params:
                self.current_params.append(param_name)
                if param.shape == (1,):
                    self.addValue(param_name)
                elif len(param.shape) < 3:
                    self.addPlot(param_name)

    def addPlot(self, plot):
        logging.info(f'adding param {plot}')
        self.subpl_ind[plot] = len(self.subpl_ind)
        self.qplot.add(getattr(self.dataset, plot), subplot = len(self.subpl_ind), 
                       color = self.color_list[0])

    def removePlot(self,plot):
        logging.info(f'removing param {plot}')
        # Deleting graphics items
        plot_index = self.subpl_ind[plot]
        subplot = self.qplot.subplots[plot_index]
        subplot.clear()
        self.qplot.win.removeItem(subplot)
        subplot.deleteLater()
        
        try:
            hist = self.qplot.traces[plot_index]['plot_object']['hist']
            self.qplot.win.removeItem(hist)
            hist.deleteLater()
        except: pass
            
        # Own bookkeeping
        self.subpl_ind.pop(plot)
        
        # Removing from qcodes qplot (does not have proper function for this)
        self.qplot.traces.pop(plot_index)
        self.qplot.subplots.remove(subplot)
        for (key, val) in self.subpl_ind.items():
            if val > plot_index:
                self.subpl_ind[key] = val - 1
            
    def addValue(self, plot):
        val = getattr(self.dataset, plot).ndarray[0]
        self.box_labels[plot].setText(str(val))
        
    def removeValue(self, plot):
        self.box_labels[plot].setText('')
    
    def loadData(self, filename, tag):
        location = os.path.split(filename)[0]
        data = qcodes.data.data_set.load_data(location)
        return data

    def _create_meta_tree(self, meta_dict):
        metatree = QtWidgets.QTreeView()
        _metamodel = QtGui.QStandardItemModel()
        metatree.setModel(_metamodel)
        metatree.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)

        _metamodel.setHorizontalHeaderLabels(['metadata', 'value'])

        try:
            self.fill_item(_metamodel, meta_dict)
            return metatree

        except Exception as ex:
            print(ex)

    def fill_item(self, item, value):
        ''' recursive population of tree structure with a dict '''
        def new_item(parent, text, val=None):
            child = QtGui.QStandardItem(text)
            self.fill_item(child, val)
            parent.appendRow(child)

        if value is None:
            return
        elif isinstance(value, dict):
            for key, val in sorted(value.items()):
                if type(val) in [str, float, int] or (type(val) is list and not any(isinstance(el, list) for el in val)):
                    child = [QtGui.QStandardItem(
                        str(key)), QtGui.QStandardItem(str(val))]
                    item.appendRow(child)
                else:
                    new_item(item, str(key), val)
        else:
            new_item(item, str(value))
            
    def parse_gates(self, gates_obj):
        gate_dict = dict()
        
        for (gate, val) in gates_obj['parameters'].items():
            if gate != 'IDN':
                gate_dict[gate] = val['value']
        
        return gate_dict
    
    def updateMetaTabs(self):
        ''' Update metadata tree '''
        meta = self.dataset.metadata
        self.tabWidget.clear()
        
        try:
            gate_tree = self.parse_gates(meta['station']['instruments']['gates'])
            self.tabWidget.addTab(self._create_meta_tree(gate_tree), 'gates')
        except: pass        

        self.tabWidget.addTab(self._create_meta_tree(meta), 'metadata')
        
        if 'pc0' in meta.keys():
            self.pulse_plot = pg.PlotWidget()
            self.pulse_plot.addLegend()
            legend_names = list()
            try:
                baseband_freqs = meta['LOs']
            except:
                pass
            for (j, (name, pdict)) in enumerate(meta['pc0'].items()):
                legend_name = name.replace('_baseband','').replace('_pulses','')
                x = list()
                y = list()
                ch_type = list()
                end_time = max([x['stop'] for y in meta['pc0'].values() for x in y.values()])
                if 'baseband' in name:
                    timepoints = set([x[key] for x in meta['pc0'][name].values() for key in ['start','stop']])
                    timepoints.add(end_time)
                    x_plot = list()
                    y_plot = list()
                    for tp in sorted(timepoints):
                        point1 = 0
                        point2 = 0
                        for (seg_name,seg_dict) in meta['pc0'][name].items():
                            if seg_dict['start'] < tp and seg_dict['stop'] > tp: # active segement
                                point1 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_stop'] )
                                point2 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_stop'] )
                            elif seg_dict['start'] == tp:
                                point2 += seg_dict['v_start']
                            elif seg_dict['stop'] == tp:
                                point1 += seg_dict['v_stop']                         
                        x_plot += [tp, tp]
                        y_plot += [point1, point2]
                
                elif 'pulses' in name:
                    try:
                        baseband = baseband_freqs[name.replace('_pulses','')]
                    except:
                        logging.warning('No baseband frequency found, assuming 0')
                        baseband = 0
                    
                    for (seg_name,seg_dict) in meta['pc0'][name].items():
                        x_ar = np.arange(seg_dict['start'],seg_dict['stop'])
                        xx_ar = x_ar-seg_dict['start']
                        f_rl = (seg_dict['frequency'] - baseband)/1e9
                        y_ar = np.sin(2*np.pi*f_rl*xx_ar+seg_dict['start_phase'])*seg_dict['amplitude']
                        x = x + list(x_ar) + [seg_dict['stop']]
                        y = y + list(y_ar) + [0]
                        x_plot = x
                        y_plot = y
                self.pulse_plot.setLabel('left', 'Voltage', 'mV')
                self.pulse_plot.setLabel('bottom', 'Time', 'ns')
                self.pulse_plot.plot(x_plot, y_plot, pen = self.color_list[j], name = legend_name)

            self.tabWidget.addTab(self.pulse_plot,'AWG Pulses')

    def pptCallback(self):
        if self.dataset is None:
            print('no data selected')
            return
        addPPT_dataset(self.dataset, customfig=self.qplot)

    def clipboardCallback(self):
        self.qplot.copyToClipboard()

    def getArrayStr(self, metadata):
        params = []
        infotxt = ''
        try:
            if 'loop' in metadata.keys():
                sv = metadata['loop']['sweep_values']
                params.append('%s [%.2f to %.2f %s]' % (sv['parameter']['label'],
                                                        sv['values'][0]['first'],
                                                        sv['values'][0]['last'],
                                                        sv['parameter']['unit']))

                for act in metadata['loop']['actions']:
                    if 'sweep_values' in act.keys():
                        sv = act['sweep_values']
                        params.append('%s [%.2f - %.2f %s]' % (sv['parameter']['label'],
                                                               sv['values'][0]['first'],
                                                               sv['values'][0]['last'],
                                                               sv['parameter']['unit']))
                infotxt = ' ,'.join(params) + ' | '
            infotxt = infotxt + ', '.join([('%s' % (v['label'])) for (
                k, v) in metadata['arrays'].items() if not v['is_setpoint']])

        except BaseException:
            infotxt = 'info about plot'

        return infotxt
    
    def split_dataset(self):  
        to_split = []
        for bp in self.subpl_ind.keys():
            plot_shape = getattr(self.dataset, bp).shape
            if len(plot_shape) == 2:
                to_split.append(bp)
        self.clearPlots()      
        for (i,zname) in enumerate(to_split):
            tmp = getattr(self.dataset, zname)
            yname = tmp.set_arrays[0].array_id
            xname = tmp.set_arrays[1].array_id
    
            try:
                ii =  np.where(np.isnan(self.dataset.arrays[zname][:,-1])==True)[0][0]
            except:
                ii = len(self.dataset.arrays[yname][:])
            even = list(range(0, ii, 2))
            odd = list(range(1, ii, 2))

            self.qplot.add(self.dataset.arrays[xname][0], self.dataset.arrays[yname][odd], self.dataset.arrays[zname][odd],
                  ylabel=self.dataset.arrays[yname].label, xlabel=self.dataset.arrays[xname].label, zlabel=self.dataset.arrays[zname].label+'_odd',
                  yunit = self.dataset.arrays[yname].unit, zunit=self.dataset.arrays[zname].unit, subplot = 2 * i + 1)
            self.qplot.add(self.dataset.arrays[xname][0], self.dataset.arrays[yname][even], self.dataset.arrays[zname][even],
                  ylabel=self.dataset.arrays[yname].label, xlabel=self.dataset.arrays[xname].label, zlabel=self.dataset.arrays[zname].label+'_even',
                  yunit = self.dataset.arrays[yname].unit, zunit =self.dataset.arrays[zname].unit, subplot = 2 * i + 2)
            self.splitted = True

    def findfiles(self, path, extension):
        filelist = list()
        for dirname, dirnames, filenames in os.walk(path):        
            # print path to all filenames.
            for filename in filenames:
                fullfile = os.path.join(dirname, filename)
                if fullfile.split('.')[-1] == extension:
                    filelist.append(fullfile)        
        return filelist