from typing import List, Any, Optional

from functools import partial
from collections.abc import Sequence

import logging

import numpy as np
from numpy import typing as npt

from qcodes import MultiParameter, Parameter


class ConvertingMultiParameter(MultiParameter):
    '''
    Converts the data of a MultiParameter using the specified function(s).
    Args:
        parameter (MultiParameter): parameter to convert.
        func (Union[Callable[[np.ndarray], np.ndarray],
                    Sequence[Callable[[np.ndarray], np.ndarray]]]):
            defines function to be applied to each item.
    Examples:
        # applies np.abs to all items
        my_param = ConvertingMultiParameter(param, np.abs)

        # determine qubit state using a different threshold per channel
        def get_state(x, threshold):
            return x > threshold

        f = (
            partial(get_state, threshold=0.4),
            partial(get_state, threshold=0.6),
            )
        my_param = ConvertingMultiParameter(param, f)
    '''
    def __init__(self, name, parameter, func):
        self.parameter = parameter
        self.n_items = len(parameter.names)
        self.func = func if isinstance(func, Sequence) else (func,)*self.n_items
        super().__init__(
                name=name, names=parameter.names,
                shapes=parameter.shapes, labels=parameter.labels,
                units=parameter.units, setpoints=parameter.setpoints,
                setpoint_names=parameter.setpoint_names,
                setpoint_labels=parameter.setpoint_labels,
                setpoint_units=parameter.setpoint_units)

    def get_raw(self):
        data = self.parameter()
        res = []
        for i in range(self.n_items):
            f = self.func[i]
            ch_data = data[i]
            res.append(f(ch_data))

        return res

    def snapshot_base(self, update=True, params_to_skip_update=None):
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot['parent'] = self.parameter.snapshot()
        return snapshot


class MappedMultiParameter(MultiParameter):
    '''
    Converts a MultiParameter to another MultiParameter.
    `channel_map` specifies the conversion for every output item.
    The key of this dictionary is the name of the output item. The value
    is a tuple of channel name, function and optionally the unit.
    The function can be a callable Python function, or a string.
    Supported strings are:
        'I' for I of I/Q signal (real part)
        'Q' for Q of I/Q signal (imaginary part)
        'Re' for real part
        'Im' for imaginary part
        'abs' for np.abs()
        'angle' for np.angle()
        'angle_deg' for np.angle(deg=True)

    Args:
        parameter (MultiParameter): parameter to convert.
        param_map (Dict[str, Tuple[int, Union[str, Callable[[np.ndarray], np.ndarray]]]):
            defines new list of derived parameters.
            Dictionary entries name: (channel_number, func).

    Example:
        ch_map = {
            'ch1_I':('ch1', np.real),
            'ch1_Q':('ch1', np.imag),
            'ch3_Amp':('ch3', np.abs),
            'ch3_Phase':('ch3', np.angle, 'rad')
            }
        my_param = MappedMultiParameter(dig.measure, ch_map)

        ch_map2 = {
            'ch1_I':('ch1', 'I'),
            'ch1_Q':('ch1', 'Q'),
            'ch3_Amp':('ch3', 'abs'),
            'ch3_Phase':('ch3', 'angle_deg', 'degrees')
            }
        my_param2 = MappedMultiParameter(dig.measure, ch_map2)
    '''
    def __init__(self, name, parameter, channel_map):
        self.parameter = parameter
        self.channel_map = channel_map.copy()

        # backwards compatibility with older iq_mode parameter
        str2func = {
                'I': np.real,
                'Q': np.imag,
                'Re': np.real,
                'Im': np.imag,
                'abs': np.abs,
                'angle': np.angle,
                'angle_deg': partial(np.angle, deg=True)}

        self.input_channels = {name:i for i,name in enumerate(parameter.names)}

        units = []
        names = []
        shapes = []
        labels = []
        setpoints = []
        setpoint_names = []
        setpoint_labels = []
        setpoint_units = []
        for k,(ch,f,*u) in channel_map.items():
            nr = self.input_channels[ch]
            names.append(k)
            labels.append(k)
            shapes.append(parameter.shapes[nr])
            units.append(u[0] if len(u)>0 else parameter.units[nr])
            setpoints.append(parameter.setpoints[nr])
            setpoint_names.append(parameter.setpoint_names[nr])
            setpoint_labels.append(parameter.setpoint_labels[nr])
            setpoint_units.append(parameter.setpoint_units[nr])
            if isinstance(f, str):
                self.channel_map[k] = (ch, str2func[f], *u)

        super().__init__(
            name=name, names=names,
            shapes=shapes, labels=labels,
            units=units, setpoints=setpoints,
            setpoint_names=setpoint_names,
            setpoint_labels=setpoint_labels,
            setpoint_units=setpoint_units)

    def get_raw(self):
        data = self.parameter()
        res = []
        for ch, func, *unit in self.channel_map.values():
            ch_data = data[self.input_channels[ch]]
            res.append(func(ch_data))

        return res

    def snapshot_base(self, update=True, params_to_skip_update=None):
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot['parent'] = self.parameter.snapshot()
        return snapshot


class AwgScanToQuantifyMapper:

    INVALID_SUBSTRINGS_IN_PARAM_NAME = {'.'}
    """Specifies the substrings that cannot occur in the parameter name."""

    def __init__(self, multiparameter: MultiParameter):  # pylint: disable=too-many-locals
        """Split the MultiParameter that is returned by the pulse_lib function fast_scand1d_qblox() into
        setter and getter parameters that can be used with Quantify-core MeasurementControl."""
        # set parameters set the index for get parameters
        self.set_params: List[Parameter] = []
        # get parameters return 1 single value
        self.get_params: List[Parameter] = []
        self.set_params_setpoints: List[npt.NDArray[Any]] = []
        self._measurement_data = None

        self._multiparameter = multiparameter
        # check setpoints are the same for every parameter
        for array in [
            multiparameter.setpoint_names,
            multiparameter.setpoint_labels,
            multiparameter.setpoint_units,
            multiparameter.setpoints,
        ]:
            self._check_all_equal(array)

        for dim, (name, label, unit, setpoints) in enumerate(
            zip(
                multiparameter.setpoint_names[0],  # type: ignore[index]
                multiparameter.setpoint_labels[0],  # type: ignore[index]
                multiparameter.setpoint_units[0],  # type: ignore[index]
                multiparameter.setpoints[0],  # type: ignore[index]
            )
        ):
            old_name = name
            name = AwgScanToQuantifyMapper._sanitize_param_name(name)
            logging.debug(f'Building settable Parameter {name} from {old_name}.')
            # reduce setpoints to 1D
            np_sp: npt.NDArray[Any] = np.asarray(setpoints)
            if np_sp.ndim > 1:
                lower_dims = tuple(range(np_sp.ndim - 1))
                setpoints_min = np_sp.min(axis=lower_dims)
                setpoints_max = np_sp.max(axis=lower_dims)
                if np.all(setpoints_min  != setpoints_max ):
                    raise Exception(f"Setpoints may only vary on last axis {np_sp}")
                # use setpoints on 1 axis
                setpoints_1d = setpoints_min
            else:
                setpoints_1d  = np_sp
            val_map = dict(zip(setpoints_1d, range(len(setpoints_1d))))
            set_param = Parameter(
                name=name,
                label=label,
                unit=unit,
                val_mapping=val_map,
                set_cmd=partial(self._set_index, dim),
            )
            self.set_params_setpoints.append(setpoints_1d )
            self.set_params.append(set_param)

        self._index = [-1] * len(self.set_params)
        self._start_index = [0] * len(self.set_params)

        for name, label, unit in zip(multiparameter.names, multiparameter.labels, multiparameter.units):
            old_name = name
            name = AwgScanToQuantifyMapper._sanitize_param_name(name)
            logging.debug(f'Building gettable Parameter {name} from {old_name}.')

            get_param = Parameter(
                name=name,
                label=label,
                unit=unit,
                get_cmd=partial(self._get_value, len(self.get_params)),
            )
            self.get_params.append(get_param)

    @classmethod
    def _sanitize_param_name(cls, name: str) -> str:
        new_name = name
        for substring in cls.INVALID_SUBSTRINGS_IN_PARAM_NAME:
            new_name = new_name.replace(substring, '_')
        return '_' + new_name

    @staticmethod
    def _check_all_equal(array: Optional[Sequence[Sequence[Any]]]) -> None:
        ref_val = array[0]  # type: ignore[index]
        for value in array[1:]:  # type: ignore[index]
            if value != ref_val:
                raise ValueError(f"Parameters not equal: {value} != {ref_val}")

    def _set_index(self, dim: int, value: int) -> None:
        if self._index[dim] == value:
            return
        self._index[dim] = value
        if self._index == self._start_index:
            # Starting new fast scan. Force re-running of fast scan at next _get_value()
            self._measurement_data = None

    def _get_value(self, i: int) -> Any:
        if self._measurement_data is None:
            self._measurement_data = self._multiparameter()
        return self._measurement_data[i][tuple(self._index)]  # type: ignore[index]
