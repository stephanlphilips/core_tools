from qcodes.dataset.measurements import Measurement
import qcodes as qc

import numpy as np
from qcodes import Parameter, MultiParameter, ArrayParameter

class spin_qubit_exp():
    """docstring for spin_qubit_exp"""
    def __init__(self, name, awg_sequence, measurment_parameter):
        self.awg_sequence = awg_sequence
        self.measurment_parameter = measurment_parameter
        self.name = name

    def run(self):
        """
        start the experiment.
        """
        set_points = list()
        set_variables = list()

        # TODO embed this in the pulse library.
        for i in range(len(self.awg_sequence.shape)):
            # 1 means single point
            if self.awg_sequence.shape[i] != 1:
                sweep_parameter = Parameter(name = self.awg_sequence.labels[i].replace(" ", "_"), label=self.awg_sequence.labels[i], unit= self.awg_sequence.units[i])
                
                set_points.append((sweep_parameter, self.awg_sequence.setpoints[i]))
                set_variables.append(sweep_parameter)

        meas = Measurement(name = self.name)

        for i in set_variables:
            meas.register_parameter(i)
        
        # need to register set variables for multiparameters and ArrayParameter!
        paramtype = "numeric"
        if hasattr(self.measurment_parameter, "shapes"):
            if len(self.measurment_parameter.shapes[0]) > 0:
                paramtype = "array"
        elif hasattr(self.measurment_parameter, "shape"):
            if len(self.measurment_parameter.shape) > 0:
                paramtype = "array"

        meas.register_parameter(self.measurment_parameter, setpoints=tuple(set_variables[::-1]), paramtype= paramtype)

        try:
            with meas.run() as datasaver:
                # recursive setting
                my_loop = looper(self.awg_sequence, datasaver, self.measurment_parameter, set_points)
                my_loop.run()
        except KeyboardInterrupt:
            print("Measurement Interrupted")

        return datasaver.dataset


class looper():
    """docstring for looper"""
    def __init__(self, awg_sequencer, data_saver, digitzer_parameter, set_points):
        """
        Args:
            awg_sequencer (sequencer) : add awg sequencer object.
            datasaver (qcodes datasaver) : argument when calling  
            digitzer_parameter (Parameter) : Qcodes parameter that fetched the data for the digitzer.

        """
        self.awg_sequencer = awg_sequencer
        self.shape = awg_sequencer.shape
        # generate setpoints and units + labels form the AWG library.
        self.datasaver = data_saver
        self.setpoints = set_points
        self.digitzer_parameter = digitzer_parameter

    def run(self, top_index = None):
        '''
        instructions ::
        
        (i index refers to a travalling flat index.)
        UPLOAD AWG DATA : upload(i) (while play)
        GET AND SAVE DATA : get_data (i-1) (while play)
        START PLAYBACK ON AWG : play(i)
        '''

        flat_index = 0

        # self.awg_sequencer.upload(np.unravel_index(flat_index, self.shape))
        # try:
        #     self.awg_sequencer.upload(np.unravel_index(flat_index + 1, self.shape))
        # except:
        #     pass

        for flat_index in range(np.prod(self.shape)):
            
            index = np.unravel_index(flat_index, self.shape)
            self.awg_sequencer.upload(np.unravel_index(flat_index, self.shape))
            self.awg_sequencer.play(index)

            # if flat_index < np.prod(self.shape) - 2:
            #     self.awg_sequencer.upload(np.unravel_index(flat_index+2, self.shape))

            self.awg_sequencer.uploader.wait_until_AWG_idle()
            self.save_data(flat_index)

        self.datasaver.flush_data_to_database()

    def save_data(self, flat_index):
        """
        save data in the qcodes database.

        Args:
            flat_index (int) : index indicating where we are in the experimenent.
        """
        index_save = np.unravel_index(flat_index, self.shape)
        my_setpoints = []

        for i in range(len(index_save)):
            # tuple(paramter, value)
            if len(self.setpoints) > 0 :
                my_setpoints.append((self.setpoints[i][0], self.setpoints[i][1][index_save[-1-i]]))

        self.datasaver.add_result(*my_setpoints, (self.digitzer_parameter, self.digitzer_parameter.get())) 
        # make sure data is written into the data base.
        if flat_index%20 == 0:
            self.datasaver.flush_data_to_database()

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

if __name__ == '__main__':

    from qcodes import Parameter, MultiParameter, new_experiment
    import time
    new_experiment("name", "testing")

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

    measurment_parameter = dummy_multi_parameter("digitzer_1", label="qubit_1 (spin up)", unit="%")
    measurment_parameter2D = dummy_multi_parameter_2dawg("digitzer_1", label="qubit_1 (spin up)", unit="%")

    # test = spin_qubit_exp("test", test_AWG_sequence0D(), measurment_parameter)    
    # test.run()
    test = spin_qubit_exp("test",test_AWG_sequence1D(), measurment_parameter)
    test.run()
    # test = spin_qubit_exp("test",test_AWG_sequence2D(), measurment_parameter2D)
    # test.run()
    # time.sleep(10)
