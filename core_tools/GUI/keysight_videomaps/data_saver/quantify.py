from typing import List, Any, Optional, Sequence

from functools import partial
from pathlib import Path

import logging

import numpy as np
import numpy.typing as npt

from qcodes import Parameter, MultiParameter, Instrument

from quantify_core.measurement import MeasurementControl
from quantify_core.data.handling import set_datadir, get_datadir, get_latest_tuid

DEFAULT_DATADIR = Path('./data')
"""The default data directory to use if none is set up for quantify_core"""
_MEASUREMENT_CONTROL_INSTRUMENT_NAME = 'MC_live_plot_saving'
"""The name to use for the measurement control instance."""

class UnravelMultiParameter:

    INVALID_SUBSTRINGS_IN_PARAM_NAME = {'.'}
    """Specifies the substrings that cannot occur in the parameter name."""

    def __init__(self, multiparameter: MultiParameter):  # pylint: disable=too-many-locals
        """Split the MultiParameter that is returned by the pulse_lib function fast_scand1d_qblox() into
        setter and getter parameters that can be used with Quantify-core MeasurementControl.

        Copied from mjwoudstra"""
        # set parameters set the index for get parameters
        self.set_params: List[Parameter] = []
        # get parameters return 1 single value
        self.get_params: List[Parameter] = []
        self.set_params_setpoints: List[npt.NDArray[Any]] = []
        self._mp_data = None

        self._mp = multiparameter
        mp = self._mp
        # check setpoints are the same for every parameter
        for array in [
            mp.setpoint_names,
            mp.setpoint_labels,
            mp.setpoint_units,
            mp.setpoints,
        ]:
            self._check_all_equal(array)

        for dim, (name, label, unit, setpoints) in enumerate(
            zip(
                mp.setpoint_names[0],  # type: ignore[index]
                mp.setpoint_labels[0],  # type: ignore[index]
                mp.setpoint_units[0],  # type: ignore[index]
                mp.setpoints[0],  # type: ignore[index]
            )
        ):
            old_name = name
            name = UnravelMultiParameter._sanitize_param_name(name)
            logging.debug(f'Building settable Parameter {name} from {old_name}.')
            # reduce setpoints to 1D
            np_sp: npt.NDArray[Any] = np.asarray(setpoints)
            if np_sp.ndim > 1:
                lower_dims = tuple(range(np_sp.ndim - 1))
                sp_min = np_sp.min(axis=lower_dims)
                sp_max = np_sp.max(axis=lower_dims)
                if np.all(sp_min != sp_max):
                    raise Exception(f"Setpoints may only vary on last axis {np_sp}")
                # use setpoints on 1 axis
                sp_1d = sp_min
            else:
                sp_1d = np_sp
            val_map = dict(zip(sp_1d, range(len(sp_1d))))
            set_param = Parameter(
                name=name,
                label=label,
                unit=unit,
                val_mapping=val_map,
                set_cmd=partial(self._set_index, dim),
            )
            self.set_params_setpoints.append(sp_1d)
            self.set_params.append(set_param)

        self._index = [-1] * len(self.set_params)
        self._start_index = [0] * len(self.set_params)

        for name, label, unit in zip(mp.names, mp.labels, mp.units):
            old_name = name
            name = UnravelMultiParameter._sanitize_param_name(name)
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
                raise Exception(f"Parameters not equal: {value} != {ref_val}")

    def _set_index(self, dim: int, value: int) -> None:
        if self._index[dim] == value:
            return
        self._index[dim] = value
        if self._index == self._start_index:
            # Starting new fast scan. Force re-running of fast scan at next _get_value()
            self._mp_data = None

    def _get_value(self, i: int) -> Any:
        if self._mp_data is None:
            self._mp_data = self._mp()
        return self._mp_data[i][tuple(self._index)]  # type: ignore[index]


def save_data(vm_data_parameter, label):
    """
    Performs a measurement using quantify_core and writes the data to disk.

    Args:
        vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and setpoints.
        label: a string that is used to label the dataset.

    Returns:
        A Tuple (ds, metadata) containing the created dataset ds and a metadata dict with information about the dataset.
    """
    try:
        datadir = get_datadir()
    except NotADirectoryError:
        logging.warning("No quantify_core datadir set. Using default.")
        datadir = str(DEFAULT_DATADIR)
        set_datadir(datadir)

    logging.info(f"Data directory set to: \"{datadir}\".")

    try:
        meas_ctrl = Instrument.find_instrument(_MEASUREMENT_CONTROL_INSTRUMENT_NAME)
    except KeyError:
        meas_ctrl = MeasurementControl(_MEASUREMENT_CONTROL_INSTRUMENT_NAME)
    meas_ctrl.verbose(False)

    unraveled_param = UnravelMultiParameter(vm_data_parameter)
    meas_ctrl.settables(unraveled_param.set_params)
    meas_ctrl.gettables(unraveled_param.get_params)

    if len(unraveled_param.set_params) > 1:
        meas_ctrl.setpoints_grid(unraveled_param.set_params_setpoints)
    else:
        meas_ctrl.setpoints(unraveled_param.set_params_setpoints[0])

    logging.debug(f'Starting measurement with name: {label}.')
    dataset = meas_ctrl.run(label)
    meas_ctrl.close()

    return dataset, {'tuid': get_latest_tuid(), 'datadir': datadir}
