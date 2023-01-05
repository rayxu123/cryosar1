#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead/SRead_FIFO_test.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''




import ok
import time
import numpy as np
import subprocess
import timeit
from bitstring import BitArray



if __name__ == "__main__":
    #### Begin Define constants ####
    WEIGHTS = [32768, 1940, 1110, 635, 365, 210, 120, 70, 40, 24, 14, 8, 5, 3, 2, 1];   # 12bRC arrangement
    ADDR_WIRE = 0x00
    DATA_FPGACOUNTER_RESET = 0x00000005
    DATA_FPGACOUNTER_START = 0x00000004
    DATA_CHIP_RESET = 0x00000003
    DATA_CHIP_START = 0x00000002
    DATA_FRAME_RESET = 0x00000001
    DATA_FRAME_START = 0x00000000
    FIFO_DEPTH = 32768
    SER_RATE = 20000000    # Serialization speed, in MHz
    SER_WIDTH = 8               # Number of bits serialized in one sampling period
    WAIT_FOR_DATA = (FIFO_DEPTH*1.2)/(SER_RATE/SER_WIDTH)  # Expression to wait for the FIFO to fill + 20% margin
    #### End Define constants ####
    
    # Initialize FPGA
    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    xem.ConfigureFPGA('cryosar1_FPGARTL.bit')

    # Load configuration for chip, serializer test mode
    subprocess.run(["./../SControl/SControl.py", "-b", "-f", "./../SControl/config/CryoSAR1_sertestmode.cfg"])

    #### TEST 1: Take data on FRAME ####
    print("==== TEST 1: FRAME ====")
    xem.SetWireInValue(ADDR_WIRE, DATA_FRAME_RESET)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(ADDR_WIRE, DATA_FRAME_START)
    xem.UpdateWireIns()
    time.sleep(WAIT_FOR_DATA)
    # Transfer data
    data = ok.okTRegisterEntries(FIFO_DEPTH)
    benchmark = timeit.timeit("xem.ReadRegisters(data)", globals=locals(), number=1)
    data = np.array([i.data for i in data]) # numpy array of radix-2 32-bit uint
    data_unique = np.unique(data)
    print("Expected: hex 9c")
    for i in data_unique:
        print("Saw unique value: hex "+BitArray(uint=i, length=32).hex)
    print("Transferred "+str(FIFO_DEPTH)+" double-words in "+str(benchmark)+" seconds: "+str(FIFO_DEPTH/benchmark)+" double-words/second.")

    #### TEST 2: Take data in serializer test mode ####
    print("==== TEST 2: SERIALIZER TEST MODE ====")
    xem.SetWireInValue(ADDR_WIRE, DATA_CHIP_RESET)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(ADDR_WIRE, DATA_CHIP_START)
    xem.UpdateWireIns()
    time.sleep(WAIT_FOR_DATA)
    # Transfer data
    data = ok.okTRegisterEntries(FIFO_DEPTH)
    benchmark = timeit.timeit("xem.ReadRegisters(data)", globals=locals(), number=1)
    data = np.array([i.data for i in data]) # numpy array of radix-2 32-bit uint
    data_unique = np.unique(data)
    print("Expected: hex 9894")
    for i in data_unique:
        print("Saw unique value: hex "+BitArray(uint=i, length=32).hex)
    print("Transferred "+str(FIFO_DEPTH)+" double-words in "+str(benchmark)+" seconds: "+str(FIFO_DEPTH/benchmark)+" double-words/second.")

    #### TEST 3: FIFO depth test ####
    print("==== TEST 3: FIFO depth test ====")
    print("The FIFO is designed to be 32768 double-words deep but is actually 32771 according to the IP generator.")
    print("To test this, the firmware 16-bit internal test counter is utilized.  It runs at the serialization clock rate and wraps around.")
    print("For a serialization factor of 8, the discrete differences read out should only be 8 and -65528 for the wraparound.")
    print("Any other values would mean the FIFO was read out beyond empty and samples are no longer in order.")
    for add in range(6):
        xem.SetWireInValue(ADDR_WIRE, DATA_FPGACOUNTER_RESET)
        xem.UpdateWireIns()
        time.sleep(0.1)
        xem.SetWireInValue(ADDR_WIRE, DATA_FPGACOUNTER_START)
        xem.UpdateWireIns()
        time.sleep(WAIT_FOR_DATA)
        # Transfer data
        print("Read "+str(FIFO_DEPTH+add)+" double-words")
        data = ok.okTRegisterEntries(FIFO_DEPTH+add)
        benchmark = timeit.timeit("xem.ReadRegisters(data)", globals=locals(), number=1)
        data = np.array([i.data for i in data]) # numpy array of radix-2 32-bit uint
        data_diff = np.diff(data)        
        data_unique = np.unique(data_diff)
        for i in data_unique:
            print("Saw unique value difference: decimal "+str(i))
        print("Transferred "+str(FIFO_DEPTH+add)+" double-words in "+str(benchmark)+" seconds: "+str((FIFO_DEPTH+add)/benchmark)+" double-words/second.")

    


   







    
    
