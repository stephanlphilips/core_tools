import core_tools.drivers.harware as hw

def boundaries():
    gate_boundaries = dict({})
    # loose boundaries for tuning. Should not damage the sample.
    for i in [1, 2,]:
        for c in ['B1', 'B2', ]:
            gate_boundaries['SD%d_%s' % (i, c)] = (-1000, 1500)
        gate_boundaries['SD%d_P' % (i)] = (0, 1500)

    gate_boundaries['B0'] = (-1000, 1200)
    for i in [1, 2, 3, 4 ]:
        gate_boundaries['P%d' % (i)] = (0, 1500)
        gate_boundaries['B%d' % (i)] = (-1000, 1500)

    return gate_boundaries

class hardware(hw.harware_parent):

    def __init__(self, name):
        super().__init__(name, "C:/XLD_code/development_code/sample_specific/station/sample_settings")
        
        self.dac_gate_map = {
            # spi 1
            'B0': (0, 1), 'P1': (0, 2), 
            'B1': (0, 3), 'P2': (0, 4),
            'B2': (0, 5), 'P3': (0, 6), 
            'B3': (0, 7), 'P4': (0, 8), 
            'B4': (0, 9),


        }

        self.boundaries = boundaries()

        virtual_gate_set_1 =  hw.virtual_gate('general',["B0", "P1", "B1", "P2", "B2", "P3", "B3", "P4", "B4" ])
        self.virtual_gates.append(virtual_gate_set_1)
        