from qcodes import Parameter, Station


class combi_par(Parameter):
    def __init__(self,
                 params: list[Parameter],
                 label: str,
                 name: str = 'combi_par'):
        """Creates a combined parameter setting all the parameter to the
        same value.

        Reading this parameter returns the last value set to this parameter.
        This value does not necessarily correspond of the actual value
        of any of the individual parameters.

        Args:
            params  list of parameters
            label: label for parameter
            name: name for parameter

        Note:
            Before a scan with reset_params=True the value of the combi_parameter must
            be set once.
        """
        super().__init__(name, label=label, unit="mV")
        self.params = params

    def set_raw(self, value: float):
        for param in self.params:
            param(value)

    def __add__(self, other):
        new = combi_par(self.params + other.params, self.label + other.label)
        return new


def make_combiparameter(
        *params: list[str | Parameter],
        name: str = 'combi_par') -> combi_par:
    """
    Make a combined qcodes parameter.
    Args:
        *params : list of gates or parameters
        label: label for parameter
        name: name for parameter

    Note:
        Before a scan with reset_params=True the value of the combi_parameter must
        be set, e.g. `P2to4(0.0)`.

    Example:
        P2to4 = make_combiparameter("P2", "P3", "P4", name="P2to4")
        B1and2 = make_combiparameter(station.gates.B1, station.gates.B2, name="B1and2")
    """
    station = Station.default
    parameters = []
    for i in params:
        if type(i) == str:
            parameters.append(getattr(station.gates, i))
        else:
            parameters.append(i)

    label = ""
    for i in parameters:
        label += i.label + " "

    return combi_par(parameters, label, name)


class v_src_rescaler(Parameter):
    def __init__(self, parameter: Parameter, scale: float):
        super().__init__(parameter.name, label=parameter.label, unit = parameter.unit)
        self._parameter = parameter
        self._scale = scale

    def set_raw(self, value: float):
        self._parameter(value/self._scale)

    def get_raw(self):
        return self._parameter()*self._scale
