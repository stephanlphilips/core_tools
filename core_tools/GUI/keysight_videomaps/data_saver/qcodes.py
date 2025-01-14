from qcodes import MultiParameter
try:
    from qcodes import Measure
    from qcodes.data.data_set import DataSet
except Exception:
    from qcodes_loop.measure import Measure
    from qcodes_loop.data.data_set import DataSet


from core_tools.GUI.keysight_videomaps.data_saver import IDataSaver


class QCodesDataSaver(IDataSaver):

    def save_data(self, vm_data_parameter: MultiParameter, label: str) -> tuple[DataSet, dict[str, str]]:
        """
        Performs a measurement using qcodes and writes the data to disk.

        Args:
            vm_data_parameter: a MultiParameter instance describing the measurement with settables, gettables and
            setpoints.
            label: a string that is used to label the dataset.

        Returns:
            A Tuple (ds, metadata) containing the created dataset ds and a metadata dict that uniquely identifies the
            dataset.
        """
        measure = Measure(vm_data_parameter)
        data = measure.run(quiet=True, name=label)
        data.finalize()
        return data, {'location': data.location}
