#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/SRead_sine.py

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

from plotFFT import plotFFT



if __name__ == "__main__":
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    # Save calibration info ##
    f = open("./output/calibration.txt", "w") 
     
    
    # Uncomment here to run calibration (connect 50 ohm sma to signal input)
    
    f.write("CAL:function\n")
    input("CALIBRATION: Disconnect any input source and attach a 50 Ohm SMA cap.  Then press ENTER.")
    cal.calibrate_ODAC_using_weights_v2()
    cal.calibrate_weights()
    input("CALIBRATION: Attach signal input source.  Then press ENTER.")
    
    # Uncomment here to apply pre-defined calibration values
    '''
    f.write("CAL:predefined\n")
    print("Using predefined constants.")
    cal.odac = "10000101"
    cal.weights = [0.00000000, 2018.06262263, 1156.82281058, 663.97719226, 378.65321412, 217.20351402, 125.33742357, 73.72678329, 41.98767581, 24.63610840, 14.36486816, 7.98997498, 5.00000000, 3.00000000, 2.00000000, 1.00000000]

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
    
    
    # Write calibration file    
    f.write("TIME\n")
    f.write(datetime.datetime.now().strftime('%Y%m%d_T%H%M%S')+"\n")
    f.write("ODAC\n")
    f.write(cal.odac+"\n")
    f.write("WEIGHTS\n")
    f.write("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]\n")
    f.close()

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
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
    # Plot time domain
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.plot(data, marker='o')
    axs.title.set_text("Calibrated")
    print("Calibrated stddev: "+str(np.std(data)))
    print("Calibrated range: "+str(np.ptp(data)))
    # Plot FFT
    plotFFT(data, fpga.SER_RATE/8000000, showNow=False, title="Calibrated", save="./output/FFT_cal")
    # Save data
    np.savetxt("./output/data_cal.txt", data)
    np.savetxt("./output/data_rad2.txt", datar2)


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
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.CAL_WEIGHTS_DEFAULT.copy(), mult=1)
    # Plot time domain
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.plot(data, marker='o')
    axs.title.set_text("UNCalibrated")
    # Plot FFT
    plotFFT(data, fpga.SER_RATE/8000000, showNow=False, title="UNCalibrated", save="./output/FFT_uncal")
    # Save data
    np.savetxt("./output/data_uncal.txt", data)


    plt.show() 


    



    




    
    
