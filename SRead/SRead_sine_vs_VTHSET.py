#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/DC/SREAD_sine_vs_VTHSET.py

Extension of both SRead_Sine.py and ../DC/meas_VTHVB.py but Sweeps across VTHSET values and measures VTH, VBN, VBP, and current draw along with sine wave acquisition.
Current draw is measured as DUT board + MOBO total, so only relative current draw with respect to VTHSET is applicable.

GPIB address mapping:
01: Measuring VDC VTH on MOBO, hp 34401a
02: Measuring VDC VTHSET on MOBO, hp 34401a
03: Measuring VDC VBN on MOBO, hp 34401a
04: Measuring VDC VBP on MOBO, hp 34401a
22: Measuring DUT RTD100 temperature, hp 3458a
10: Power supply powering test setup and providing VTHSET, hp e3631a
USB: Agilent 33220A AWG

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''

import time, sys, subprocess, os
import numpy as np
import argparse
import tabulate
import datetime
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from bitstring import BitArray
import fpga
import calibration
import logger
from plotFFT import plotFFT
# Import shared folder
sys.path.insert(0, '../shared')
import prologixUSBGPIB
import pandasWriter
import hp3458a_gpib
import hp34401a_gpib
import hpe3631a_gpib
import hp33220a_visa

if __name__ == "__main__":
    # Input arguments
    parser = argparse.ArgumentParser(description='Sweeps across VTHSET values and measures VTH, VBN, VBP, current draw, and sine wave performance.')
    parser.add_argument('-t', dest='setTemp', action='store', default=25, help="Set temperature, in celsius.  For metadata only.")
    parser.add_argument('-s', dest='sweep', action='store', default="0.25,0.02,0.45", help="VTHSET sweep in start,step,stop inclusive.  Units in volts.")
    parser.add_argument('-f', dest='awgFreq', action='store', default="1.002670288E6", help="AWG sine wave frequency, in Hz.")
    parser.add_argument('-a', dest='awgAmpl', action='store', default="1.77", help="AWG sine wave amplitude, in Vpp.  (Optimal may be 100 ADC counts below -1dBFS?)")
    parser.add_argument('--awg1MHz', dest='awg1MHz', action='store_true', default="False", help="1.002670288E6 Hz, 1.77 Vpp preset")
    parser.add_argument('--awg8MHz', dest='awg8MHz', action='store_true', default="False", help="7.997146606E6 Hz, 2.00 Vpp preset")
    args = parser.parse_args()

    awgFreq = args.awgFreq
    awgAmpl = args.awgAmpl
    if args.awg1MHz is True:
        awgFreq = "1.002670288E6"
        awgAmpl = "1.77"
    if args.awg8MHz is True:
        awgFreq = "7.997146606E6"
        awgAmpl = "2.00"

    # Parse sweep and initialize dataframe and initialize output directory
    folderPrefix = os.path.splitext(os.path.basename(__file__))[0]
    userCommentsDict = {"setTemp": args.setTemp,
                        "sweep": args.sweep,
                        "awgFreq": awgFreq,
                        "awgAmpl": awgAmpl,
                        "userComments": ""}
    pw = pandasWriter.pandasWriter(userComments=userCommentsDict, compress=False, csvFilePrefix=os.path.splitext(os.path.basename(__file__))[0], folderPrefix=folderPrefix)
    startVolts = float(args.sweep.split(",")[0])
    stepVolts = float(args.sweep.split(",")[1])
    stopVolts = float(args.sweep.split(",")[2])
    sweepList = np.arange(startVolts, stopVolts+stepVolts, stepVolts)
    #sweepList = np.append(sweepList, 0.36)   # Append a VTHSET=0.36V
    sweepList = np.append(sweepList, 0.6)   # Append a VTHSET=0.6V to immitate a case where VBN/VBP are fixed to VSS/VDD.
    itrList = list(range(len(sweepList)))
    measFolder = "./output/"+folderPrefix+"/"+os.path.splitext(os.path.basename(pw.csvFilepath()))[0]+"_meas"
    os.makedirs(measFolder)

    # Initialize instruments
    gpib = prologixUSBGPIB.prologixUSBGPIB()
    VTH = hp34401a_gpib.hp34401a_gpib(gpib, "VTH", 1)
    VTHSET = hp34401a_gpib.hp34401a_gpib(gpib, "VTHSET", 2)
    VBN = hp34401a_gpib.hp34401a_gpib(gpib, "VBN", 3)
    VBP = hp34401a_gpib.hp34401a_gpib(gpib, "VBP", 4)
    RTD = hp3458a_gpib.hp3458a_gpib(gpib, "RTD", 22)
    PSU = hpe3631a_gpib.hpe3631a_gpib(gpib, "PSU", 10)
    AWG = hp33220a_visa.hp33220a_visa()
    AWG.initSine(awgFreq, awgAmpl)
    AWG.setOutput(False)

    # Initialize DAQ
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)

    # Initialize DUT
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    
    
    # Sweep VTHSET
    for vthset,itr in zip(sweepList, itrList):
        # Make data folder
        dataFolder = measFolder+"/data{:04d}".format(itr)
        os.makedirs(dataFolder)

        # Set VTHSET        
        PSU.setVTH(vthset)
        # AWG off
        AWG.setOutput(False)

        # Let signals settle
        time.sleep(1)

        # Measure DC
        measVTHSET = VTHSET.measDCV()
        measVTH = VTH.measDCV()
        measVBN = VBN.measDCV()
        measVBP = VBP.measDCV()
        measRTDR = RTD.measResistance()
        measRTDT = RTD.measTemperature()
        measPSUI = PSU.measVDDCurr()
        PSU.dispVTH()

        # Calibrate
        cal.calibrate_ODAC_using_weights_v2()
        cal.calibrate_weights()
        # Save calibration info 
        with open(dataFolder+"/calibration.txt", "w") as f:
            f.write("TIME\n")
            f.write(datetime.datetime.now().strftime('%Y%m%d_T%H%M%S')+"\n")
            f.write("ODAC\n")
            f.write(cal.odac+"\n")
            f.write("WEIGHTS\n")
            f.write("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]\n")

        # Apply data taking configuration + ODAC calibration
        try:
            subprocess.run(["./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+cal.odac,
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)

        # AWG on
        AWG.setOutput(True)

        # Let signals settle
        time.sleep(2)
        
        # Take data, calibrated
        data, valid_cal, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)

        # Analyze, calibrated
        ENOB_cal, SNDR_cal, SFDR_cal, _, _, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=False, numbins=1)    # Uncomment this for 12b code levels
        # Save data, calibrated
        np.savetxt(dataFolder+"/data_cal.txt", data)
        np.savetxt(dataFolder+"/data_cal_rad2.txt", datar2)

        ## Uncalibrated data ##
        # Apply data taking configuration + ODAC calibration
        try:
            subprocess.run(["./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+cal.CAL_ODAC_DEFAULT,
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        # Take data, uncalibrated
        data, valid_uncal, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.CAL_WEIGHTS_DEFAULT.copy(), mult=1)

         # Analyze, uncalibrated
        ENOB_uncal, SNDR_uncal, SFDR_uncal, _, _, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=False, numbins=1)    # Uncomment this for 12b code levels
        # Save data, uncalibrated
        np.savetxt(dataFolder+"/data_uncal.txt", data)
        np.savetxt(dataFolder+"/data_uncal_rad2.txt", datar2)

        # Write dataframe.  Waveform data not saved here otherwise it would be difficult to view the csv.
        dataDict = {
                    "measFolder": dataFolder,
                    "data_valid_cal": valid_cal,
                    "ENOB_cal": ENOB_cal,
                    "SNDR_cal": SNDR_cal,
                    "SFDR_cal": SFDR_cal,
                    "data_valid_uncal": valid_uncal,
                    "ENOB_uncal": ENOB_uncal,
                    "SNDR_uncal": SNDR_uncal,
                    "SFDR_uncal": SFDR_uncal,
                    "VTHSET_cmd": vthset,
                    "VTHSET": measVTHSET,
                    "VTH": measVTH,
                    "VBN": measVBN,
                    "VBP": measVBP,
                    "RTDR": measRTDR,
                    "RTDT": measRTDT,
                    "PSUI": measPSUI,
                    }
        pw.appendData(dataDict)
    
    pw.writeCSV()


    '''
    # Initialize DUT
    try:
        subprocess.run(["./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)

    # Initialize instruments
    gpib = prologixUSBGPIB.prologixUSBGPIB()
    VTH = hp34401a_gpib.hp34401a_gpib(gpib, "VTH", 1)
    VTHSET = hp34401a_gpib.hp34401a_gpib(gpib, "VTHSET", 2)
    VBN = hp34401a_gpib.hp34401a_gpib(gpib, "VBN", 3)
    VBP = hp34401a_gpib.hp34401a_gpib(gpib, "VBP", 4)
    RTD = hp3458a_gpib.hp3458a_gpib(gpib, "RTD", 22)
    PSU = hpe3631a_gpib.hpe3631a_gpib(gpib, "PSU", 10)

    

    # Sweep VTHSET
    for vthset in sweepList:
        # Debug
        sys.stdout.write("\rSetting VTHSET={:f} in range [{:f}, {:f}, {:f}]".format(vthset, startVolts, stepVolts, stopVolts))
        sys.stdout.flush()

        # Set VTHSET        
        PSU.setVTH(vthset)

        # Let signals settle
        time.sleep(0.1)

        # Debug printing: see if signal settles after wait
        #print(VBP.measDCV())
        #print(VBP.measDCV())
        #print(VBP.measDCV())
        #print(VBP.measDCV())
        #print(VBP.measDCV())
        #print("====")
        

        # Measure
        measVTHSET = VTHSET.measDCV()
        measVTH = VTH.measDCV()
        measVBN = VBN.measDCV()
        measVBP = VBP.measDCV()
        measRTDR = RTD.measResistance()
        measRTDT = RTD.measTemperature()
        measPSUI = PSU.measVDDCurr()

        # Debug
        #print("measVTHSET: "+str(measVTHSET))
        #print("measVTH: "+str(measVTH))
        #print("measVBN: "+str(measVBN))
        #print("measVBP: "+str(measVBP))
        #print("measRTDR: "+str(measRTDR))
        #print("measRTDT: "+str(measRTDT))
        #print("measPSUI: "+str(measPSUI))
        #print("====")
        

        dataDict = {
                    "VTHSET_cmd": vthset,
                    "VTHSET": measVTHSET,
                    "VTH": measVTH,
                    "VBN": measVBN,
                    "VBP": measVBP,
                    "RTDR": measRTDR,
                    "RTDT": measRTDT,
                    "PSUI": measPSUI
                    }
        pw.appendData(dataDict)

    print("\n")
    pw.writeCSV()
    '''










