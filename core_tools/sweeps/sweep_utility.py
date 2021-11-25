from dataclasses import dataclass
from qcodes import Parameter
import numpy as np

class KILL_EXP(Exception):
    pass

def get_measure_data(m_instr):
    '''
    measure date for given paramters in m_instr

    Args:
        m_instr (list<qc.Parameter>) : list with parameters to be measured
    Returns
        my_data (list<qc.Parameter>), np.ndarray/str/float/int>)
    '''
    my_data = []
    for instr in m_instr:
        my_data.append( (instr, instr.get()))

    return my_data


FAST = "FAST"
SLOW = "SLOW"


MODE = SLOW


class PulseLibParameter(Parameter):

    def add_setpoints(self, setpoints, sequencer, lowest_level):
        self.flat_index = 0
        self.setpoints = setpoints
        self.sequencer = sequencer
        self.lowest_level = lowest_level

    def get_raw(self):
        current_val = self.setpoints[self.flat_index%len(self.setpoints)]

        self.flat_index += 1
        if self.flat_index >= np.prod(self.sequencer.shape):
            self.flat_index = 0

        return current_val

    def set_raw(self, value):
        if self.lowest_level:
            if self.flat_index == 0 and hasattr(self.sequencer, 'starting_lambda'):
                    self.sequencer.starting_lambda(self.sequencer)

            if MODE == SLOW or self.flat_index == 0:
                self.sequencer.upload(np.unravel_index(self.flat_index, self.sequencer.shape))

            index = np.unravel_index(self.flat_index, self.sequencer.shape)
            self.sequencer.play(index, release=True)
            if hasattr(self.sequencer, 'm_param'):
                self.sequencer.m_param.setIndex(tuple(index))
            if MODE == SLOW:
                self.sequencer.uploader.wait_until_AWG_idle()
            if MODE==FAST and self.flat_index < np.prod(self.sequencer.shape) - 1:
                self.sequencer.upload(np.unravel_index(self.flat_index+1, self.sequencer.shape))

class SequenceStartAction:
    def __init__(self, sequence):
        self._sequence = sequence

    def __call__(self):
        sequence = self._sequence
        if hasattr(sequence, 'starting_lambda'):
            sequence.starting_lambda(sequence)
        sequence.upload((0, ))
        sequence.play((0, ))
        if hasattr(sequence, 'm_param'):
            sequence.m_param.setIndex((0, ))


def pulselib_2_qcodes(awg_sequence):
    '''
    convert pulse sequencer object in qcodes parameters that are usable in sweeps.

    Args:
        awg_sequence (pulselib.sequencer.sequencer) : sequence object

    Returns:
        set_param (list<PulseLibParameter>) : set paramters for the pulselib to be used in the sweep
    '''
    set_param = list()
    if awg_sequence.shape == (1,):
        return set_param
    for i in range(len(awg_sequence.shape)):
        param = PulseLibParameter(name=awg_sequence.labels[i].replace(" ", "_"),
                                  label=awg_sequence.labels[i],
                                  unit=awg_sequence.units[i])
        param.add_setpoints(awg_sequence.setpoints[i], awg_sequence, False)
        set_param.append(sweep_info(param, n_points = len(awg_sequence.setpoints[i])))

    set_param[0].param.lowest_level=True
    return set_param[::-1]

@dataclass
class sweep_info():
    '''
    data class that hold the sweep info for one of the paramters.
    '''
    param : Parameter = None
    start : float = 0
    stop : float = 0
    n_points : int = 50
    delay : float = 0

    def __post_init__(self):
        self.orignal_value = None
        if not isinstance(self.param, PulseLibParameter):
            self.orignal_value = self.param()

    def reset_param(self):
        if self.orignal_value is not None:
            self.param.set(self.orignal_value)


def check_OD_scan(sequence, minstr):
    raise Exception('This function was broken beyond repair. Do not use it. [SdS]')
