from core_tools.sweeps.progressbar import progress_bar
from core_tools.data.measurement import AbortMeasurement

def run_wrapper(run_function):
    def run(self, *args, **kwargs):
        silent = getattr(self, 'silent', False)
        self.n = progress_bar(self.n_tot) if not silent else 0
        try:
            returns = run_function(self, *args, **kwargs)
        except AbortMeasurement:
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
        return x
