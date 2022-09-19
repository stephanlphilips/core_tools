import core_tools as ct

from setup_config.init_pulse_lib import init_pulse_lib
from setup_config.init_station import init_station

# setup logging open database
ct.configure('./setup_config/ct_config_measurement.yaml')

station = init_station()

pulse = init_pulse_lib()

# start GUIs
ct.start_parameter_viewer()
ct.start_virtual_matrix_gui(pulse)

ct.start_parameter_viewer_qml()
ct.start_virtual_matrix_gui_qml()

# start in separate processes
ct.launch_databrowser()
ct.launch_db_sync(kill=True, close_at_exit=True)


# Optionally change configuration without restarting console
# ct.set_sample_info(project='Project2', sample='Magic_10x10_3', setup='Fridge_9')

