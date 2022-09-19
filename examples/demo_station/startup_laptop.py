import core_tools as ct

# setup logging open database
ct.configure('./setup_config/ct_config_laptop_full.yaml')

# start in separate processes
ct.launch_databrowser()


