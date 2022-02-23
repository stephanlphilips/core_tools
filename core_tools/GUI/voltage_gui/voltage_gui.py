# -*- coding: utf-8 -*-
from .voltage_gui_GUI_window import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets
from functools import partial
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import logging
import numpy as np
try:
    import gdstk # Probably need to conda install -c conda-forge gdstk (or pip install gdstk) this
except:
    logging.warning('no gdstk, importing design not possible')
import pickle
from dataclasses import dataclass
from core_tools.data.ds.data_set import load_by_id

@dataclass
class poly_data_obj:
    points : any
    gate_name : any
    gate_layer: any

@dataclass
class plotter_figure:
    figure : any
    axis : any
    canvas : any
    colorbar: any
    colorbar_scaler: any

class voltage_plotter_pyqt(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for voltage_plotter_pyqt"""
    def __init__(self, gates, device_name):
        instance_ready = True
        
        self.gates = gates
        self.fc = 'white'
        self.cmap_diff = cm.seismic
        self.cmap = cm.hot_r
        
        self.polygons = list()
        
        self.plotter_figures = list()
        self.ds_plotter_figures = list()
        
        self._layers = list()
        
        self._split = False
        self._ds_split = False
        self._ds_diff = False
        
        self.filename = device_name
        
        # set graphical user interface
        self.app = QtCore.QCoreApplication.instance()
        if self.app is None:
            instance_ready = False
            self.app = QtWidgets.QApplication([])

        super(QtWidgets.QMainWindow, self).__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        
        try:
            self.load_layout()
        except:
            self.init_gui()
            logging.warning(f'layout of {self.filename} not found, initializing blank')
        
        self.draw_ds_plots()
        
        self._enabled_check.setChecked(True)
        self._ds_enabled_check.setChecked(True)
        self._split_check.setChecked(False)

        self._enabled_check.clicked.connect(partial(self._enable_call, 'main', self._enabled_check.isChecked))
        self._split_check.clicked.connect(partial(self._split_call, self._split_check.isChecked))
        
        self._load_layout_name.clicked.connect(partial(self._layout_name_call, self._layout_name.text))
        self._load_design_file.clicked.connect(self.getfile)
        self._add_layer_button.clicked.connect(partial(self._add_layer_call, self._add_layer_name.text))
        self._del_layer_button.clicked.connect(partial(self._del_layer_call, self._del_layer_name.currentText))
        self._load_ds_button.clicked.connect(partial(self._load_ds_call, self._load_ds_text.text))
        self._ds_split_check.clicked.connect(partial(self._ds_setting_call, 'split', self._ds_split_check.isChecked))
        self._ds_diff_check.clicked.connect(partial(self._ds_setting_call, 'diff', self._ds_diff_check.isChecked))
        self._ds_enabled_check.clicked.connect(partial(self._enable_call, 'ds', self._ds_enabled_check.isChecked))
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(1000)

        self.show()
        if instance_ready == False:
            self.app.exec()
    
    @property
    def layers(self):
        return sorted(self._layers)
    
    def init_gui(self):
        self._clear_gate_layout()
        self._add_gates()

        self.id_pf = self.create_plots(self._gate_plotter_layout, False, False)
        self._id_poly_handles = self.plot_gates(self.id_pf)

        self._del_layer_name.clear()
        for layer in self.layers:
            self._del_layer_name.addItem(layer)
    
    def draw_main_plots(self):
        self.delete_plots(self.plotter_figures)
        self.plotter_figures = self.create_plots(self._plotter_layout, self._split, False)
        self._main_poly_handles = self.plot_gates(self.plotter_figures)
        self.color_voltages(self._main_poly_handles, self.get_voltages(), self.plotter_figures, self._split, False)
    
    def draw_ds_plots(self):
        self.delete_plots(self.ds_plotter_figures)
        self.ds_plotter_figures = self.create_plots(self._ds_plotter_layout, self._ds_split, self._ds_diff)
        self._ds_poly_handles = self.plot_gates(self.ds_plotter_figures)
        self.color_ds_plots()
    
    def color_ds_plots(self):
        current_volts = self.get_voltages()
        volts = dict()
        for poly in self.polygons:
            gn = poly.gate_name
            try:
                if self._ds_diff:
                    volts[gn] = current_volts[gn] - self._ds_volts[gn]
                else:
                    volts[gn] = self._ds_volts[gn]
            except:
                volts[gn] = 0
        self.color_voltages(self._ds_poly_handles, volts, self.ds_plotter_figures, self._ds_split, self._ds_diff)
    
    def add_layers(self, layers):
        print(f'add {layers}')
        if type(layers) is str:
            layers = [layers]
        
        for lay in layers:
            if lay and lay not in self._layers:
                self._layers.append(lay)
        
        self.init_gui()
        self.draw_main_plots()
    
    def remove_layers(self, layers):
        print(f'removing {layers}')
        if type(layers) is not list or type(layers) is not tuple:
            layers = [layers]
        
        for lay in layers:
            self._layers.remove(lay)
        
        self.init_gui()
    
    def getfile(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 
                                                      'c:\\',"Layout files (*.gds *.oas *.GDS *.OAS)")
        try:
            self.load_pattern(fname[0], fname[0].split('.')[-1].lower())
        except Exception as e:
            print(e)
            logging.warning(f'file invalid: {fname[0]}')
              
    
    def import_data(self, gn, gl, points):
        self.polygons = list()
        for n,l,p in zip(gn,gl,points):
            polygon = poly_data_obj(p, n, l)
            self.polygons.append(polygon)         
    
    def load_pattern(self, filename, filetype = 'gds'):
        
        if filetype not in ['gds', 'oas']:
            raise ValueError(f'filetype {filetype} is invalid, only gds or oas allowed.')
        
        self.polygons = list()
        if filetype == 'gds':
            lib = gdstk.read_gds(filename)
        else:
            lib = gdstk.read_oas(filename)

        topcell = lib.cells[0]
        
        all_layers = {str(pg.layer) for pg in topcell.polygons}
        self._layers += list(all_layers)
        
        for i, pg in enumerate(topcell.polygons):
            polygon = poly_data_obj(pg.points, f'G{i}', str(pg.layer))
            self.polygons.append(polygon)
        
        self.init_gui()
        self.draw_main_plots()
        self.save_layout()

    def save_layout(self):
        filename = self.filename + '.pickle'
        with open(filename, 'wb') as f:
            pickle.dump(self.polygons, f)
    
    def load_layout(self):
        filename = self.filename + '.pickle'
        with open(filename, 'rb') as f:
            self.polygons = pickle.load(f)
        
        self._layout_name.setText(self.filename)
        self.add_layers(list(set([p.gate_layer for p in self.polygons])))
        self.draw_main_plots()
    
    def delete_plots(self, plotter_figures):
        for pf in plotter_figures:
            pf.canvas.close()
            
    def create_plots(self, frame, split, diff):
        if split:
            n_plots = len(self.layers)
            titles = self.layers
        else:
            n_plots = 1
            titles = ['all layers']
        
        plotter_figures = list()
        for k in range(n_plots):
            figure = Figure()
            canvas = FigureCanvas(figure)
            policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, 
                                           QtWidgets.QSizePolicy.Preferred)
            policy.setHeightForWidth(True)
            canvas.setSizePolicy(policy)
            
            ax = figure.add_axes([0,0,1,0.85])
            ax.set_aspect('equal')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_facecolor('grey')
            ax.title.set_text(titles[k])
            cbaxes = figure.add_axes([0, 0.95, 1, 0.05]) 
            if diff:
                cmap = self.cmap_diff
            else:
                cmap = self.cmap
            cb_scaler = cm.ScalarMappable(cmap = cmap)
            cb = figure.colorbar(cb_scaler,orientation="horizontal", cax = cbaxes)
            
            frame.addWidget(canvas, 0, k, 1, 1)
            
            pf = plotter_figure(figure, ax, canvas, cb, cb_scaler)
            plotter_figures.append(pf)  
        return plotter_figures
    
    def get_voltages(self):
        volts = dict()
        for poly in self.polygons:
            gn = poly.gate_name
            
            try:
                volt = getattr(self.gates, gn)()
            except:
                volt = np.random.randint(-1000, 0)/1000
            volts[gn] = volt
        return volts
    
    def color_voltages(self, phs, volts, plotter_figures, split, diff):
        # check min/max per fg
        normalizers = []
        if split:
            for i in range(len(plotter_figures)):
                layer = self.layers[i]
                rel_volts = [volts[poly.gate_name] for poly in self.polygons if poly.gate_layer == layer]
                minV = min(rel_volts, default = 0)
                maxV = max(rel_volts, default=1)
                absmax = max((abs(minV), abs(maxV), 1))
                if diff:
                    norm = Normalize(vmin=-absmax, vmax=absmax)
                else:
                    norm = Normalize(vmin=minV, vmax=maxV)
                normalizers.append(norm)
        else:
            maxV = max(volts.values(), default = 1)
            minV= min(volts.values(), default = -1)
            absmax = max((minV, maxV))
            if diff:
                norm = Normalize(vmin= -absmax, vmax= absmax)
            else:
                norm = Normalize(vmin = minV, vmax = maxV)

            normalizers.append(norm)
            normalizers *= max(len(self.layers), 1)
        
        if diff:
            cmap = self.cmap_diff
        else:
            cmap = self.cmap
                
        invalid_layer = False
        for i, poly in enumerate(self.polygons):
            v = volts[poly.gate_name]
            layer = poly.gate_layer
            try:
                fig_index = self.layers.index(layer)
            except:
                invalid_layer = True
                fig_index = 0
            norm = normalizers[fig_index]
            ph = phs[i]
            ph.set_facecolor(cmap(norm(v)))

        if invalid_layer:
            logging.warning('Please specify at least one layer. Plotting, but '
                            'will keep shouting this error until a layer is '
                            'added...')

        for i, pf in enumerate(plotter_figures):
            pf.colorbar_scaler.set_clim(vmin = normalizers[i].vmin, vmax = normalizers[i].vmax)
            pf.canvas.draw()
            
    
    def plot_gates(self, plotter_figures):
        poly_handles = list()
        for poly in self.polygons:
            if len(plotter_figures) > 1:
                i = self.layers.index(poly.gate_layer)
                ax = plotter_figures[i].axis
            else:
                ax = plotter_figures[0].axis
            
            ph = ax.fill(poly.points[:,0], poly.points[:,1], facecolor = self.fc)
            poly_handles.append(ph[0])
            
        minx = min([p.points[:,0].min() for p in self.polygons], default = 0)
        maxx = max([p.points[:,0].max() for p in self.polygons], default = 1)
        miny = min([p.points[:,1].min() for p in self.polygons], default = 0)
        maxy = max([p.points[:,1].max() for p in self.polygons], default = 1)     
        
        for pf in plotter_figures:
            pf.axis.set_xlim(minx, maxx)
            pf.axis.set_ylim(miny, maxy)
            pf.canvas.draw()
        
        return poly_handles

    def load_dataset(self, ds_id):
        print(f'load{ds_id}')
        try:
            ds = load_by_id(ds_id)
        except:
            pass
        volts = dict()
        for poly in self.polygons:
            gn = poly.gate_name
            try:
                volt = ds.snapshot['station']['instruments']['gates']['parameters'][gn]['value']
            except:
                volt = 0
            
            volts[gn] = volt
        
        self.ds_plotter_figures = self.create_plots(self._ds_plotter_layout, self._ds_split, self._ds_diff)
        self._ds_poly_handles = self.plot_gates(self.ds_plotter_figures)
        self._ds_volts = volts
        self.color_ds_plots()
        self._clear_voltages()
        self._add_voltages(volts)
        
    def _clear_gate_layout(self):
        layout = self._gate_container
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)
    
    def _clear_voltages(self):
        layout = self._ds_voltage_layout
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)        
    
    def _add_voltages(self, volts):
        layout = self._ds_voltage_layout
        volts = dict(sorted(volts.items()))
        for i, (key, val) in enumerate(volts.items()):  
            gate_name = QtWidgets.QLabel(self.ds_tab)
            gate_name.setObjectName(key + "_voltage_key")
            gate_name.setText(key)
            layout.addWidget(gate_name, i, 0, 1, 1)
    
            gate_val = QtWidgets.QLabel(self.ds_tab)
            gate_val.setObjectName(key + "_voltage_val")
            gate_val.setText(f'{val:.1f}')
            layout.addWidget(gate_val, i, 1, 1, 1)
            

    def _add_gates(self):
        layout = self._gate_container
        for i, poly in enumerate(self.polygons):
            gn = poly.gate_name
            name = f'polygon{i}'
    
            _translate = QtCore.QCoreApplication.translate
    
            highlight_input = QtWidgets.QCheckBox(self.gate_mapping)
            highlight_input.setObjectName(name + "_checkbox")
            highlight_input.clicked.connect(partial(self._highlight_gate, i, highlight_input.isChecked))
            layout.addWidget(highlight_input, i, 0, 1, 1)
    
            gate_name = QtWidgets.QLineEdit(self.gate_mapping)
            gate_name.setObjectName(name + "_name")
            gate_name.setText(_translate("MainWindow", gn))
            gate_name.textChanged.connect(partial(self._change_gatename, i, gate_name.text))
            layout.addWidget(gate_name, i, 1, 1, 1)
            
            gate_layer = QtWidgets.QComboBox(self.gate_mapping)
            gate_layer.setObjectName(name + "_layer")
            for lay in self.layers:
                gate_layer.addItem(lay)
                try:
                    if poly.gate_layer:
                        gate_layer.setCurrentText(poly.gate_layer)
                    else:
                        poly.gate_layer = gate_layer.currentText()
                except:
                    pass
            gate_layer.currentTextChanged.connect(partial(self._change_gatelayer, i, gate_layer.currentText))
            layout.addWidget(gate_layer, i, 2, 1, 1)
            
    def _change_gatename(self, i, data):
        self.polygons[i].gate_name = data()
        self.save_layout()
    
    def _change_gatelayer(self, i, data):
        self.polygons[i].gate_layer = data()
        self.save_layout()
    
    def _highlight_gate(self, i, param):
        ph = self._id_poly_handles[i]
        if param():
            ph.set_facecolor('red')
        else:
            ph.set_facecolor(self.fc)
        
        self.id_pf[0].canvas.draw()
    
    def _add_layer_call(self, param):
        self.add_layers(param())
    
    def _del_layer_call(self, param):
        self.remove_layers(param())
    
    def _layout_name_call(self, param):
        self.filename = param()
        self.save_layout()
    
    def _load_ds_call(self, param):
        self.load_dataset(param())
    
    def _ds_setting_call(self, setting, param):
        setattr(self, f'_ds_{setting}', param())
        if setting == 'split':
            self.draw_ds_plots()        
        else:
            self.color_ds_plots()
    
    def _enable_call(self, tab, param):
        state = param()
        if tab == 'ds':
            self._enabled_check.setChecked(state)
        else:
            self._ds_enabled_check.setChecked(state)
        
        if state:
            self.timer.start(1000)
        else:
            self.timer.stop()
    
    def _split_call(self, param):
        self._split = param()
        self.draw_main_plots()
        
    def _update(self):
        if self.polygons:
            if self.tabWidget.currentIndex() == 0:
                self.color_voltages(self._main_poly_handles, self.get_voltages(), self.plotter_figures, self._split, False)
            elif self.tabWidget.currentIndex() == 1:
                self.color_ds_plots()
        else:
            logging.warning('No layout present, cannot plot, turning off update.')
            self._enabled_check.setChecked(False)
            self._ds_enabled_check.setChecked(False)
            self.timer.stop()
            
    def closeEvent(self, event):
        """
        overload the Qt close funtion. Make sure that all timers are stopped.
        """
        self.timer.stop()
        logging.info('Window closed')
        