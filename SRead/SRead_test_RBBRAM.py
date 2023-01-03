#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead/SRead_test.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''




import ok
import time
from bitstring import BitArray

if __name__ == "__main__":
    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    #xem.LoadDefaultPLLConfiguration()
    xem.ConfigureFPGA('RBBRAM.bit')

    # Mode 0
    xem.SetWireInValue(0x00, 0xffffffff)
    xem.UpdateWireIns()

    for value in range(65536):
        addr = BitArray(uint=value, length=32)
        data = device.ReadRegister(addr.bytes)
        print(str(addr.bytes)+": "+str(data)))







    
    
