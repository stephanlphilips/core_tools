# import necessary wrappers and measurement functions
from qdev_wrappers.file_setup import (
    CURRENT_EXPERIMENT, my_init, close_station, init_python_logger)
from qcodes import new_experiment, new_data_set
import qcodes as qc


def load_experiment(sample_batch, sample_name):
	station = qc.Station.default
	# Set up folders, settings and logging for the experiment
	my_init(sample_batch + sample_name, station,
	        pdf_folder=False, png_folder=False, analysis_folder=True,
	        waveforms_folder=False, calib_config=False,
	        annotate_image=False, mainfolder="D:/data/", display_pdf=False,
	        display_individual_pdf=False, qubit_count=2)
	new_experiment(sample_batch, sample_name)
	