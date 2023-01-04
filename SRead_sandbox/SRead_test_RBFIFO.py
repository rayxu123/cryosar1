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
    xem.ConfigureFPGA('RBFIFO.bit')


    # Reset, mode 1
    xem.SetWireInValue(0x00, 0x00000003)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(0x00, 0x00000002)
    xem.UpdateWireIns()



    
    
    for value in range(32768):
        addr = BitArray(uint=value, length=32)
        data = xem.ReadRegister(addr.uint)
        data = BitArray(uint=data, length=32)
        print(str(addr.hex)+": "+str(data.hex))

    addr = BitArray(uint=65535, length=32)
    data = xem.ReadRegister(addr.uint)
    data = BitArray(uint=data, length=32)
    print(str(addr.hex)+": "+str(data.hex))
    addr = BitArray(uint=65535, length=32)
    data = xem.ReadRegister(addr.uint)
    data = BitArray(uint=data, length=32)
    print(str(addr.hex)+": "+str(data.hex))







    
    
