from lmfit import Parameters, minimize
from lmfit.printfuncs import report_fit



def residual(pars, x, data=None):
    argu = (x * pars['decay'])**2
    shift = pars['shift']
    if abs(shift) > pi/2:
        shift = shift - sign(shift)*pi
    model = pars['amp'] * sin(shift + x/pars['period']) * exp(-argu)
    if data is None:
        return model
    return model - data

fit_params = Parameters()
fit_params.add('Tc', value=0.3, max=10, min=0.0)
fit_params.add('gamma', value=1)


out = minimize(residual, fit_params, args=(x,), kws={'data': data})
fit = residual(out.params, x)