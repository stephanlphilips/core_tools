import core_tools as ct
import qcodes as qc
from qcodes import ManualParameter, Parameter

ct.configure('./setup_config/ct_config_measurement.yaml')

ct.launch_databrowser()

station = qc.Station()

# Scan.verbose = True

# %%

i1 = ManualParameter('i1', initial_value=0)
i2 = ManualParameter('i2', initial_value=0)
v1 = ManualParameter('v1', initial_value=0)
v2 = ManualParameter('v2', initial_value=0)
v3 = ManualParameter('v3', initial_value=0)


def get_current():
    return -0.001 * (v1() + v2() + v3())

meas_param = Parameter('I', unit='uA', get_cmd=get_current)


from core_tools.sweeps.scans import Scan, sweep, Function, Break, Section
from qcodes import DelegateParameter

def param_alias(param, name):
    return DelegateParameter(name, param, label=name)


def break_at(param_name, Imax, resume_at):
    def check_break(last_values):
        I = last_values[param_name]
        if I > Imax:
            raise Break(f"I: {I}", resume_at_label=resume_at)
    return Function(check_break, add_last_values=True)

def reset_voltage():
    v1(0.0)

ds1 = Scan(
        sweep(i1, range(1, 3)),
        sweep(i2, range(1, 4), label="i2"),
        Section(
            sweep(v1, -500, -1100, 21, delay=0.001, value_after='start'),
            param_alias(meas_param, "I1"),
            break_at("I1", Imax=1.7, resume_at="v2"),
        ),
        Section(
            sweep(v2, -500, -1100, 21, value_after='start', delay=0.01, label="v2"),
            param_alias(meas_param, "I2"),
            break_at("I2", Imax=1.3, resume_at="i2"),
        ),
        Section(
            sweep(v3, -500, -1100, 21, value_after='start', delay=0.01, label="v3"),
            param_alias(meas_param, "I3"),
        ),
        Function(reset_voltage, label="reset_voltage"),
        name='Scan with sections and break',
        reset_param=True).run()


ds1
