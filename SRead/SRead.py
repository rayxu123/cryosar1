#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/SRead.py

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
import fpga
import calibration

from plotFFT import plotFFT



if __name__ == "__main__":
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Uncomment here to run calibration
    
    cal.calibrate_ODAC_using_weights()
    cal.calibrate_weights()
    
    # Uncomment here to apply pre-defined calibration values
    '''
    cal.odac = "10000101"
    cal.weights = [0.00000000, 1905.57759770, 1091.37488475, 626.72083549, 357.71243830, 204.87015594, 118.58812263, 69.55837715, 39.66100922, 23.76150513, 13.49820709, 8.00000000, 5.00000000, 3.00000000, 2.00000000, 1.00000000]
    '''
    # Uncomment here to apply play values
    '''
    cal.odac = "10000101"
    cal.weights = [0.000, 1894.597, 1084.891, 623.030, 355.733, 203.613, 117.979, 69.216, 39.405, 23.765, 13.457, 8.000, 5.000, 3.000, 2.000, 1.000]
    '''
    
    ## Calibrated data ##
    # Apply data taking configuration + ODAC calibration
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Take data
    data, valid = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
    # Round
    #print(np.unique(data))
    print("Calibrated Std dev: "+str(np.std(data)))
    # Plot histogram (rounded)
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.hist(np.round(data), bins=len(np.unique(np.round(data))), edgecolor = "black")
    axs.title.set_text("Calibrated")
    # Plot time domain
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.plot(data, marker='o')
    axs.title.set_text("Calibrated")
    plotFFT(data, 25, showNow=False, title="Calibrated")
    np.savetxt("data_cal.txt", data)


    ## Uncalibrated data ##
    # Apply data taking configuration + ODAC calibration
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.CAL_ODAC_DEFAULT,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Take data
    data, valid = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.CAL_WEIGHTS_DEFAULT.copy(), mult=1)
    # Round
    #print(np.unique(data))
    print("Uncalibrated Std dev: "+str(np.std(data)))
    # Plot histogram
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.hist(np.round(data), bins=len(np.unique(np.round(data))), edgecolor = "black")
    axs.title.set_text("UNCalibrated")
    # Plot time domain
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.plot(data, marker='o')
    axs.title.set_text("UNCalibrated")
    plotFFT(data, 25, showNow=False, title="UNCalibrated")


    plt.show() 


    



    




    
    
