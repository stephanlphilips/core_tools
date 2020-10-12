import numpy as np
import copy
import string

class m_param_origanizer():
    def __init__(self, m_param_raw):
        self.m_param_raw = m_param_raw

    def get(self, key, nth_set):
        items = self[key]
        for i in items:
            if i.nth_set == nth_set:
                return i

        raise ValueError('m_param with id {} and set {} not found in this data collection.'.format(key, nth_set))

    def __getitem__(self, key):
        '''
        gets a list with parameters containing this key

        Returns
            list<m_param_raw> : raw parameters originating from this id.
        '''
        param_s = []
        for m_param in self.m_param_raw:
            if m_param.param_id == key:
                param_s.append(m_param)

        if len(param_s) != 0:
            return param_s
        raise ValueError('m_param with id {} not found in this data collection.'.format(key))

    def get_m_param_id(self):
        '''
        get the measurement id's
        '''
        id_s = set()
        for m_param in self.m_param_raw:
            id_s.add(m_param.param_id_m_param)

        return list(id_s)

    def __copy__(self):
        new_m_param = []
        for i in self.m_param_raw:
            new_m_param.append(copy.copy(i))

        return m_param_origanizer(new_m_param)

class data_descriptor: #autogenerate parameter info
    def __set_name__(self, owner, name): # from python 3.6 (super handy :) )
        self.name = name
    def __get__(self, obj, objtype):
        return getattr(obj.__dict__.get("_dataset_data_description__raw_data"), self.name)

class dataset_data_description():
    unit = data_descriptor()
    label = data_descriptor()
    name = data_descriptor()
    shape = data_descriptor()

    def __init__(self, name, m_param_raw, m_params_raw_collection):
        '''
        Args:
            m_param_raw (m_param_raw) : pointer to the raw parameter to add
            m_params_raw_collection (m_param_origanizer) : object containing a representation of all the data in the dataset
        '''
        self.name = name
        self.__raw_data = m_param_raw
        self.__raw_data_org =  m_params_raw_collection
        self.__repr_attr_overview = []
        self.ndim = len(m_param_raw.dependency) + 1
        self.__populate_data()

    def __populate_data(self):
        for i in range(len(self.__raw_data.dependency)):
            repr_attr_overview = []
            raw_data = self.__raw_data_org[self.__raw_data.dependency[i]]

            for j in range(len(raw_data)): #this is not pretty, but it works..
                dataDescription = dataset_data_description('', raw_data[j], self.__raw_data_org)
                
                name = string.ascii_lowercase[23+i] + str(j+1)

                self.__setattr__(name, dataDescription)
                if j == 0:
                    self.__setattr__(string.ascii_lowercase[23+i], dataDescription)
                    if len(raw_data) == 1:
                        name = string.ascii_lowercase[23+i]
                
                if self.ndim < 3:
                    self.__setattr__(string.ascii_lowercase[8+i] + str(j+1), dataDescription)
                    if len(raw_data) == 1:
                        self.__setattr__(string.ascii_lowercase[8+i], dataDescription)
                        repr_attr_overview += [(string.ascii_lowercase[8+i], dataDescription)]
                    else:
                        repr_attr_overview += [(string.ascii_lowercase[8+i] + str(j+1), dataDescription)]
                else:
                    repr_attr_overview += [(name, dataDescription)]

            self.__repr_attr_overview += [repr_attr_overview]

        if self.ndim <= 3:
            name  = string.ascii_lowercase[23+self.ndim-1]
        else:
            name  = string.ascii_lowercase[8+self.ndim-1]

        self.__setattr__(name, self)
        self.__repr_attr_overview += [[(name, self)]]

    def __call__(self):
        return self.__raw_data.data_buffer.data

    def average(self, dim):
        pass

    def slice(self, dim, i):
        pass

    def __repr__(self):
        output_print = ""
        output_print += "| " + "{:<15}".format(self.name) + " | " + "{:<15}".format(self.label) + " | " +  "{:<8}".format(self.unit)+ " | " +  "{:<25}".format(self.shape) + "|\n"
        for i in self.__repr_attr_overview:
            for j in i:
                dataDescription = j[1]
                if dataDescription.ndim == 1:
                    output_print +=  "|  " +  "{:<14}".format(j[0]) + " | " +  "{:<15}".format(dataDescription.label) + " | " +   "{:<8}".format(dataDescription.unit)+ " | " +  "{:<25}".format(dataDescription.shape) + "|\n"

        return output_print

class data_set_property_intializer():
    def __init__(self, m_params):
        self.__repr_attr_overview = []
        # m_meas_id's
        m_id = m_params.get_m_param_id()

        for i in range(len(m_id)): #this is not pretty.
            n_sets = len(m_params[m_id[i]])
            repr_attr_overview = []
            for j in range(n_sets):
                ds_descript = dataset_data_description('', m_params.get(m_id[i],  j), m_params)

                name = 'm' + str(i+1) + string.ascii_lowercase[j]
                setattr(self, name, ds_descript)

                if j == 0:
                    setattr(self, 'm' + str(i+1), ds_descript)
                
                if j == 0 and n_sets==1: #consistent printing
                    repr_attr_overview += [('m' + str(i+1), ds_descript)]
                    ds_descript.name = 'm' + str(i+1)
                else:
                    repr_attr_overview += [(name, ds_descript)]
                    ds_descript.name = name

            self.__repr_attr_overview += [repr_attr_overview]

    def __repr__(self):
        output_print = "DataSet :: my_measurement_name\n\nid = 1256\nTrueID = 1225565471200\n\n"
        output_print += "| idn             | label           | unit     | size                     |\n"
        output_print += "---------------------------------------------------------------------------\n"
        for i in self.__repr_attr_overview:
            for j in i:
                output_print += j[1].__repr__()
                output_print += "\n"
        output_print += "database : vanderyspen\n"
        output_print += "set_up : XLD\n"
        output_print += "project : 6dot\n"
        output_print += "sample_name : SQ19\n"
        return output_print

if __name__ == '__main__':
        

    from core_tools.data.ds.data_set_raw import m_param_raw

    a = m_param_raw(param_id=1636274596872, nth_set=0, param_id_m_param=1636274596872, setpoint=False, setpoint_local=False, name_gobal='test', name='chan_1', label='keithley 1', unit='pA', dependency=[1635967634696, 1635967635080], shape='[100, 100, 10]', size=100000, oid=16478, data_buffer=None) 
    b = m_param_raw(param_id=1636274596872, nth_set=1, param_id_m_param=1636274596872, setpoint=False, setpoint_local=False, name_gobal='test', name='chan_2', label='keithley 2', unit='pA', dependency=[1635967634696, 1635967635080, 32719381726400], shape='[100, 100, 10]', size=100000, oid=16479, data_buffer=None) 
    c = m_param_raw(param_id=16359690863200, nth_set=0, param_id_m_param=1636274596872, setpoint=False, setpoint_local=True, name_gobal='local_var', name='P1', label='P1', unit='m', dependency=[], shape='[10]', size=10, oid=16476, data_buffer=None) 
    d = m_param_raw(param_id=32719381726400, nth_set=0, param_id_m_param=1636274596872, setpoint=False, setpoint_local=True, name_gobal='local_var', name='P2', label='P2', unit='m', dependency=[], shape='[10]', size=10, oid=16477, data_buffer=None) 
    e = m_param_raw(param_id=1635967634696, nth_set=0, param_id_m_param=1636274596872, setpoint=True, setpoint_local=False, name_gobal='name1', name='name1', label='B field', unit='mT', dependency=[], shape='[100, 100]', size=10000, oid=16474, data_buffer=None) 
    f = m_param_raw(param_id=1635967635080, nth_set=0, param_id_m_param=1636274596872, setpoint=True, setpoint_local=False, name_gobal='name2', name='name2', label='P1', unit='mV', dependency=[], shape='[100, 100]', size=10000, oid=16475, data_buffer=None)

    l = m_param_origanizer([a,b,c,d,e,f])


    ds = data_set_property_intializer(l)
    print(ds)
    # print(ds.m1a.label)
    # print(ds.m1b.unit)
    # print(ds.m1b.label)

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

    
    '''