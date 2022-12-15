#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead/SRead_pipeoutlvds.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''




import ok
import time
from bitstring import BitArray

if __name__ == "__main__":
    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    #xem.LoadDefaultPLLConfiguration()
    xem.ConfigureFPGA('lvds_v4.bit')

    # Reset
    xem.SetWireInValue(0x00, 0xffffffff)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(0x00, 0x00000000)
    xem.UpdateWireIns()

    # Prepare payload, 32 bit word
    #number = BitArray(hex='00000001')
    #number.byteswap()

    # Write to pipe in
    #buf = bytearray(number.bytes)*4
    #xem.WriteToPipeIn(0x80, buf)
    #buf = BitArray(bytes=buf)
    #buf.byteswap()
    #print(buf.hex)

    # Read from pipe out
    while True:
        buf = bytearray(16)
        xem.ReadFromPipeOut(0xa0, buf)
        buf = BitArray(bytes=buf)
        buf.byteswap()
        buf.invert()
        print(buf.hex)
        time.sleep(0.5)
