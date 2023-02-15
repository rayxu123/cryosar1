#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SControl/SControl.py

Configures CryoSAR1 via FTDI MPSSE SPI digital slow-control

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
import SControl_GUI


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='CryoSAR1 interactive digital slow-control via FTDI MPSSE SPI.')
    parser.add_argument('-a', dest='addr', action='store', default='ftdi://ftdi:232h:FT6X0PWN/1', help="FTDI address.  (Default: 'ftdi://ftdi:232h:FT6X0PWN/1')")
    parser.add_argument('-b', dest='batch', action='store_true', default=False, help="Launch in batch mode.  Program, verify, then exit.  Use with -f.")
    parser.add_argument('-l', dest='listFTDI', action='store_true', help="Lists available FTDI addresses and exits", default=False)
    parser.add_argument('-f', dest='cfgFile', action='store', default='./config/CryoSAR1.cfg',
                        help="Initial configuration file.  (Default: ./config/CryoSAR1.cfg)")
    parser.add_argument('-n', dest='noConnect', action='store_true', default=False,
                        help="No-connect mode.  (Default: False)")
    parser.add_argument('-o', dest='override', action='append',
                        help="Overrides specific fields on startup.  May specify more than once.  Specified as '<field name>,<value>' pairs.  Where <field name> is from the section name and <value> must be a bit string in order of MSB...LSB.  For example, 'ODAC_CODE,11111111' or 'CAL_FORCE_P,000111111111111'.  Field min and max must be obeyed, otherwise the bitstring will be truncated.")
    args = parser.parse_args()
    # Launch application
    if args.listFTDI:
        Ftdi.show_devices()
        sys.exit()
    else:
        app = QApplication(sys.argv)
        window = SControl_GUI.SControl_GUI(args)
        window.show()
        sys.exit(app.exec_())
