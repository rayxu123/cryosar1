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

# Function to read and print current PSU status
def read_current():
    print("==== READ CURRENT ====")
    print("+6V Output: "+gpib.query("hpe3631a", "MEAS:VOLT:DC? P6V")+" V @ "+gpib.query("hpe3631a", "MEAS:CURR:DC? P6V")+" A")
    print("+25V Output: "+gpib.query("hpe3631a", "MEAS:VOLT:DC? P25V")+" V @ "+gpib.query("hpe3631a", "MEAS:CURR:DC? P25V")+" A")
    print("-25V Output: "+gpib.query("hpe3631a", "MEAS:VOLT:DC? N25V")+" V @ "+gpib.query("hpe3631a", "MEAS:CURR:DC? N25V")+" A")

# Function to read and print setting PSU status
def read_setting():
    print("==== READ SETTING ====")
    print("+6V Output: "+gpib.query("hpe3631a", "APPL? P6V")+" V")
    print("+25V Output: "+gpib.query("hpe3631a", "APPL? P25V")+" V")
    print("-25V Output: "+gpib.query("hpe3631a", "APPL? N25V")+" V")


# Function to enable PSU output
def output_on():
    print("==== OUTPUT ON ====")
    print(gpib.query("hpe3631a", "OUTP ON"))

# Function to disable PSU output
def output_off():
    print("==== OUTPUT OFF ====")
    print(gpib.query("hpe3631a", "OUTP OFF"))



# MAIN function
if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='Stand-alone utility to enable/disable/read from a Agilent E3631A PSU')
    parser.add_argument('action', action='store', default='read', 
                        help="Action to perform: on, off, read.  (Default: read)")
    args = parser.parse_args()
    
    # Establish connection to PSU
    global gpib
    gpib = prologixUSBGPIB.prologixUSBGPIB(noConnect=False, verbose=False)
    gpib.addInstr("hpe3631a", 10)
    print("==== IDENTIFY ====")
    print(gpib.query("hpe3631a", "*IDN?"))
    read_setting()
    if (args.action == "on"):
        output_on()
    elif (args.action == "off"):
        output_off()
    read_current()





    
