from core_tools.data.SQL.connector import sample_info, SQL_conn_info_local
from core_tools.data.SQL.buffer_writer import buffer_reference
from dataclasses import dataclass, field
import copy

@dataclass
class data_set_raw:
    exp_id : int = None
    exp_uuid : int = None
    exp_name : str = None

    set_up : str = field(default_factory=lambda: sample_info.set_up)
    project : str = field(default_factory=lambda: sample_info.project)
    sample : str = field(default_factory=lambda: sample_info.sample)

    database : str = field(default_factory=lambda: SQL_conn_info_local.dbname)
    
    SQL_datatable : str = None
    measurement_parameters : list = field(default_factory=lambda: [])
    measurement_parameters_raw : list = field(default_factory=lambda: [])
    
    UNIX_start_time : int = None
    UNIX_stop_time : int = None
    
    uploaded_complete : bool = None
    
    snapshot : dict = None
    metadata : dict = None
    tags : list = field(default_factory=lambda: [])

    completed : bool = False
    writecount : int = 0

    def sync_buffers(self):
        for m_param in self.measurement_parameters_raw:
            m_param.data_buffer.sync()

    def size(self):
        # size in bytes
        size = 0
        for m_param in self.measurement_parameters_raw:
            size = m_param.data_buffer.cursor*8 #(64 bit numbers)
        
        return size
@dataclass
class m_param_raw:
    param_id : int
    nth_set : int # if part of a set
    nth_dim : int # non-local setpoints are recorded in higher dimensions, so this needs to be tracked.
    param_id_m_param : int #unique identifier for this m_param
    setpoint : bool
    setpoint_local : bool
    name_gobal : str
    name : str
    label : str
    unit : str
    dependency : str
    shape : str
    size : int
    oid : int
    data_buffer : any = None

    def __copy__(self):
        data_buffer = buffer_reference(self.data_buffer.data)
        return m_param_raw(copy.copy(self.param_id), copy.copy(self.nth_set), copy.copy(self.nth_dim), copy.copy(self.param_id_m_param), copy.copy(self.setpoint), 
            copy.copy(self.setpoint_local), copy.copy(self.name_gobal), copy.copy(self.name), copy.copy(self.label),
            copy.copy(self.unit), copy.copy(self.dependency), copy.copy(self.shape), copy.copy(self.size), copy.copy(self.oid), data_buffer)