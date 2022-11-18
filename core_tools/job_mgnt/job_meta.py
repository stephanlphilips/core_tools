from core_tools.sweeps.progressbar import progress_bar
from core_tools.sweeps.sweep_utility import KILL_EXP

def run_wrapper(run_function):
    def run(self, *args, **kwargs):
        silent = getattr(self, 'silent', False)
        self.n = progress_bar(self.n_tot) if not silent else 0
        try:
            returns = run_function(self, *args, **kwargs)
        except KILL_EXP:
            print('kill signal for the current experiment received.')
            returns = None
        finally:
            if not silent:
                self.n.close()
            self.n = 0

        return returns
    return run

class job_meta(type):
    def __new__(cls,name, bases, dct):
        if 'run' not in dct:
            raise ValueError('Please define a run function in your job class.')

        x = super().__new__(cls, name, bases, dct)
        x.run = run_wrapper(dct['run'])

        x.n_tot = 0
        x.n = 0
        x.KILL = False
        return x

if __name__ == '__main__':
    import time

    class pulse_lib_sweep_virt(metaclass=job_meta):
        def __init__(self, n_steps):
            self.n_tot = n_steps

        def run(self):
            for i in range(self.n_tot):
                time.sleep(0.01)
                self.n += 1

    a = pulse_lib_sweep_virt(5)
    a.run()
    a.KILL = True

    b = pulse_lib_sweep_virt(5)
    b.run()
    print(b.KILL)