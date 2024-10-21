from core_tools.data.gui.plots.unit_management import format_unit, return_unit_scaler
from PyQt5 import QtCore, QtWidgets
from si_prefix import si_format
import pyqtgraph as pg

graph_color = list()
graph_color += [{"pen":(0,114,189), 'symbolBrush':(0,114,189), 'symbolPen':'w', "symbol":'p', "symbolSize":12}]
graph_color += [{"pen":(217,83,25), 'symbolBrush':(217,83,25), 'symbolPen':'w', "symbol":'h', "symbolSize":12}]
graph_color += [{"pen":(250,194,5), 'symbolBrush':(250,194,5), 'symbolPen':'w', "symbol":'t3', "symbolSize":12}]
graph_color += [{"pen":(54,55,55), 'symbolBrush':(55,55,55), 'symbolPen':'w', "symbol":'s', "symbolSize":12}]
graph_color += [{"pen":(119,172,48), 'symbolBrush':(119,172,48), 'symbolPen':'w', "symbol":'d', "symbolSize":12}]
graph_color += [{"pen":(19,234,201), 'symbolBrush':(19,234,201), 'symbolPen':'w', "symbol":'t1', "symbolSize":12}]
graph_color += [{'pen':(0,0,200), 'symbolBrush':(0,0,200), 'symbolPen':'w', "symbol":'o', "symbolSize":12}]
graph_color += [{"pen":(0,128,0), 'symbolBrush':(0,128,0), 'symbolPen':'w', "symbol":'t', "symbolSize":12}]
graph_color += [{"pen":(195,46,212), 'symbolBrush':(195,46,212), 'symbolPen':'w', "symbol":'t2', "symbolSize":12}]
graph_color += [{"pen":(237,177,32), 'symbolBrush':(237,177,32), 'symbolPen':'w', "symbol":'star', "symbolSize":12}]
graph_color += [{"pen":(126,47,142), 'symbolBrush':(126,47,142), 'symbolPen':'w', "symbol":'+', "symbolSize":12}]

class _1D_plot:
    def __init__(self, ds_list, logmode):
        '''
        plot 1D plot

        Args:
            ds_descr (list<dataset_data_description>) : list descriptions of the data to be plotted in the same plot
            logmode dict(<str, bool>) : plot axis in a logaritmic scale (e.g. {'x':True, 'y':False})
        '''
        self.ds_list = ds_list
        self.logmode = logmode

        # only change if still default
        if pg.getConfigOption('foreground') == 'd' and pg.getConfigOption('background') == 'k':
            pg.setConfigOption('background', None)
            pg.setConfigOption('foreground', 'k')

        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()

        self.plot = pg.PlotWidget()
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self.layout.addWidget(self.plot)
        self.layout.addWidget(self.label)
        self.widget.setLayout(self.layout)

        self.curves = []

        self.plot.addLegend()

        for i in range(len(self.ds_list)):
            ds = self.ds_list[i]
            curve = self.plot.plot(*self.get_x_and_y(ds), **graph_color[i], name=ds.label, connect='finite')
            self.curves.append(curve)
        self.plot.setLabel('left', self.ds_list[0].y.label, units=format_unit(self.ds_list[0].y.unit))
        self.plot.setLabel('bottom', self.ds_list[0].x.label, units=format_unit(self.ds_list[0].x.unit))
        self.plot.setLogMode(**logmode)
        self.plot.showGrid(True, True)
        if self.ds_list[0].y.unit == '%':
            self.plot.setYRange(0,1)
        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def update(self):
        for i in range(len(self.curves)):
            curve = self.curves[i]
            ds = self.ds_list[i]
            curve.setData(*self.get_x_and_y(ds), connect='finite')

    @property
    def name(self):
        name = "Plotting "
        for ds in self.ds_list:
            name += " {} +".format(ds.name)

        return name[:-1]

    def get_x_and_y(self, ds):
        return ds.x()*return_unit_scaler(ds.x.unit), ds.y()*return_unit_scaler(ds.y.unit)

    def mouseMoved(self, evt):
        vb = self.plot.getPlotItem().vb
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            index = int(mousePoint.x())

            x_val = mousePoint.x()
            if self.logmode['x'] == True:
                x_val = 10**x_val
            y_val = mousePoint.y()
            if self.logmode['y'] == True:
                y_val = 10**y_val

            self.label.setText("x={}, y={}".format(
                si_format(x_val, 3) + format_unit(self.ds_list[0].x.unit),
                si_format(y_val, 3) + format_unit(self.ds_list[0].y.unit)))
