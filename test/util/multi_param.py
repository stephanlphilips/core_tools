import numpy as np
import qcodes as qc

class MyDigitizerParam(qc.MultiParameter):
    def __init__(self, t_measure, ch=[0, 1], name='my_param',
                 Vmax=2.0, sample_rate=1e9, n_rep=1000):
        self.t_measure = t_measure
        self.ch = ch
        self.Vmax = Vmax
        self.sample_rate = sample_rate

        self.timetrace = tuple(np.arange(0, t_measure, 1e9/sample_rate))
        self.n_samples = len(self.timetrace)
        self.n_rep = n_rep

        names = tuple()
        shapes = tuple()
        setpoints = tuple()
        setpoint_names = tuple()
        setpoint_units = tuple()
        setpoint_labels = tuple()
        if n_rep is None or n_rep < 2:
            for (i, channel) in enumerate(ch):
                names += (f't_trace{i+1}',)
                shapes += ((self.n_samples,),)
                setpoints += ((self.timetrace,),)
                setpoint_names += (('t',),)
                setpoint_units +=(('ns',),)
                setpoint_labels += (('time',),)
        else:
            sp_rep = tuple(np.arange(0, n_rep))
            for (i, channel) in enumerate(ch):
                names += (f't_trace{i+1}',)
                shapes += ((self.n_rep, self.n_samples),)
                setpoints += ((sp_rep, (self.timetrace,)*n_rep), )
                setpoint_names += (('n_rep','t',),)
                setpoint_units +=(('', 'ns',),)
                setpoint_labels += (('repetitions',),)

        super().__init__(name=name, names=names, shapes=shapes,
                         units=('mV',)*len(ch),
                         setpoints=setpoints, setpoint_names=setpoint_names,
                         setpoint_labels=setpoint_labels,
                         setpoint_units=setpoint_units)

    def snapshot_base(self, update=True, params_to_skip_update=None):
        snapshot = super().snapshot_base(update, params_to_skip_update)
        snapshot['t_measure'] = self.t_measure
        snapshot['sample_rate'] = self.sample_rate
        snapshot['Vmax'] = self.Vmax
        snapshot['n_rep'] = self.n_rep
        return snapshot

    def get_raw(self):
        return_data = list()
        for ch in self.ch:
            apex = int(self.n_samples / (ch+1))
            data = self.Vmax * np.concatenate([np.linspace(0, 1, apex),
                                               np.linspace(1, 0, self.n_samples-apex)])
            if self.n_rep is not None and self.n_rep > 1:
                reps = np.arange(0, self.n_rep)
                data = data * reps[:,None]
            return_data.append(data)

        return return_data
