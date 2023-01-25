#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/SRead_noise.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH

Use this script to take pedestal data.
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



if __name__ == "__main__":
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Uncomment here to run calibration
    '''
    cal.calibrate_ODAC_using_weights()
    cal.calibrate_weights()
    '''
    # Uncomment here to apply pre-defined calibration values
    
    cal.odac = "10000101"
    cal.weights = [0.00000000, 1934.97674713, 1109.17049561, 636.41151428, 363.16341553, 208.24048767, 120.19647980, 70.89272308, 40.33333130, 24.00000000, 14.00000000, 8.00000000, 5.00000000, 3.00000000, 2.00000000, 1.00000000]
    
    # Uncomment here to apply default settings
    '''
    cal.odac = cal.CAL_ODAC_DEFAULT          
    cal.weights = cal.CAL_WEIGHTS_DEFAULT.copy()    # Deep copy!
    '''

    # Apply data taking configuration + ODAC calibration
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Take a pedestal
    data, valid = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
    # Round
    data = [round(i) for i in data] 
    #print(np.unique(data))
    print("Std dev: "+str(np.std(data)))
    # Plot histogram
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.hist(data, bins=len(np.unique(data)), edgecolor = "black")
    plt.show() 
    # Plot time domain
    #fig, axs = plt.subplots(1,1,tight_layout=True)
    #axs.plot(data, marker='o')
    #plt.show() 


    



    




    
    
