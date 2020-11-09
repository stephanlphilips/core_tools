import numpy as np
a= 1.23*1e-10
s = 1e-1*1e-10
for i in range(100):
    a = a + float(s*1.)

    precision = int(-np.log10(s) + 5)
    if precision > 0:
        a = np.round(a, precision)

    print(a)