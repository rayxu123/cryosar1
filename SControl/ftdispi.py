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
 
 See: https://eblot.github.io/pyftdi/installation.html#windows
 Windows must use libusb-win32 stack
'''


from pyftdi.ftdi import Ftdi
from pyftdi import spi

import sys
#sys.path.insert(0, './pyftdi-cs_act_hi/pyftdi/')
#import ftdi
#import spi
import time
import subprocess

from bitstring import BitArray

class ftdispi:
    def __init__(self, addr=None, noConnect=False, csacthi=False, mode=0):
        self.noConnect = noConnect
        if addr is None:
            self.list()
            raise ValueError("Must connect to a FTDI device.")
        else:
            if not self.noConnect:
                self.ftdi = spi.SpiController()
                if csacthi:
                     self.ftdi.configure(addr, cs_act_hi=(0, 0))
                else:
                    self.ftdi.configure(addr)
                # Get a SPI port to a SPI slave w/ /CS on A*BUS3 and SPI mode 0 @ 1MHz
                self.spi = self.ftdi.get_port(cs=0, freq=1E6, mode=mode)
                self.spi.flush()
                # Get BDBUS7 and set to logic high output
                self.gpio = self.ftdi.get_gpio()
                self.gpio.set_direction(0x80, 0x80)
                self.gpio.write(0x80)


    def list(self):
        print(" ==== FTDI DRIVER ==== ")
        Ftdi.show_devices()
        print(" ==== LIBUSB STACK (Win32) ==== ")
        subprocess.run("pnputil /enum-devices /ids /class \"libusb-win32 devices\"")
        # TODO: implement conditional for linux OS
        
    def close(self):
        if not self.noConnect:
            self.ftdi.ftdi.close()

    # Set GPIOL0 (BDBUS4 or ADBUS4).  For AD5313 this is connected to !LDAC input.  Otherwise, use at your discretion.
    def setgpio(self, state):
        if not self.noConnect:
            if state > 0:
                self.gpio.write(0x80)
            else:
                self.gpio.write(0x00)

    # Returns next greater multiple of 8
    def RoundUp8(self, x):
        return ((x + 7) & (-8))

    # Perform full-duplex write and read
    # Length of inStr must be in multiples of 8 bits!  (Byte level boundaries)  droptail capability not yet implemented.
    # Input: string of bits to write, MSB first
    # Output: string of bits read out.  Output is same length as what was written
    def query(self, inStr, startCS=True, stopCS=True):
        if (len(inStr) % 8 != 0):
            raise ValueError("Input bitstring must be integer bytes long.")
        if not self.noConnect:
            # It appears that the pyftdi module outputs LSB first.  Reverse it.
            # TODO: Check FTDSPI endianness
            bitsWr = BitArray(bin=inStr)
            #bitsWr.reverse()
            # SPI transaction
            bitsRead = self.spi.exchange(out=bitsWr.bytes, readlen=int(bitsWr.len/8), start=startCS, stop=stopCS, duplex=True, droptail=0)
            # Format read data to a binary string
            bitsRead = BitArray(bytes=bitsRead)
            # It appears that the pyftdi module outputs LSB first.  Reverse it 
            #bitsRead.reverse()
            return bitsRead.bin
        else:
            return inStr
            
    # Programs one or more daisy chained AD5313 (or similar) DAC's using low-level commands
    # !LDAC of all daisy chained DAC's connected to *BUS4 GPIO.
    # !SYNC of all daisy chained DAC's connected to !CS.
    def progAD5313half(self, bits):
        if (len(bits) % 8 != 0):
            raise ValueError("Input bitstring must be integer bytes long.")
        if not self.noConnect:
            # Make sure !LDAC is high 
            self.setgpio(1)
            # Program and keep !CS active 
            #print("Program: "+bits)
            returnBits = self.query(bits, stopCS=False)
            #print("Return:  "+returnBits)
            # Pulse !LDAC low
            self.setgpio(0)
            time.sleep(0.01)
            self.setgpio(1)
            time.sleep(0.01)
            # Deactivate !CS
            self.spi.force_select(level=True)
            return returnBits


