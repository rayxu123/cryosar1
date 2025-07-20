#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
July 2025
cryosar1/DAQ/measV3_pdel.py

Figures out the maximum DEL_PER to get all ~1M samples valid
'''

import time, sys, subprocess, os
import numpy as np
from bitstring import BitArray
# Import SRead folder
sys.path.insert(0, '../SRead')
import fpga



    

# Test: Take pedestal data
def takePedestal(datadir):
    print("Taking pedestal data.")
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    time.sleep(0.3)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=args.mult)
    if valid is False: print("WARNING: non-valid sample encountered!")
    # Save raw data
    np.savetxt(datadir+"/baseline_cal.txt.gz", data)
    np.savetxt(datadir+"/baseline_cal_r2.txt.gz", datar2)
    # Debug printing
    data_rounded = np.round(data)
    data_unique = np.unique(data_rounded)
    data_stddev = np.std(data_rounded)
    print("Pedestal Values: "+str(data_unique))
    print("Pedestal Stddev: "+str(data_stddev))

# Test: calibration
def calibrate(datadir):
    tty = sys.stdout
    # Temporairily redirect stdout
    sys.stdout = logger.logger(datadir+"/calibration.log")
    cal.calibrate_ODAC_using_weights_v2()
    cal_odac_int = BitArray(bin=cal.odac).uint
    cal.calibrate_weights()
    cal_weights_list = cal.weights.copy()
    print("==== ====")
    print("Calibrated ODAC: \""+str(cal.odac)+"\"")
    print("Calibrated weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    sys.stdout = tty
    # Load in calibrated ODAC
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    time.sleep(0.3)






    


    

    

if __name__ == "__main__":
    print("REMINDER: Make sure DIP switches are set to MAN, RAIL setting!")
    print("REMINDER: Have CryoCon or TMon running in the background to poll every second!")
    
    mult = 32

    
    
    # Init readout 
    fpga = fpga.fpga()

    
    
    
    # Initialize DUT
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1_DAC.cfg"])
    except Exception as e:
        sys.exit(e)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-r",
            "-q"])
    except Exception as e:
        sys.exit(e)
    # Wait for signal to settle 
    time.sleep(0.3)
    
    
    DEL_PER_list = []
    valid_list = []
    all_valid = False
    DEL_PER = BitArray(uint=0, length=5)
    
    for i in range(5):
        # Try a value for delay
        DEL_PER.set(value=True, pos=i)
        # Set DUT
        print("Setting DEL_PER: "+DEL_PER.bin)
        try:
            subprocess.run([sys.executable,
                "./../SControl/SControl.py", 
                "-b",
                "-o", "DEL_PER,"+DEL_PER.bin,
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        # Read DUT
        try:
            data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, mult=mult)
        except Exception as e:
            valid = False
        # Adjust delay value accordingly
        if valid:
            print("All Valid!  Increasing Delay.")
            DEL_PER.set(value=True, pos=i)
        else:
            print("Decreasing Delay.")
            DEL_PER.set(value=False, pos=i)
            
    # Try final value
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-o", "DEL_PER,"+DEL_PER.bin,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Read DUT
    try:
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, mult=mult)
    except Exception as e:
        valid = False
    print("Try final value (EXPECT TRUE): "+str(valid))

    
    # Try final value plus one
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-o", "DEL_PER,"+BitArray(uint=DEL_PER.uint+1, length=5).bin,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Read DUT
    try:
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, mult=mult)
    except Exception as e:
        valid = False
    print("Try final value plus one (EXPECT FALSE): "+str(valid))
    
    
    print("FINAL DEL_PER UINT = "+str(DEL_PER.uint))
    
    











