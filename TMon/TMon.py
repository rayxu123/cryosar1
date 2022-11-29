#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/TMon/TMon.py

Stand-alone real-time temperature and data logging with the HP 3458A and a 100 Ohm RTD (alpha=0.85) sensor.

Requires the packages:
 - pyqt5
 - pyserial
 - pandas
'''

import sys
import argparse
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
import TMon_GUI


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='Stand-alone real-time temperature and data logging with the HP 3458A and a 100 Ohm RTD (alpha=0.85) sensor.')
    parser.add_argument('-a', dest='addr', action='store', default=22, help="GPIB address.  (Default: 22)")
    parser.add_argument('-2', dest='twowire', action='store_true', help="Use 2-wire sensing.  (Default: False)", default=False)
    parser.add_argument('-o', dest='enableOutfile', action='store_false', default=True, help="Enable data logging.  (Default: True)")
    parser.add_argument('-f', dest='filenamePrefix', action='store', default='',
                        help="Filename Prefix, use only with -o.  (Default: None)")
    parser.add_argument('-c', dest='userComments', action='store', default='',
                        help="User comments, use only with -o.  (Default: None)")
    parser.add_argument('-n', dest='noConnect', action='store_true', default=False,
                        help="No connect/demo mode, useful for debugging.  (Default: False)")
    parser.add_argument('-p', dest='pollingInterval', action='store', default=1,
                        help="Polling interval, seconds.  (Default: 1)")
    parser.add_argument('-v', dest='verbose', action='store_true', default=False,
                        help="Verbose output.  (Default: False)")
    args = parser.parse_args()
    # Launch application
    app = QApplication(sys.argv)
    window = TMon_GUI.TMon_GUI(args)
    window.show()
    sys.exit(app.exec_())
