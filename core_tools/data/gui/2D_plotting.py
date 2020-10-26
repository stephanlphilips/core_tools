import pyqtgraph as pg

class _2D_plot:
    def __init__(self, ds_list, logmode):
        self.ds = ds

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # self.win = pg.GraphicsLayoutWidget(show=True, title="Scatter Plot Symbols")
        self.plot = pg.PlotWidget()
        # self.win.addWidget(self.plot)
        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        self.img.setImage(ds())

        self.plot.setLabel('left', self.ds.y.label, units=self.ds.y.unit)
        self.plot.setLabel('bottom', self.ds.x.label, units=self.ds.x.unit)


    def update(self):
        self.img.setImage(ds())
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
    ds = ds.m1[:, :]
    
    plot = _2D_plot(ds, logmode)
    plot.update()
    app.processEvents()


    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()