import logging
from dataclasses import dataclass
from typing import List, Union

import numpy as np
from numpy import ndarray


from core_tools.data.measurement import Measurement
from qcodes import ManualParameter

logger = logging.getLogger(__name__)


@dataclass
class Axis:
    '''
    Axis in dataset.
    '''
    name: str
    label: str
    unit: str
    values: Union[ndarray, List[float]]


@dataclass
class Data:
    '''
    Data / variables in dataset.
    '''
    name: str
    label: str
    unit: str
    values: Union[ndarray, List[float]]


@dataclass
class _Action:
    action: str
    param: ManualParameter
    values: Union[ndarray, List[float]]


class DataWriter:
    def __init__(self, name, *args):
        self._measurement = Measurement(name, silent=True)
        self._actions = []
        self._set_params = []

        for arg in args:
            if isinstance(arg, Axis):
                # create param, add data
                self._add_axis(arg)
            elif isinstance(arg, Data):
                # create param, add data
                self._add_data(arg)
            else:
                raise TypeError(f"Unknown argument of type {type(arg)}")
        self._measurement.add_snapshot('data_writer', {'message': 'Data written by data writer'})

    def _add_axis(self, axis):
        param  = ManualParameter(axis.name, label=axis.label, unit=axis.unit)
        self._measurement.register_set_parameter(param, len(axis.values))
        self._set_params.append(param)
        self._actions.append(_Action('set', param, np.asarray(axis.values)))

    def _add_data(self, data):
        param  = ManualParameter(data.name, label=data.label, unit=data.unit)
        self._measurement.register_get_parameter(param, *self._set_params)
        self._actions.append(_Action('get', param, np.asarray(data.values)))

    def run(self):
        try:
            self._setpoints = [[param, None] for param in self._set_params]
            self._index = [0] * len(self._setpoints)
            with self._measurement:
                self._loop()
        except KeyboardInterrupt:
            logger.debug('Data saving interrupted', exc_info=True)
            logger.warning('Data saving interrupted')
            raise KeyboardInterrupt('Measurement interrupted') from None
        except Exception as ex:
            print(f'\n*** ERROR in data saver: {ex}')
            logger.error('Exception in data saver', exc_info=True)
            raise

        return self._measurement.dataset

    def _loop(self, iaction=0, isetpoint=0):
        if iaction == len(self._actions):
            return
        action = self._actions[iaction]
        if action.action == 'set':
            for i,value in enumerate(action.values):
                self._setpoints[isetpoint][1] = value
                self._index[isetpoint] = i
                self._loop(iaction + 1, isetpoint + 1)
        else:
            index = tuple(self._index[:isetpoint])
            self._measurement.add_result((action.param, action.values[index]), *self._setpoints)
            self._loop(iaction + 1, isetpoint)


def write_data(name: str, *args):
    '''
    Creates a dataset `name` using the specified Axis and Data.

    Args:
        name: name of the dataset.
        args: list of Axis and Data objects.

    Example:
        write_data(
            'Test',
            Axis('f', 'frequency', 'Hz', np.linspace(100e6, 200e6, 11)),
            Axis('e12', 'detuning', 'mv', np.linspace(-10, 10, 5)),
            Data('SD1', 'Sensor 1', 'mV', np.linspace(10, 20, 55).reshape((11, 5))),
            Data('SD1', 'Sensor 2', 'mV', np.linspace(0, -20, 55).reshape((11, 5))),
        )

    Note:
        The values of a Data object must have the combined dimensions of the Axis objects preceding it
        in the list.

        write_data(
            'Test',
            Axis('a', 'a', 'a.u.', values_a),
            Data('x', 'x', 'a.u., <array with shape(len(values_a)>),
            Axis('b', 'b', 'a.u.', values_b),
            Data('y', 'y', 'a.u., <array with shape(len(values_a), len(values_b)>),
            Axis('c', 'c', 'a.u.', values_c),
            Data('z', 'z', 'a.u., <array with shape(len(values_a), len(values_b), len(values_c)>),
        )
    '''
    return DataWriter(name, *args).run()


if __name__ == "__main__":
    import core_tools as ct
    ct.configure("../../examples/demo_station/setup_config/ct_config_measurement.yaml")
    write_data(
        'Test',
        Axis('f', 'frequency', 'Hz', np.linspace(100e6, 200e6, 11)),
        Axis('e12', 'detuning', 'mv', np.linspace(-10, 10, 5)),
        Data('SD1', 'Sensor 1', 'mV', np.linspace(10, 20, 55).reshape((11, 5))),
        Data('SD1', 'Sensor 2', 'mV', np.linspace(0, -20, 55).reshape((11, 5))),
    )


