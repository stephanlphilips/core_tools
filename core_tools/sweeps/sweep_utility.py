from dataclasses import dataclass
from qcodes import Parameter

class KILL_EXP(Exception):
    pass

@dataclass
class sweep_info():
    '''
    data class that hold the sweep info for one of the paramters.
    -- also contains a looper - (should this one move to somewhere else?)
    '''
    _param : Parameter = None
    start : float = 0
    stop : float = 0
    n_points : int = 50
    delay : float = 0

    def __post_init__(self):
        self.param = self._param

    @property
    def param(self):
        return self._param

    @param.setter
    def param(self, input_param):
        self.param_val = input_param.get()
        self._param = input_param

    def reset_param(self):
        self._param.set(self.param_val)

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

class PulseLibParameter(Parameter):
    setpoints = None
    flat_index = 0

    def add_setpoints(self, setpoints, sequencer, lowest_level):
        self.setpoints = setpoints
        self.sequencer = sequencer
        self.lowest_level = lowest_level

    def get_raw(self):
        current_val = self.setpoints[self.flat_index%len(self.setpoints)]

        self.flat_index += 1
        if self.flat_index > np.prod(self.sequencer.shape):
            self.flat_index = 0

        return current_val

    def set_raw(self, value):
        if self.lowest_level:
            if self.flat_index == 0:
                self.sequencer.upload(np.unravel_index(flat_index, self.sequencer.shape))

            index = np.unravel_index(flat_index, self.shape)
            self.sequencer.play(index)

            if flat_index < np.prod(self.shape) - 1:
                self.sequencer.upload(np.unravel_index(flat_index+1, self.shape))

            self.sequencer.uploader.wait_until_AWG_idle()

    '''
    @ sander, how can we make sure that a unused upload is removed when the garbage collector collects this?
    (e.g. when a set is performed to reset parameters -- normally this does not happen, but user might accidentatly do this.)
    '''

def pulselib_2_qcodes(awg_sequence):
    '''
    convert pulse sequencer object in qcodes parameters that are usable in sweeps.

    Args:
        awg_sequence (pulselib.sequencer.sequencer) : sequence object

    Returns:
        set_param (list<PulseLibParameter>) : set paramters for the pulselib to be used in the sweep
    '''
    set_param = list()
    for i in range(len(awg_sequence.shape)):
        param = PulseLibParameter(name = awg_sequence.labels[i].replace(" ", "_"), label=awg_sequence.labels[i], unit= awg_sequence.units[i])
        param.add_setpoints(awg_sequence.setpoints[i], awg_sequence, False)
        set_param.append(sweep_info(param, n_points = len(awg_sequence.setpoints[i])))

    set_param[0].param.lowest_level=True

    return set_param[::-1]
