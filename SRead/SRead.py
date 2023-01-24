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



if __name__ == "__main__":
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    cal.calibrate_ODAC()

    #data, valid = fpga.takeData("data", bipolar=True, printBinary=True)
    #print(np.unique(np.diff(data)))
    #print(np.unique(data))


    # Plot histogram
    #fig, axs = plt.subplots(1,1,tight_layout=True)
    #axs.hist(data, bins=len(np.unique(data)), edgecolor = "black")
    #plt.show() 


    



    




    
    
