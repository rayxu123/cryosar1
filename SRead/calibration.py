#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/calibration.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''


import ok
import time
import sys
import os
import subprocess
import numpy as np
from bitstring import BitArray
from multiprocessing import Pool
from itertools import repeat

import matplotlib.pyplot as plt     # DNF: python3-matplotlib

class calibration:
    # When assigning variables from these class constants, a deep copy must be performed to avoid altering the constants!
    MULT = 10            # multiplicity: number of 32768 samples to consider for averaging
    CAL_WEIGHTS_DEFAULT = [0.0, 1940.0, 1110.0, 635.0, 365.0, 210.0, 120.0, 70.0, 40.0, 24.0, 14.0, 8.0, 5.0, 3.0, 2.0, 1.0]   # 12bRC arrangement.  List elements must be of type float.
    CAL_ODAC_DEFAULT = "10000000"                                           # Default value, this means nothing    
    ## Constants related to ODAC calibration
    CAL_ODAC_SLICEEN = "000000000000001"                                    # Only enable LSB comparison for ODAC calibration
    CAL_ODAC_WEIGHTS = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]     # Weighting to be used in ODAC calibration
    CAL_ODAC_ITER = 8                                                       # 8 binary-searches for ODAC calibration.  Must be no more than the bit width of the ODAC code.
    CAL_ODAC_BITWIDTH = 8
    CAL_ODAC_START = 4
    CAL_ODAC_SEED = np.multiply(CAL_WEIGHTS_DEFAULT, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1])
    ## Constants related to weight calibration (first 3 weights are fixed)
    CAL_WEIGHTS_WIDTH = 15      # Total number of calibrate-able bits
    CAL_WEIGHTS_START = 8       # LSB index to start calibration at.  value of 1 represents LSB; value of 2 represents LSB+1, etc.  Bit 8 is the start of the CDAC whereas lower bits are RCDAC.
    CAL_WEIGHTS_END = 15        # LSB index to end calibration at
    CAL_WEIGHTS_SEED = np.multiply(CAL_WEIGHTS_DEFAULT, [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
    CAL_WEIGHTS_SLICEEN_NONE = "000000000000000"  
    

    def __init__(self, fpga):
        # Instance of class fpga
        self.fpga = fpga
        # calibrated ODAC value, bit string
        self.odac = None
        # TODO: remove hard code
        #self.odac = "10100001"
        #self.odac = "10000000"
        #self.odac = "10000101"  # Using weights method
        #self.odac = "10000000"
        self.weights = None
        

    # Helper function to configure chip
    # Input: settings to explicitly modify in list name/value pair form: ["<name1>,<value1>", "<name2>,<value2>, ...] where name is from config file and value is bitstring
    def __config(self, args):
        # Insert element "-o" before each item in args list
        for b in range (0,len(args)):
            args.insert(b*2,"-o")

        try:
            subprocess.run(["./../SControl/SControl.py", 
                "-b"]
                + args +
                ["-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)

    # Calibrate offset by observing the statistics of the LSB bit flipping
    def calibrate_ODAC_using_LSB(self):
        # Initial conditions        
        odac_value = 0
        odac_weight = pow(2, self.CAL_ODAC_BITWIDTH-1)
        for i in range(self.CAL_ODAC_ITER):
            # Set ODAC code
            self.__config([
                "CAL_EN,1",
                "SLICE_EN_P,"+self.CAL_ODAC_SLICEEN,
                "SLICE_EN_N,"+self.CAL_ODAC_SLICEEN,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
            # Take data, get mean of LSB bit flips
            data,valid = self.fpga.takeData("data", weighting=self.CAL_ODAC_WEIGHTS, bipolar=True, printBinary=False)
            if (np.mean(data) > 0):
                odac_value = odac_value - odac_weight
            else:
                odac_value = odac_value + odac_weight
            # Set up next iteration
            odac_weight = odac_weight/2
            # Debug printing
            print("== ITERATION "+str(i)+" ==")
            print("Mean: "+str(np.mean(data)))
            print("ODAC uint8: "+str(odac_value))
            print("ODAC binary: "+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin)
        # Update class attribute
        self.odac = BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin

    # Calibrate offset using the first step in weight calibration.
    # This method imitates the first iteration of weight calibration procedure.  Under these conditions, we do not want the SAR to over-range as we calibrate out the weights of the LSB's hence the need for offset nulling.
    def calibrate_ODAC_using_weights(self, bsel=False):
        # Initial conditions        
        odac_value = 0
        odac_weight = pow(2, self.CAL_ODAC_BITWIDTH-1)
        cal_sliceen = BitArray(uint=int(pow(2,self.CAL_ODAC_START)-1), length=self.CAL_WEIGHTS_WIDTH).bin
        for i in range(self.CAL_ODAC_ITER):
            # Set ODAC code
            if bsel is False:
                self.__config([
                    "CAL_EN,1",
                    "B_SEL,0",
                    "CAL_DIR_P,0",
                    "CAL_DIR_N,0",
                    "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "SLICE_EN_P,"+cal_sliceen,
                    "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
                ])
            else:
                self.__config([
                    "CAL_EN,1",
                    "B_SEL,1",
                    "CAL_DIR_P,0",
                    "CAL_DIR_N,0",
                    "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                    "SLICE_EN_N,"+cal_sliceen,
                    "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
                ])
            # Take data, get mean of downstream slices
            data,valid = self.fpga.takeData("data", weighting=self.CAL_ODAC_SEED, bipolar=True, printBinary=False)
            if bsel is False:
                if (np.mean(data) > 0):
                    odac_value = odac_value - odac_weight
                else:
                    odac_value = odac_value + odac_weight
            else:
                if (np.mean(data) > 0):
                    odac_value = odac_value + odac_weight
                else:
                    odac_value = odac_value - odac_weight
            # Set up next iteration
            odac_weight = odac_weight/2
            # Debug printing
            print("== ITERATION "+str(i)+" ==")
            print("Mean: "+str(np.mean(data)))
            print("ODAC uint8: "+str(odac_value))
            print("ODAC binary: "+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin)
        # Update class attribute
        self.odac = BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
        # Check the final value of self.odac
        if bsel is False:
            self.__config([
                "CAL_EN,1",
                "B_SEL,0",
                "CAL_DIR_P,0",
                "CAL_DIR_N,0",
                "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_P,"+cal_sliceen,
                "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
        else:
            self.__config([
                "CAL_EN,1",
                "B_SEL,1",
                "CAL_DIR_P,0",
                "CAL_DIR_N,0",
                "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_N,"+cal_sliceen,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
        data,valid = self.fpga.takeData("data", weighting=self.CAL_ODAC_SEED, bipolar=True, printBinary=False)
        print("Final Mean: "+str(np.mean(data)))
        print("==== ODAC CALIBRATION (weights method)====")
        print("Calibrated ODAC: \""+str(self.odac)+"\"")
        print("==== ====")
        

    # Calibrate weights starting from LSB
    def calibrate_weights(self):
        # Initial conditions
        weights_pdac = self.CAL_WEIGHTS_SEED.copy()     # Perform deep copy!
        weights_ndac = self.CAL_WEIGHTS_SEED.copy()     # Perform deep copy!
        weights = self.CAL_WEIGHTS_SEED.copy()          # Perform deep copy!
        for cal_index in range(self.CAL_WEIGHTS_START, self.CAL_WEIGHTS_END+1):
            cal_force = BitArray(uint=int(pow(2,cal_index-1)), length=self.CAL_WEIGHTS_WIDTH).bin
            cal_sliceen = BitArray(uint=int(pow(2,cal_index)-1), length=self.CAL_WEIGHTS_WIDTH).bin
            
            print("== BIT "+str(cal_index)+" ==")
            print("cal force vector: "+cal_force)
            print("slice enable vector: "+cal_sliceen)
            
            # Set P-DAC (bsel=0), direction 0 (cal_force=0)
            self.__config([
                "CAL_EN,1",
                "B_SEL,0",
                "CAL_DIR_P,0",
                "CAL_DIR_N,0",
                "CAL_FORCE_P,"+cal_force,
                "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_P,"+cal_sliceen,
                "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "ODAC_CODE,"+self.odac
            ])
            # Take data, get mean 
            data,valid = self.fpga.takeData("data", weighting=weights_pdac, bipolar=True, printBinary=False, mult=self.MULT)
            w_pdac_force0 = np.mean(data)
            ###
            #fig, axs = plt.subplots(1,1,tight_layout=True)
            #axs.plot(data, marker='o')
            #axs.title.set_text("P-DAC (bsel=0), direction 0 (cal_force=0)")
            ###

            # Set P-DAC (bsel=0), direction 1 (cal_force=1)
            self.__config([
                "CAL_EN,1",
                "B_SEL,0",
                "CAL_DIR_P,1",
                "CAL_DIR_N,1",
                "CAL_FORCE_P,"+cal_force,
                "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_P,"+cal_sliceen,
                "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "ODAC_CODE,"+self.odac
            ])
            # Take data, get mean 
            data,valid = self.fpga.takeData("data", weighting=weights_pdac, bipolar=True, printBinary=False, mult=self.MULT)
            w_pdac_force1 = np.mean(data)
            ###
            #fig, axs = plt.subplots(1,1,tight_layout=True)
            #axs.plot(data, marker='o')
            #axs.title.set_text("P-DAC (bsel=0), direction 1 (cal_force=1)")
            ###

            # Calculate intermediate weight
            w_pdac = (w_pdac_force1 - w_pdac_force0)*0.5
            print("Measured P-DAC weight: "+str(w_pdac))
            weights_pdac[-cal_index] = w_pdac
            print("P-DAC weights:")
            print(["{0:0.3f}".format(i) for i in weights_pdac])
            
            
            # Set N-DAC (bsel=1), direction 0 (cal_force=0)
            self.__config([
                "CAL_EN,1",
                "B_SEL,1",
                "CAL_DIR_P,0",
                "CAL_DIR_N,0",
                "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "CAL_FORCE_N,"+cal_force,
                "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_N,"+cal_sliceen,
                "ODAC_CODE,"+self.odac
            ])
            # Take data, get mean 
            data,valid = self.fpga.takeData("data", weighting=weights_ndac, bipolar=True, printBinary=False, mult=self.MULT)
            w_ndac_force0 = np.mean(data)
            ###
            #fig, axs = plt.subplots(1,1,tight_layout=True)
            #axs.plot(data, marker='o')
            #axs.title.set_text("N-DAC (bsel=1), direction 0 (cal_force=0)") 
            ###

            # Set N-DAC (bsel=1), direction 1 (cal_force=1)
            self.__config([
                "CAL_EN,1",
                "B_SEL,1",
                "CAL_DIR_P,1",
                "CAL_DIR_N,1",
                "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "CAL_FORCE_N,"+cal_force,
                "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_N,"+cal_sliceen,
                "ODAC_CODE,"+self.odac
            ])
            # Take data, get mean 
            data,valid = self.fpga.takeData("data", weighting=weights_ndac, bipolar=True, printBinary=False, mult=self.MULT)
            w_ndac_force1 = np.mean(data)
            ###
            #fig, axs = plt.subplots(1,1,tight_layout=True)
            #axs.plot(data, marker='o')
            #axs.title.set_text("N-DAC (bsel=1), direction 1 (cal_force=1)")
            ###

            # Calculate intermediate weight
            w_ndac = (w_ndac_force1 - w_ndac_force0)*0.5
            print("Measured N-DAC weight: "+str(w_ndac))
            weights_ndac[-cal_index] = w_ndac
            print("N-DAC weights:")
            print(["{0:0.3f}".format(i) for i in weights_ndac])
            
            # Update composite weights
            weights = np.mean([weights_pdac, weights_ndac], axis=0)
            print("Composite weight:")
            print(["{0:0.3f}".format(i) for i in weights])
            
            

        # Update class attribute
        self.weights = weights
        print("==== WEIGHT CALIBRATION ====")
        print("FINAL Composite weight:")
        print("["+', '.join([f'{item:.8f}' for item in self.weights])+"]")
        print("==== ====")
        plt.show()

        

        

        

        




