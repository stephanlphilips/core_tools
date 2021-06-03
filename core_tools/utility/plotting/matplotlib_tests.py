import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from pylab import cm

from dataclasses import dataclass



import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype'] = 'none'

@dataclass
class plot_layout:
	size : tuple = (100, 50)

	n_plots_x : int = 1
	n_plots_y : int = 1

	share_x : bool = False
	share_y : bool = False

	xbins : int = 8
	ybins : int = 5
	@property
	def hspace(self):
		return 0 if self.share_x == True else None

	@property
	def wspace(self):
		return 0 if self.share_y == True else None
	

@dataclass
class graph_settings_1D:
	linestyle : str   = '-'
	linewith  : float = 1.2
	marker    : str   = ''
	markersize: float = 3
	color	  : str   = None
	label     : str   = None
	alpha	  : float = 1
	ecolor	  : str   = None
	elinewidth: float = 0.6

	def set_color(self, color):
		cpy = copy.copy(self)
		cpy.color = color
		return cpy

import matplotlib.font_manager as fm
# Rebuild the matplotlib font cache

# Collect all the font names available to matplotlib
font_names = [f.name for f in fm.fontManager.ttflist]
# print(font_names)

fm._rebuild()

colors = cm.get_cmap('tab10', 2)


mpl.rcParams['font.family'] = 'Helvetica'
plt.rcParams['font.size'] = 6
plt.rcParams['axes.linewidth'] = 1

x_size = 100*2
y_size = 50

a = np.linspace(0,120, 100)
b = np.random.random([100])
c = np.sin(a/10)

n_plots_x = 2
n_plots_y = 1


# Create figure and add axes object
# fig, ax = plt.subplots(n_plots_y,n_plots_x, sharex=False, sharey=False,figsize=(x_size*0.0393, y_size*0.0393))# Plot and show our data
# print(fig, ax)




fig = plt.figure(figsize=(x_size*0.0393, y_size*0.0393))
gs  = fig.add_gridspec(n_plots_y,n_plots_x, wspace=0)
axs = gs.subplots(sharex='col', sharey=False)

axs[0].plot(a, b)
axs[1].plot(a, c)
plt.savefig('test.pdf')


n_plots_x = 1
n_plots_y = 2

x_size = 100
y_size = 50*2

fig = plt.figure(figsize=(x_size*0.0393, y_size*0.0393))
gs  = fig.add_gridspec(n_plots_y,n_plots_x, hspace=0)
axs = gs.subplots(sharex=False, sharey='row')

axs[0].plot(a, b)
axs[1].plot(a, c)
plt.savefig('test.pdf')


n_plots_x = 2
n_plots_y = 2

x_size = 100*2
y_size = 50*2
import matplotlib.ticker as tck

fig = plt.figure(figsize=(x_size*0.0393, y_size*0.0393))
gs  = fig.add_gridspec(n_plots_y,n_plots_x, hspace=0, wspace=0)
axs = gs.subplots(sharex='col', sharey='row')

axs[0,0].plot(a, b, linewidth=1.2, color=colors(1))
axs[0,0].locator_params(axis='x', nbins=5)
axs[0,0].locator_params(axis='y', nbins=8)
axs[0,0].xaxis.set_minor_locator(tck.AutoMinorLocator())
axs[0,0].yaxis.set_minor_locator(tck.AutoMinorLocator())

axs[0,0].tick_params(direction='in', which='both', top=True, right=True)
axs[1,0].set_xlabel('time (ns)')
axs[1,0].set_ylabel('spin up prob (%)')

axs[0,1].plot(a, c, linestyle='', marker='o', label = 'test', markersize=3)
axs[1,0].plot(a, b, marker='o', linewidth=1.2, label = 'test', markersize=3)
axs[1,0].plot(a, c, linestyle='--', linewidth=1.2, label = 'test')
axs[1,0].locator_params(axis='x', nbins=5)
axs[1,0].locator_params(axis='y', nbins=8)
axs[1,1].errorbar(a, c, yerr = b/10,ecolor='g',linewidth=1.2,elinewidth=0.7)
# axs[0,1].spines['right'].set_visible(False)
# axs[0,1].spines['top'].set_visible(False)
axs[0,1].locator_params(axis='x', nbins=5)
axs[0,1].locator_params(axis='y', nbins=8)
axs[1,0].legend()
plt.savefig('test.svg', transparent=False, format="svg")


my_fig = plt_mkr_1D(layout)

properties = prop('label_x', 'label_y', xbins, ybins, logx, logy)

my_fig[0,0].set_plot_properties(properties)
my_fig[0,0].plot(x,y, settings = settings.set_color('FF00FF'))
my_fig[0,0].plot_fit(x,y, settings = settings)

my_fig[1,0].set_plot_properties(properties)
my_fig[1,0].plot_ebar(x,y, xerr = xerr, settings = settings)
my_fig[1,0].plot_fit(x,y, settings = settings)


my_fig.render('name.svg')