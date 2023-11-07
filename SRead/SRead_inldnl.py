#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/SRead_inldnl.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''




import ok
import time
import numpy as np
import subprocess
import tabulate
import datetime
import time
import sys
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from bitstring import BitArray
import fpga
import calibration
import logger

from plotFFT import plotFFT



if __name__ == "__main__":
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    sys.stdout = logger.logger("./output/inldnl/log.txt")
    # Save calibration info ##
    f = open("./output/inldnl/calibration.txt", "w") 
     
    
    # Uncomment here to run calibration (connect 50 ohm sma to signal input)
    
    f.write("CAL:function\n")
    # With the logger, textoutput from input() is not displayed.  workaround: print beforehand.
    print("CALIBRATION: Disable any input source.  Then press ENTER.")
    input("")
    cal.calibrate_ODAC_using_weights_v2()
    cal.calibrate_weights()
    print("CALIBRATION: Attach signal input source.  Then press ENTER.")
    input("")
    
    # Uncomment here to apply pre-defined calibration values
    '''
    f.write("CAL:predefined\n")
    print("Using predefined constants.")
    cal.odac = "10000101"
    cal.weights = [0.00000000, 2015.18280995, 1154.39856270, 662.66275483, 378.32254476, 216.67832853, 125.36733881, 73.58890683, 41.83486600, 25.03399658, 14.34997559, 8.20101929, 5.00000000, 3.00000000, 2.00000000, 1.00000000]



    print("Calibrated ODAC: \""+str(cal.odac)+"\"")
    print("Calibrated weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    '''
    # Uncomment here to apply play values
    '''
    print("Using predefined constants.")
    cal.odac = "10000101"
    cal.weights = [0.00000000, 1891.53274546, 1083.37309737, 622.01532083, 355.12751688, 203.32445951, 117.74653721, 69.15250705, 39.35890198, 23.75098572, 13.49131165, 8.00000000, 5.00000000, 3.00000000, 2.00000000, 1.00000000]
    print("Calibrated ODAC: \""+str(cal.odac)+"\"")
    print("Calibrated weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    '''
    # Uncomment here to apply DEFAULT (UNCALIBRATED) values
    '''
    print("Using UNCALIBRATED DEFAULT constants.")
    cal.odac = CAL_ODAC_DEFAULT
    cal.weights = cal.CAL_WEIGHTS_DEFAULT
    print("DEFAULT ODAC: \""+str(cal.odac)+"\"")
    print("DEFAULT weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    '''
    
    
    # Write calibration file    
    f.write("TIME\n")
    f.write(datetime.datetime.now().strftime('%Y%m%d_T%H%M%S')+"\n")
    f.write("ODAC\n")
    f.write(cal.odac+"\n")
    f.write("WEIGHTS\n")
    f.write("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]\n")
    f.close()

    ## Take data ##
    # Specify number of batches.  Number of data points = 32768 * nMult
    nMult = 64
    RedundancyFactor = 2.0    # Combine this many LSB's together.  This divides the effective code space.
    # Apply data taking configuration + ODAC calibration
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Take data
    cal.weights = np.array(cal.weights)/RedundancyFactor
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=nMult)
    #data = np.array(data)/RedundancyFactor
    data = np.round(data)
    # Plot time domain
    #fig, axs = plt.subplots(1,1,tight_layout=True)
    #axs.plot(data, marker='o')
    #axs.title.set_text("Calibrated")
    print("Number of unique codes: "+str(len(np.unique(data))))
    print("Code coverage [%]: "+str(100*len(np.unique(data))/np.ptp(data)))
    print("Calibrated stddev [LSB]: "+str(np.std(data)))
    print("Calibrated range [LSB]: "+str(np.ptp(data)))
    print("Calibrated FS (-1dBFS) [LSB]: "+str(np.sum(cal.weights))+" ("+str(0.9*np.sum(cal.weights))+")")
    if (np.ptp(data) > (np.sum(cal.weights)*0.9)):
        print("WARNING: Exceeding 90% of FS")
    # Plot FFT
    #plotFFT(data, fpga.SER_RATE/8, showNow=False, title="Calibrated", save="./output/sine/FFT_cal")
    # Save data
    np.savetxt("./output/inldnl/data_cal.txt.gz", data)
    np.savetxt("./output/inldnl/data_rad2.txt.gz", datar2)

    ## Calculate DNL then INL
    # Histogram
    N = np.log2(np.max(data)-np.min(data))
    hist, bin_edges = np.histogram(data, bins = np.arange(np.min(data), np.max(data), 1), density=True)
    bin_edges = bin_edges[:-1]
    
    ## A different way of calculating INL, using best fit method from sine wave
    # https://gitlab.cern.ch/jgonski/colutaanalysis/-/blob/dev_kiryeong/cv4_analysis/plotting/plots_slow_sine.py
    # https://www3.advantest.com/documents/11348/27fd03db-3c5d-49e7-afb9-e0bcb6861cee
    A = (np.max(data)-np.min(data))/2
    print(np.sum(hist))
    M = np.sum(hist)   # This needs to equal unity
    sum_Hk = np.cumsum(hist)    # Cumulative distribution function
    # Back-calculate the probability distribution function to obtain the transition locations
    V_j = -A*np.cos((np.pi/M)*sum_Hk)
    # Calculate DNL
    dnl = np.diff(V_j) - 1
    # Perform best line of fit, for use in INL
    V_fit = np.poly1d(np.polyfit(bin_edges, V_j, 1))
    inl = V_j - V_fit(bin_edges)
    
    
    # Plot INL/DNL
    fig, (axs1, axs2) = plt.subplots(2,1,tight_layout=True, sharex=True)
    fig.set_size_inches(8, 8)
    axs1.plot(bin_edges[:-1], dnl)
    axs2.plot(bin_edges, inl)
    # Plot graphics
    axs1.grid(which='both')
    axs2.grid(which='both')
    axs1.set_ylabel(r"DNL [LSB]")
    axs2.set_ylabel(r"INL [LSB]")
    axs2.set_xlabel(r"Code")
    # Save
    plt.savefig('./output/inldnl/DNLINL.png', dpi=900, pad_inches=0)
    # Plot histogram
    #fig, axs = plt.subplots(1,1,tight_layout=True)
    #fig.set_size_inches(8, 8)
    #axs.bar(bin_edges, hist)
    ## Plot cumulative sum
    #fig, axs = plt.subplots(1,1,tight_layout=True)
    #fig.set_size_inches(8, 8)
    #axs.plot(bin_edges, sum_Hk)
    


    plt.show() 


    





    




    
    
