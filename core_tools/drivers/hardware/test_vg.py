# -*- coding: utf-8 -*-
"""
Created on Tue May 18 12:47:59 2021

@author: TUD278088
"""

tg = station.gates.vP7

cvs = [p() for p in station.gates.parameters.values()]
tg.increment(1)
evs = [p() for p in station.gates.parameters.values()]
tg.increment(-1)

for (name, cv, ev) in zip(station.gates.parameters.keys(), cvs, evs):
    if cv != ev:
        print(f'{name} changed by {ev-cv:.2f} mV')