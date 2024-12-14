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
    CAL_WEIGHTS_DEFAULT = [0.0, 1940.0, 1110.0, 635.0, 365.0, 210.0, 120.0, 70.0, 40.0, 24.0, 14.0, 8.0, 5.0, 3.0, 2.0, 1.0]   # 12bRC arrangement.  List elements must be of type float.
    #CAL_WEIGHTS_DEFAULT = [0.0, 1940.0, 1110.0, 635.0, 365.0, 210.0, 120.0, 70.0, 40.0, 24.0, 14.0, 8.0, 3.47, 1.5, 1.2, 1.0]    # Experimental!
    CAL_ODAC_DEFAULT = "10000000"                                           # Default value, this means nothing    
    ## Constants related to ODAC calibration
    CAL_ODAC_MULT = 1                                                       # multiplicity: number of 32768 samples to consider for averaging
    CAL_ODAC_SLICEEN = "000000000000001"                                    # Only enable LSB comparison for ODAC calibration
    CAL_ODAC_WEIGHTS = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]     # Weighting to be used in ODAC calibration
    CAL_ODAC_ITER = 8                                                       # 8 binary-searches for ODAC calibration.  Must be no more than the bit width of the ODAC code.
    CAL_ODAC_BITWIDTH = 8
    CAL_ODAC_START = 2                                                      # Only evaluate LSB
    CAL_ODAC_SEED = np.multiply(CAL_WEIGHTS_DEFAULT, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])  # Only enable slices that have known/assumed weights
    #CAL_ODAC_CONV = 3                                                       # Quit ODAC calibration when the mean is within +/- this many LSBs
    ## Constants related to weight calibration (first 3 weights are fixed)
    CAL_WEIGHTS_MULT = 1       # multiplicity: number of 32768 samples to consider for averaging
    CAL_WEIGHTS_WIDTH = 15      # Total number of calibrate-able bits
    CAL_WEIGHTS_START = 5       # LSB index to start calibration at.  value of 1 represents LSB; value of 2 represents LSB+1, etc.  Bit 8 is the start of the CDAC whereas lower bits are RCDAC.
    CAL_WEIGHTS_END = 15        # LSB index to end calibration at
    CAL_WEIGHTS_SEED = np.multiply(CAL_WEIGHTS_DEFAULT, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1])   # Only enable slices that have known/assumed weights
    CAL_WEIGHTS_SLICEEN_NONE = "000000000000000"  
    

    def __init__(self, fpga):
        # Instance of class fpga
        self.fpga = fpga
        # calibrated ODAC value, bit string
        self.odac = None
        self.odac_mean = 0
        self.odac_force0 = 0
        self.odac_force1 = 0
        # TODO: remove hard code
        #self.odac = "10100001"
        #self.odac = "10000000"
        #self.odac = "10000101"  # Using weights method.  In V3 setup sometimes comparator offset cal will not converge, probably because the serial data output is not DC balanced so it reads in noise when it is a DC value.  A bad ODAC value will cause normal calibration to fail.  This value is probably the closest to true ODAC.
        #self.odac = "01110100"      # Experimentally found for V3 DUT D3
        #self.odac = "10000101"     # Experimentally found for V3 DUT D1
        self.weights = None
        

    # Helper function to configure chip
    # Input: settings to explicitly modify in list name/value pair form: ["<name1>,<value1>", "<name2>,<value2>, ...] where name is from config file and value is bitstring
    def __config(self, args):
        # Insert element "-o" before each item in args list
        for b in range (0,len(args)):
            args.insert(b*2,"-o")

        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
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
            data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_ODAC_WEIGHTS, bipolar=True, printBinary=False)
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
        # Check the final value of self.odac
        self.__config([
                "CAL_EN,1",
                "SLICE_EN_P,"+self.CAL_ODAC_SLICEEN,
                "SLICE_EN_N,"+self.CAL_ODAC_SLICEEN,
                "ODAC_CODE,"+self.odac
            ])
        data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_ODAC_SEED, bipolar=True, printBinary=False)
        print("Final Mean: "+str(np.mean(data)))
        print("==== ODAC CALIBRATION (LSB method)====")
        print("Calibrated ODAC: \""+str(self.odac)+"\"")
        print("==== ====")

    # Calibrate offset using the first step in weight calibration.
    # This method imitates the first iteration of weight calibration procedure.  Under these conditions, we do not want the SAR to over-range as we calibrate out the weights of the LSB's hence the need for offset nulling.
    #
    # Recall that the weights are derived in a pseudo-differential manner.  First, the P-DAC side is manipulated while the N-DAC stays constant at VCM, then vice versa.  
    #
    # The offset nulling mechanism also works in a pseudo-differential manner to best imitate the weights calibration procedure.  Depending on bsel parameter, only the P-DAC or N-DAC are enabled.  Only the LSB slice is enabled, evaluated, and averaged over 32768 samples.  Offset is appropriately nulled when the comparator (LSB bit output) flips roughly 50% to logic low and 50% to logic high.  Depending on the average, the ODAC code (8 bits wide) is binary searched to make the comparator output 50/50 probability for logic low/high.
    #Either setting of bsel should result in the same ODAC code.
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
            data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_ODAC_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
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
        data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_ODAC_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
        print("Final Mean: "+str(np.mean(data)))
        print("==== ODAC CALIBRATION (weights method)====")
        print("Calibrated ODAC: \""+str(self.odac)+"\"")
        print("==== ====")
        
    # Version 2, more closely imitates calibrate_weights
    # Only imitate the first bit calibration in calibrate_weights
    def calibrate_ODAC_using_weights_v2(self, bsel=False, verbose=True):
        # Initial conditions   
        redundancy = 0  # Extra steps to take     
        odac_value = 0
        odac_weight = pow(2, self.CAL_ODAC_BITWIDTH-1)
        cal_index = self.CAL_WEIGHTS_START
        cal_force = BitArray(uint=int(pow(2,cal_index-1)), length=self.CAL_WEIGHTS_WIDTH).bin
        cal_sliceen = BitArray(uint=int(pow(2,cal_index)-1), length=self.CAL_WEIGHTS_WIDTH).bin
        # Keep a running record of ODAC values 
        odac_list = []
        mean_list = []
        force0_list = []
        force1_list = []
        try:
            for i in range(self.CAL_ODAC_ITER+redundancy):
                # Set ODAC code, force 0
                if bsel is False:
                    self.__config([
                        "CAL_EN,1",
                        "B_SEL,0",
                        "CAL_DIR_P,0",
                        "CAL_DIR_N,0",
                        "CAL_FORCE_P,"+cal_force,
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
                        "CAL_FORCE_N,"+cal_force,
                        "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                        "SLICE_EN_N,"+cal_sliceen,
                        "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
                    ])
                # Take data
                data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_WEIGHTS_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
                force0 = np.mean(data)
                force0_list.append(force0)
                # Set ODAC code, force 1
                if bsel is False:
                    self.__config([
                        "CAL_EN,1",
                        "B_SEL,0",
                        "CAL_DIR_P,1",
                        "CAL_DIR_N,1",
                        "CAL_FORCE_P,"+cal_force,
                        "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                        "SLICE_EN_P,"+cal_sliceen,
                        "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                        "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
                    ])
                else:
                    self.__config([
                        "CAL_EN,1",
                        "B_SEL,1",
                        "CAL_DIR_P,1",
                        "CAL_DIR_N,1",
                        "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                        "CAL_FORCE_N,"+cal_force,
                        "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                        "SLICE_EN_N,"+cal_sliceen,
                        "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
                    ])
                # Take data
                data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_WEIGHTS_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
                force1 = np.mean(data)
                force1_list.append(force1)
                # Debug printing
                if verbose is True:
                    print("== ITERATION "+str(i)+" ==")
                    print("Current ODAC binary: "+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin)
                    print("Current ODAC uint8: "+str(odac_value))
                    print("Force 0: "+str(force0))
                    print("Force 1: "+str(force1))
                    print("Current Mean: "+str(np.mean([force0, force1])))
                
                # Keep record 
                mean_list.append(np.mean([force0, force1]))
                odac_list.append(odac_value)
                
                '''
                # Check if calibration already converged (if so then quit)
                if np.abs(np.mean([force0, force1])) <= self.CAL_ODAC_CONV:
                    print("ODAC Calibration converged.")
                    break
                '''
                '''
                # Check if calibration already converged by seeing if neither force0 nor force1 overflowed
                if (np.abs(force0) != 11) and (np.abs(force1) != 11):
                    print("ODAC Calibration converged.")
                    break
                '''    
                # Apply ODAC correction 
                if bsel is False:
                    if (np.mean([force0, force1]) > 0):
                        odac_value = odac_value - odac_weight
                    else:
                        odac_value = odac_value + odac_weight
                else:
                    if (np.mean([force0, force1]) > 0):
                        odac_value = odac_value + odac_weight
                    else:
                        odac_value = odac_value - odac_weight
                # Set up next iteration
                odac_weight = np.ceil(odac_weight/2)
        except KeyboardInterrupt:
            print("Quitting gracefully.")
            exit()
            
                
        
        # Check the final value ODAC value after the last iteration's correction  
        if bsel is False:
            self.__config([
                "CAL_EN,1",
                "B_SEL,0",
                "CAL_DIR_P,0",
                "CAL_DIR_N,0",
                "CAL_FORCE_P,"+cal_force,
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
                "CAL_FORCE_N,"+cal_force,
                "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_N,"+cal_sliceen,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
        data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_WEIGHTS_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
        force0 = np.mean(data)
        force0_list.append(force0)
        if bsel is False:
            self.__config([
                "CAL_EN,1",
                "B_SEL,0",
                "CAL_DIR_P,1",
                "CAL_DIR_N,1",
                "CAL_FORCE_P,"+cal_force,
                "CAL_FORCE_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_P,"+cal_sliceen,
                "SLICE_EN_N,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
        else:
            self.__config([
                "CAL_EN,1",
                "B_SEL,1",
                "CAL_DIR_P,1",
                "CAL_DIR_N,1",
                "CAL_FORCE_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "CAL_FORCE_N,"+cal_force,
                "SLICE_EN_P,"+self.CAL_WEIGHTS_SLICEEN_NONE,
                "SLICE_EN_N,"+cal_sliceen,
                "ODAC_CODE,"+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin
            ])
        data,valid,nc = self.fpga.takeData("data", weighting=self.CAL_WEIGHTS_SEED, bipolar=True, printBinary=False, mult=self.CAL_ODAC_MULT)
        force1 = np.mean(data)
        force1_list.append(force1)
        # Debug printing
        if verbose is True:
            print("== LAST ITERATION ==")
            print("Current ODAC binary: "+BitArray(uint=int(odac_value), length=self.CAL_ODAC_BITWIDTH).bin)
            print("Current ODAC uint8: "+str(odac_value))
            print("Force 0: "+str(force0))
            print("Force 1: "+str(force1))
            print("Current Mean: "+str(np.mean([force0, force1])))
        
        
        # Add record of the last update to odac_value 
        mean_list.append(np.mean([force0, force1]))
        odac_list.append(odac_value)
        
        
        # Pick the most optimal ODAC value 
        # Check for any over/under flow in force results 
        force0_overflow = np.array(np.abs(np.array(force0_list)) == np.sum(self.CAL_WEIGHTS_SEED, axis=None))
        force1_overflow = np.array(np.abs(np.array(force1_list)) == np.sum(self.CAL_WEIGHTS_SEED, axis=None))
        mean_list_normal = np.array(mean_list)[~force0_overflow & ~force1_overflow]
        odac_list_normal = np.array(odac_list)[~force0_overflow & ~force1_overflow]
        force0_list_normal = np.array(force0_list)[~force0_overflow & ~force1_overflow]
        force1_list_normal = np.array(force1_list)[~force0_overflow & ~force1_overflow]
        try:
            idx = np.argmin(np.abs(mean_list_normal))
            odac_optimal = odac_list_normal[idx]
        except:
            odac_optimal = 128
            idx = 1
        '''
        print(force0_overflow)
        print(force1_overflow)
        print(mean_list)
        print(odac_list)
        '''
        '''
        # Pick the last ODAC iteration 
        idx = len(odac_list)-1
        odac_optimal = odac_list[idx]
        '''
        
        # Update class attribute
        self.odac = BitArray(uint=int(odac_optimal), length=self.CAL_ODAC_BITWIDTH).bin
        self.odac_mean = mean_list_normal[idx]
        self.odac_force0 = force0_list_normal[idx]
        self.odac_force1 = force1_list_normal[idx]
        if verbose is True:
            print("==== ODAC CALIBRATION (weights method v2)====")
            print("Force 0: "+str(force0_list_normal[idx]))
            print("Force 1: "+str(force1_list_normal[idx]))
            print("Final Mean: "+str(mean_list_normal[idx]))
            print("Calibrated ODAC: \""+BitArray(uint=int(odac_optimal), length=self.CAL_ODAC_BITWIDTH).bin+"\"")
            print("==== ====")
        

    # Calibrate weights starting from LSB
    def calibrate_weights(self, verbose=True):
        # Initial conditions
        weights_pdac = self.CAL_WEIGHTS_SEED.copy()     # Perform deep copy!
        weights_ndac = self.CAL_WEIGHTS_SEED.copy()     # Perform deep copy!
        weights = self.CAL_WEIGHTS_SEED.copy()          # Perform deep copy!
        try:
            for cal_index in range(self.CAL_WEIGHTS_START, self.CAL_WEIGHTS_END+1):
                cal_force = BitArray(uint=int(pow(2,cal_index-1)), length=self.CAL_WEIGHTS_WIDTH).bin
                cal_sliceen = BitArray(uint=int(pow(2,cal_index)-1), length=self.CAL_WEIGHTS_WIDTH).bin
                
                if verbose is True:
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
                data,valid,nc = self.fpga.takeData("data", weighting=weights_pdac, bipolar=True, printBinary=False, mult=self.CAL_WEIGHTS_MULT)
                w_pdac_force0 = np.mean(data)
                if verbose is True: print("Measured P-DAC force 0: "+str(w_pdac_force0))
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
                data,valid,nc = self.fpga.takeData("data", weighting=weights_pdac, bipolar=True, printBinary=False, mult=self.CAL_WEIGHTS_MULT)
                w_pdac_force1 = np.mean(data)
                if verbose is True: print("Measured P-DAC force 1: "+str(w_pdac_force1))
                ###
                #fig, axs = plt.subplots(1,1,tight_layout=True)
                #axs.plot(data, marker='o')
                #axs.title.set_text("P-DAC (bsel=0), direction 1 (cal_force=1)")
                ###

                # Calculate intermediate weight
                w_pdac = (w_pdac_force1 - w_pdac_force0)*0.5
                weights_pdac[-cal_index] = w_pdac
                if verbose is True:
                    print("Measured P-DAC weight: "+str(w_pdac))
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
                data,valid,nc = self.fpga.takeData("data", weighting=weights_ndac, bipolar=True, printBinary=False, mult=self.CAL_WEIGHTS_MULT)
                w_ndac_force0 = np.mean(data)
                if verbose is True: print("Measured N-DAC force 0: "+str(w_ndac_force0))
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
                data,valid,nc = self.fpga.takeData("data", weighting=weights_ndac, bipolar=True, printBinary=False, mult=self.CAL_WEIGHTS_MULT)
                w_ndac_force1 = np.mean(data)
                if verbose is True: print("Measured N-DAC force 1: "+str(w_ndac_force1))
                ###
                #fig, axs = plt.subplots(1,1,tight_layout=True)
                #axs.plot(data, marker='o')
                #axs.title.set_text("N-DAC (bsel=1), direction 1 (cal_force=1)")
                ###

                # Calculate intermediate weight
                w_ndac = (w_ndac_force1 - w_ndac_force0)*0.5
                weights_ndac[-cal_index] = w_ndac
                if verbose is True:
                    print("Measured N-DAC weight: "+str(w_ndac))
                    print("N-DAC weights:")
                    print(["{0:0.3f}".format(i) for i in weights_ndac])
                
                # Update composite weights
                weights = np.mean([weights_pdac, weights_ndac], axis=0)
                if verbose is True:
                    print("Composite weight:")
                    print(["{0:0.3f}".format(i) for i in weights])
        except KeyboardInterrupt:
            print("Quitting gracefully.")
            exit()
            
            

        # Update class attribute
        self.weights = weights
        if verbose is True:
            print("==== WEIGHT CALIBRATION ====")
            print("FINAL Composite weight:")
            print("["+', '.join([f'{item:.8f}' for item in self.weights])+"]")
            print("==== ====")
        #plt.show()

        

        

        

        




