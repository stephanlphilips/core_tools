import numpy as np
from matplotlib.colors import hsv_to_rgb

def ccurve(x, sign, f):
    a = x-0.5
    c = 0.25-a**2
    return 0.5 + sign*(a+f*c)

def polar_to_rgb(r, phi, colors='dark'):
    # note: convert to numpy array for boolean filter
    max_r = np.max(r)
    if max_r != 0.0:
        a = (r/np.max(r))
    else:
        a = 0.0
    a[a<0] = 0.0
    if colors == 'light':
        h = (phi / (2*np.pi) + 0.5) % 1
#        s = ccurve(a, 1, -0.5)
        s = a - 0.05 * np.sin(a*np.pi*2)
        v = 1-1*(a/2)**2
    elif colors == 'bright':
        h = (phi / (2*np.pi) + 0.5) % 1
        s = 0.5 + 0.5*ccurve(a, 1, -1.0)
        v = 1
    elif colors == 'neon':
        h = (phi / (2*np.pi) + 0.5) % 1
        s = a
        v = ccurve(a, 1, 0.5)
    elif colors == 'dark':
        h = (phi / (2*np.pi) + 0.0) % 1
        s = 1 - 0.25 * a**2
        v = ccurve(a, 1, 0.2)
    else:
        raise ValueError(f'unknown colors:{colors}')
    hsv = np.zeros(r.shape + (3,))
    hsv[...,0] = h
    hsv[...,1] = s
    hsv[...,2] = v
    return hsv_to_rgb(hsv)


def compress_range(data, upper=99.8, lower=25, subtract_low=False):
    res = data.copy()
    th_upper = np.percentile(data, upper)
    th_lower = np.percentile(data, lower)

    res[data > th_upper] = th_upper
    res[data < th_lower] = th_lower
    if subtract_low:
        res -= th_lower
    return res
