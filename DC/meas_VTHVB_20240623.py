#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
June 2024
cryosar1/DC/meas_VTHVB_20240623.py

Sweeps VBN and measures ITEST and VTH (defined as VDS = VGS for a diode connected NMOS)

GPIB address mapping:
01: Measuring VDC VTH on MOBO, hp 34401a
02: Measuring VDC VBN on MOBO, hp 34401a
22: Measuring ITEST, hp 3458a
10: Power supply powering test setup and providing VBN, hp e3631a
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
    parser = argparse.ArgumentParser(description='Sweeps VBN and measures ITEST and VTH for a diode-connected NMOS.')
    parser.add_argument('-t', dest='setTemp', action='store', default=25, help="Set temperature, in celsius.  For metadata only.")
    parser.add_argument('-s', dest='sweep', action='store', default="0.000,0.001,1.200", help="VBN sweep in start,step,stop inclusive.  Units in volts.")
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
    VBN = hp34401a_gpib.hp34401a_gpib(gpib, "VBN", 2)
    ITEST = hp3458a_gpib.hp3458a_gpib(gpib, "ITEST", 22)
    PSU = hpe3631a_gpib.hpe3631a_gpib(gpib, "PSU", 10)

    

    # Sweep VBN
    for vbnset in sweepList:
        # Debug
        sys.stdout.write("\rSetting VBN={:f} in range [{:f}, {:f}, {:f}]".format(vbnset, startVolts, stepVolts, stopVolts))
        sys.stdout.flush()

        # Set VTHSET        
        PSU.setVTH(vbnset)

        # Let signals settle
        time.sleep(0.1)

        # Debug printing: see if signal settles after wait
        '''
        print(VBN.measDCV())
        print(VTH.measDCV())
        print(ITEST.measIDC10uA())
        print("====")
        '''

        # Measure
        measVBN = VBN.measDCV()
        measVTH = VTH.measDCV()
        measITEST = ITEST.measIDC10uA()

        # Debug
        '''
        print(VBN.measDCV())
        print(VTH.measDCV())
        print(ITEST.measIDC10uA())
        print("====")
        '''

        dataDict = {
                    "VBN_cmd": vbnset,
                    "VBN": measVBN,
                    "VTH": measVTH,
                    "ITEST": measITEST
                    }
        pw.appendData(dataDict)

    print("\n")
    pw.writeCSV()











