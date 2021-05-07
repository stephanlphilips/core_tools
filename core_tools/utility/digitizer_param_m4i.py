from qcodes.instrument.parameter import MultiParameter
import numpy as np
import numbers
import pyspcm

class digitizer_param(MultiParameter):
    """
    A gettable qcodes parameter that returns an array of channels.
    For each channel the data is returned in an 0, 1, 2, or 3-dimensional
    array. The dimensions of the channel data are [repetition, trigger, time],
    each dimensions being optional:
        * repetition is present when `n_rep` is specified and average_repetition=False
        * trigger is present when `n_triggers` is specified
        * time is present when average_time=False

    Args:
        digitizer (Instrument): the digitizer this parameter belongs to.
        t_measure (float): measurement duration.
        n_rep (Optional[int]): number of repetitions of the measurement.
        n_triggers (Optional[int]): number of read-outs in 1 meausrement.
        channels (Optional[list]): List of channels to be measured.
        sample_rate (Optional[int]): Sampling rate to be set in the digitizer.
        mV_range (Optional[list]): mV_range of each active channel.
        sw_trigger (bool): Use software trigger instead of EXT0 trigger settings.
        start_func (Callable[[None],None]): function to call to start acquisition.
        box_averages (Optional[int]): Use boxcar averaging with specified length.
        average_time (bool): Average time values (removes time dimension)
        average_repetitions (bool): Average over repetitions (removes repetition dimension)
        name (Optional[str]): the local name of the whole parameter. Should be a valid
            identifier, ie no spaces or special characters. If this parameter
            is part of an Instrument or Station, this is how it will be
            referenced from that parent, ie ``instrument.name`` or
            ``instrument.parameters[name]``
        names (Optional[Tuple[str]]): A name for each channel returned by the digitizer.
        labels (Optional[Tuple[str]]): A label for each channel.
        units (Optional[Tuple[str]]): The unit of measure for each channel

    Note:
        Setup related settings, such as input termination and coupling, should be set
        with driver methods:
            digitizer.set_channel_settings(...), or
            digitizer.initialize_channels(...)
            digitizer.set_ext0_OR_trigger_settings(...)

        `start_func` can be used to (externally) trigger the digitizer acquisition.
        `start_func` is called in every get_raw() call.
    """
    def __init__(self, digitizer, t_measure, n_rep=None, n_triggers=None,
                 channels=None, sample_rate = None, mV_range= None,
                 sw_trigger=False, start_func=None, box_averages=None,
                 average_time=False, average_repetitions=False,
                 name=None, names=None, labels=None, units=None):

        if channels is not None:
            if len(channels) not in [1,2,4]:
                raise Exception('Number of enabled channels on M4i must be 1, 2 or 4.')
            digitizer.enable_channels(sum(2**ch for ch in channels))
        else:
            channels = digitizer.active_channels()

        if name is None:
            name = digitizer.name + '_measurement'

        if names is None:
            names = []
            for ch in channels:
                names.append(f'dig_{ch}')

        if labels is None:
            labels = []
            for ch in channels:
                labels.append(f'dig_{ch}')

        if units is None:
            units = ['mV']*len(channels)

        super().__init__(name=name, instrument=digitizer,
             names=names, labels=labels, units=units,
             shapes = ((),)*len(channels))

        self.digitizer = digitizer
        self.channels = channels
        self.num_ch = len(self.channels)
        self.t_measure = t_measure
        self.n_rep = n_rep
        self.n_trigger = n_triggers
        self.average_time = average_time
        self.average_repetitions = average_repetitions
        self.n_seg = ifNone(self.n_rep, 1) * ifNone(self.n_trigger, 1)
        self.start_func = start_func

        if sample_rate is not None:
            self._digitizer.sample_rate(sample_rate)
        # read sample rate after setting, because M4i adjusts automatically to supported rates
        self.sample_rate = self._instrument.sample_rate()

        self.eff_sample_rate = self.sample_rate / box_averages if box_averages is not None else self.sample_rate
        self.seg_size = int(np.round(self.eff_sample_rate * self.t_measure))
        if self.seg_size == 0:
            raise ValueError(f'invalid settings: sample_rate:{self.sample_rate} t_measure:{self.t_measure}')

        add_time = not average_time
        add_triggers = self.n_trigger
        add_repetitions = self.n_rep and not average_repetitions
        shape, setpoints, sp_names, sp_labels, sp_units = \
            self._shape_and_setpoints(add_time, add_triggers, add_repetitions)
        self.shapes = (shape,)*self.num_ch
        self.setpoints = (setpoints,)*self.num_ch
        self.setpoint_names = (sp_names,)*self.num_ch
        self.setpoint_labels = (sp_labels,)*self.num_ch
        self.setpoint_units = (sp_units,)*self.num_ch

        self.shape = (self.num_ch, ) + shape

        if mV_range is not None:
            if isinstance(mV_range, numbers.Number):
                mV_range = [int(mV_range)]*self.num_ch
            try:
                for i,ch in enumerate(channels):
                    self._digitizer.set(f'range_channel_{ch}', mV_range[i])
            except:
                raise Exception('Failed to set mV_ranges. Array length same as channels?')
        else:
            mV_range = [self.digitizer.get(f'range_channel_{ch}') for ch in channels]
        self.mV_range = mV_range

        self.derived_params = []

        if sw_trigger:
            self.digitizer.trigger_or_mask(pyspcm.SPC_TMASK_SOFTWARE)
        else:
            self.digitizer.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)

        if box_averages:
            self.digitizer.box_averages(box_averages)
        self.digitizer.setup_multi_recording(self.seg_size, n_triggers=self.n_seg,
                                             boxcar_average=box_averages is not None)
        acq_shape = (self.num_ch, )
        if self.n_rep:
            acq_shape += (self.n_rep, )
        if self.n_trigger:
            acq_shape += (self.n_trigger, )
        acq_shape += (self.digitizer.segment_size(),)
        self.acq_shape = acq_shape

    def _shape_and_setpoints(self, add_time, add_triggers, add_repetitions):
        shape = ()
        setpoints = ()
        sp_names = ()
        sp_labels = ()
        sp_units = ()

        # build dimensions from last to first for correct setpoints
        if add_time:
            setp_time = tuple((np.arange(self.seg_size))/self.eff_sample_rate)
            shape = (self.seg_size,)
            setpoints = (setp_time,)
            sp_names = ('t',)
            sp_labels = ('time',)
            sp_units = ('s',)

        if add_triggers:
            setp_trigger = tuple(range(1,self.n_trigger+1))
            shape = (self.n_trigger,) + shape
            setpoints =  (setp_trigger,) + ( (setpoints,) if setpoints else () )
            sp_names = ('trigger',) + sp_names
            sp_labels = ('trigger',) + sp_labels
            sp_units = ('',) + sp_units

        if add_repetitions:
            setp_rep = tuple(range(1,self.n_rep+1))
            shape = (self.n_rep,) + shape
            setpoints =  (setp_rep,) + ( (setpoints,) if setpoints else () )
            sp_names = ('N',) + sp_names
            sp_labels = ('repetitions',) + sp_labels
            sp_units = ('',) + sp_units
        return shape, setpoints, sp_names, sp_labels, sp_units


    def add_derived_param(self, name, func, label=None, unit='mV',
                          reduce_time=False, reduce_triggers=False,
                          reduce_repetitions=False,
                          setpoints=None, setpoint_units=None,
                          setpoint_labels=None, setpoint_names=None):
        '''
        Create a parameter that is derived from a trace (such as an
        average). Input of the function is the array of channels that
        would be returned from get_raw() without derived parameters.

        Args:
            name (str): name of the parameter
            func (Callable[[np.ndarray], np.ndarray]): function
                calculating derived parameter
            label (Optional[str]): label for the parameter
            unit (str): unit for the parameter
            reduce_time (bool): if True `func` reduce the time dimension
            reduce_triggers (bool): if True `func` reduce the trigger dimension
            reduce_repetitions (bool): if True `func` reduce the repetitions dimension
            setpoints (Optional[np.ndarray]): setpoints
            setpoint_unitss (Optional[np.ndarray]): setpoint units
            setpoint_labels (Optional[np.ndarray]): setpoint labels
            setpoint_names (Optional[np.ndarray]): setpoint names
        '''
        if label is None:
            label = name

        # check the shape returned by the derived parameter
        dummy_ar = np.zeros((len(self.channels),)+self.shapes[0])
        dp_shape = np.shape(func(dummy_ar))

        self.derived_params.append(func)
        self.names.append(name)
        self.shapes = self.shapes + (dp_shape,)
        self.units.append(unit)
        self.labels.append(label)

        if setpoints is None:
            add_time = not self.average_time and not reduce_time
            add_triggers = self.n_trigger and not reduce_triggers
            add_repetitions = (self.n_rep
                               and not self.average_repetitions
                               and not reduce_repetitions)
            shape, setpoints, sp_names, sp_labels, sp_units = \
                self._shape_and_setpoints(add_time, add_triggers, add_repetitions)

            if shape != dp_shape:
                raise Exception(f"Shapes don't match. "
                                f"func returns {dp_shape}, expected {shape}")
                self.setpoints = self.setpoints + (setpoints,)
                self.setpoint_labels = self.setpoint_labels + (sp_labels,)
                self.setpoint_names = self.setpoint_names + (sp_names,)
                self.setpoint_units = self.setpoint_units + (sp_units,)
        else:
            if setpoint_labels and setpoint_names and setpoint_units:
                self.setpoints = self.setpoints + (setpoints,)
                self.setpoint_labels = self.setpoint_labels + (setpoint_labels,)
                self.setpoint_names = self.setpoint_names + (setpoint_names,)
                self.setpoint_units = self.setpoint_units + (setpoint_units,)
            else:
                raise Exception('Please also supply setpoint names/units/labels')


    def get_raw(self):
        if self.start_func:
            self.start_func()

        m4i_seg_size = self.digitizer.segment_size()
        memsize = self.digitizer.data_memory_size()
        pretrigger = self.digitizer.pretrigger_memory_size()
        n_seg = memsize / m4i_seg_size

        if n_seg != self.n_seg:
            raise Exception(f'n_seg mismatch: {n_seg} != {self.n_seg}')

        data_raw = self.digitizer.get_data()
#        print(f'data: {len(data_raw)} {memsize}, seg:{m4i_seg_size}, pre:{pretrigger}, n_seg:{n_seg}')
        # reshape and remove pretrigger
        data = np.reshape(data_raw, self.acq_shape)
        data = data[...,pretrigger:pretrigger+self.seg_size]

        # average
        res_volt = data

        if self.average_time:
            time_axis = res_volt.ndim - 1
            res_volt = np.mean(res_volt, axis=time_axis)
        if self.average_repetitions:
            res_volt = np.mean(res_volt, axis=1)

        derived_params = [dp(res_volt) for dp in self.derived_params]
#        print(derived_params)
        return list(res_volt)+derived_params


def ifNone(x, value):
    return x if x is not None else value

