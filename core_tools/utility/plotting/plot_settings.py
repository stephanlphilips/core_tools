from dataclasses import dataclass
import numpy as np

@dataclass
class plot_layout:
	_size : tuple = (None, None)

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

	@property
	def sharex(self):
		if self.share_x == True and self.share_y == True:
			return 'col'
		return self.share_x

	@property
	def sharey(self):
		if self.share_x == True and self.share_y == True:
			return 'row'
		return self.share_y

	@property
	def size(self):
		if self._size[0] is None:
			return (80*self.n_plots_x, 50*self.n_plots_y)
		return self._size
	
	@size.setter
	def size(self, value):
		self._size = value
	


@dataclass
class graph_settings_1D:
	linestyle : str   = '-'
	linewidth  : float = 1.2
	marker    : str   = ''
	markersize: float = 3
	color	  : str   = None
	label     : str   = None
	alpha	  : float = 1
	ecolor	  : str   = None
	elinewidth: float = 0.6

	xlabel : str = None
	ylabel : str = None

	xlog : bool = False
	ylog : bool = False

	def set_color(self, color):
		cpy = copy.copy(self)
		cpy.color = color
		return cpy

	def plot_settings_to_dict(self, ith_render, scaler):
		color = self.color
		if isinstance(self.color, list):
			color = self.color[ith_render]

		return {'linestyle' :self.linestyle,
				'linewidth' :self.linewidth*scaler,
				'marker' : self.marker,
				'markersize' :self.markersize*scaler,
				'label' :self.label,
				'alpha' : self.alpha,
				'color' : color}
@dataclass
class graph_settings_2D:
	cbar : bool = True
	cmap : str = 'RdBu'

	xlabel : str = None
	ylabel : str = None
	zlabel : str = None

	xlog : bool = False
	ylog : bool = False
	zlog : bool = False


@dataclass
class _1D_raw_plot_data:
	x_data   : np.ndarray
	y_data   : np.ndarray
	x_error  : np.ndarray = None 
	y_error  : np.ndarray = None 
	settings : graph_settings_1D = None


@dataclass
class _2D_raw_plot_data:
	z_data   : np.ndarray
	x_data   : np.ndarray = None
	y_data   : np.ndarray = None
	settings : graph_settings_1D = None
