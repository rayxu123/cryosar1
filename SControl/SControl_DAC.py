#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
July 2023
QRFCP1/SControl/SControl_DAC.py

Configures a daisy chain of AD5313 DAC's via FTDI MPSSE SPI digital slow-control

Requires the packages:
 - pyqt5
 - python3-bitstring (via system package manager)
 - libusb (via system package manager)
 - pyftdi (see manual for installation and setup instructions)
'''

import sys
import argparse
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QApplication
from pyftdi.ftdi import Ftdi
import SControl_DAC_GUI
import SControl_ADC


#sys.path.insert(0, './pyftdi-cs_act_hi/')
#from ftdi import Ftdi

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='AD5313 interactive digital slow-control via FTDI MPSSE SPI.')
    parser.add_argument('-a', dest='addr', action='store', default='ftdi://ftdi:2232:FT73TM02/2', help="FTDI address.  Use -l to find this.  (Default: 'ftdi://ftdi:2232:FT73TM02/2')")
    parser.add_argument('-b', dest='batch', action='store_true', default=False, help="Launch in batch mode.  Program, verify, then exit.  Use with -f.")
    parser.add_argument('-l', dest='listFTDI', action='store_true', help="Lists available FTDI addresses and exits", default=False)
    parser.add_argument('-f', dest='cfgFile', action='store', default='./config/CryoSAR1_DAC.cfg',
                        help="Initial configuration file.  (Default: ./config/CryoSAR1_DAC.cfg)")
    parser.add_argument('-n', dest='noConnect', action='store_true', default=False,
                        help="No-connect mode.  (Default: False)")
    parser.add_argument('-o', dest='override', action='append',
                        help="Overrides specific fields on startup.  May specify more than once.  Specified as '<field name>,<value>' pairs.  Where <field name> is from the section name and <value> must be a bit string in order of MSB...LSB.  For example, 'ODAC_CODE,11111111' or 'CAL_FORCE_P,000111111111111'.  Field min and max must be obeyed, otherwise the bitstring will be truncated.")
    parser.add_argument('-r', dest='read', action='store_true', default=False, help="Reads from ADC's, writes values to an output file, and exit.  DAC settings are not touched.")
    parser.add_argument('-q', dest='quiet', action='store_true', default=False, help="Do not print ADC output to console.")
    args = parser.parse_args()
    # Launch application
    if args.listFTDI:
        print(" ==== FTDI DRIVER ==== ")
        Ftdi.show_devices()
        sys.exit()
    else:
        if args.read is False:
            app = QApplication(sys.argv)
            window = SControl_DAC_GUI.SControl_DAC_GUI(args)
            window.show()
            sys.exit(app.exec_())
        else:
            SControl_ADC.SControl_ADC(args)
            

