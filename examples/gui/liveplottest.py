import qcodes

from core_tools.GUI.keysight_videomaps import liveplotting
from core_tools.GUI.keysight_videomaps.data_saver.qcodes import QCodesDataSaver
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import fake_digitizer
from core_tools.GUI.qt_util import qt_init


from pulse_lib.base_pulse import pulselib


#start_all_logging()
#logger.get_file_handler().setLevel(logging.DEBUG)

try:
    qcodes.Instrument.close_all()
except: pass

class DummyAwg(qcodes.Instrument):
    def __init__(self, name):
        super().__init__(name)

    def release_waveform_memory(self):
        pass


def create_pulse_lib(awgs):
    pulse = pulselib()

    for awg in awgs:

        pulse.add_awg(awg)

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'{awg.name}.{ch}', awg.name, ch)

    pulse.finish_init()
    return pulse

if __name__ == '__main__':
    station = qcodes.Station()

    awg_slots = [2, 3]
    awgs = []
    for i, slot in enumerate(awg_slots):
        awg = DummyAwg(f'AWG{slot}')
        awgs.append(awg)
        station.add_component(awg)

    dig = fake_digitizer("fake_digitizer")
    station.add_component(dig)


    pulse = create_pulse_lib(awgs)

    defaults = {
        'gen': {'n_columns': 2}
        }

    qt_init()

    # Using the qcodes datasaver since that can be used without establishing the connection to the database.
    # Remove this line to use the default datasaver.
    liveplotting.set_data_saver(QCodesDataSaver())

    # Start the liveplotting
    plotting = liveplotting.liveplotting(pulse, dig, "Virtual", cust_defaults=defaults)
