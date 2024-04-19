import logging
import copy
import string


logger = logging.getLogger(__name__)


class m_param_organizer():
    def __init__(self, m_param_raw):
        self.m_param_raw = m_param_raw

    def get(self, key, nth_set):
        items = self[key]
        for i in items:
            if i.nth_set == nth_set:
                return i

        raise ValueError(f'm_param with id {key} and set {nth_set} not found in this data collection.')

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
        raise ValueError(f'm_param with id {key} not found in this data collection.')

    def get_m_param_id(self):
        '''
        get the measurement id's
        '''
        id_s = []
        for m_param in self.m_param_raw:
            # check if this param is a measurement param or setpoint.
            if m_param.param_id == m_param.param_id_m_param:
                id_s.append(m_param.param_id_m_param)

        return id_s

    def __copy__(self):
        new_m_param = []
        for i in self.m_param_raw:
            new_m_param.append(copy.copy(i))

        return m_param_organizer(new_m_param)


class data_descriptor: #autogenerate parameter info
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype):
        return getattr(obj.__dict__.get("_dataset_data_description__raw_data"), self.name)


class dataset_data_description():
    unit = data_descriptor()
    label = data_descriptor()

    def __init__(self, name, m_param_raw, m_params_raw_collection):
        '''
        Args:
            m_param_raw (m_param_raw) : pointer to the raw parameter to add
            m_params_raw_collection (m_param_organizer) : object containing a representation of all the data in the dataset
        '''
        self.name = name # @@@ will be overwritten by data_set_core.data_set.__init_properties
        self.param_name = m_param_raw.name
        self.__raw_data = m_param_raw
        self.__raw_data_org =  m_params_raw_collection
        self.__repr_attr_overview = []
        self.__populate_data()


    def __populate_data(self):
        for i in range(len(self.__raw_data.dependency)):
            repr_attr_overview = []
            raw_data = self.__raw_data_org[self.__raw_data.dependency[i]]

            for j in range(len(raw_data)): #this is not pretty, but it works..
                dataDescription = dataset_data_description('', raw_data[j], self.__raw_data_org)

                # @@@ Fix x, y, z
                if self.ndim <= 2:
                    name = string.ascii_lowercase[23+i] + str(j+1)
                    self.__setattr__(name, dataDescription)
                    if j == 0:
                        self.__setattr__(string.ascii_lowercase[23+i], dataDescription)
                        if len(raw_data) == 1:
                            name = string.ascii_lowercase[23+i]

                    repr_attr_overview += [(name, dataDescription)]

                if self.ndim > 2:
                    self.__setattr__(string.ascii_lowercase[8+i] + str(j+1), dataDescription)
                    if len(raw_data) == 1:
                        self.__setattr__(string.ascii_lowercase[8+i], dataDescription)
                        repr_attr_overview += [(string.ascii_lowercase[8+i], dataDescription)]
                    else:
                        repr_attr_overview += [(string.ascii_lowercase[8+i] + str(j+1), dataDescription)]

                dataDescription.name = repr_attr_overview[-1][0] # @@@ overwrites name

            self.__repr_attr_overview += [repr_attr_overview]

        if self.ndim <= 2:
            name = string.ascii_lowercase[23+self.ndim-1]
            if len(self.__raw_data.dependency) != 0:
                name = string.ascii_lowercase[23+self.ndim]
        else:
            name  = string.ascii_lowercase[8+self.ndim-1]
            if len(self.__raw_data.dependency) != 0:
                name = string.ascii_lowercase[8+self.ndim]

        self.__setattr__(name, self)

    def __call__(self):
        if self.__raw_data.setpoint is True or self.__raw_data.setpoint_local is True:
            if self.__raw_data.data_buffer.data.ndim > 1: #over dimensioned
                # NOTE: Assumes the setpoint does not depend on the other dimensions!
                #       This will fail when the parameter is swept in alternating direction.
                idx = [0] * self.__raw_data.data_buffer.data.ndim
                idx[self.__raw_data.nth_dim] = slice(None)

                return self.__raw_data.data_buffer.data[tuple(idx)]

        return self.__raw_data.data_buffer.data

    @property
    def shape(self):
        return self().shape

    @property
    def ndim(self):
        return len(self.shape)

    def full(self):
        return self.__raw_data.data_buffer.data

    def written(self):
        try:
            return self.__raw_data.data_buffer.cursor
        except:
            return None

    def get_raw_content(self):
        return self.__repr_attr_overview

    def average(self, dim):
        '''
        average the array across 1 dimension

        arg:
            dim (str/int) : 0 ('x'), 1 ('y') , ...
        '''
        dim = self.dim_to_int(dim)

        if dim > self.ndim:
            raise ValueError("you are trying to average over a dimension that does not exists")

        raw_data_org_copy = copy.copy(self.__raw_data_org)
        raw_data_cpy = raw_data_org_copy.get(self.__raw_data.param_id, self.__raw_data.nth_set)
        raw_data_cpy.dependency.pop(dim)
        raw_data_cpy.data_buffer.buffer_lambda =  raw_data_cpy.data_buffer.averaging_lambda(dim)

        return dataset_data_description(self.name, raw_data_cpy, raw_data_org_copy)


    def slice(self, dim, i):
        '''
        take the ith slice of dimension i
        '''
        dim = self.dim_to_int(dim)

        if not isinstance(i, slice):
            i = slice(int(i),int(i)+1)

        if dim > self.ndim:
            raise ValueError("you are trying to average over a dimension that does not exists")

        idx = [slice(None)]*self.ndim
        idx[dim] = i
        raw_data_org_copy = copy.copy(self.__raw_data_org)

        raw_data_cpy = raw_data_org_copy.get(self.__raw_data.param_id, self.__raw_data.nth_set)

        if i.start is not None and i.stop-i.start == 1:
            idx[dim] = i.start
            raw_data_cpy.dependency.pop(dim)
        elif i.stop is not None:
            id_to_slice = raw_data_cpy.dependency[dim]
            items= raw_data_org_copy[id_to_slice]
            for item in items:
                # TODO this is not generic yet (I think, this has to be checked).
                item.data_buffer.buffer_lambda =  item.data_buffer.slice_lambda([idx[dim]])

        raw_data_cpy.data_buffer.buffer_lambda =  raw_data_cpy.data_buffer.slice_lambda(idx)
        return dataset_data_description(self.name, raw_data_cpy, raw_data_org_copy)


    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = [args]
        args = list(args)

        to_slice = None
        for i in range(len(args)):
            if isinstance(args[i], int):
                to_slice = (i, slice(args[i], args[i]+1))
            elif isinstance(args[i], slice) and args[i] != slice(None):
                to_slice = (i, args[i])
        if to_slice is None:
            return self

        args.pop(to_slice[0])

        return self.slice(to_slice[0], to_slice[1])[tuple(args)]

    def __repr__(self):
        output_print = f"| {self.name:<15} | {self.label:<15} | {self.unit:<8} | {str(self.shape):<25}|\n"
        for i in self.__repr_attr_overview:
            for j in i:
                # data description
                dd = j[1]
                if dd.ndim == 1:
                    output_print +=  f"|  {j[0]:<14} | {dd.label:<15} | {dd.unit:<8} | {str(dd.shape):<25}|\n"

        return output_print

    @staticmethod
    def dim_to_int(dim):
        '''
        convert dim (if text) into a number on which axix of the array to performan a operation (e.g. x = 0, y=1)
        '''
        if isinstance(dim, str):
            if dim in 'xyz':
                dim = list(string.ascii_lowercase).index(dim) - 23
            else:
                dim = list(string.ascii_lowercase).index(dim) - 8
        return dim
