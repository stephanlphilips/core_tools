import matplotlib.pyplot as plt
import matplotlib as mpl

class _data_plotter:
	def __getitem__(self, idx):
		if isinstance(idx, int):
			return self.local_data.flat[idx] 
		else:
			#inverting indexes since matplotlib uses unverted indexes..
			return self.local_data[idx[::-1]]

	def render(self, scaler = 1):
		self.__set_nature_settings(scaler)
		layout = self.plot_layout
		fig = plt.figure(figsize=(layout.size[0]*0.0393*scaler, layout.size[1]*0.0393*scaler))
		if layout.n_plots_y == 1 and layout.n_plots_x == 1:
			gs  = fig.add_gridspec(layout.n_plots_y,layout.n_plots_x)
			ax = [[gs.subplots()]]
		elif layout.n_plots_y == 1:
			gs  = fig.add_gridspec(layout.n_plots_y,layout.n_plots_x, hspace=layout.hspace, wspace=layout.wspace)
			ax = [gs.subplots(sharex=layout.sharex, sharey=layout.sharey)]
		elif layout.n_plots_x == 1:
			gs  = fig.add_gridspec(layout.n_plots_y,layout.n_plots_x, hspace=layout.hspace, wspace=layout.wspace)
			ax = [ [i] for i in gs.subplots(sharex=layout.sharex, sharey=layout.sharey)]
		else:
			gs  = fig.add_gridspec(layout.n_plots_y,layout.n_plots_x, hspace=layout.hspace, wspace=layout.wspace)
			ax = gs.subplots(sharex=layout.sharex, sharey=layout.sharey)

		for i in range(self.local_data.shape[0]):
			for j in range(self.local_data.shape[1]):
				self[j,i]._render(ax[i][j], layout, (i,j) ,scaler, figure= fig)

	def plot(self):
		self.render(1)
		plt.show()

	def save(self, location):
		self.render()
		plt.tight_layout()
		plt.savefig(location,transparent=True, format="svg")

	def __set_nature_settings(self, scaler):
		mpl.rcParams['font.family'] = 'Helvetica'
		plt.rcParams['font.size'] = 6*scaler
		plt.rcParams['axes.linewidth'] = 1*scaler
		plt.rcParams['svg.fonttype'] = 'none'