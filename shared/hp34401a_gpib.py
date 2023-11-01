#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/shared/hp34401a_gpib.py

Class to control Aiglent 34401A via GPIB
'''



class hp34401a_gpib():
    # Inputs:
    # prologix GPIB instantiation
    # name: name of instrument
    # addr: GPIB address
    def __init__(self, gpib, name, addr):
        self.gpib = gpib
        self.name = name
        # Initialize instrument
        self.gpib.addInstr(self.name, addr)
        self.gpib.resetBuffers()
        self.gpib.write(self.name, "*RST", wait=0.2)   
        self.gpib.write(self.name, "*CLS", wait=0.2)
        self.gpib.write(self.name, "STAT:PRES", wait=0.2)
        self.gpib.write(self.name, "SYST:BEEP:STAT OFF", wait=0.2)
        self.gpib.resetBuffers()
        # Flush buffers
        self.gpib.query(self.name, "*IDN?", wait=0.2)
        self.gpib.resetBuffers()
        # Initialize for VDC measurements
        self.gpib.write(self.name, "CONF:VOLT:DC 1.5")
        self.gpib.write(self.name, "TRIG:SOUR BUS")
        self.gpib.query(self.name,"READ?", wait=0.5)    # Fake read to put instrument in a ready state
        self.gpib.resetBuffers()
        
    # Measure DC voltage, in units of volts.  With a range of 1.5V
    def measDCV(self):
        self.gpib.resetBuffers()
        #self.gpib.write(self.name,"TRIG:COUN 1")
        #self.gpib.write(self.name,"TRIG:SOUR IMM")
        return float(self.gpib.query(self.name,"READ?", wait=0.2))
    

    # Query ID
    def IDN(self):
        self.gpib.resetBuffers()
        meas = self.gpib.query(self.name, "*IDN?", wait=0.2)
        self.gpib.resetBuffers()
        return meas






if __name__ == "__main__":
    import prologixUSBGPIB
    gpib = prologixUSBGPIB.prologixUSBGPIB()
    instr = hp34401a_gpib(gpib, "hp34401a", 4)
    #print(instr.IDN())
    print(str(instr.measDCV()))
    print(str(instr.measDCV()))





