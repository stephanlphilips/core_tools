from dataclasses import dataclass
from functools import partial
from PyQt5.QtCore import QThread
from PyQt5 import QtWidgets, QtGui
from PyQt5 import QtCore
import pyqtgraph as pg
import numpy as np
from scipy import ndimage
import time
import logging
from matplotlib import colormaps
from .colors import polar_to_rgb, compress_range

logger = logging.getLogger(__name__)

colormap = colormaps["viridis"]
colormap._init()
lut = np.array(colormap.colors)*255 # Convert matplotlib colormap from 0-1 to 0-255 for Qt

@dataclass
class plot_widget_data:
    plot_widget: pg.PlotWidget # widget.
    plot_items: list # line in the plot.
    color_bar: any = None

class plot_param:
    def __init__(self, multi_parameter, i):
        self.name = multi_parameter.names[i]
        self.label = multi_parameter.labels[i]
        self.unit = multi_parameter.units[i]
        self.shape = multi_parameter.shapes[i]
        self.ndim = len(self.shape)
        self.setpoints = multi_parameter.setpoints[i]
        self.setpoint_names = multi_parameter.setpoint_names[i]
        self.setpoint_labels = multi_parameter.setpoint_labels[i]
        self.setpoint_units = multi_parameter.setpoint_units[i]

    def xlabel(self, dim):
        # x0 .. xn
        return self.setpoint_labels[dim]

    def xunit(self, dim):
        # x0 .. xn
        return self.setpoint_units[dim]

    def xrange(self, dim):
        # in qcodes: ndim of setpoints has dimension ndim+1 in a tuple.
        # convert to numpy n*m array
        setpoints = np.array(self.setpoints[dim])
        base_index = (0,) * dim
        # return first and last value
        return setpoints[base_index+(0,)], setpoints[base_index+(-1,)]

    def get_index(self, *values):
        indices = []
        for i,value in enumerate(values):
            xrange = self.xrange(i)
            index = int((value-xrange[0]) / (xrange[1]-xrange[0]) * self.shape[i])
            if index < 0 or index >= self.shape[i]:
                index = None
            indices.append(index)
        return indices


class live_plot(QThread):

    def __init__(self,  top_layout, parameter_getter, averaging, gradient,
                 n_col, prog_bar=None, gate_values_label=None,
                 gates=None, refresh_rate_ms=100,
                 on_mouse_moved=None, on_mouse_clicked=None):
        '''
        init the class

        top_frame (QtWidgets.QFrame) : frame wherin to place the plots
        top_layout (QtWidgets.QGridLayout) : layout in the frame for the plots
        parameter_getter (QCoDeS multiparamter) : qCoDeS multiparamter that is used to get the data.
        averaging (int) : number of times the plot needs to be averaged.
        differentiate (bool) : differentiate plot - true/false
        n_col (int): max number of plots on a row
        '''
        super().__init__()

        self.n_plots = len(parameter_getter.names)
        self.top_layout = top_layout
        self.n_col = n_col
        self.prog_bar = prog_bar
        self.gate_values_label = gate_values_label
        self.gates = gates
        self.refresh_rate_ms = refresh_rate_ms
        self._on_mouse_moved = on_mouse_moved
        self._on_mouse_clicked = on_mouse_clicked
        self.gate_x_voltage = None
        self.gate_y_voltage = None
        self.active = False
        self.plt_finished = True
        self.clear_buffers = False
        self._buffers_need_resize = False

        # getter for the scan.
        self.parameter_getter = parameter_getter
        self.plot_params = [plot_param(parameter_getter, i) for i in range(self.n_plots)]
        self.shape = parameter_getter.shapes[0] #assume all the shapes are the same.
        self.plot_widgets = []

        # plot properties
        self._averaging = averaging
        self._gradient = gradient

        self.set_busy(True)

        # generate the buffers needed for the plotting and construct the plots.
        self.generate_buffers()
        self.init_plot()

        # make a updater to plot periodically plot what is in the buffer.
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)


    @property
    def averaging(self):
        return self._averaging

    @averaging.setter
    def averaging(self, value):
        if value == self._averaging:
            return

        self._averaging = value
        if self._averaging < 1:
            self._averaging = 1

        self._buffers_need_resize = True

    @property
    def gradient(self):
        return self._gradient

    @gradient.setter
    def gradient(self, value):
        self._gradient = value
        self.refresh()

    def generate_buffers(self):
        self.clear_buffers = False
        self.buffer_data = []
        self.plot_data = []
        self.plot_data_valid = False
        self.average_scans = 0
        for i in range(self.n_plots):
            plot_shape = self.plot_params[i].shape
            self.plot_data.append(np.zeros(plot_shape))
            buffer_shape = (self._averaging, *plot_shape)
            self.buffer_data.append(np.zeros(buffer_shape))

    def _resize_buffers(self):
        self._buffers_need_resize = False
        self.average_scans = min(self.average_scans, self._averaging)

        for i in range(self.n_plots):
            plot_shape = self.plot_params[i].shape
            old_buffer = self.buffer_data[i]
            n_copy = min(self._averaging, old_buffer.shape[0])
            new_shape = (self._averaging, *plot_shape)
            new_buffer = np.zeros(new_shape)
            new_buffer[:n_copy] = old_buffer[:n_copy]
            self.buffer_data[i] = new_buffer

    def start(self):
        self.active = True
        self.plt_finished = False
        self.timer.setSingleShot(False)
        # refresh rate of images in milliseconds
        self.timer.start(self.refresh_rate_ms)

        # start thread
        super().start()

    def stop(self):
        self.active = False
        self.set_busy(False)

        while self.plt_finished != True:
            time.sleep(0.01) # 10 ms interval to make sure gil releases.
        self.timer.stop()
        self.update_plot()

    def refresh(self):
        if not self.active:
            self.timer.setSingleShot(True)
            self.timer.start(1)

    def remove(self):
        self.timer.stop()
        self.timer.deleteLater()
        self.timer = None

        for plot in self.plot_widgets:
            self.top_layout.removeWidget(plot.plot_widget)
            plot.plot_widget.clear()
            plot.plot_widget.deleteLater()
            plot.plot_widget = None

        self.plot_widgets = []

    def set_busy(self, show):
        if show:
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("Busy")
            msg.setText("Loading waveforms and instrument program")
            msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
            msg.show()
            self.msg_box = msg
        else:
            self.msg_box.accept()
            self.msg_box.close()

    def _read_dc_voltage(self, gate_name):
        if self.gates is not None:
            try:
                return self.gates.get(gate_name)
            except Exception:
                logging.debug(f'Cannot read DC gate {gate_name}')

    def _format_dc_voltage(self, voltage):
        if voltage is not None:
            return f'{voltage:6.2f} mV'
        else:
            return ' - - -'


class _1D_live_plot(live_plot):

    def init_plot(self):
        self.prog_per = 0
        n_col = self.n_col
        for i in range(self.n_plots):
            param = self.plot_params[i]
            plot_1D = pg.PlotWidget()
            plot_1D.getAxis('left').enableAutoSIPrefix(enable=False)
            plot_1D.getAxis('bottom').enableAutoSIPrefix(enable=False)
            plot_1D.showGrid(x=True, y=True)
            plot_1D.setLabel('left', param.label, param.unit)
            plot_1D.setLabel('bottom', param.xlabel(0), param.xunit(0))

            cursor = QtCore.Qt.CrossCursor
            plot_1D.setCursor(cursor)

            icol = i % n_col
            irow = i // n_col
            self.top_layout.addWidget(plot_1D, irow, icol, 1, 1)

            xrange = param.xrange(0)[1]
            self.x_data = np.linspace(-xrange, xrange, self.plot_data[i].size)

            curve = plot_1D.plot(self.x_data, self.plot_data[i], pen=(255,0,0))
            plot_data = plot_widget_data(plot_1D, [curve])
            plot_data.proxy = pg.SignalProxy(plot_1D.scene().sigMouseMoved, rateLimit=10,
                                             slot=partial(self.mouse_moved, plot_1D, i))
            plot_data.proxy2 = pg.SignalProxy(plot_1D.scene().sigMouseClicked,
                                              slot=partial(self.mouse_clicked, plot_1D, i))
            self.plot_widgets.append(plot_data)

    def _read_dc_voltages(self):
        self.gate_x_voltage = self._read_dc_voltage(self.plot_params[0].setpoint_names[0])

    def _get_plot_coords(self, plot, index, coordinates):
        if plot.sceneBoundingRect().contains(coordinates):
            # filter on min/max
            mouse_point = plot.plotItem.vb.mapSceneToView(coordinates)
            x = mouse_point.x()
            ix = self.plot_params[index].get_index(x)[0]
            if ix is not None:
                return x, ix
        return None, None

    def mouse_clicked(self, plot, index, event):
        try:
            x, ix = self._get_plot_coords(plot, index, event[0].scenePos())
            if ix is None:
                return
            if self._on_mouse_clicked:
                self._on_mouse_clicked(x)
        except Exception as ex:
            print(ex)

    def mouse_moved(self, plot, index, event):
        try:
            x, ix = self._get_plot_coords(plot, index, event[0])
            if ix is None:
                return
            v = self.plot_data[index][ix] # TODO @@@ check with diff ...
            if self._on_mouse_moved:
                plot_param = self.plot_params[index]
                self._on_mouse_moved(x, plot_param.name, v)
        except Exception as ex:
            print(ex)
            print(ex.__traceback__)

    def update_plot(self):
        if not self.plot_data_valid:
            return
        self.set_busy(False)
        try:
            for i in range(len(self.plot_widgets)):
                y = self.plot_data[i]
                if self.gradient:
                    y = np.gradient(y)
                self.plot_widgets[i].plot_items[0].setData(self.x_data, y)
            self.prog_bar.setValue(self.prog_per)
            if self.gates is not None:
                gate_x = self.plot_params[0].setpoint_names[0]
                x_voltage_str = self._format_dc_voltage(self.gate_x_voltage)
                self.gate_values_label.setText(
                        f'DC {gate_x}:{x_voltage_str}')
        except:
            logger.error('Plotting failed', exc_info=True)
            # slow down to reduce error burst
            time.sleep(1.0)

    def run(self):
        while self.active:
            try:
                input_data = self.parameter_getter.get()
                self._read_dc_voltages()
                if self.clear_buffers:
                    self.generate_buffers()
                if self._buffers_need_resize:
                    self._resize_buffers()

                self.average_scans = min(self.average_scans+1, self._averaging)
                for i in range(self.n_plots):
                    buffer_data = self.buffer_data[i]
                    y = input_data[i]
                    buffer_data = np.roll(buffer_data,1,0)
                    buffer_data[0] = y
                    self.buffer_data[i] = buffer_data
                    self.plot_data[i] = np.sum(buffer_data, 0)/self.average_scans
                self.plot_data_valid = True
                self.prog_per = int(self.average_scans / self._averaging * 100)
            except Exception as e:
                self.plot_data_valid = True
                logger.error(f'Exception: {e}', exc_info=True)
                print('frame dropped (check logging)')
                # slow down to reduce error burst
                time.sleep(1.0)

        self.plt_finished = True


class _2D_live_plot(live_plot):

    _enhanced_contrast = False
    _filter_background = False
    _background_rel_sigma = 0.1
    _filter_noise = False
    _noise_sigma = 1.0

    def init_plot(self):
        n_col = self.n_col
        self.prog_per = 0
        self.min_max = []
        for i in range(self.n_plots):
            param = self.plot_params[i]
            plot_2D = pg.PlotWidget()
            plot_2D.setDefaultPadding(0.01)
            img = pg.ImageItem()
            # Note: lookup table is set via color bar
            plot_2D.addItem(img)
            plot_2D.getAxis('left').enableAutoSIPrefix(enable=False)
            plot_2D.getAxis('bottom').enableAutoSIPrefix(enable=False)
            plot_2D.setLabel('left', param.xlabel(0), param.xunit(0))
            plot_2D.setLabel('bottom', param.xlabel(1), param.xunit(1))

            plot_2D.setTitle(param.label, size='10pt')

            min_max = pg.LabelItem(parent=plot_2D.graphicsItem())
            min_max.anchor(itemPos=(1,0), parentPos=(1,0))
            self.min_max.append(min_max)

            icol = i % n_col
            irow = i // n_col
            self.top_layout.addWidget(plot_2D, irow, icol, 1, 1)

            range0 = param.xrange(0)[1] # y value
            range1 = param.xrange(1)[1] # x value
            shape = param.shape
            tr = QtGui.QTransform()
            tr.translate(-range1, -range0)
            tr.scale(1/shape[1]*range1*2, 1/shape[0]*range0*2)
            img.setTransform(tr)

            cursor = QtCore.Qt.CrossCursor
            img.setCursor(cursor)

            plot_data = plot_widget_data(plot_2D, [img])
            plot_data.proxy = pg.SignalProxy(img.scene().sigMouseMoved, rateLimit=10,
                                             slot=partial(self.mouse_moved, plot_2D, i))
            plot_data.proxy2 = pg.SignalProxy(img.scene().sigMouseClicked,
                                              slot=partial(self.mouse_clicked, plot_2D, i))
            self.plot_widgets.append(plot_data)

    def set_background_filter(self, enabled, rel_sigma):
        self._filter_background = enabled
        self._background_rel_sigma = rel_sigma
        self.refresh()

    def set_noise_filter(self, enabled, rel_sigma):
        self._filter_noise = enabled
        self._noise_sigma = rel_sigma
        self.refresh()

    def set_cross(self, enabled):
        if enabled:
            for pwd in self.plot_widgets:
                crosshair_color = (100, 100, 100)
                pwd.plot_widget.addLine(x=0, pen=crosshair_color)
                pwd.plot_widget.addLine(y=0, pen=crosshair_color)

    def set_colorbar(self, enabled):
        if enabled:
            for pwd in self.plot_widgets:
                cb = pg.ColorBarItem(colorMap='viridis', interactive=False, width=14)
                cb.setImageItem(pwd.plot_items[0], insert_in=pwd.plot_widget.plotItem)
                pwd.color_bar = cb

    def _get_plot_coords(self, plot, index, coordinates):
        if plot.sceneBoundingRect().contains(coordinates):
            # filter on min/max
            mouse_point = plot.plotItem.vb.mapSceneToView(coordinates)
            x,y = mouse_point.x(), mouse_point.y()
            iy,ix = self.plot_params[index].get_index(y,x)
            if iy is not None and ix is not None:
                return x, y, ix, iy
        return None, None, None, None

    def mouse_clicked(self, plot, index, event):
        try:
            x, y, ix, iy = self._get_plot_coords(plot, index, event[0].scenePos())
            if iy is None or ix is None:
                return
            if self._on_mouse_clicked:
                self._on_mouse_clicked(x, y)
        except Exception as ex:
            print(ex)

    def mouse_moved(self, plot, index, event):
        try:
            x, y, ix, iy = self._get_plot_coords(plot, index, event[0])
            if iy is None or ix is None:
                return
            v = self.plot_data[index][ix,iy]
            if self._on_mouse_moved:
                plot_param = self.plot_params[index]
                self._on_mouse_moved(x, y, plot_param.name, v)
        except Exception as ex:
            print(ex)

    @property
    def enhanced_contrast(self):
        return self._enhanced_contrast

    @enhanced_contrast.setter
    def enhanced_contrast(self, value):
        self._enhanced_contrast = value
        self.refresh()

    def _read_dc_voltages(self):
        self.gate_x_voltage = self._read_dc_voltage(self.plot_params[0].setpoint_names[1])
        self.gate_y_voltage = self._read_dc_voltage(self.plot_params[0].setpoint_names[0])

    def update_plot(self):
        try:
            if not self.plot_data_valid:
                return
            self.set_busy(False)
            for i in range(len(self.plot_widgets)):
                pwd = self.plot_widgets[i]
                color_bar = pwd.color_bar
                img_item = self.plot_widgets[i].plot_items[0]
                plot_data = self.plot_data[i] # @@@@ empty when clicking reset !! There is a race condition
                if self._filter_background:
                    sigma = self.plot_params[i].shape[0] * self._background_rel_sigma
                    plot_data = plot_data - ndimage.gaussian_filter(plot_data, sigma, mode = 'nearest')
                if self._filter_noise:
                    plot_data = ndimage.gaussian_filter(plot_data, self._noise_sigma, mode = 'nearest')
                if self.gradient == 'Off':
                    if self.enhanced_contrast:
                        plot_data = compress_range(plot_data, upper=99.5, lower=0.5)
                    mn, mx = np.min(plot_data), np.max(plot_data)
                    self.min_max[i].setText(f"min:{mn:4.0f} mV<br/>max:{mx:4.0f} mV")
                    if color_bar:
                        color_bar.setLevels(values=(mn,mx))
                        if img_item.lut is None:
                            img_item.setLookupTable(color_bar.colorMap().getLookupTable())
                    else:
                        img_item.setLookupTable(lut)
                elif self.gradient == 'Magnitude':
                    dx = ndimage.sobel(plot_data, axis=0, mode='nearest')
                    dy = ndimage.sobel(plot_data, axis=1, mode='nearest')
                    plot_data = np.hypot(dx, dy)
                    if self.enhanced_contrast:
                        plot_data = compress_range(plot_data, upper=99.8, lower=25)
                    mn, mx = np.min(plot_data), np.max(plot_data)
                    self.min_max[i].setText(f"min:{mn:4.0f} a.u.<br/>max:{mx:4.0f} a.u.")
                    if color_bar:
                        color_bar.setLevels(values=(mn,mx))
                        if img_item.lut is None:
                            img_item.setLookupTable(color_bar.colorMap().getLookupTable())
                    else:
                        img_item.setLookupTable(lut)
                elif self.gradient == 'Mag & angle':
                    dx = ndimage.sobel(plot_data, axis=0, mode='nearest')
                    dy = ndimage.sobel(plot_data, axis=1, mode='nearest')
                    mag = np.hypot(dx, dy)
                    angle = np.arctan2(dy, dx)
                    if self.enhanced_contrast:
                        mag = compress_range(mag, upper=99.8, lower=25, subtract_low=True)
                    plot_data = polar_to_rgb(mag, angle)
                    self.min_max[i].setText('  ')
                    img_item.setLookupTable(None)
                else:
                    logger.warning(f'Unknown gradient setting {self.gradient}')

                img_item.setImage(plot_data)
            self.prog_bar.setValue(self.prog_per)
            if self.gates is not None:
                gate_x = self.plot_params[0].setpoint_names[1]
                gate_y = self.plot_params[0].setpoint_names[0]
                x_voltage_str = self._format_dc_voltage(self.gate_x_voltage)
                y_voltage_str = self._format_dc_voltage(self.gate_y_voltage)
                self.gate_values_label.setText(
                        f'DC {gate_x}:{x_voltage_str}, {gate_y}:{y_voltage_str}')

        except Exception as e:
            logger.error(f'Exception plotting: {e}', exc_info=True)
            # slow down to reduce error burst
            time.sleep(1.0)

    def run(self):
        while self.active:
            try:
                input_data = self.parameter_getter.get()
                self._read_dc_voltages()

                if self.clear_buffers:
                    self.generate_buffers()
                if self._buffers_need_resize:
                    self._resize_buffers()

                self.average_scans = min(self.average_scans+1, self._averaging)
                for i in range(self.n_plots):
                    buffer_data = self.buffer_data[i]
                    xy = input_data[i][:, :].T
                    buffer_data = np.roll(buffer_data,1,0)
                    buffer_data[0] = xy
                    self.buffer_data[i] = buffer_data
                    self.plot_data[i] = np.sum(buffer_data, 0)/self.average_scans
                self.plot_data_valid = True
                self.prog_per = int(self.average_scans / self._averaging * 100)
            except Exception as e:
                self.plot_data_valid = True
                logger.error(f'Exception: {e}', exc_info=True)
                # slow down to reduce error burst
                time.sleep(1.0)

        self.plt_finished = True


