#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/shared/hpe3631a_gpib.py

Class to control Aiglent E3631A via GPIB

+6V output: VTHSET

+25V output: Test setup VDD @ +3.5V, ~219mA nominal current draw under default chip configuration
'''

import time

class hpe3631a_gpib():
    # Inputs:
    # prologix GPIB instantiation
    # name: name of instrument
    # addr: GPIB address
    def __init__(self, gpib, name, addr):
        self.gpib = gpib
        self.name = name
        # Initialize instrument
        self.gpib.addInstr(self.name, addr)
        # Flush buffers
        self.gpib.query(self.name, "*IDN?", wait=0.4)  
        self.gpib.resetBuffers()
        # Initialize outputs
        self.gpib.write(self.name, "OUTP:STAT ON", wait=0.4)    # Need a delay before the next write, otherwise instrument will crash   
        self.gpib.write(self.name, "APPL P6V, 0.6, 0.1", wait=0.4)
        self.gpib.write(self.name, "APPLy P25V, 3.8, 0.5", wait=0.4)
        #print(self.gpib.query(self.name, "APPL? P25V", wait=0.4))
        #print(self.gpib.query(self.name, "APPL? P6V", wait=0.4))
        self.gpib.resetBuffers()

    # Set P6V output
    def setVTH(self, vset):
        #print("APPL P6V,{:0.3f},1.0".format(vset))
        self.gpib.write(self.name, "APPL P6V,{:0.3f},0.1".format(vset), wait=0.4)
    
    # Measure current from +25V output (in amps)
    def measVDDCurr(self):
        return float(self.gpib.query(self.name, "MEAS:CURR? P25V", wait=0.4))

    # Set instrument front display to P6V channel
    def dispVTH(self):
        self.gpib.write(self.name, "INST:SEL P6V", wait=0.4)
    
    # Query ID
    def IDN(self):
        self.gpib.resetBuffers()
        meas = self.gpib.query(self.name, "*IDN?", wait=0.4)
        self.gpib.resetBuffers()
        return meas






if __name__ == "__main__":
    import prologixUSBGPIB
    gpib = prologixUSBGPIB.prologixUSBGPIB()
    instr = hpe3631a_gpib(gpib, "hpe3631a", 10)
    #instr.setVTH(0.100)
    print(instr.IDN())
    print(str(instr.measVDDCurr()))





