#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Oct 2023
cryosar1/DC/meas_VTHVB.py

Sweeps across VTHSET values and measures VTH, VBN, VBP, and current draw.
Current draw is measured as DUT board + MOBO total, so only relative current draw with respect to VTHSET is applicable.

GPIB address mapping:
01: Measuring VDC VTH on MOBO, hp 34401a
02: Measuring VDC VTHSET on MOBO, hp 34401a
03: Measuring VDC VBN on MOBO, hp 34401a
04: Measuring VDC VBP on MOBO, hp 34401a
22: Measuring DUT RTD100 temperature, hp 3458a
10: Power supply powering test setup and providing VTHSET, hp e3631a
'''

import time, sys, subprocess, os
import numpy as np
import argparse
# Import shared folder
sys.path.insert(0, '../shared')
import prologixUSBGPIB
import pandasWriter
import hp3458a_gpib
import hp34401a_gpib
import hpe3631a_gpib

if __name__ == "__main__":
    # Input arguments
    parser = argparse.ArgumentParser(description='Sweeps across VTHSET values and measures VTH, VBN, VBP, and current draw.')
    parser.add_argument('-t', dest='setTemp', action='store', default=25, help="Set temperature, in celsius.  For metadata only.")
    parser.add_argument('-s', dest='sweep', action='store', default="0.100,0.0025,0.600", help="VTHSET sweep in start,step,stop inclusive.  Units in volts.")
    args = parser.parse_args()

    # Parse sweep and initialize dataframe
    userCommentsDict = {"setTemp": args.setTemp,
                        "sweep": args.sweep,
                        "userComments": ""}
    pw = pandasWriter.pandasWriter(userComments=userCommentsDict, compress=False, csvFilePrefix=os.path.splitext(os.path.basename(__file__))[0])
    startVolts = float(args.sweep.split(",")[0])
    stepVolts = float(args.sweep.split(",")[1])
    stopVolts = float(args.sweep.split(",")[2])
    sweepList = np.arange(startVolts, stopVolts+stepVolts, stepVolts)
    
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
        '''
        print(VBP.measDCV())
        print(VBP.measDCV())
        print(VBP.measDCV())
        print(VBP.measDCV())
        print(VBP.measDCV())
        print("====")
        '''

        # Measure
        measVTHSET = VTHSET.measDCV()
        measVTH = VTH.measDCV()
        measVBN = VBN.measDCV()
        measVBP = VBP.measDCV()
        measRTDR = RTD.measResistance()
        measRTDT = RTD.measTemperature()
        measPSUI = PSU.measVDDCurr()

        # Debug
        '''
        print("measVTHSET: "+str(measVTHSET))
        print("measVTH: "+str(measVTH))
        print("measVBN: "+str(measVBN))
        print("measVBP: "+str(measVBP))
        print("measRTDR: "+str(measRTDR))
        print("measRTDT: "+str(measRTDT))
        print("measPSUI: "+str(measPSUI))
        print("====")
        '''

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











