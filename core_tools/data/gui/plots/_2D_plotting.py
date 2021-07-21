from core_tools.data.gui.plots.unit_management import format_value_and_unit, format_unit, return_unit_scaler
from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.pyplot import get_cmap
from si_prefix import si_format
import pyqtgraph as pg
import numpy as np

class _2D_plot:
    def __init__(self, ds_descr, logmode=dict()):
        '''
        plot 2D plot
        
        Args:
            ds_descr (dataset_data_description) : description of the data
            logmode (dict) : logmode for the z axis -- not supported atm...

        Plotter can handle
            * only lineary/log spaced axis
            * flipping axis also supported
            (limitations due to image based implemenation in pyqtgraph)
        '''
        self.ds = ds_descr
        self.logmode = {'x':False, 'y':False, 'z':False}
        
        pg.setConfigOption('background', None)
        pg.setConfigOption('foreground', 'k')

        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()
        
        self.plot = pg.PlotItem()
        self.plot.setLabel('bottom', self.ds.y.label, units = format_unit(self.ds.y.unit))
        self.plot.setLabel('left', self.ds.x.label, units = format_unit(self.ds.x.unit))
        self.img = pg.ImageItem()
        self.img_view = pg.ImageView(view=self.plot, imageItem=self.img)
        self.img_view.setColorMap(get_color_map())

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self.layout.addWidget(self.img_view)
        self.layout.addWidget(self.label)
        self.widget.setLayout(self.layout)
        
        self.current_x_scale = 1
        self.current_y_scale = 1
        self.current_x_off_set = 0
        self.current_y_off_set = 0

        self.update()
        self.plot.setAspectLocked(False)
        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def update(self):
        x = self.ds.x()*return_unit_scaler(self.ds.x.unit)
        y = self.ds.y()*return_unit_scaler(self.ds.y.unit)

        if self.detect_log_mode(x):
            self.logmode['y'] = True
            x = np.log10(x)
        if self.detect_log_mode(y):
            self.logmode['x'] = True
            y = np.log10(y)
        try:
            x_args = np.argwhere(np.isfinite(x)).T[0]
            x_limit = [np.min(x_args), np.max(x_args)]
            x_limit_num = (x[x_limit[0]], x[x_limit[1]])
            y_args = np.argwhere(np.isfinite(y)).T[0]
            y_limit = [np.min(y_args), np.max(y_args)]
            y_limit_num = (y[y_limit[0]], y[y_limit[1]])
            
            data = self.ds()
            data_cp = np.empty(data.shape)
            data_cp[:,:] = np.nan
            data_cp[slice(*x_limit), slice(*y_limit)]= data[slice(*x_limit), slice(*y_limit)]
            data = data_cp
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

            self.plot.invertY(False)
            self.img.setImage(data.T)

            if x_scale != 0 and not np.isnan(x_scale) and x_scale != self.current_x_scale:
                # update coordinates
                off = x_off_set - self.current_x_off_set
                scale = x_scale/self.current_x_scale

                self.current_x_scale = x_scale
                self.current_x_off_set = x_off_set
                self.img.scale(1, scale)
                self.img.translate(0, off)

            if y_scale != 0 and not np.isnan(y_scale) and y_scale != self.current_y_scale:
                # update coordinates
                off = y_off_set - self.current_y_off_set
                scale = y_scale/self.current_y_scale

                self.current_y_scale = y_scale
                self.current_y_off_set = y_off_set
                self.img.scale(scale, 1)
                self.img.translate(off, 0)

            self.plot.setLogMode(**{'x': self.logmode['x'], 'y': self.logmode['y']})
        except:
            pass

    def detect_log_mode(self, data):
        args = np.argwhere(np.isfinite(data)).T[0]

        if len(args) >= 3:
            log_diff_data = np.diff(np.log(np.abs(data[args] + 1e-90)))
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

    def mouseMoved(self, evt):
        vb = self.plot.vb
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
                si_format(x_val, 3) + format_unit(self.ds.x.unit), 
                si_format(y_val, 3) + format_unit(self.ds.y.unit)))

def get_color_map():
    numofLines = 5
    cMapType = 'viridis'
    colorMap = get_cmap(cMapType) # get_cmap is matplotlib object     

    colorList = np.linspace(0, 1, numofLines) 
    lineColors = colorMap(colorList) 

    lineColors = lineColors * 255
    lineColors = lineColors.astype(int)
    return pg.ColorMap(pos=np.linspace(0.0, 1.0, numofLines), color=lineColors)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    from pyqtgraph.Qt import QtGui, QtCore
    from core_tools.data.SQL.connector import SQL_conn_info_local, SQL_conn_info_remote, sample_info, set_up_local_storage
    from core_tools.data.ds.data_set import load_by_uuid
    import time
    set_up_local_storage('stephan', 'magicc', 'test', 'Intel Project', 'F006', 'SQ38328342')
    ds = load_by_uuid(1603912517622618611)

    app = QtGui.QApplication([])


    ds = ds.m1
    plot = _2D_plot(ds)
    
    win = QtGui.QMainWindow()
    win.setCentralWidget(plot.widget)
    win.show()

    # import sys
    # if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    #     QtGui.QApplication.instance().exec_()