from qcodes import MultiParameter
from scipy import signal
import numpy as np
import matplotlib.pyplot as plt
import lmfit


def lin_func(x, a, b):
    return x*a + b


#TODO move to better location at later point
def get_phase_compentation_IQ_signal(param):
    '''
    Args:
        param (Multiparameter) : parameter with a get method that returns an I and Q array of a signal.
    Return:
        rotation_angle (double) : angle at which to rotate the signal to project it to the I plane.
    '''
    data_in = param.get()
    
    model = lmfit.Model(lin_func)
    
    a = np.average(data_in[0])/np.average(data_in[1])
    b = 0
    param = model.make_params(a=a, b=b)
    result = model.fit(data_in[1], param, x=data_in[0])
    
    angle = np.angle(1+1j*result.best_values['a'])
    
    # print(result.best_values['a'])
    # print(angle)
    # x= np.linspace(-120, 20, 100) 
    # plt.plot(x, lin_func(x, result.best_values['a'], result.best_values['b']))
    # plt.plot(data_in[0], data_in[1])
    # new_data = data_in[0] +1j*data_in[1]
    # new_data *= np.exp(1j*(-angle))
    # plt.plot(np.real(new_data), np.imag(new_data))

    # new_data = x +1j*lin_func(x, result.best_values['a'], result.best_values['b'])
    # new_data *= np.exp(1j*(-angle))
    # plt.plot(np.real(new_data), np.imag(new_data))
    return angle

class IQ_to_scalar(MultiParameter):
    '''
    parameter that converts IQ data of the digitizer into scalar data
    NOTE : ONLY ONE IQ CHANNEL PAIR SUPPORTED ATM !!!
    '''
    def __init__(self, digitizer_meas_param, phase_rotation):
        '''
        Args:
            digitizer (MultiParameter) : instrument class of the digitizer
            phase_rotation (double) : rotation in the IQ plane (will keep only I)
        '''
        self.dig = digitizer_meas_param
        self.phase_rotation = phase_rotation
        self.sample_rate = digitizer_meas_param.sample_rate

        names = ('RF_readout_amplitude',)
        super().__init__('IQ_to_scalar_convertor', names=names, shapes=(self.dig.shapes[0],),
                         labels=(self.dig.labels[0],), units=(self.dig.units[0],),
                         setpoints=(self.dig.setpoints[0],),
                         setpoint_names=(self.dig.setpoint_names[0],),
                         setpoint_labels=(self.dig.setpoint_labels[0],),
                         setpoint_units=(self.dig.setpoint_units[0],))

    def get_raw(self):
        data_in = self.dig.get_raw()
        data_out = (data_in[0] + 1j*data_in[1])*np.exp(1j*self.phase_rotation[0])
        data_out_SD2 = (data_in[2] + 1j*data_in[3])*np.exp(1j*self.phase_rotation[1])
        return (data_out.real+1j*data_out_SD2.real, ) #EDITED Mateusz


class down_sampler(MultiParameter):
    '''
    Down sampler for a digitizer, given a certain bandwidth, take make blibs for example more clear.
    '''
    def __init__(self, digitizer, bandwidth, highpass = None):
        '''
        Args: 
            digitizer (MultiParameter) : instrument class of the digitizer 
            bandwidth (double) : wanted bandwidth (3db point of a butterworth filter)
            highpass (double) : if defined, sets a highpass filter at a given freq
        '''
        self.dig = digitizer
        self.bandwidth = bandwidth
        self.highpass = highpass
        self.sample_rate = digitizer.sample_rate
        self.sample_drop_rate = int(self.dig.sample_rate/bandwidth/2)

        shapes, setpoints = self.get_shape()
        super().__init__('Elzerman_state_differentiator', names=digitizer.names, shapes=shapes,
                         labels=digitizer.labels, units=digitizer.units, setpoints=setpoints,
                         setpoint_names=digitizer.setpoint_names,
                         setpoint_labels=digitizer.setpoint_labels,
                         setpoint_units=digitizer.setpoint_units)

    def get_raw(self):
        data_out = tuple()
        data_in = self.dig.get()

        for i in range(len(data_in)):
            filtered_data = np.empty(self.shapes[0])

            if filtered_data.ndim == 2:
                for j in range(len(filtered_data)):
                    filtered_data[j,:] = filter_data(data_in[i][j], self.bandwidth, self.dig.sample_rate, 'lowpass')[::self.sample_drop_rate]
                
                    if self.highpass is not None:
                        filtered_data[j,:] =  filter_data(filtered_data[j], self.highpass,  self.sample_rate/self.sample_drop_rate, 'highpass')
            else:
                filtered_data[:] = filter_data(data_in[i], self.bandwidth, self.dig.sample_rate, 'lowpass')[::self.sample_drop_rate]
                
                if self.highpass is not None:
                    filtered_data[:] =  filter_data(filtered_data[:], self.highpass, self.sample_rate/self.sample_drop_rate, 'highpass')

            data_out += (filtered_data,)

        return tuple(data_out)

    def get_shape(self):
        shapes, setpoints = tuple(), tuple()

        for i in range(len(self.dig.names)):
            setpt = self.dig.setpoints[i]
            shape = tuple()

            if len(setpt) > 1:
                setpt = (setpt[0], np.asarray(setpt[1]).flatten()[::self.sample_drop_rate], )
                shape = (len(setpt[0]), len(setpt[1]))
            else:
                setpt = (np.asarray(setpt).flatten()[::self.sample_drop_rate], )
                shape = setpt[0].shape

            shapes += (shape, )
            setpoints += (setpt, )

        return shapes, setpoints

    def update_shape(self):
        self.shapes, self.setpoints = self.get_shape()

class data_reshaper(MultiParameter):
    '''
    reshapes the dataarray of the incomming array.
    '''
    def __init__(self, N, digitizer):
        '''
        Args:
            N (int) : number of slices
            digitizer (MultiParameter) : instrument class of the digitizer
        '''
        self.N = int(N)
        self.dig = digitizer
        self.sample_rate = digitizer.sample_rate

        names, shapes, labels, units = [],[],[],[]
        for name, label, unit, shape in zip(self.dig.names, self.dig.labels,self.dig.units, self.dig.shapes):
            shape = [*shape]
            shape[0] = int(shape[0]/self.N)
            
            for nth_qubit in range(self.N):
                names += ['{}_qubit_{}'.format(name, nth_qubit)]
                labels += ['{}_qubit_{}'.format(label, nth_qubit)]
                units += ['{}_qubit_{}'.format(unit, nth_qubit)]

                shapes += [tuple(shape)]

        setpoints, setpoint_names, setpoint_labels, setpoint_units = [],[],[],[]
        for i in range(len(self.dig.setpoints)):
            setpoint = [*self.dig.setpoints[i]]

            setpoint[0] = setpoint[0][0:int(len(setpoint[0])/self.N)]

            for nth_qubit in range(self.N):
                setpoints += [tuple(setpoint)]
                setpoint_names += [self.dig.setpoint_names[i]]
                setpoint_labels += [self.dig.setpoint_labels[i]]
                setpoint_units += [self.dig.setpoint_units[i]]


        super().__init__('{}_reshaped_{}'.format(self.dig.name, self.N), names=tuple(names), shapes=tuple(shapes),
                         labels=tuple(labels), units=tuple(units),
                         setpoints=tuple(setpoints),
                         setpoint_names=tuple(setpoint_names),
                         setpoint_labels=tuple(setpoint_labels),
                         setpoint_units=tuple(setpoint_units))

    def get_raw(self):
        data_in = self.dig.get_raw()
        data_out = []

        # print(data_in)
        for data_slice in data_in:
            for N in range(self.N):
                data_out += [data_slice[N::self.N]]

        return tuple(data_out)

class Elzerman_param(MultiParameter):
    """
    parameter that aims to detect blibs.
    expected that the input data is already well filtered.
    """
    def __init__(self, digitizer, threshold, blib_down):
        '''
        Args:
            digitizer (MultiParameter) :  parameter providing the data for the dip detection
            threshold (double) : threadhold for the detection
            blib_down (bool) : direction of the blib (if true, downward blib expected).
        '''
        self.dig = digitizer
        self.threshold = threshold  
        self.blib_down = blib_down

        names = tuple()
        shapes = tuple()
        labels = tuple()
        units = tuple()
        setpoints = tuple()

        for i in range(len(digitizer.names)):
            names += ("qubit_{}".format(i), )
            shapes += ((), )
            labels += ('Spin probability qubit {}'.format(i+1) ,)
            units += ('%', )
            
            setpoints += ((),)

        super().__init__('Elzerman_state_differentiaor', names=names, shapes=shapes,
                         labels=labels, units=units, setpoints=setpoints)

    
    def get_raw(self):
        # expected format from the getter <tuple<np.ndarray[ndim=2,dtype=double]>>
        data_in = self.dig.get()
        data_out = []

        for data in data_in:
            if self.blib_down == True:
                blib_pt = np.where(data<self.threshold)[0]
            else :
                blib_pt = np.where(data>self.threshold)[0]
            
            data_out.append(np.unique(blib_pt).size/data.shape[0])

        return data_out

def filter_data(data, cutoff, fs, pass_zero, order = 4):
    '''
    filter noise out of a dataset
    Args:
        data (np.ndarray) : data array to filter
        cutoff (double) : cutoff in HZ (not that this is the last 0db point and not -3db)
        fs (double) : sample rate of the signal
        pass_zero (str) : 'lowpass' or 'highpass'
    '''
    b, a = signal.butter(order, cutoff/(fs/2), pass_zero)
    return signal.filtfilt(b, a, data)


if __name__ == '__main__':
    from projects.keysight_measurement.M3102A import SD_DIG, DATA_MODE
    from core_tools.utility.mk_digitizer_param import get_digitizer_param

    dig = SD_DIG('name', 1, 6)

    # dig.set_digitizer_software(1e3, 500*2)
    param = get_digitizer_param(dig, 50, 20*2, data_mode=DATA_MODE.FULL)
    print(param)
    param_scalar = IQ_to_scalar(param, 0)
    print(param_scalar)

    param_scaled_1 = data_reshaper(1, param)
    param_scaled_2 = data_reshaper(2, param_scalar)

    param_elzerman = Elzerman_param(param_scaled_2, 0, True)

    print(param_elzerman.names)
    print(param_elzerman.setpoint_names)
    
class PSB_param(MultiParameter):
    """
    """
    def __init__(self, digitizer, order, threshold=None):
        '''
        Args:
            digitizer (MultiParameter) :  parameter providing the data for the dip detection
             '''
        self.dig = digitizer
        self.order = order
        self.threshold = threshold        
        names = tuple()
        shapes = tuple()
        labels = tuple()
        units = tuple()
        setpoints = tuple()

        for i in range(len(digitizer.names)):
            names += ("qubit_{}".format(i), )
            shapes += ((), )
            if threshold is not None:
                if i%2 == 0:
                    labels += ('N states selected q{}{}'.format(i+1, i+2) ,)
                    units += ('#', )
                else : 
                    labels += ('S/T probability q{}{}'.format(i, i+1) ,)
                    units += ('%', )
            else:
                labels += ('Signal {}'.format(i+1) ,)
                units += ('mV', )
            
            setpoints += ((),)

        super().__init__('PSB_state_differentiaor', names=names, shapes=shapes,
                         labels=labels, units=units, setpoints=setpoints)

    
    def get_raw(self):
        # expected format from the getter <tuple<np.ndarray[ndim=2,dtype=double]>>
        data_inn = self.dig.get()
        data_in_SD1 = []
        data_in_SD2 = []   
        data_in =[]     
        for data_slice in data_inn:
            data_in_SD1 += [data_slice.real]
            data_in_SD2 += [data_slice.imag]
        for n in range(len(self.order)):
            if self.order[n] == 1:
                data_in +=  [data_in_SD1[n]] 
            else:
                data_in +=  [data_in_SD2[n]] 
        data_out = []
        if not isinstance(self.threshold, list):
            for n in range(len(data_in)):
                if self.threshold is None:
                    data_out.append(np.mean(data_in[n]))
                else:
                    threshold = self.threshold[n]
                    data_out += [(np.where(data_in[n] > threshold)[0].size)/np.asarray(data_in[n]).size]
            return data_out

        else:
            # print(data_in[0])
            if len(self.threshold) == 1:
                return (np.where(data_in[0] < self.threshold[0])[0]).size/data_in[0].size

            elif len(self.threshold) == 2:
                # expected S to be high in signal
                selection_1 = np.where(data_in[0] > self.threshold[0])[0]
                selected_data_1 = 0

                if selection_1.size != 0:
                    selected_data_1 = (np.where(data_in[1][selection_1] < self.threshold[1])[0].size)/selection_1.size
                return (selection_1.size, selected_data_1)

            # elif len(self.threshold) == 3:
            #     selection_1 = np.where(data_in[0] < self.threshold[0])[0]
            #     selection_2 = np.where(data_in[1] < self.threshold[1])[0]

            #     sel=np.intersect1d(selection_1, selection_2)

            #     if selection_1.size != 0:
            #         selected_data_1 = (np.where(data_in[2][sel] < self.threshold[2])[0].size)/sel.size

            #     return (selection_1.size, sel.size, selected_data_1)  

            elif len(self.threshold) == 3:
                selection_1 = np.where(data_in[0] > self.threshold[0])[0]
                selection_2 = np.where(data_in[1] < self.threshold[1])[0]

                sel=np.intersect1d(selection_1, selection_2)

                if selection_1.size != 0:
                    selected_data_1 = (np.where(data_in[2][sel] < self.threshold[2])[0].size)/sel.size
                # print(selected_data_1)
                return (selection_1.size, sel.size, selected_data_1)                

            elif len(self.threshold) == 4:
                selection_1 = np.where(data_in[0] > self.threshold[0])[0]
                selection_2 = np.where(data_in[1] > self.threshold[1])[0]
                if selection_1.size != 0:
                    selected_data_1 = (np.where(data_in[2][selection_1] < self.threshold[2])[0].size)/selection_1.size
                if selection_2.size != 0:
                    selected_data_2 = (np.where(data_in[3][selection_2] < self.threshold[3])[0].size)/selection_2.size

                return (selection_1.size, selected_data_1, selection_2.size, selected_data_2)

            elif len(self.threshold) == 8:
                selection_1 = np.where(data_in[0] < self.threshold[0])[0]
                selection_2 = np.where(data_in[1] > self.threshold[1])[0]
                selection_3 = np.where(data_in[2] < self.threshold[2])[0]
                selection_4 = np.where(data_in[3] > self.threshold[3])[0]

                sel123=np.intersect1d(selection_1, selection_2)
                sel456=np.intersect1d(selection_3, selection_4)
                sel=np.intersect1d(sel123, sel456)

                if sel.size != 0:
                    Q12 = (np.where(data_in[4][sel] < self.threshold[4])[0].size)/sel.size
                    Q3 = (np.where((data_in[4][sel] < self.threshold[4]) & (data_in[5][sel] > self.threshold[5]) | (data_in[4][sel] > self.threshold[4]) & (data_in[5][sel] < self.threshold[5]))[0].size)/sel.size
                    Q56 = (np.where(data_in[6][sel] < self.threshold[6])[0].size)/sel.size
                    Q4 = (np.where((data_in[6][sel] < self.threshold[6]) & (data_in[7][sel] > self.threshold[7]) | (data_in[6][sel] > self.threshold[6]) & (data_in[7][sel] < self.threshold[7]))[0].size)/sel.size

                return (sel123.size, sel456.size, sel.size, (sel.size/data_in[0].size), Q12, Q3, Q4, Q56)