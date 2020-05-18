import numpy as np

data = np.zeros([5,20])

i = 0
d = np.linspace(1,20, 20)

y = np.zeros(20)

for i in range(5):
    data = np.roll(data,-1,0)
    data[-1] = d +i

    y = np.sum(data, 0)/len(data)


print(data)
print(y)

class test(object):
    """docstring for test"""
    def __init__(self):
        self._differentiate = "a"

    @property
    def differentiate(self):
        return self._differentiate

    @differentiate.setter
    def differentiate(self, value):
        self._differentiate = value
        self.update_buffers = True

    def diff(self):
        print(self.differentiate)
    
t = test()
print(t.differentiate)
t.differentiate = True
print(t.differentiate)
t.diff()