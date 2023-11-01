#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/shared/hp33220a_visa.py

Class to control Aiglent 33220A via VISA (like USB)

Why does Keysight libioTraceHelper segfault when pytho exits ??
'''

import time
import pyvisa

class hp33220a_visa():
    # Inputs:
    # addr: VISA resource address
    def __init__(self, addr='USB0::0x0957::0x0407::MY44012701::0::INSTR'):
        # Initialize instrument
        rm = pyvisa.ResourceManager('/opt/keysight/iolibs/libktvisa32.so')  # Point this to Keysight IO Libraries kernel drivers
        self.inst = rm.open_resource(addr)
        # Initialize output
        self.freq = 1e6
        self.ampl = 0.01
        self.inst.write("APPL:SIN 1E6,0.01,0")
        self.inst.write("OUTP OFF")
        
    # Apply sine wave of freq and ampl in units of hertz and vpp accordingly
    def initSine(self, freq, ampl):
        self.freq = float(freq)
        self.ampl = float(ampl)
        #print("APPL:SIN {:f},{:f},0".format(self.freq, self.ampl))
        self.inst.write("APPL:SIN {:f},{:f},0".format(self.freq, self.ampl))

    
    # Set output either on or off
    def setOutput(self, state=False):
        if state:
            self.inst.write("VOLT {:f}".format(self.ampl))
            self.inst.write("OUTP ON")
        else:
            self.inst.write("VOLT 0.01")
            self.inst.write("OUTP OFF")

    # Query ID
    def IDN(self):
        return self.inst.query("*IDN?")






if __name__ == "__main__":
    instr = hp33220a_visa()
    print(instr.IDN())
    instr.initSine(2.000778198e6, 2.25)
    instr.setOutput(False)
    time.sleep(1)
    instr.setOutput(True)





