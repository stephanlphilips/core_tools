from core_tools.sweeps.sweep_utility import sweep_info
from qcodes import Parameter

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



if __name__ == '__main__':

    from qcodes import Parameter, MultiParameter, new_experiment
    import numpy as np
    import time
    new_experiment("name", "testing")

    class test_AWG_sequence0D(object):
        """docstring for test_AWG_sequence"""
        def __init__(self):
            super(test_AWG_sequence0D, self).__init__()
            self.shape = (1, )
            self.uploader = uploader()
            self.units = ("V",)
            self.labels = ("y axis",)
            self.setpoints = (np.linspace(20,50,1),)
        def play(self, idx):
            time.sleep(0.01)
            pass
            
            
        def upload(self, idx):
            pass
    class test_AWG_sequence1D(object):
        """docstring for test_AWG_sequence"""
        def __init__(self):
            super(test_AWG_sequence1D, self).__init__()
            self.shape = (50, )
            self.uploader = uploader()
            self.units = ("V",)
            self.labels = ("y axis",)
            self.setpoints = (np.linspace(20,50,50),)
        def play(self, idx):
            time.sleep(0.01)
            pass
            
        
        def upload(self, idx):
            pass
    class test_AWG_sequence2D(object):
        """docstring for test_AWG_sequence"""
        def __init__(self):
            super(test_AWG_sequence2D, self).__init__()
            self.shape = (50, 50)
            self.units = ("V", "V")
            self.labels = ("x axis", "y axis")
            self.setpoints = (np.linspace(20,50,50), np.linspace(50,125,50))
            self.uploader = uploader()

        def play(self, idx):
            time.sleep(0.01)
            pass
            
            
        def upload(self, idx):
            pass
    class dummy_parameter(Parameter):
        def __init__(self, name, label=None, unit=None):
            
            super().__init__(name=name,
                             instrument=None,
                             labels=( "digitzer_response"),
                             units=("unit1" ))
    class dummy_multi_parameter(MultiParameter):
        def __init__(self, name, label=None, unit=None):
            
            super().__init__(name=name,
                             instrument=None,
                             names=("test12","test1234"),
                             shapes=( (200, ) , (200, ), ),
                             labels=( "digitzer_response",  "D2"),
                             units=("unit1", "unit2"), )
            self.setpoints = ( (np.linspace(70,500,200),  ),  (np.linspace(70,500,200), ))
            self.setpoint_shapes = ( (200, ),   (200, ))
            self.setpoint_labels = ( ("I channel", ),   ('Q channel', ))
            self.setpoint_units = ( ("mV", ),   ("mV", ))
            self.setpoint_names = ( ("test_name", ),   ("testname_2", ))
            self.i = 2
        def get_raw(self):
            self.i +=1
            return (np.linspace(0,500,200)+self.i, np.linspace(0,500,200)+self.i+100)
    class dummy_multi_parameter_2dawg(MultiParameter):
        def __init__(self, name, label=None, unit=None):
            
            super().__init__(name=name,
                             instrument=None,
                             names=("test12","test1234"),
                             shapes=( tuple() , tuple() ),
                             labels=( "digitzer_response",  "D2"),
                             units=("unit1", "unit2"), )
            self.setpoints = ( tuple(),  tuple())
            self.setpoint_shapes = ( tuple(),   tuple())
            self.setpoint_labels = ( ("I channel", ),   ('Q channel', ))
            self.setpoint_units = ( ("mV", ),   ("mV", ))
            self.setpoint_names = ( ("I_channel", ),   ("Q_channel", ))
            self.i = 2
        def get_raw(self):
            self.i +=1
            return (self.i, self.i+100)
    class uploader(object):
        """docstring for uploader"""
        def __init__(self, ):
            super(uploader, self).__init__()
        
        def wait_until_AWG_idle(self):
            '''
            check if the AWG is doing playback, when done, release this function
            '''
            time.sleep(0.01)
            pass
            
    measurment_parameter = dummy_multi_parameter("digitzer_1", label="qubit_1 (spin up)", unit="%")
    measurment_parameter2D = dummy_multi_parameter_2dawg("digitzer_1", label="qubit_1 (spin up)", unit="%")

    awg_sequence0D = test_AWG_sequence0D()
    awg_sequence1D = test_AWG_sequence1D()
    awg_sequence2D = test_AWG_sequence2D()
    test = pulselib_2_qcodes(awg_sequence0D)
    print(test)