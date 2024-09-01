#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Sept 2024
cryosar1/DC/measV3_DC_vs_VTHSET.py

Sweeps across VTHSET values and measures from motherboard AD7888

Make sure DIP switches are set to FDBK, DAC setting!

Have CryoCon running in the background to poll every second!
'''

import time, sys, subprocess, os
import numpy as np
import argparse
# Import shared folder
sys.path.insert(0, '../shared')
import pandasWriter
from bitstring import BitArray
import csv


if __name__ == "__main__":
    print("REMINDER: Make sure DIP switches are set to FDBK, DAC setting!")
    print("REMINDER: Have CryoCon running in the background to poll every second!")
    
    # Input arguments
    parser = argparse.ArgumentParser(description='Sweeps across VTHSET values and measures biases.')
    parser.add_argument('-t', dest='setTemp', action='store', default=25, help="Set temperature, in celsius.  For metadata only.")
    parser.add_argument('-s', dest='sweep', action='store', default="4,4,512", help="VTHSET sweep in start,step,stop inclusive.  Units in DAC setting out of 1024 (1.2V).")
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help="Verbose output/debug output.")
    args = parser.parse_args()

    # Parse sweep and initialize dataframe
    userCommentsDict = {"setTemp": args.setTemp,
                        "sweep": args.sweep,
                        "DACREF_V": "1.2",
                        "DACREF_LSB": "1023",
                        "ADCREF_V": "2.5",
                        "ADCREF_LSB": "4095",
                        "userComments": ""}
    pw = pandasWriter.pandasWriter(userComments=userCommentsDict, compress=False, csvFilePrefix=os.path.splitext(os.path.basename(__file__))[0])
    startDAC = float(args.sweep.split(",")[0])
    stepDAC = float(args.sweep.split(",")[1])
    stopDAC = float(args.sweep.split(",")[2])
    sweepList = np.arange(startDAC, stopDAC+stepDAC, stepDAC)
    sweepList = np.flip(sweepList)  # Start with highest VTH setting (VBN and VBP most near rails)
    
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

    

    # Sweep VTHSET
    for vthset in sweepList:
        vthset_int = int(vthset)
        vthset_bin = BitArray(uint=vthset_int, length=10).bin
        # Status printing 
        sys.stdout.write("\rSetting VTHSET={:d} in range [{:d}, {:d}, {:d}]".format(vthset_int, int(startDAC), int(stepDAC), int(stopDAC)))
        sys.stdout.flush()

        # Set VTHSET        
        try:
            subprocess.run([sys.executable,
                "./../SControl/SControl_DAC.py", 
                "-o", "DAC5A_data,"+vthset_bin,
                "-b",
                "-f", "./../SControl/config/CryoSAR1_DAC.cfg"])
        except Exception as e:
            sys.exit(e)

        # Let signals settle
        time.sleep(0.1)

        # Debug printing: see if signal settles after wait
        if args.debug is True:
            print("")
            try:
                subprocess.run([sys.executable,
                    "./../SControl/SControl_DAC.py", 
                    "-r"])
            except Exception as e:
                sys.exit(e)
        

        # Measure
        try:
            subprocess.run([sys.executable,
                "./../SControl/SControl_DAC.py", 
                "-r",
                "-q"])
        except Exception as e:
            sys.exit(e)
        with open("./output/adc.csv") as csv_file:
            reader = csv.reader(csv_file)
            ad7888_data = dict(reader)

        # Debug
        if args.debug is True:
            print("")
            print(ad7888_data)
            print("====")
        
        # Read sensor A last temperature file
        with open("./../CryoCon/sensorA_last", "r") as f:
            while True:
                try:
                    sensorA = float(f.read())
                except Exception as e:
                    continue # File may be being written
                else:
                    break
        
        # Combine data dictionaries
        dataDict = {
                    "VTHSET_DAC": vthset_int,
                    "sensorA": sensorA
                    }
        dataDict = {**dataDict, **ad7888_data}
        pw.appendData(dataDict)

    print("\n")
    pw.writeCSV()











