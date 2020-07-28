from qcodes import Parameter
import qcodes as qc

class combi_par(Parameter):
    def __init__(self,param, label):
        """
        Make a combined parameter:
        Args:
            param (list) : list of parameters
            label (list) : list of labels
            
        """
        super().__init__("combi_par", label = label, unit= "mV" )
        self.param = param
    
    def set_raw(self, value):
        for param in self.param:
            param(value)
    
    def __add__(self, other):
        new = combi_par(self.param + other.param, self.label + other.label)
        return new
                
def make_combiparameter(*args):
    """
    Make a combined qcodes parameter. 
    Args: 
        *args : list of gates or parameters
        (e.g. make_combiparameter("A1", "A3", station.gates.B1 ))
    """
    station = qc.Station.default
    parameters = []
    for i in args:
        if type(i) == str:
            parameters.append(getattr(station.gates, i))
        else:
            parameters.append(i)
    
    label = ""
    for i in parameters:
        label += i.label + " "

    return combi_par(parameters, label)

class v_src_rescaler(Parameter):
    def __init__(self, parameter, scale):
        super().__init__(parameter.name, label=parameter.label, unit = parameter.unit)
        self._parameter = parameter
        self._scale = scale
    def set_raw(self,value):
        self._parameter(value/self._scale)
    
    def get_raw(self,):
        return self._parameter()*self._scale
