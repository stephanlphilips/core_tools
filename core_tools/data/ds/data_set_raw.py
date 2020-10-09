from core_tools.data.SQL.connector import sample_info
from dataclasses import dataclass, field

@dataclass
class data_set_raw:
    exp_id : int = None
    exp_name : str = None

    set_up : str = field(default_factory=lambda: sample_info.set_up)
    project : str = field(default_factory=lambda: sample_info.project)
    sample : str = field(default_factory=lambda: sample_info.sample)
    
    SQL_datatable : str = None
    measurement_parameters : list = field(default_factory=lambda: [])
    measurement_parameters_raw : list = field(default_factory=lambda: [])
    
    UNIX_start_time : int = None
    UNIX_stop_time : int = None
    
    uploaded_complete : bool = None
    
    snapshot : str = None
    metadata : str = None

    completed : bool = False
    writecount : int = 0

    def sync_buffers(self):
        for m_param in self.measurement_parameters_raw:
            m_param.data_buffer.sync()

@dataclass
class m_param_raw:
    param_id : int
    nth_set : int
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
    data_buffer : any