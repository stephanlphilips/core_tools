from functools import partial
import qcodes
from qcodes.data.io import DiskIO
from qcodes.data.data_set import DataSet

from core_tools.GUI.keysight_videomaps.liveplotting import liveplotting, set_data_saver
from core_tools.GUI.keysight_videomaps.data_saver.qcodes import QCodesDataSaver
from core_tools.GUI.keysight_videomaps.data_getter.scan_generator_Virtual import fake_digitizer
from core_tools.GUI.qt_util import qt_init

from pulse_lib.base_pulse import pulselib


#start_all_logging()
#logger.get_file_handler().setLevel(logging.DEBUG)

try:
    qcodes.Instrument.close_all()
except: pass

class DummyGates(qcodes.Instrument):
    def __init__(self, name, gates, v_gates):
        super().__init__(name)
        self.gates = gates
        self.v_gates = v_gates
        self._voltages = {}

        for gate_name in gates + v_gates:
            self.add_parameter(gate_name,
                               set_cmd=partial(self._set, gate_name),
                               get_cmd=partial(self._get, gate_name),
                               unit="mV")
            self._voltages[gate_name] = 0.0

    def get_idn(self):
        return {}

    def _set(self, gate_name, value):
        print(f'{gate_name}: {value:5.2f} mV')
        self._voltages[gate_name] = value

    def _get(self, gate_name):
        return self._voltages[gate_name]

    def get_gate_voltages(self):
        res = {}
        for gate_name in self.gates + self.v_gates:
            res[gate_name] = f'{self.get(gate_name):.2f}'
        return res


class DummyAwg(qcodes.Instrument):
    def __init__(self, name):
        super().__init__(name)

    def get_idn(self):
        return {}

    def awg_flush(self, ch):
        pass

    def release_waveform_memory(self):
        pass


def create_pulse_lib(awgs):
    pulse = pulselib()

    for awg in awgs:

        pulse.add_awg(awg)

        # define channels
        for ch in range(1,5):
            pulse.define_channel(f'{awg.name}_{ch}', awg.name, ch)

    pulse.finish_init()
    return pulse


qt_init()

# setup QCODES data storage
path = 'C:/Projects/test_data'

io = DiskIO(path)
DataSet.default_io = io
set_data_saver(QCodesDataSaver())

station = qcodes.Station()

awg_slots = [2,3]
awgs = []
for i,slot in enumerate(awg_slots):
    awg = DummyAwg(f'AWG{slot}')
    awgs.append(awg)
    station.add_component(awg)

dig = fake_digitizer("fake_digitizer")
station.add_component(dig)

# use AWG2 for real and AWG3 for virtual gates. (It's all fake)
gates = DummyGates('gates',
                   [f'AWG2_{ch}' for ch in range(1,5)],
                   [f'AWG3_{ch}' for ch in range(1,5)])
station.add_component(gates)

pulse = create_pulse_lib(awgs)

settings = {
    'gen':{
        '2D_colorbar':True,
        '2D_cross':True,
        }
    }
plotting = liveplotting(pulse, dig, "Virtual", settings)#, gates=gates)
plotting._2D_gate2_name.setCurrentIndex(1)
plotting._2D_t_meas.setValue(1)
plotting._2D_V1_swing.setValue(100)
plotting._2D_npt.setValue(80)

