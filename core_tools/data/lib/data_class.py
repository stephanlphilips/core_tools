from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager
from core_tools.data.SQL.buffer_writer import buffer_writer, buffer_reader
from core_tools.data.ds.data_set_raw import m_param_raw
from dataclasses import dataclass, field

import uuid
import numpy as np
import numbers
import json


class dataclass_raw_parent:
    def generate_data_buffer(self, setpoint_shape=[]):
        '''
        generate the buffers that are needed to write the data to the database.

        Args:
            setpoint_shape (list) : shape of the setpoints (if applicable) (measurent param is measured exactly the same amount of times than the setpoint)
        '''
        SQL_mgr = SQL_database_manager()

        for i in range(len(self.shapes)):
            shape = setpoint_shape + list(self.shapes[i])
            if i <= len(self.oid): # write data
                if len(self.data) > i: #this is statement is kinda dirty..
                    arr=self.data[i]
                else:
                    arr = np.full(shape, np.nan, order='C')
                    self.data.append(arr)
                data_buffer = buffer_writer(SQL_mgr.conn_local, arr)
                self.oid.append(data_buffer.oid)
            else: # load data
                oid = self.oid[i]
                data_buffer = buffer_reader(SQL_mgr.conn_local, oid, shape)
                arr = data_buffer.buffer
                self.data.append(arr)

            self.data_buffer.append(data_buffer)

    def write_data(self, input_data):
        '''
        write data to memory of the measurement

        Args:
            input_data (dict): dict formatted as e.g. write_data({'id(parameter_1)' : parameter_1.get(), id(parameter_2) : parameter_2.get(), ..})
        '''
        if self.id_info not in input_data.keys():
            txt = 'Key not found. A write is attempted to a parameter that has not been declaired yet. '
            txt += 'Please first register the parameter with register_set_parameter/register_get_parameter '
            raise KeyError(txt)
        data_in = input_data[self.id_info]

        if len(self.data) == 1:
            # data in is not a iterator
            data = np.ravel(np.asarray(data_in))
            self.data_buffer[0].write(data)
        else:
            # data_in expected to be a iterator
            for i in range(len(data_in)):
                data = np.ravel(np.asarray(data_in[i]))
                self.data_buffer[i].write(data)

    def to_SQL_data_structure(self, m_param_id, setpoint, setpoint_local, nth_dim=0, dependencies=[]):
        '''
        disassembele the dataset into a sql like structure

        Args:
            m_param_id (int): id of the measurement parameter where this data belongs to.
            setpoint (bool): is this data a setpoint?
            setpoint_local (bool) : is this data a local setpoint (e.g. of a multiparameter)
            nth_dim (int) : if two setpoints are taken, that both x and y have e.g. the dimension 100x100
            dependencies (str<JSON>) : json of the dependencies
        '''
        data_items = list()
        for i in range(len(self.data)):
            data_items +=[m_param_raw(self.uuid_dc, i, nth_dim, m_param_id, setpoint, setpoint_local,
                self.name, self.names[i], self.labels[i],
                self.units[i], dependencies[i], self.data[i].shape, self.data[i].size, self.oid[i], self.data_buffer[i])]

        return data_items

@dataclass
class setpoint_dataclass(dataclass_raw_parent):
    id_info : id
    npt : np.NaN
    name : str
    names : list
    labels : list
    units : list
    shapes : list = field(default_factory=lambda: list( ((),) ))
    nth_set : int = 0
    data : list = field(default_factory=lambda: [])
    oid : list = field(default_factory=lambda: [])
    data_buffer : list = field(default_factory=lambda: [])
    uuid_dc : int = field(default_factory=lambda: int.from_bytes(uuid.uuid1().bytes, byteorder='big', signed=True)>>64)

    def __repr__(self):
        description = "id :: {} \tname :: {}\tnpt :: {}\n".format(self.id_info, self.name, self.npt)
        description += "names :\t{}\tlabels :\t{}\nunits :\t{}\tshapes :\t{}\n".format(self.names, self.labels, self.units, self.shapes)

        return description

    @property
    def dependencies(self):
        dep_tot = []
        for i in range(len(self.data)):
            dep_tot.append([])
        return dep_tot

    def __copy__(self):
        return setpoint_dataclass(self.id_info, self.npt, self.name, self.names, self.labels, self.units, self.shapes, self.nth_set)

@dataclass
class m_param_dataclass(dataclass_raw_parent):
    id_info : id
    name : str
    names : list
    labels : list
    units : list
    shapes : list = field(default_factory=lambda: list(((),)))
    setpoints : list = field(default_factory=lambda: [])
    setpoints_local : list = field(default_factory=lambda: [])
    data : list = field(default_factory=lambda: [])
    oid : list = field(default_factory=lambda: [])
    data_buffer : list = field(default_factory=lambda: [])
    uuid_dc : int = field(default_factory=lambda: int.from_bytes(uuid.uuid1().bytes, byteorder='big', signed=True)>>64)
    __initialized : bool = False

    def write_data(self, input_data):
        '''
        write data to memory of the measurement

        Args:
            input_data : dict formatted as e.g. write_data({'id(parameter_1)' : parameter_1.get(), id(parameter_2) : parameter_2.get(), ..})
        '''
        super().write_data(input_data)

        for setpoint in self.setpoints:
            setpoint.write_data(input_data)

    def to_SQL_data_structure(self):
        data_items = []

        data_items += super().to_SQL_data_structure(self.uuid_dc, False, False, -1, self.dependencies)
        for i in range(len(self.setpoints_local)):
            setpt_list = self.setpoints_local[i]
            for j,setpt in enumerate(setpt_list):
                data_items += setpt.to_SQL_data_structure(self.uuid_dc, False, True, j, setpt.dependencies)

        for i in range(len(self.setpoints)):
            setpt = self.setpoints[i]
            data_items += setpt.to_SQL_data_structure(self.uuid_dc, True, False, i, setpt.dependencies)

        return data_items

    def init_data_dataclass(self):
        '''
        initialize the arrays in the dataset.
        '''
        setpoint_shape = []
        for setpoint in self.setpoints:
            setpoint_shape += [setpoint.npt]

        for setpoint in self.setpoints:
            setpoint.generate_data_buffer(setpoint_shape)

        # for setpoint_local_list in self.setpoints_local:
        #     for setpoint_local in setpoint_local_list:
        #         setpoint_local.generate_data_buffer()

        self.generate_data_buffer(setpoint_shape)
        self.__initialized = True

    @property
    def dependencies(self):
        dep_tot= []
        for i in range(len(self.data)):
            dep = []
            for setpt in self.setpoints:
                dep.append(setpt.uuid_dc)

            if len(self.setpoints_local) > i:
                for setpt_l in self.setpoints_local[i]:
                    dep.append(setpt_l.uuid_dc)

            dep_tot.append(dep)

        return dep_tot

    def __repr__(self):
        description = "\n########################\nMeasurement dataset info\n########################\nid :: {} \nname :: {}\n\n".format(self.id_info, self.name)
        description += "names :\t{}\nlabels :\t{}\nunits :\t{}\nshapes :\t{}\n".format(self.names, self.labels, self.units, self.shapes)
        for i in range(len(self.setpoints_local)):
            description += "\n##################\nlocal setpoint {}\n".format(i)
            description += self.setpoints_local[i].__repr__()

        for i in range(len(self.setpoints)):
            description += "\n##################\nsetpoint {}\n".format(i)
            description += self.setpoints[i].__repr__()

        return description