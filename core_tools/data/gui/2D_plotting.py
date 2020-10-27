import pyqtgraph as pg
from matplotlib.pyplot import get_cmap
import numpy as np

numofLines = 5
cMapType = 'viridis'
colorMap = get_cmap(cMapType) # get_cmap is matplotlib object     

colorList = np.linspace(0, 1, numofLines) 
lineColors = colorMap(colorList) 

lineColors = lineColors * 255
lineColors = lineColors.astype(int)
cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, numofLines), color=lineColors)

class _2D_plot:
    known_units = {"mA" : 1e-3, "uA" : 1e-6, "nA" : 1e-9, "pA" : 1e-12, "fA" : 1e-15, 
                    "nV" : 1e-9, "uV" : 1e-6, "mV" : 1e-3, 
                    "ns" : 1e-9, "us" : 1e-6, "ms" : 1e-3, 
                    "KHz" : 1e3, "MHz" : 1e6, "GHz" : 1e9 }

    def __init__(self, ds_descr):
        '''
        plot 2D plot
        
        Args:
            ds_descr (dataset_data_description) : description of the data

        Plotter can handle
            * only lineary/log spaced axis
            * flipping axis also supported
            (limitations due to image based implemenation in pyqtgraph)
        '''
        self.ds = ds_descr

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.plot= pg.PlotItem()
        self.img = pg.ImageView(view=self.plot)

        self.img.view.setAspectLocked(False)
        self.update()
        
        self.img.setColorMap(cmap)
        self.plot.setLabel('left', self.ds.y.label, units = self.fix_units(self.ds.y)[0])
        self.plot.setLabel('bottom', self.ds.x.label, units = self.fix_units(self.ds.x)[0])


    def update(self):
        logmode = {'x':False, 'y':False}

        x = self.ds.x()*self.fix_units(self.ds.x)[1]
        y = self.ds.y()*self.fix_units(self.ds.y)[1]

        if self.detect_log_mode(x):
            logmode['y'] = True
            x = np.log10(x)
        if self.detect_log_mode(y):
            logmode['x'] = True
            y = np.log10(y)

        x_args = np.argwhere(np.isfinite(x)).T[0]
        x_limit = [np.min(x_args), np.max(x_args)]
        x_limit_num = (x[x_limit[0]], x[x_limit[1]])
        y_args = np.argwhere(np.isfinite(y)).T[0]
        y_limit = [np.min(y_args), np.max(y_args)]
        y_limit_num = (y[y_limit[0]], y[y_limit[1]])
        
        data = self.ds()[slice(*x_limit), slice(*y_limit)]

        # X and Y seems to be swapped for image items (+ Y inverted)
        x_scale = abs(x_limit_num[1] - x_limit_num[0])/(x_limit[1] - x_limit[0])
        y_scale = abs(y_limit_num[1] - y_limit_num[0])/(y_limit[1] - y_limit[0])
        x_off_set = np.min(x[x_args])/x_scale
        y_off_set = np.min(y[y_args])/y_scale

        # flip axis is postive to negative scan
        if x_limit_num[0] > x_limit_num[1]:
            data = data[::-1, :]
        if y_limit_num[0] > y_limit_num[1]:
            data = data[:, ::-1]

        self.img.setImage(data.T)
        self.img.imageItem.scale(y_scale, x_scale)
        self.img.imageItem.translate(y_off_set, x_off_set)
        self.plot.setLogMode(**logmode)
        self.plot.setYRange(x_limit_num[0], x_limit_num[1])
        self.plot.setXRange(y_limit_num[0], y_limit_num[1])
        self.plot.invertY(False)
        # events are processed on a higher level.

    def detect_log_mode(self, data):
        args = np.argwhere(np.isfinite(data)).T[0]

        if len(args) >= 3:
            log_diff_data = np.diff(np.log(data[args] + 1e-90))
            if np.isclose(log_diff_data[-1],log_diff_data[-2]):
                return True

        return False

    def fix_units(self, descr):
        unit = descr.unit
        scaler = 1
        if descr.unit in self.known_units.keys():
            scaler = self.known_units[descr.unit]
            unit = descr.unit[1:]

        return unit, scaler

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    from pyqtgraph.Qt import QtGui, QtCore
    from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
    from core_tools.data.ds.data_set import load_by_uuid

    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
    ds = load_by_uuid(1603792891275642671)

    app = QtGui.QApplication([])
    win = QtGui.QMainWindow()
    win.resize(800,800)


    logmode = {'x':True, 'y':False}
    # 2d dataset
    ds = ds.m1[:, :]
    
    plot = _2D_plot(ds)
    win.setCentralWidget(plot.img)
    win.show()
    # plot.update()
    app.processEvents()


    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
