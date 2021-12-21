import qcodes.utils.validators as vals
import numpy as np
import time, pyvisa

from qcodes import Instrument, MultiParameter, Parameter

class TimeTrace(MultiParameter):
    def __init__(self, parent):
        super().__init__('time_trace', instrument=parent, names=('amp',), shapes=((parent.n_samples, ), ),
                         labels=('Current', ),
                         units=('A',),
                         setpoints=((np.linspace(0, parent.t_meas, parent.n_samples),),),
                         setpoint_names=(('time',),),
                         setpoint_labels=(('time',),),
                         setpoint_units=(('s',),)
                         )
        self.multiplier = 1

    def get_raw(self):
        return self.root_instrument.measure_buffer()*self.multiplier

class keithley6500(Instrument):
    def __init__(self, name, address, scaler = 1e-8):
        super().__init__(name)
        rm = pyvisa.ResourceManager()
        self.instr = rm.open_resource(address)
        self.mode = None
        self.n_samples = 10000
        self.t_meas = 1
        self.scaler = scaler

        self.add_parameter('amplitude',
                           get_cmd=self.get_voltage_measurement, unit='A')

    @property
    def TimeTrace(self):
        return TimeTrace(self)

    def prepare_buffer(self, t_meas, n_samples=10000):
        self.t_meas = t_meas
        self.n_samples = n_samples

    def get_voltage_measurement(self):
        if self.mode != 'voltage':
            self.mode = 'voltage'
            self.instr.write('*RST')
            self.instr.write(':SENS:FUNC "VOLT:DC" ')
            self.instr.write(':SENS:VOLT:RANG 10')
            self.instr.write(':SENS:VOLT:INP AUTO')
            self.instr.write(':SENS:VOLT:NPLC 1')
            self.instr.write(':SENS:VOLT:AZER ON')
            self.instr.write(':SENS:VOLT:AVER:TCON REP')
            self.instr.write(':SENS:VOLT:AVER:COUN 1')
            self.instr.write(':SENS:VOLT:AVER OFF')
            self.instr.write(':SENS:COUNT 1')
        return float(self.instr.query(':READ?'))*self.scaler

    def measure_buffer(self):
        self.mode='buffer'
        srate = int(self.n_samples/self.t_meas)

        self.instr.write('*CLS')
        self.instr.write('*RST')
        self.instr.write(f':TRAC:MAKE "noise_measurement", {self.n_samples}')

        self.instr.write(':DIG:FUNC "VOLT"')
        self.instr.write(f'SENS:DIG:VOLT:SRAT {srate}')
        self.instr.write(f'SENS:DIG:COUN {self.n_samples}')
        self.instr.write(':TRAC:TRIG:DIG "noise_measurement"')

        time.sleep(self.t_meas)
        s =self.instr.query('TRAC:ACT? "noise_measurement"')
        if self.n_samples != int(s):
            raise ValueError(f'Error samples is too low; ({int(s)})')
        data= self.instr.query(f'TRACe:DATA? 1,{self.n_samples}, "noise_measurement"')
        self.instr.write(':TRAC:DEL "noise_measurement"')
        data = np.fromstring(data, sep=',')
        return data*self.scaler
        # return data#data.reshape(int(data.size/2),2)[:, ::-1].T

if __name__ == '__main__':
    k = keithley6500('name', 'USB0::0x05E6::0x6500::04401705::0::INSTR')
    # print(k.set_voltage_measurement())
    # print(k.amplitude())
    # print(k.trace())
    # print(k.trace.setpoints[0].shape)

    t = 1

    # k.prepare_buffer(t)
    data = k.TimeTrace()
    print(data)
    import matplotlib.pyplot as plt
    plt.plot(np.linspace(0,t, data.size), data)
    plt.show()