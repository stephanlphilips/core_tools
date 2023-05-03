# -*- coding: utf-8 -*-
from .data_browser_GUI_window import Ui_dataviewer
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
import pyqtgraph as pg
import qcodes
# qcodes legacy imports
from qcodes.data.io import DiskIO
from qcodes.data.data_set import DataSet
import numpy as np
import qdarkstyle
import logging
from core_tools.utility.powerpoint_qcodes import addPPT_dataset
import os
from qcodes.plots.pyqtgraph import QtPlot
import pickle
import glob

logger = logging.getLogger(__name__)

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
            datadir = DataSet.default_io.base_location

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
        self.data_view.doubleClicked.connect(self.showMeasurement)
        self.actionReload_data.triggered.connect(self.reloadFiles)
        self.actionPreload_all_info.triggered.connect(self.loadInfo)
        self.actionAdd_directory.triggered.connect(self.selectDirectory)
        self.filter_button.clicked.connect(lambda: self.updateMeasurements(filter_str=self.filter_input.text()))
        self.send_ppt.clicked.connect(self.pptCallback)
        self.copy_im.clicked.connect(self.clipboardCallback)
        self.split_data.clicked.connect(self.split_dataset)

        # initialize defaults
        self.extensions =['dat', 'hdf5']
        self.dataset = None
        self.datadirlist = []
        self.datadirindex = 0
        self.color_list = [pg.mkColor(cl) for cl in qcodes.plots.pyqtgraph.color_cycle]
        self.subpl_ind = dict()
        self.splitted = False
        self.filtered = False
        self.active_params = []

        # add default directory
        self.addDirectory(datadir)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateToday)
        self.timer.start(5000)

        # Launch app
        self.show()
        if instance_ready == False:
            self.app.exec()

    def closeEvent(self, event):
        self.timer.stop()

    @property
    def current_dir(self):
        return self.datadirlist[self.datadirindex]

    def loadInfo(self):
        logger.debug('loading info')
        try:
            for row in range(self._treemodel.rowCount()):
                item = self._treemodel.item(row, 0)
                self.loadInfoNode(item)
        except Exception as e:
            logger.warning(e, exc_info=True)

    def loadInfoNode(self, node, indent=0):
        # print('  '*indent, node.text())
        for i in range(node.rowCount()):
            if node.child(i, 1) is not None:
                # print('  '*indent, ' ', node.child(i, 0).text())
                filename = node.child(i, 2).text()
                loc =  os.path.dirname(filename)
                tempdata = DataSet(loc)
                tempdata.read_metadata()
                infotxt = self.getArrayStr(tempdata.metadata)
                self._treemodel.setData(node.child(i, 1).index(), infotxt)
            if node.child(i, 0).hasChildren():
                self.loadInfoNode(node.child(i, 0), indent=indent+1)


    def findFiles(self, basepath):
        filelist = []
        for ext in self.extensions:
            filelist += glob.glob(basepath + '/**/*.'+ext, recursive=True)
        filelist.sort()
        return filelist

    def setDatadir(self, newindex):
        logger.info(f'Setting datadir with index: {newindex}')
        oldindex = self.datadirindex
        self.datadirindex = newindex
        datadir = self.datadirlist[newindex]

        self.io = DiskIO(datadir)
        logger.info('DataViewer: data directory %s' % datadir)
        self.logfile.setText('Log files at %s' % datadir)

        self.menuFolder.actions()[oldindex + 1].setText(self.menuFolder.actions()[oldindex + 1].text()[2:])
        self.menuFolder.actions()[newindex + 1].setText('>>' + self.menuFolder.actions()[newindex + 1].text())

        self.pickle_path = datadir + os.path.sep + 'pickle_dv'
        try:
            self.datafiles_list = pickle.load( open( self.pickle_path, "rb" ) )
        except:
            logger.warning("no pickle found, indexing all files once")
            self.datafiles_list = self.findFiles(datadir)
            pickle.dump(self.datafiles_list, open(self.pickle_path, "wb" ) )

        self.updateMeasurements(filter_str = '')

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

    def reloadFiles(self):
        self.datafiles_list = self.findFiles(self.current_dir)
        self.updateMeasurements()

    def updateToday(self):
        if self.filtered:
            # filtered view: skip update
            return
        root_folders = os.listdir(self.current_dir)

        non_date = [os.path.sep.join([self.current_dir, fol])
                    for fol in root_folders
                    if os.path.isdir(os.path.sep.join([self.current_dir, fol])) and not fol[0].isdigit()]
        check_folders = [self.current_dir] + non_date
        for cf in check_folders:
            # print('check', cf)
            root_folders = os.listdir(cf)
            date_folders = sorted([fol for fol in root_folders
                                   if os.path.isdir(os.path.sep.join([cf, fol]))
                                   and fol[0].isdigit()],
                                  reverse = True)

            for df in date_folders:
                # print(df)
                update_dir = os.path.sep.join([cf, df])
                # logger.info(f'Checking {update_dir} for new files')
                update_data = self.findFiles(update_dir)
                new_data = sorted(list(set(update_data) - set(self.datafiles_list)))
                try:
                    if cf == self.current_dir:
                        today_row = self._treemodel.findItems(df)[0]
                    else:
                        sub_folder = self._treemodel.findItems(cf.split(os.path.sep)[-1])[0]
                        today_row = [sub_folder.child(r)
                                     for r in range(sub_folder.rowCount())
                                     if sub_folder.child(r).text() == df][0]
                except:
                    today_row = None
                if not today_row:
                    new_row = QtGui.QStandardItem(df)
                    if cf == self.current_dir:
                        self._treemodel.appendRow(new_row)
                    else:
                        sub_folder.appendRow(new_row)
                    today_row = self._treemodel.findItems(df)[0]
                new_keys = list()
                for dat in new_data:
                    self.datafiles_list.append(dat)
                    key = dat.split(os.path.sep)[-2]
                    val = dat
                    if key not in new_keys:
                        child1 = QtGui.QStandardItem(key)
                        child2 = QtGui.QStandardItem('info about plot')
                        child3 = QtGui.QStandardItem(val)
                        today_row.insertRow(0, [child1, child2, child3])
                        new_keys.append(key)
                        self.data_view.sortByColumn(0, 1)

                if df in '\t'.join(self.datafiles_list):
                    break # Don't check old folders
        pickle.dump(self.datafiles_list, open(self.pickle_path, "wb" ) )

    def updateMeasurements(self, filter_str = None):
        ''' Update the list of measurements '''
        logger.info('updating measurements')


        dd = self.datafiles_list
        self.filtered = filter_str is not None and filter_str != ''
        if self.filtered:
            dd = [s for s in dd if filter_str in s]

        logger.info(f'DataViewer: found {len(dd)} files')

        filedict = self.genDict(dd)

        self.data_view.setSortingEnabled(False) # Turn off sorting for efficiency
        model = self._treemodel
        model.clear()
        model.setHorizontalHeaderLabels(['Log', 'Arrays', 'filename'])

        logger.debug('DataViewer: create gui elements')
        self.walkTree(filedict, model)

        self.data_view.setColumnWidth(0, 240)
        self.data_view.setColumnHidden(2, True)
        self.data_view.setSortingEnabled(True) # Turn on sorting
        self.data_view.sortByColumn(0, 1)

        logger.debug('DataViewer: updating measurements done')

    def genDict(self, pathlist):
        '''
        Creates a nested directory with directory name -> subdir or filename -> full path.
        '''
        filedict = {}
        path_len = len(self.current_dir.split(os.path.sep))
        for item in pathlist:
            p = filedict
            items = item.split(os.path.sep)[path_len:]
            for (i,x) in enumerate(items[:-1]):
                if i == len(items) - 2:
                    p = p.setdefault(x, item)
                else:
                    p = p.setdefault(x, {})
        return filedict

    def walkTree(self, filedict, basetree):
        for (key, val) in filedict.items():
            if not isinstance(val, dict):
                child1 = QtGui.QStandardItem(key)
                child2 = QtGui.QStandardItem('info about plot')
                child3 = QtGui.QStandardItem(val)
                basetree.appendRow([child1, child2, child3])
            else:
                folder_item = QtGui.QStandardItem(key)
                basetree.appendRow(folder_item)
                self.walkTree(val, folder_item)

    def showMeasurement(self, index):
        logger.info('showMeasurement: index %s' % str(index))

        oldtab_index = self.tabWidget.currentIndex()
        pp = index.parent()
        row = index.row()
        tag = pp.child(row, 1).data()
        filename = pp.child(row, 2).data()
        if tag is None:
            return

        logger.debug(f'DataViewer showMeasurement: tag {tag}, filename {filename}')

        try:
            logger.debug(f'DataViewer: load {filename}')
            data = self.loadData(filename)
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
            print('Error showMeasurement: %s' % str(e))
            logger.exception(e)

    def resetComboItems(self, data, keys):
        # Clearing old stuff
        self.clearLayout(self.data_select_lay)
        self.qplot.clear()
        self.boxes = dict()
        self.box_labels = dict()
        self.param_keys = list()
        to_plot = list()
        self.active_params = list()
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

        for param in self.subpl_ind.keys():
            if param in self.param_keys:
                self.boxes[param].setChecked(True)
                to_plot.append(param)
        self.data_select_lay.setLabelAlignment(QtCore.Qt.AlignLeft)

        # If no old parameters can be plotted, defined first one
        if not to_plot:
            try:
                def_key = list(self.boxes.values())[0].text()
                to_plot.append(self.boxes[def_key].text())
                self.boxes[def_key].setChecked(True)
            except:
                logger.warning("No data available to plot")

        # Update the parameter plots
        self.clearPlots()
        self.updatePlots(to_plot)
        if self.splitted:
            self.split_dataset()

    def clearPlots(self):
        self.qplot.clear()
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
        all_plots = {**dict.fromkeys(self.active_params), **dict.fromkeys(param_names)}
        for param_name in all_plots.keys():
            param = getattr(self.dataset, param_name)
            if param_name not in param_names:
                if param.shape == (1,):
                    self.removeValue(param_name)
                elif len(param.shape) < 3:
                    self.removePlot(param_name)
                else:
                    self.removeValue(param_name)
            elif param_name not in self.subpl_ind.keys():
                if param.shape == (1,):
                    self.addValue(param_name)
                elif len(param.shape) < 3:
                    self.addPlot(param_name)
                else:
                    self.addValue(param_name, val = f'{int(len(param.shape))}D data')

    def addPlot(self, plot):
        self.active_params.append(plot)
        logger.info(f'adding param {plot}')
        self.subpl_ind[plot] = len(self.subpl_ind)
        # self.qplot.add(getattr(self.dataset, plot), subplot = len(self.subpl_ind),
        #                 color = self.color_list[0])
        set_arr = getattr(self.dataset, plot).set_arrays
        d_arr = self.dataset.arrays[plot]

        if len( set_arr ) == 1:
            self.qplot.add(set_arr[0].ndarray, d_arr, subplot = len(self.subpl_ind),
                           xlabel = set_arr[0].label, xunit = set_arr[0].unit,
                           ylabel = d_arr.label, yunit = d_arr.unit,
                            color = self.color_list[0])
        elif len( set_arr ) == 2:
            self.qplot.add(set_arr[1].ndarray, set_arr[0].ndarray, d_arr.ndarray, subplot = len(self.subpl_ind),
                           xlabel = set_arr[1].label, xunit = set_arr[1].unit,
                           ylabel = set_arr[0].label, yunit = set_arr[0].unit,
                           zlabel = d_arr.label, zunit = d_arr.unit,
                            color = self.color_list[0])
        else:
            self.qplot.add(getattr(self.dataset, plot), subplot = len(self.subpl_ind),
                            color = self.color_list[0])


    def removePlot(self,plot):
        self.active_params.remove(plot)
        logger.info(f'removing param {plot}')
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

    def addValue(self, plot, val = None):
        self.active_params.append(plot)
        if not val:
            val = getattr(self.dataset, plot).ndarray[0]
        self.box_labels[plot].setText(str(val))

    def removeValue(self, plot):
        self.active_params.remove(plot)
        self.box_labels[plot].setText('')

    def loadData(self, filename):
        location = os.path.split(filename)[0]
        data = DataSet(location=location)
        try:
            data.read_metadata()
        except: pass
        io_manager = data.io
        self.io = io_manager
        data_files = io_manager.list(location)
        data_files = [df for df in data_files if df[-3:] == 'dat']
        ids_read = set()
        for fn in data_files:
            #size = os.path.getsize(fn)
            with io_manager.open(fn, 'r') as f:
                head = [next(f) for x in range(3)]
                dims = head[-1]
                datashape = list(map(int, dims[1:].strip().split('\t')))
                if not len(datashape) > 2:
                    with io_manager.open(fn, 'r') as f:
                        try:
                            data.formatter.read_one_file(data, f, ids_read)
                        except ValueError:
                            logger.warning('error reading file ' + fn)
                else:
                    logger.warning(f'Skipping "{fn}", data has {len(datashape)} dimensions')
                    print(datashape)
                    print(head[0][1:-1])
                    print(head[1][1:-1])
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
            pc_keys = [key for key in list(meta.keys()) if key.startswith('pc')]
            gate_keys = set([key for pc in pc_keys for key in meta[pc].keys() if not key.startswith('_')])
            try:
                baseband_freqs = meta['LOs']
            except:
                pass
            for (j, name) in enumerate(gate_keys):
                t0 = 0
                x_plot = list()
                y_plot = list()
                for pc in pc_keys:
                    legend_name = name.replace('_baseband','').replace('_pulses','')
                    x = list()
                    y = list()
                    try:
                        end_time = meta[pc]['_total_time']
                        while isinstance(end_time, list):
                            end_time = end_time[-1]
                    except:
                        end_time = max([x['stop'] for y in meta[pc].values() for x in y.values()])
                    try:
                        meta[pc][name]
                    except:
                        t0 += end_time
                        continue

                    if 'baseband' in name:
                        timepoints = set([x[key] for x in meta[pc][name].values() for key in ['start','stop']])
                        timepoints.add(end_time)
                        for tp in sorted(timepoints):
                            point1 = 0
                            point2 = 0
                            for (seg_name,seg_dict) in meta[pc][name].items():
                                if seg_dict['start'] < tp and seg_dict['stop'] > tp: # active segement
                                    # print(f'seg {seg_name} is active at tp {tp}, during pulse {name}')
                                    point1 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                    point2 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                elif seg_dict['start'] == tp:
                                    point2 += seg_dict['v_start']
                                elif seg_dict['stop'] == tp:
                                    point1 += seg_dict['v_stop']
                            x_plot += [tp + t0, tp + t0]
                            y_plot += [point1, point2]

                    elif 'pulses' in name:
                        try:
                            baseband = baseband_freqs[name.replace('_pulses','')]
                        except:
                            logger.warning('No baseband frequency found, assuming 0')
                            baseband = 0

                        for (seg_name,seg_dict) in meta[pc][name].items():
                            x_ar = np.arange(seg_dict['start'],seg_dict['stop'])
                            xx_ar = x_ar-seg_dict['start']
                            f_rl = (seg_dict['frequency'] - baseband)/1e9
                            y_ar = np.sin(2*np.pi*f_rl*xx_ar+seg_dict['start_phase'])*seg_dict['amplitude']
                            x = x + list(x_ar) + [seg_dict['stop']]
                            y = y + list(y_ar) + [0]
                            x_plot = x
                            y_plot = y
                    t0 += end_time

                self.pulse_plot.setLabel('left', 'Voltage', 'mV')
                self.pulse_plot.setLabel('bottom', 'Time', 'ns')
                self.pulse_plot.plot(x_plot, y_plot, pen = self.color_list[j%len(self.color_list)], name = legend_name)
            self.tabWidget.addTab(self.pulse_plot,'AWG Pulses')

    def pptCallback(self):
        if self.dataset is None:
            logger.warning('Cannot send data to PPT, no data selected')
        addPPT_dataset(self.dataset, customfig=self.qplot)

    def clipboardCallback(self):
        self.app.clipboard().setPixmap(self.qplot.win.grab())

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
