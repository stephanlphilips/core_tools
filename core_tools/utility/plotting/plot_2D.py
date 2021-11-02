import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import copy

from core_tools.utility.plotting.plot_settings import plot_layout, graph_settings_2D, _2D_raw_plot_data
from core_tools.utility.plotting.plot_general import _data_plotter


class plotter_2D(_data_plotter):
	def __init__(self, plt_layout = plot_layout(), graph_setings = graph_settings_2D()):
		self.plot_layout = plt_layout
		self.local_data = np.empty([plt_layout.n_plots_y, plt_layout.n_plots_x], dtype = _2D_plot_single)

		for i in range(self.local_data.size):
			self.local_data.flat[i] = _2D_plot_single(graph_setings)



class _2D_plot_single:
	def __init__(self, graph_settings):
		self.data     = _2D_raw_plot_data(None, None, None, graph_settings)

	def set_labels(self, xlabel, ylabel, zlabel):
		self.data.settings.xlabel = xlabel
		self.data.settings.ylabel = ylabel
		self.data.settings.zlabel = zlabel

	def add_data(self, z, x=None, y=None, settings = None, c_map=None):
		if settings is not None:
			settings.xlabel =self.data.settings.xlabel
			settings.ylabel =self.data.settings.ylabel
			settings.zlabel =self.data.settings.zlabel

			self.data.settings = settings
		if c_map is not None:
			self.data.settings.c_map = c_map

		self.data = _2D_raw_plot_data(z, x, y, self.data.settings)

	def _render(self, ax, layout_settings, index, scaler = 1, figure=None):	
		settings = dict()
		settings['cmap'] = self.data.settings.cmap
		settings['shading'] = 'auto'
		
		# ticks outward seem to look nicest.
		# ax.tick_params(direction='in', which='both', top=True, right=True)

		if self.data.settings.zlog == True:
			settings['norm'] = mpl.colors.LogNorm()
		if self.data.settings.xlog == True:
			ax.set_xscale('log')
		if self.data.settings.ylog == True:
			ax.set_yscale('log')

		if self.data.x_data is None:
			c = ax.pcolormesh(self.data.z_data, **settings, rasterized=True)
		else:
			c = ax.pcolormesh(self.data.x_data, self.data.y_data, self.data.z_data, **settings, rasterized=True)
		
		if self.data.settings.cbar == True:
			cbar = figure.colorbar(c, ax=ax)
			cbar.ax.set_ylabel(self.data.settings.zlabel)

		if self.data.settings.xlabel is not None:
			if layout_settings.share_x == False:
				ax.set_xlabel(self.data.settings.xlabel)
			elif index[0] == 0 :
				ax.set_xlabel(self.data.settings.xlabel)

		if self.data.settings.ylabel is not None:
			if layout_settings.share_y == False:
				ax.set_ylabel(self.data.settings.ylabel)
			elif index[1] == 0 :
				ax.set_ylabel(self.data.settings.ylabel)


if __name__ == '__main__':
	a = np.linspace(0,1235, 20*20).reshape(20,20)
	x_s = np.linspace(0,25, 20)
	x,y = np.empty([20,20]), np.empty([20,20])
	y_s = np.linspace(-5, 20, 20)
	for i in range(20):
		x[i] = x_s
		y[:,i] = y_s

	p = plotter_2D()
	p[0].set_labels('x label', 'y label', 'z label')
	settings = graph_settings_2D
	settings.zlog = True
	p[0].add_data(1.1**a,2* x, 2*y, settings= settings)
	p.save('test2D_11')

	a = np.linspace(0,1235, 20*20).reshape(20,20)
	p = plotter_2D(plot_layout(n_plots_x = 2,n_plots_y = 1, share_x=False, share_y=False))

	settings = graph_settings_2D
	settings.cbar = True
	p[0].set_labels('x label', 'y label', 'z label')
	p[0].add_data(a,2* x, 2*y, settings=settings)

	

	p[1].set_labels('x label', 'y label', 'z label')
	p[1].add_data(a,2* x, 2*y)
	p.save('test2D_21')
	plt.show()