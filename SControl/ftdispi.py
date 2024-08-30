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
from pyftdi import spi, gpio

import sys
#sys.path.insert(0, './pyftdi-cs_act_hi/pyftdi/')
#import ftdi
#import spi, gpio
import time
import subprocess

from bitstring import BitArray

# Some constants for ADC GPIO on the hacked-up second FTDI FT2232 module
SPISEL10_MASK = 0x03 # GPIO AD1,0
SPISEL1_MASK = 0x02 # GPIO AD1
SPISEL0_MASK = 0x01 # GPIO AD0

## HACK: 
# SPIMUX is a bool to determine if this class controls the DUT or the AD5313/AD7888 combo.
# A secibd FTDI module is needed for the AD5313/AD7888 combo because a SPI MUX in hardware needs to be controlled.

class ftdispi:
    def __init__(self, addr=None, noConnect=False, csacthi=False, mode=0, SPIMUX=False):
        self.noConnect = noConnect
        self.SPIMUX = SPIMUX
        if addr is None:
            self.list()
            raise ValueError("Must connect to a FTDI device.")
        else:
            if not self.noConnect:
                if SPIMUX is True:
                    self.ftdi = spi.SpiController(cs_count=4)
                else:
                    self.ftdi = spi.SpiController()
                '''
                if csacthi:
                     self.ftdi.configure(addr, cs_act_hi=(0, 0))
                else:
                    self.ftdi.configure(addr)
                '''
                self.ftdi.configure(addr)
                    
                ## HACK: Set SPI MUX using a second FTDI FT2232 device on bus A.
                if SPIMUX is True:
                    self.mux = gpio.GpioAsyncController()
                    self.mux.configure('ftdi://ftdi:2232:FT74A2JW/1')
                    
                if SPIMUX is True:
                    # Get 3 SPI ports to a SPI slave w/ /CS on A*BUS3,4,5,6 and SPI mode 0 @ 1MHz
                    self.spi = self.ftdi.get_port(cs=0, freq=1E6, mode=mode)
                    self.spi.flush()
                    self.adc1 = self.ftdi.get_port(cs=1, freq=1E6, mode=mode)
                    self.adc1.flush()
                    self.adc2 = self.ftdi.get_port(cs=2, freq=1E6, mode=mode)
                    self.adc2.flush()
                    self.adc3 = self.ftdi.get_port(cs=3, freq=1E6, mode=mode)
                    self.adc3.flush()
                else:
                    # Get a SPI port to a SPI slave w/ /CS on A*BUS3 and SPI mode 0 @ 1MHz
                    self.spi = self.ftdi.get_port(cs=0, freq=1E6, mode=mode)
                    self.spi.flush()
                    
                # Get BDBUS7 and set to logic high output
                self.gpio = self.ftdi.get_gpio()
                self.gpio.set_direction(0x80, 0x80)
                self.gpio.write(0x80)
                
                # Default setting for SPIMUX. The SPI MUX and the two outputs have no effect on the DAC.
                if SPIMUX is True:
                    self.mux.set_direction(0xFF & SPISEL10_MASK, 0xFF & SPISEL10_MASK)
                    self.setSPIMUX(0)
                    


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
                
    # Sets SPI Mux
    # val = 0: ADC2
    # val = 1: ADC3
    # val = 2: DAC
    # val = 3: ADC1
    def setSPIMUX(self, val):
        if self.SPIMUX is True:
            if val == 0:    self.mux.write(0x00 & SPISEL10_MASK)
            elif val == 1:  self.mux.write(0x01 & SPISEL10_MASK)
            elif val == 2:  self.mux.write(0x02 & SPISEL10_MASK)
            elif val == 3:  self.mux.write(0x03 & SPISEL10_MASK)
            else: print("Invalid!")
        else: print("Not supported!")
        time.sleep(0.1) # Let signal settle
    
    # Reads from AD71888
    # Addr is int 0-7 for inputs 1-8
    # Returns unsigned int of the ADC value.  To get volts, multiply by 2.5/4096
    def readAD7188(self, spiObj, addr):
        bitsWr = BitArray(bin='00'+BitArray(uint=addr, length=3).bin+'1'+'00'+'00000000')
        bitsRead = spiObj.exchange(out=bitsWr.bytes, readlen=int(bitsWr.len/8), start=True, stop=True, duplex=True)
        bitsRead = BitArray(bytes=bitsRead)
        return bitsRead.uint


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


