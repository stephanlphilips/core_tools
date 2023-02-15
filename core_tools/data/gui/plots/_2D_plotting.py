from core_tools.data.gui.plots.unit_management import format_unit, return_unit_scaler
from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.pyplot import get_cmap
from si_prefix import si_format
import pyqtgraph as pg
import numpy as np
import logging

logger = logging.getLogger(__name__)

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
        self.x_unit_scaler = return_unit_scaler(self.ds.x.unit)
        self.y_unit_scaler = return_unit_scaler(self.ds.y.unit)
        self.value_unit_scaler = return_unit_scaler(self.ds.unit)
        self.logmode = {'x':False, 'y':False, 'z':False}

        pg.setConfigOption('background', None)
        pg.setConfigOption('foreground', 'k')

        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()

        self.plot = pg.PlotItem()
        self.plot.setLabel('bottom', self.ds.y.label, units = format_unit(self.ds.y.unit))
        self.plot.setLabel('left', self.ds.x.label, units = format_unit(self.ds.x.unit))
        self.img = pg.ImageItem()
        # set some image data. This is required for pyqtgraph > 0.11
        self.img.setImage(np.zeros((1,1)))

        self.img_view = pg.ImageView(view=self.plot, imageItem=self.img)
        self.img_view.setColorMap(get_color_map())
        self.img_view.ui.roiBtn.hide()
        self.img_view.ui.menuBtn.hide()
        self.img_view.ui.histogram.autoHistogramRange()

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self.layout.addWidget(self.img_view)
        self.layout.addWidget(self.label)
        self.widget.setLayout(self.layout)

        self.update()
        self.plot.setAspectLocked(False)

        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def update(self):
        try:
            # logger.info(f'updating {self.ds.name} {self.ds.y.name} vs {self.ds.x.name} ')
            x = self.ds.x()*self.x_unit_scaler
            y = self.ds.y()*self.y_unit_scaler

            if self.detect_log_mode(x):
                self.logmode['y'] = True
                x = np.log10(x)
            if self.detect_log_mode(y):
                self.logmode['x'] = True
                y = np.log10(y)

            x_args = np.argwhere(np.isfinite(x)).T[0]
            if len(x_args) == 0:
                # No data yet. Nothing to update.
                return
            x_limit = [np.min(x_args), np.max(x_args)]
            x_limit_num = (x[x_limit[0]], x[x_limit[1]])
            y_args = np.argwhere(np.isfinite(y)).T[0]
            y_limit = [np.min(y_args), np.max(y_args)]
            y_limit_num = (y[y_limit[0]], y[y_limit[1]])

            data = self.ds()
            data_cp = np.empty(data.shape)
            data_cp[:,:] = np.nan
            x_slice = slice(x_limit[0], x_limit[1]+1)
            y_slice = slice(y_limit[0], y_limit[1]+1)
            data_cp[x_slice, y_slice] = data[x_slice, y_slice]
            data = data_cp

            # X and Y seems to be swapped for image items (+ Y inverted)
            x_scale = abs(x_limit_num[1] - x_limit_num[0])/(x_limit[1] - x_limit[0])
            y_scale = abs(y_limit_num[1] - y_limit_num[0])/(y_limit[1] - y_limit[0])

            x_off_set = np.min(x[x_args])
            y_off_set = np.min(y[y_args])

            # flip axis is postive to negative scan
            if x_limit_num[0] > x_limit_num[1]:
                data = data[::-1, :]
            if y_limit_num[0] > y_limit_num[1]:
                data = data[:, ::-1]

            self.plot.invertY(False)
            self.img.setImage(data.T)

            if x_scale == 0 or np.isnan(x_scale):
                x_scale = 1
            else:
                x_off_set -= 0.5*x_scale
            if y_scale == 0 or np.isnan(y_scale):
                y_scale = 1
            else:
                y_off_set -= 0.5*y_scale
            tr = QtGui.QTransform()
            tr.translate(y_off_set, x_off_set)
            tr.scale(y_scale, x_scale)
            self.img.setTransform(tr)
            self.plot.setLogMode(x=self.logmode['x'], y=self.logmode['y'])
        except Exception:
            logger.error("Error in plot update", exc_info=True)

    def detect_log_mode(self, data):
        args = np.argwhere(np.isfinite(data)).T[0]

        if len(args) >= 3:
            log_diff_data = np.diff(np.log(np.abs(data[args] + 1e-90)))
            if np.isclose(log_diff_data[-1],log_diff_data[-2]):
                return True

        return False

    def mouseMoved(self, evt):
        try:
            vb = self.plot.vb
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            if self.plot.sceneBoundingRect().contains(pos):
                mousePoint = vb.mapSceneToView(pos)
                x_val = mousePoint.x()
                if self.logmode['x'] == True:
                    x_val = 10**x_val
                y_val = mousePoint.y()
                if self.logmode['y'] == True:
                    y_val = 10**y_val

                # Note: x and y are mixed up... x_val = ds.y(), y_val = ds.x()
                # ds.y is plotted on x-axis and vice versa.
                y = x_val
                x = y_val

                ds = self.ds
                # Note: numpy 1.22 has nanargmin, but we're still on python 3.7.
                # So use a[isnan(a)] = np.inf to remove nans
                d = np.abs(ds.x()*self.x_unit_scaler-x)
                d[np.isnan(d)] = np.inf
                ix = d.argmin()
                d = np.abs(ds.y()*self.y_unit_scaler-y)
                d[np.isnan(d)] = np.inf
                iy = d.argmin()
                value = ds()[ix,iy]
                value_formatted = si_format(value*self.value_unit_scaler, 3) if not np.isnan(value) else 'NaN '

                self.label.setText("x={}, y={}: {}".format(
                    si_format(y, 3) + format_unit(ds.y.unit),
                    si_format(x, 3) + format_unit(ds.x.unit),
                    value_formatted + format_unit(ds.unit)))
        except:
            logger.error('Error mouse move', exc_info=True)



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