from qcodes.instrument.base import Instrument

import spirack

class SPI_rack(Instrument):
    def __init__(self, name, address, baud_rate='115200', timeout=1):
        super().__init__(name)
        self.spi_rack = spirack.SPI_rack(address, baud=baud_rate, timeout=timeout)
        self.spi_rack.unlock()

    def get_idn(self):
        return dict(vendor='CoreTools',
                    model='SPI_rack',
                    serial='',
                    firmware='')
