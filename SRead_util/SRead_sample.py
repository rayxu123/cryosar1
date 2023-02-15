#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead_util/SRead_sample.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''




import ok
import time
import numpy as np
import subprocess
import tabulate
import time
import sys
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from bitstring import BitArray



if __name__ == "__main__":
    #### Begin Define constants ####
    MASK_VALID = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];   
    DEF_WEIGHTS = [0, 1940, 1110, 635, 365, 210, 120, 70, 40, 24, 14, 8, 5, 3, 2, 1];   # 12bRC arrangement
    ADDR_WIRE = 0x00
    DATA_FPGACOUNTER_RESET = 0x00000005
    DATA_FPGACOUNTER_START = 0x00000004
    DATA_CHIP_RESET = 0x00000003
    DATA_CHIP_START = 0x00000002
    DATA_FRAME_RESET = 0x00000001
    DATA_FRAME_START = 0x00000000
    #FIFO_DEPTH = 32768
    FIFO_DEPTH = 10
    SER_RATE = 92000000    # Serialization speed, in MHz
    SER_WIDTH = 8               # Number of bits serialized in one sampling period
    WAIT_FOR_DATA = (FIFO_DEPTH*1.2)/(SER_RATE/SER_WIDTH)  # Expression to wait for the FIFO to fill + 20% margin
    #### End Define constants ####

    # Initialize FPGA
    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    xem.ConfigureFPGA('cryosar1_FPGARTL.bit')
    
    
    # Read from FPGA
    xem.SetWireInValue(ADDR_WIRE, DATA_CHIP_RESET)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(ADDR_WIRE, DATA_CHIP_START)
    xem.UpdateWireIns()
    time.sleep(WAIT_FOR_DATA)
    # Transfer data
    data = ok.okTRegisterEntries(FIFO_DEPTH)
    xem.ReadRegisters(data)
    # Parse and bit weigh data
    dataw = []  # Weighted data
    valid = []  # Is sample valid?
    for i in data:
        i = i.data  # Grab data from datastructure.  uint32 format.but only 16 bits are used.
        i = BitArray(uint=i, length=16).bin
        i = [*i]    # split each bit into a list
        i = [eval(j) for j in i]    # re-evaluate, convert char to int in bit list
        print(i)
        dataw.append(np.dot(i, DEF_WEIGHTS))
        valid.append(np.dot(i, MASK_VALID))
    



    




    
    
