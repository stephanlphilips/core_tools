import logging

from qcodes.measure import Measure

from core_tools.sweeps.sweeps import do0D
from core_tools.data.SQL.connect import sample_info


def save_data(vm_data_parameter, label):
    is_ds_configured = False
    try:
        is_ds_configured = isinstance(sample_info.project, str)
    except:
        pass

    try:
        if is_ds_configured:
            logging.info('Save')
            job = do0D(vm_data_parameter, name=label)
            ds = job.run()
            return ds
        else:
            # use qcodes measurement
            measure = Measure(vm_data_parameter)
            data = measure.run(quiet=True, name=label)
            data.finalize()
            return data
    except:
        logging.error(f'Error during save data', exc_info=True)