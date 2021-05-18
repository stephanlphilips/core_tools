import core_tools.drivers.harware_legacy as hw

class hardware6dot(hw.harware_parent):

    def __init__(self, name):
        super().__init__(name, "./")
        
        self.dac_gate_map = {
            # spi 1
            'B0': (0, 1),  'P1': (0, 2), 
            'B1': (0, 3),  'P2': (0, 4),
            'B2': (0, 5),  'P3': (0, 6), 
            'B3': (0, 7),  'P4': (0, 8), 
            'B4': (0, 9),  'P5': (0, 10),
            'B5': (0, 11), 'P6': (0, 12),
            'B6': (0, 13),
 
            # spi 2
            'A1': (1, 1),
            'A2': (1, 2),
            'A3': (1, 3),
            'A4': (1, 4),
            'A5': (1, 5),



            # Screening gates:
            'S1': (1, 9),
            'S2': (1, 10),
            'S3': (1, 11),
            'S4': (1, 12),
            'S5': (1, 13),
            'S6': (1, 14),

            # spi 3
            'SD1_B1': (2, 1), 'SD1_P': (2, 2), 'SD1_B2': (2, 3),
            'SD2_B1': (2, 4), 'SD2_P': (2, 5), 'SD2_B2': (2, 6),

            'V_src_1': (1, 15),
            'V_src_2': (1, 16)
        }

        self.boundaries

        virtual_gate_set_1 =  hw.virtual_gate('general',["B0", "P1", "B1", "P2", "B2", "P3", "B3", "P4", "B4", "P5", "B5", "P6", "B6", "S6", "SD1_P", "SD2_P"])

        self.virtual_gates.append(virtual_gate_set_1)