#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/shared/hp3458a_gpib.py

Class to control Aiglent 3458A via GPIB
'''



class hp3458a_gpib():
    # Inputs:
    # prologix GPIB instantiation
    # name: name of instrument
    # addr: GPIB address
    def __init__(self, gpib, name, addr):
        self.gpib = gpib
        self.name = name
        # Initialize instrument
        self.gpib.addInstr(self.name, addr)
        self.gpib.write(self.name, "PRESET NORM")   # Preset normal
        self.gpib.write(self.name, "TRIG HOLD")     # Pause data taking otherwise gpib input buffer will be filled
        self.gpib.resetBuffers()
        # Query twice to clear out crap in the hardware buffer
        self.gpibid = self.gpib.query(self.name,"ID?")
        self.gpibid = self.gpib.query(self.name,"ID?")
        self.gpib.query(self.name, "TRIG SGL")
        self.gpib.resetBuffers()

    # Measure temperature measurement of RTD100
    def measTemperature(self, twoWire=False):
        self.gpib.resetBuffers()
        if twoWire:
            self.gpib.write(self.name, "OHM 200")
        else:
            self.gpib.write(self.name, "OHMF 200")
        self.gpib.write(self.name, "MATH CRTD85")
        meas = float(self.gpib.query(self.name, "TRIG SGL"))
        self.gpib.resetBuffers()
        return meas

    # Measure VDC with a range of 100mV
    def measVDC100mV(self):
        self.gpib.resetBuffers()
        self.gpib.write(self.name, "DCV 0.1")
        meas = float(self.gpib.query(self.name, "TRIG SGL"))
        self.gpib.resetBuffers()
        return meas

    # Measure resistance
    def measResistance(self, twoWire=False):
        self.gpib.resetBuffers()
        if twoWire:
            self.gpib.write(self.name, "OHM 200")
        else:
            self.gpib.write(self.name, "OHMF 200")
        self.gpib.write(self.name, "MATH OFF")
        meas = float(self.gpib.query(self.name, "TRIG SGL"))
        self.gpib.resetBuffers()
        return meas

    # Query ID
    def IDN(self):
        return self.gpib.query(self.name,"ID?")






if __name__ == "__main__":
    import prologixUSBGPIB
    gpib = prologixUSBGPIB.prologixUSBGPIB()
    instr = hp3458a_gpib(gpib, "hp3458a", 22)
    print(instr.IDN())
    print(str(instr.measVDC100mV()))
    #print(str(instr.measResistance()))
    #print(str(instr.measTemperature()))




