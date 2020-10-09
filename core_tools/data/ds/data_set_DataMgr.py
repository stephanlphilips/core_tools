'''

'''

import numpy as np

def get_m_param_id(m_params_raw):
    id_s = set()
    for m_param in m_params_raw:
        id_s.append(m_param.param_id_m_param)

    return id_s

def get_m_params_from_id(m_params_raw, id_info):
    m_params = []
    for m_param in m_param_raw:
        if m_param.id_info == id_info:
            m_params.append(m_param)

    return m_params

def construct_low_level_data_structure(m_params_raw):
    m_param_ids = get_m_param_id(m_params_raw)

    for id_info in m_param_ids:
        dataset_data_descriptor(m_param_raw, m_params_raw):



class dataset_data_descriptor():
    def __init__(self, id_info, m_params_raw):
        # 1 :: get setpoints
    
    def __call__(self):
        return self.x_data

    def average(self, dim):
        pass

    def slice(self, dim, i):
        pass


    def __repr__(self):
        pass

class test():
    def __init__(self):
        self.x = dataset_data_descriptor()
        # self.x = 6    


from core_tools.data.ds.data_set_raw import m_param_raw

a = m_param_raw(param_id=140455866128848, nth_set=0, param_id_m_param=140455866128848, setpoint=False, setpoint_local=False, name_gobal='name3', name='name3', label='name3', unit='', dependency=[140455866119360, 140455866119216], shape='[100, 100]', size=10000, oid=18249,data_buffer=None) 
b = m_param_raw(param_id=140455866119360, nth_set=0, param_id_m_param=140455866128848, setpoint=True, setpoint_local=False, name_gobal='name1', name='name1', label='name1', unit='', dependency=[], shape='[100, 100]', size=10000, oid=18247,data_buffer=None)
c = m_param_raw(param_id=140455866119216, nth_set=0, param_id_m_param=140455866128848, setpoint=True, setpoint_local=False, name_gobal='name2', name='name2', label='name2', unit='', dependency=[], shape='[100, 100]', size=10000, oid=18248,data_buffer=None)

l = [a,b,c]


ds = test()
print(ds)
print(ds.x())
''' representation of the dataset.

dataset :: my_measurement_name

id = 1256
TrueID = 1225565471200

| idn   | label | unit  | size      |
------------------------------------- 
| m1    | 'I1'  | 'A'   | (100,100) |
| * x   | 'P1'  | 'mV'  | (100,)    |
| * y   | 'P2'  | 'mV'  | (100,)    |

| m2    | 'I2'  | 'A'   | (100)     |
| * x   | 'P1'  | 'mV'  | (100,)    |

| m3a   | 'I2'  | 'A'   | (100)     |
|  x    | 'P2'  | 'mV'  | (100,)    |

| m3b   | 'I2'  | 'A'   | (100)     |
|  x1   | 'P1'  | 'mV'  | (100,)    |
|  x2   | 'P1'  | 'mV'  | (100,)    |

database : vanderyspen
set_up : XLD
project : 6dot
sample_name : SQ19
'''