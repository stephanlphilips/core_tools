import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
sample_rate = 10e6

def test_BW_needed():
	# with hann window
	# time pulse to not have a lot of cross talk is at least 1/BW*5 not to have to much cross task (<.02%)
	# factor 10 < 0.002%
	# with cosine window (more raw signal) :
	# time pulse to not have a lot of cross talk is at least 1/BW*5 not to have to much cross task (<0.2%)
	# take factor 10 for <0.02%
	# with boxcar window (more raw signal) : < 3%.
	# time pulse to not have a lot of cross talk is at least 1/BW*5 not to have to much cross task (<3%)
	# take factor 10 for <2%
	'''
	# RAW signal
		boxcar : 1
		hann   : 0.5
		cosine : 0.64

	conclusion box car not recommneded as it gives bad performance on crosstask.
	Consine seems like nice balance between crosstask and SNR
	Hann good is SNR is excellent.
	'''
	BW = 50e3
	freq = 100e3

	t_total = 1/BW*10
	n_points = t_total*sample_rate

	times = np.linspace(0,t_total, n_points)
	amp = 1
	sin_test = 5.31*np.sin(freq*2*np.pi*times)

	offset = np.linspace(0,50e3)
	return_value = np.linspace(0,20e3)

	for i in range(len(offset)):
		# see below for phase correction.
		freq_carrier = freq + offset[i]
		sin_carrier = np.sin(freq_carrier*2*np.pi*times)

		window = signal.cosine(int(n_points))
		sin_multi = sin_carrier*sin_test*window
		return_value[i] = np.average(sin_multi)*2*2


	plt.plot(offset, return_value)
	plt.show()

def multi_data_test():
	BW = 50e3

	t_total = 1/BW*5
	n_points = t_total*sample_rate

	times = np.linspace(0,t_total, n_points)
	amp = 1
	freq_1 = 100e3
	freq_2 = 100e3 + BW
	freq_3 = 100e3 + BW*2
	sin_test = 5.31*np.sin(freq_1*2*np.pi*times+0.3) +\
			 1.2*np.sin(freq_2*2*np.pi*times+0.2) +\
			 0.1*np.sin(freq_3*2*np.pi*times-0.1) *20

	freq = np.linspace(freq_1, freq_3, 3)
	return_value = np.linspace(freq_1, freq_3, 3)

	for i in range(len(freq)):
		freq_carrier = freq[i]
		sin_carrier = np.sin(freq_carrier*2*np.pi*times)
		cos_carrier = np.cos(freq_carrier*2*np.pi*times)
		window = signal.hann(int(n_points))
		demod_signal = np.average(sin_carrier*sin_test*window) +1j*np.average(cos_carrier*sin_test*window)
		# phases
		print(np.angle(demod_signal))
		# amp
		return_value[i] = np.abs(demod_signal)*4

	print(return_value)

def generate_dig_data_set(cycles, sample_rate, total_time, freq):
	'''
	generate a sample set of data that is expected as outcome of the digitezer (just for quick development)
	
	Args:
		cycles : numbner of ccycles of the digitizer (is effectively the number of points in the final end result)
		sample rate : rate of the digitizer
		total_time : total time of one cycle measurement
		freq (list) : frequecies at which there will be modulated

	returns:
		data (tuple<np.ndarray>) : typical data format used in qcodes drives .. 
	'''

	n_points = int(total_time*sample_rate)

	I_data = np.zeros([cycles, n_points])
	Q_data = np.zeros([cycles, n_points])

	# lets supporse scan to 50 mV
	amp_scan = 2.73**(-0.5*((np.linspace(0,50, cycles) - 25)/1)**2)
	
	time = np.linspace(0, total_time, n_points)
	for i in range(len(freq)):
		for cycle in range(cycles):
			I_data[cycle, :] += np.sin(freq[i]*2*np.pi*time)/(i+1)*amp_scan[cycle]

	# will be a ratio.
	Q_data = I_data*0.2

	return (I_data, Q_data)


if __name__ == '__main__':
	from mod_test import demodulate_data, process_data_IQ

	freq = [100e3,150e3,200e3]
	sample_rate = 25e6
	data = generate_dig_data_set(200, sample_rate, 1e-3, freq)

	output_data = process_data_IQ(data, freq, sample_rate)

	for i in output_data:
		plt.plot(i)
	plt.show()