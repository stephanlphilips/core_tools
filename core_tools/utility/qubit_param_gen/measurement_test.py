import numpy as np
from core_tools.utility.qubit_param_gen.measurement import measurement, measurement_manager

def generate_test_data(n_shots, spin_prob, threshold, IQ_angle):
    samples = np.random.uniform(0,1,n_shots)
    a = np.where(samples > spin_prob)[0] #  0
    b = np.where(samples <= spin_prob)[0] #  1
    data = np.empty([n_shots])
    data[a] = np.random.normal(loc = threshold + 10, size=len(a))
    data[b] = np.random.normal(loc = threshold - 10, size=len(b))
    return (data*np.exp(-1j*IQ_angle).real, data*np.exp(-1j*IQ_angle).imag)


nrep = 200

test_data_init_1 = generate_test_data(nrep, 0.2, 50, 1.8)
test_data_init_2 = generate_test_data(nrep, 0.2, 50, 1.8)

test_data_read_1 = generate_test_data(nrep, 0.5, 50, 1.8)
test_data_read_2 = generate_test_data(nrep, 0.9, 50, 1.8)

data = (np.asarray([test_data_init_1[0],
        test_data_init_2[0],
        test_data_read_1[0],
        test_data_read_2[0]]).T, np.asarray([test_data_init_1[1],
        test_data_init_2[1],
        test_data_read_1[1],
        test_data_read_2[1]]).T,
        np.asarray([test_data_init_1[0],
        test_data_init_2[0],
        test_data_read_1[0],
        test_data_read_2[0]]).T, np.asarray([test_data_init_1[1],
        test_data_init_2[1],
        test_data_read_1[1],
        test_data_read_2[1]]).T)

# accept is measurement outcome
m12_init = measurement('q12 init', [1,2], accept = 0, threshold=50, phase = 1.8)
m3_init = measurement('q3  init', [3,4], accept = 0, threshold=50, phase = 1.8)

m12_read = measurement('q12 read', [1,2], threshold=50, phase = 1.8)
# flip result if the other qubit measured 1
m3_read = measurement('q3  read', [1,2], threshold=50, flip='q12 read', phase = 1.8)

m_mgr = measurement_manager()
m_mgr.add(m12_init)
m_mgr.add(m3_init)

m_mgr.add(m12_read)
m_mgr.add(m3_read)

m_mgr.set_repetitions(nrep)

spt = m_mgr.generate_setpoints_information()

from qcodes import MultiParameter

class digitzer_qubit_param(MultiParameter):
    def __init__(self, measurement_mgr):
        self.measurement_mgr = measurement_mgr
        param_prop = measurement_mgr.generate_setpoints_information()
        super().__init__(name='test', names = param_prop.names, shapes = param_prop.shapes,
                        labels = param_prop.labels, units = param_prop.units,
                        setpoints = param_prop.setpoints, setpoint_names=param_prop.setpoint_names,
                        setpoint_labels=param_prop.setpoint_labels, setpoint_units=param_prop.setpoint_units)

    def get_raw(self):
        return self.measurement_mgr.format_data(data)


m  = digitzer_qubit_param(m_mgr)
d = m.get()
print(d)


a = np.asarray([True, True, False, False])
b = np.asarray([True, False,True,  False])

