#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Dec 2022
cryosar1/util/agilent_e3631a_psu.py

Remote control for Agilent E3631A on GPIB address 10
'''

import sys
import argparse
sys.path.insert(0, '../shared')
import prologixUSBGPIB



# Function to read and print setting PSU status
def read_setting():
    print("==== READ SETTING ====")
    print("Freq: "+gpib.query("hp8648a", ":FREQ?")+" ")




# MAIN function
if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='Stand-alone utility to enable/disable/read from a Agilent E3631A PSU')
    parser.add_argument('freq', action='store', default='400', 
                        help="Sets frequency in MHz (Default: 400 MHz)")
    args = parser.parse_args()
    
    # Establish connection to PSU
    global gpib
    gpib = prologixUSBGPIB.prologixUSBGPIB(noConnect=False, verbose=False)
    gpib.addInstr("hp8648a", 23)
    print("==== IDENTIFY ====")
    print(gpib.query("hp8648a", "*IDN?"))
    read_setting()
    print("==== SET ====")
    gpib.query("hp8648a", ":FREQ "+args.freq)
    read_setting()



    
