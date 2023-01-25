#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/fpga.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''


import ok
import time
import sys
import os
import numpy as np
from bitstring import BitArray
from multiprocessing import Pool
from itertools import repeat

class fpga:
    ## Constants related to FPGA firmware/configuration
    FPGA_BITFILE = 'cryosar1_FPGARTL.bit'
    ## Constants related to data taking
    ADDR_WIRE = 0x00
    DATA_FPGACOUNTER_RESET = 0x00000005
    DATA_FPGACOUNTER_START = 0x00000004
    DATA_CHIP_RESET = 0x00000003
    DATA_CHIP_START = 0x00000002
    DATA_FRAME_RESET = 0x00000001
    DATA_FRAME_START = 0x00000000
    FIFO_MAXDEPTH = 32768
    SER_RATE = 200000000    # Serialization speed, in Hz.  Also main ADC clock speed.
    SER_WIDTH = 8               # Number of bits serialized in one sampling period
    ## Constants related to data parsing
    MASK_VALID = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]   
    DEF_WEIGHTS = [0, 1940, 1110, 635, 365, 210, 120, 70, 40, 24, 14, 8, 5, 3, 2, 1]   # 12bRC arrangement
    

    def __init__(self, noConnect=False):
        self.noConnect = noConnect
        # Initialize multi-processing for parsing data
        self.pool = Pool(os.cpu_count())                         # Create a multiprocessing Pool
        # Initialize FPGA
        self.xem = ok.FrontPanel()
        if not self.noConnect:
            self.xem.OpenBySerial("")
            self.xem.ConfigureFPGA(self.FPGA_BITFILE)

    # Take data
    # Inputs: source ("data", "frame", "fpgacounter"), numSamples (1...32768), weighting (a list of 16 numbers from MSB to LSB), bipolar weighting (boolean)
    # Outputs: data (list of numbers versus time), all valid (bool)
    #
    # Case: source = data
    # weights from 'weighting' are applied
    #
    # Case: source = frame
    # radix-2 weights are applied
    # output 'all valid' is always True 
    #
    # Case: source = fpgacounter
    # radix-2 weights are applied
    # output 'all valid' is always True
    #
    # If option noConnect: data returns is a list of zeros of length numSamples and 'all valid' is always True
    #
    # If bipolar weighting is true, then bits 0,1 is converted to -1,+1 when computing the dot product of bits and bit weights.  This option only applies to source = data.  
    #
    # Multiplicity: number of times to loop the fpga data taking (to get more than 32k samples but discontinuous)
    def takeData(self, source="data", numSamples=FIFO_MAXDEPTH, weighting=DEF_WEIGHTS, bipolar=False, printBinary=False, mult=1):
        # Sanity check
        if (numSamples > self.FIFO_MAXDEPTH) or (numSamples < 1):
            raise ValueError("Number of samples must be between 1 and 32768 inclusive.")
        if not isinstance(numSamples, int):
            raise ValueError("Number of samples must be integer.")

        if not self.noConnect:        
            dataw_list = []
            valid_list = []
            for mult_loop in range(mult):
                # Set FPGA to fill the FIFO
                if (source == "data"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_CHIP_RESET)
                elif (source == "frame"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_FRAME_RESET)
                elif (source == "fpgacounter"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_FPGACOUNTER_RESET)
                else:
                    raise ValueError("Invalid data source.")
                self.xem.UpdateWireIns()
                time.sleep(0.001)
                if (source == "data"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_CHIP_START)
                elif (source == "frame"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_FRAME_START)
                elif (source == "fpgacounter"):
                    self.xem.SetWireInValue(self.ADDR_WIRE, self.DATA_FPGACOUNTER_START)
                self.xem.UpdateWireIns()
                # Wait for data to fill FIFO
                wait_for_data = (numSamples*1.2)/(self.SER_RATE/self.SER_WIDTH)  # Expression to wait for the FIFO to fill + 20% margin
                time.sleep(wait_for_data)
                # Transfer data.  
                fifodata = ok.okTRegisterEntries(numSamples)
                self.xem.ReadRegisters(fifodata)
                # Pickle the data manually for multiprocessing
                fifodata = [i.data for i in fifodata]
                # Parse the data using multiprocessing
                if (source == "data"):
                    weight = weighting
                elif (source == "frame"):
                    weight = None
                elif (source == "fpgacounter"):
                    weight = None
                result = self.pool.starmap(parse, zip(fifodata, repeat(weight), repeat(bipolar), repeat(printBinary)))
                dataw, valid = zip(*result)
                if not all(valid):
                    raise ValueError("Encountered at least one non-valid sample.  Quitting.")
                dataw_list.extend(dataw)
                valid_list.extend(valid)
            return dataw_list, all(valid_list)
        else:
            # No connect is asserted
            return [0]*numSamples*mult, True         

# Method used by multiprocessing pool to parse data
# Input: fifodata (uint16), and a list of 16 bit weights from MSB to LSB or "None" to use radix-2 weighting, and whether to use bipolar weighting
# Return: weighted data, valid (only if weighting is not None) otherwise True
def parse(fifodata, weighting, bipolar, printBinary):
    #print(weighting) 
    if weighting is None:
        # Do nothing
        return fifodata, True
    else:
        # Apply custom bit weighting
        valid = (fifodata >= 32768)
        fifodata = BitArray(uint=fifodata, length=16).bin  
        fifodata = [*fifodata]    # split each bit into a list
        fifodata = [eval(j) for j in fifodata]    # re-evaluate, convert char to int in bit list
        if printBinary:
            print(fifodata)
        if bipolar:
            fifodata = [(2*j)-1 for j in fifodata]    # Convert 0,1 to -1,+1
            #fifodata = [0.5*j for j in fifodata]        # Re-normalize to account for the doubling in magnitude
        return np.dot(fifodata, weighting), valid







    
