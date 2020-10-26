import pyqtgraph as pg

graph_color = list()
graph_color += [{"pen":(0,114,189), 'symbolBrush':(0,114,189), 'symbolPen':'w', "symbol":'p', "symbolSize":14}]
graph_color += [{"pen":(217,83,25), 'symbolBrush':(217,83,25), 'symbolPen':'w', "symbol":'h', "symbolSize":14}]
graph_color += [{"pen":(250,194,5), 'symbolBrush':(250,194,5), 'symbolPen':'w', "symbol":'t3', "symbolSize":14}]
graph_color += [{"pen":(54,55,55), 'symbolBrush':(55,55,55), 'symbolPen':'w', "symbol":'s', "symbolSize":14}]
graph_color += [{"pen":(119,172,48), 'symbolBrush':(119,172,48), 'symbolPen':'w', "symbol":'d', "symbolSize":14}]
graph_color += [{"pen":(19,234,201), 'symbolBrush':(19,234,201), 'symbolPen':'w', "symbol":'t1', "symbolSize":14}]
graph_color += [{'pen':(0,0,200), 'symbolBrush':(0,0,200), 'symbolPen':'w', "symbol":'o', "symbolSize":14}]
graph_color += [{"pen":(0,128,0), 'symbolBrush':(0,128,0), 'symbolPen':'w', "symbol":'t', "symbolSize":14}]
graph_color += [{"pen":(195,46,212), 'symbolBrush':(195,46,212), 'symbolPen':'w', "symbol":'t2', "symbolSize":14}]
graph_color += [{"pen":(237,177,32), 'symbolBrush':(237,177,32), 'symbolPen':'w', "symbol":'star', "symbolSize":14}]
graph_color += [{"pen":(126,47,142), 'symbolBrush':(126,47,142), 'symbolPen':'w', "symbol":'+', "symbolSize":14}]

class _1D_plot:
    def __init__(self, ds_list, logmode):
        self.ds_list = ds_list

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.win = pg.GraphicsLayoutWidget(show=True, title="Scatter Plot Symbols")
        self.plot = self.win.addPlot(title=self.name)
        self.curves = []
        
        self.plot.addLegend()
        for i in range(len(self.ds_list)):
            ds = self.ds_list[i]
            curve = self.plot.plot(ds.x(), ds.y(), **graph_color[i], name=ds.name)
            self.curves.append(curve)
        self.plot.setLabel('left', self.ds_list[0].y.label, units=self.ds_list[0].y.unit)
        self.plot.setLabel('bottom', self.ds_list[0].x.label, units=self.ds_list[0].x.unit)
        self.plot.setLogMode(**logmode)
        self.plot.showGrid(True, True)

    def update(self):
        for i in range(len(self.curves)):
            curve = self.curves[i]
            ds = self.ds_list[i]
            curve.setData(ds.x(), ds.y())
        # events are processed on a higher level.

    @property
    def name(self):
        name = "Plotting "
        for ds in self.ds_list:
            name += " {} +".format(ds.name)

        return name[:-1]


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    from pyqtgraph.Qt import QtGui, QtCore
    from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
    from core_tools.data.ds.data_set import load_by_uuid

    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
    ds = load_by_uuid(1603652809326642671)

    app = QtGui.QApplication([])
    
    logmode = {'x':True, 'y':False}
    # 2d dataset
    ds = [ds.m1[0, :], ds.m1[:, 0]]
    
    plot = _1D_plot(ds, logmode)
    plot.update()
    app.processEvents()


    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()