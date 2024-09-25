from core_tools.GUI.keysight_videomaps import liveplotting


from pulse_lib.tests.configurations.test_configuration import context

pulse = context.init_pulselib(n_gates=6, n_sensors=2, virtual_gates=True)


defaults = {
    'gen': {
        'n_columns': 2,
        },
    }


# Start the liveplotting
plotting = liveplotting.liveplotting(pulse, cust_defaults=defaults)
