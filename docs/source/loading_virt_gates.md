Loading old virtual gates
=========================

Old virtual gates can be imported from a dataset using:
```python
from core_tools.drivers.hardware.utility import load_virtual_gate_matrix_from_ds, load_AWG_to_dac_conversion_from_ds


ds_id = 1220

# hardware_name is the hardware name as defined in the station (core tools defaults to hardware)
load_virtual_gate_matrix_from_ds(ds_id, hardware_name='hardware') 
load_AWG_to_dac_conversion_from_ds(ds_id, hardware_name='hardware')
```
In case you are using a differnt dataset, it is also possible to provide a snapshot.

```python
from core_tools.drivers.hardware.utility import load_virtual_gate_matrix_from_snapshot, load_AWG_to_dac_conversion_from_snapshot

load_virtual_gate_matrix_from_snapshot(my_dataset.snapshot(), hardware_name='hardware') 
load_AWG_to_dac_conversion_from_snapshot(my_dataset.snapshot(), hardware_name='hardware') 
```
