'''
contains the descriptors that are used to generate the fast access data_sets
'''

import numpy as np


class dataset_data_descriptor():
    def __init__(self):
        self.x_data = np.linspace(0,1000, 20)
        self.unit = 'mV'
    
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



ds = test()
print(ds)
print(ds.x())
print(ds.x)

''' representation of the dataset.

dataset :: my_measurement_name

id = 1256
TrueID = 1225565471200

| idn   | label | unit  | size      |
------------------------------------- 
| m1    | 'I1'  | 'A'   | (100,100) |
|  x    | 'P1'  | 'mV'  | (100,)    |
|  y    | 'P2'  | 'mV'  | (100,)    |

| m2    | 'I2'  | 'A'   | (100)     |
|  x    | 'P1'  | 'mV'  | (100,)    |

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