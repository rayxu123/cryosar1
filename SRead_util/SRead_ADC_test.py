#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead_util/SRead_ADC_test.py

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
    FIFO_DEPTH = 32768
    SER_RATE = 20000000    # Serialization speed, in MHz
    SER_WIDTH = 8               # Number of bits serialized in one sampling period
    WAIT_FOR_DATA = (FIFO_DEPTH*1.2)/(SER_RATE/SER_WIDTH)  # Expression to wait for the FIFO to fill + 20% margin
    #### End Define constants ####

    # Initialize FPGA
    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    xem.ConfigureFPGA('cryosar1_FPGARTL.bit')
    
    # Initialize test vectors
    odac_list = ["00000000", "00010000", "1110000", "10000000", "10010000", "11101111", "11111111"]
    df = pd.DataFrame(columns=['ODAC Code','CMP_P Mean', 'CMP_P Stddev', 'CMP_N Mean', 'CMP_N Stddev'])
    for odac in odac_list:
        # Set BSEL = 0 (CMP_N)
        # Load configuration for chip
        try:
            subprocess.run(["./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+odac,
                "-o", "B_SEL,0",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
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
            dataw.append(np.dot(i, DEF_WEIGHTS))
            valid.append(np.dot(i, MASK_VALID))
        # Make sure all samples valid   
        program_ends = time.time()   
        if not all(valid):
            sys.exit("Encountered at least one non-valid sample, at BSEL=0 and ODAC="+odac)
        # Obtain statistics
        cmpn_mean = np.mean(dataw)
        cmpn_stddev = np.std(dataw)
        # Plot histogram
        fig, axs = plt.subplots(1,1,tight_layout=True)
        axs.hist(dataw, bins=len(np.unique(dataw)), edgecolor = "black")
        axs.title.set_text("CMP_N Code, ODAC="+odac)
        

        # Set BSEL = 1 (CMP_P)
        # Load configuration for chip
        try:
            subprocess.run(["./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+odac,
                "-o", "B_SEL,1",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
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
            dataw.append(np.dot(i, DEF_WEIGHTS))
            valid.append(np.dot(i, MASK_VALID))
        # Make sure all samples valid   
        program_ends = time.time()   
        if not all(valid):
            sys.exit("Encountered at least one non-valid sample, at BSEL=0 and ODAC="+odac)
        # Obtain statistics
        cmpp_mean = np.mean(dataw)
        cmpp_stddev = np.std(dataw)
        # Plot histogram
        fig, axs = plt.subplots(1,1,tight_layout=True)
        axs.hist(dataw, bins=len(np.unique(dataw)), edgecolor = "black")
        axs.title.set_text("CMP_P Code, ODAC="+odac)

        # Add to pandas dataframe
        odac = BitArray(bin=odac).uint  # Convert to integer
        df.loc[len(df.index)] = [odac, cmpp_mean, cmpp_stddev, cmpn_mean, cmpn_stddev]
    
       
    print(tabulate.tabulate(df, headers='keys', tablefmt='psql', showindex=False, floatfmt=".3f"))
    plt.show() 




    




    
    
