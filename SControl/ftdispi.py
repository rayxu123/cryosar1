#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SControl/ftdispi.py

Interfaces with a FTDI device capable of MPSSE/SPI communications

Requires the packages:
 - libusb (via system package manager)
 - pyftdi (see manual for installation and setup instructions)
'''

from pyftdi.ftdi import Ftdi
from pyftdi import spi
from bitstring import BitArray

class ftdispi:
    def __init__(self, addr=None, noConnect=False):
        self.noConnect = noConnect
        if addr is None:
            self.list()
            raise ValueError("Must connect to a FTDI device.")
        else:
            if not self.noConnect:
                self.ftdi = spi.SpiController()
                self.ftdi.configure(addr)
                # Get a SPI port to a SPI slave w/ /CS on A*BUS3 and SPI mode 0 @ 1MHz
                self.spi = self.ftdi.get_port(cs=0, freq=1E6, mode=0)
                self.spi.flush()


    def list(self):
        Ftdi.show_devices()

    # Returns next greater multiple of 8
    def RoundUp8(self, x):
        return ((x + 7) & (-8))

    # Perform full-duplex write and read
    # Length of inStr must be in multiples of 8 bits!  (Byte level boundaries)  droptail capability not yet implemented.
    # Input: string of bits to write, MSB first
    # Output: string of bits read out.  Output is same length as what was written
    def query(self, inStr):
        if (len(inStr) % 8 != 0):
            raise ValueError("Input bitstring must be integer bytes long.")
        if not self.noConnect:
            # It appears that the pyftdi module outputs LSB first.  Reverse it.
            # TODO: Check FTDSPI endianness
            bitsWr = BitArray(bin=inStr)
            #bitsWr.reverse()
            # SPI transaction
            bitsRead = self.spi.exchange(out=bitsWr.bytes, readlen=int(bitsWr.len/8), start=True, stop=True, duplex=True, droptail=0)
            # Format read data to a binary string
            bitsRead = BitArray(bytes=bitsRead)
            # It appears that the pyftdi module outputs LSB first.  Reverse it 
            #bitsRead.reverse()
            return bitsRead.bin
        else:
            return inStr


