import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import copy

from core_tools.utility.plotting.plot_settings import plot_layout, graph_settings_1D, _1D_raw_plot_data
from core_tools.utility.plotting.plot_general import _data_plotter

class plotter_1D(_data_plotter):
	def __init__(self, plt_layout = plot_layout(), graph_setings = graph_settings_1D()):
		self.plot_layout = plt_layout
		self.local_data = np.empty([plt_layout.n_plots_y, plt_layout.n_plots_x], dtype = _1D_plot_single)

		for i in range(self.local_data.size):
			self.local_data.flat[i] = _1D_plot_single(graph_setings)

class _1D_plot_single:
	def __init__(self, graph_settings):
		self.settings = copy.copy(graph_settings) #default settings
		self.data     = []
		self.x_lim    = None
		self.y_lim    = None

	def set_labels(self, xlabel, ylabel):
		self.settings.xlabel = xlabel
		self.settings.ylabel = ylabel

	def set_range(self, x_range=None, y_range=None):
		if x_range is not None:
			self.x_lim = x_range
		if y_range is not None:
			self.y_lim = y_range


	def add_data(self, x, y, xerr = None, yerr = None, label = None, settings = None, w=None, c=None, alpha=None):
		if settings == None:
			settings = copy.copy(self.settings)
		else:
			settings = copy.copy(settings)
		if label is not None:
			settings.label = label
		if w is not None:
			if 'l' not in w:
				settings.linestyle  = ''
			if 'p' in w:
				settings.marker = 'o'
		if c is not None:
			settings.color = c
		if alpha is not None:
			settings.alpha = alpha

		self.data += [_1D_raw_plot_data(x,y, xerr, yerr, settings)]

	def add_bardata(self, x,y, width=1, xerr = None, yerr = None, label = None, w=None, c=None, alpha=None, settings = None):
		if settings == None:
			settings = copy.copy(self.settings)
		else:
			settings = copy.copy(settings)
		if label is not None:
			settings.label = label
		if w is not None:
			if 'l' not in w:
				settings.linestyle  = ''
			if 'p' in w:
				settings.marker = 'o'
		if c is not None:
			settings.color = c
		if alpha is not None:
			settings.alpha = alpha

		self.data += [_1D_raw_plot_data(x,y, xerr, yerr, settings)]

	def _render(self, ax, layout_settings, index, scaler = 1, figure=None):
		ax.locator_params(axis='x', nbins=layout_settings.xbins)
		ax.locator_params(axis='y', nbins=layout_settings.ybins)
	

		ax.xaxis.set_minor_locator(mpl.ticker.AutoMinorLocator())
		ax.yaxis.set_minor_locator(mpl.ticker.AutoMinorLocator())
		
		ax.tick_params(direction='in', which='both', top=True, right=True)
		if self.settings.xlog == True:
			ax.set_xscale('log')
		if self.settings.ylog == True:
			ax.set_yscale('log')

		if self.x_lim is not None:
			ax.set_xlim(*self.x_lim)
		if self.y_lim is not None:
			ax.set_ylim(*self.y_lim)

		labels = False
		for i in range(len(self.data)):
			data = self.data[i]
			if data.x_error == None and data.y_error == None:
				ax.plot(data.x_data, data.y_data, **data.settings.plot_settings_to_dict(i, scaler), rasterized=True)
			else:
				pass
				# ax.errorbar(a, c, yerr = b/10,ecolor='g',linewidth=1.2,elinewidth=0.7)
			if data.settings.label is not None:
				labels = True

		if self.settings.xlabel is not None:
			if layout_settings.share_x == False:
				ax.set_xlabel(self.settings.xlabel)
			elif index[0] == layout_settings.n_plots_x-1 :
				ax.set_xlabel(self.settings.xlabel)

		if self.settings.ylabel is not None:
			if layout_settings.share_y == False:
				ax.set_ylabel(self.settings.ylabel)
			elif index[1] == 0 :
				ax.set_ylabel(self.settings.ylabel)

		if labels == True:
			ax.legend()

# TODO add log scale support !!!


if __name__ == '__main__':

	from colors import MATERIAL_COLOR, Red

	# global settings
	g = graph_settings_1D()
	g.color = Red[::-1]
	g.linewidth = 1

	a = plotter_1D(graph_setings=g)
	a[0].set_labels('x_label', 'y_label')
	a[0].add_data(np.linspace(0,50,200), np.sin(np.linspace(10,50,200)), w = 'p', alpha = 1, c=Red[5])
	a[0].add_data(np.linspace(0,50,200), np.sin(np.linspace(10,50,200)), w = 'l', alpha = 0.3, c=Red[5])

	# a.plot()
	a.save('test1D_single.svg')

	a = plotter_1D(plot_layout(n_plots_x = 1,n_plots_y = 2))

	a[0].set_labels('x_label', 'y_label')
	a[0].add_data(np.linspace(10,50,50), np.random.random([50]))

	a[0,1].set_labels('x_label', 'y_label')
	a[0,1].add_data(np.linspace(10,50,50), np.random.random([50]))

	a.save('test1D_12.svg')
	# a.plot()


	a = plotter_1D(plot_layout(n_plots_x = 2,n_plots_y = 2, share_x=True, share_y=True))

	a[0].set_labels('x_label', 'y_label')
	a[0].add_data(np.linspace(10,50,50), np.random.random([50]), label='test 1')

	a[0,1].set_labels('x_label', 'y_label')
	a[0,1].add_data(np.linspace(10,50,50), np.random.random([50]), label='test 2')
	a[0,1].add_data(np.linspace(10,50,50), np.random.random([50]))

	a[1,0].set_labels('x_label', 'y_label')
	a[1,0].add_data(np.linspace(10,50,50), np.random.random([50]))

	a[1,1].set_labels('x_label', 'y_label')
	a[1,1].add_data(np.linspace(10,50,50), np.sin(np.linspace(10,50,50)))
	a.save('test1D_22.svg')
	# a.plot()

	
	a = plotter_1D(plot_layout((300, 70), n_plots_x = 6,n_plots_y = 1, share_x=False, share_y=True))

	a[0].set_labels('time (ns)', 'Spin up probably (%)')
	a[0].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))

	a[1].set_labels('time (ns)', 'Spin up probably (%)')
	a[1].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))

	a[2].set_labels('time (ns)', 'Spin up probably (%)')
	a[2].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))

	a[3].set_labels('time (ns)', 'Spin up probably (%)')
	a[3].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))

	a[4].set_labels('time (ns)', 'Spin up probably (%)')
	a[4].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))

	a[5].set_labels('time (ns)', 'Spin up probably (%)')
	a[5].add_data(np.linspace(0,500,50), np.sin(np.linspace(10,50,50)))
	print(a)
	a.save('test1D_61.svg')

	a.plot()