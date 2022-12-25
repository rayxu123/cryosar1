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
    # Input: string of bits to write, MSB first
    # Output: string of bits read out.  Output is same length as what was written
    def query(self, inStr):
        if not self.noConnect:
            # Format inStr to the nearest byte alignment
            inLen = len(inStr)
            byteLen = self.RoundUp8(inLen)
            # It appears that the pyftdi module outputs LSB first.  Reverse it before zero extension
            bitsWr = BitArray(bin=inStr).reverse()
            bitsWr = BitArray(uint=bitsWr.uint,length=byteLen)
            bitsWr.reverse()
            dropLen = int(byteLen - inLen)
            # SPI transaction
            bitsRead = self.spi.exchange(out=bitsWr.bytes, readlen=int(byteLen/8), start=True, stop=True, duplex=True, droptail=dropLen)
            # Format read data to a binary string and match the length of inStr
            bitsRead = BitArray(bytes=bitsRead)
            # It appears that the pyftdi module outputs LSB first.  Reverse it after dropping zeros
            bitsRead = bitsRead.bin[:-dropLen]
            bitsRead = bitsRead.reverse()
            return bitsRead.bin
        else:
            return inStr


