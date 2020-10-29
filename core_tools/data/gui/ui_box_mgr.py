from core_tools.data.gui._1D_plotting import _1D_plot
from core_tools.data.gui._2D_plotting import _2D_plot

class ui_box_mgr():
	def __init__(self, app, ui_box_data_mgrs, pyqt_draw_window):
		'''
		Manager that will generate the plots (connecting the selected settings from the user with the pyqtgraph plotting library

		Args:
			ui_box_data_mgrs (list<data_mgr_4_plot>) : data managers for every measurement parameter.
			pyqt_draw_window (tbd) : qt layout where the pyqt windows can be inserted in. 
		'''
		self.ui_box_mgrs = ui_box_data_mgrs
		self.pyqt_draw_window = pyqt_draw_window
		self.timer=QTimer()
		self.plot_windows = []
		self.app  = app
	def update(self):
		self.timer.stop()

		self.plot_windows = []
		for item in self.ui_box_mgrs:
			if item.ndim == 1 and item.enable == True:
				_1D_plot([item.ds], {'x':item.x_log, 'y':item.y_log})
			if item.ndim == 2 and item.enable == True:
				_2D_plot([item.ds], {'z':item.z_log})

		# update plot every 200 ms for a smooth plottin experience
		self.timer.timeout.connect(self.showTime)
		self.timer.start(300)


	def update_plots(self):
		for plot in self.plot_windows:
			plot.update()
		self.app.processEvents()