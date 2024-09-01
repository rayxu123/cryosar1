#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
June 2023
QRFCP1/CryoCon/CryoCon.py

Stand-alone monitoring and control for CryoCon 22C

Requires the packages:
 - pyqt5
 - pyvisa
 - pandas
'''

import sys
import argparse
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
import CryoCon_GUI
import pyvisa


if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description='Remote Control for Cryo-Con 22C.')
    parser.add_argument('-a', dest='addr', action='store', default="ASRL4::INSTR", help="VISA resource.  (Default: ASRL4::INSTR)")
    parser.add_argument('-d', dest='disableOutfile', action='store_true', default=False, help="Disable data logging.  (Default: False)")
    parser.add_argument('-f', dest='filenamePrefix', action='store', default='',
                        help="Filename Prefix, cannot be used with -d.  (Default: None)")
    parser.add_argument('-c', dest='userComments', action='store', default='',
                        help="User comments, cannot be used with -d.  (Default: None)")
    parser.add_argument('-n', dest='noConnect', action='store_true', default=False,
                        help="No connect/demo mode, useful for debugging.  (Default: False)")
    parser.add_argument('-p', dest='pollingInterval', action='store', default=1,
                        help="Polling interval, seconds.  (Default: 1)")
    parser.add_argument('-v', dest='verbose', action='store_true', default=False,
                        help="Verbose output.  (Default: False)")
    parser.add_argument('-m', dest='monOnly', action='store_true', default=False,
                        help="Monitoring only.  Do not let user interactively change settings.  (Default: False)")
    parser.add_argument('--control', dest='control', action='store_true', default=True,
                        help="Start in control mode.  Necessary for any loop activities.  (Default: True)")
    parser.add_argument('--controlfile', dest='controlfile', action='store', default=None,
                        help="Path to a local file to receive control instructions.  Polled at the same measurement polling interval.  Must be in control mode.  The contents of this file specifies values for --loop_type, --loop_range, and --loop_set separated by comma.  Settings in the file override any of the below arguments.  (Default: None)")
    parser.add_argument('--loop_set', dest='loop_setTemp', action='store', default="110",
                        help="Loop set temperature.  Integer, units in Kelvin.  (Default: 110)")
    parser.add_argument('--loop_type', dest='loop_type', action='store', default="PID",
                        help="Loop type.  See manual.  OFF or PID.  (Default: PID)")
    parser.add_argument('--loop_range', dest='loop_range', action='store', default="HI",
                        help="Loop range.  See manual.  HI, MID, LOW.  (Default: HI)")
    parser.add_argument('-l', dest='listVISA', action='store_true', default=False,
                        help="List VISA resources and exit.")
    parser.add_argument('--pgain', dest='pgain', action='store', default=5,
                        help="P-gain.  (Default: 5)")
    parser.add_argument('--igain', dest='igain', action='store', default=60,
                        help="I-gain.  (Default: 60)")
    parser.add_argument('--dgain', dest='dgain', action='store', default=7.5,
                        help="D-gain.  Only PI-control is recomended with diode sensors.  (Default: 7.5)")
    args = parser.parse_args()
    if ((args.controlfile is not None) and (args.control is False)):
        print("Application must be in control mode to receive control instructions!")
        exit()
    if args.listVISA:
        pyvisa.ResourceManager('@py')
        rm = pyvisa.ResourceManager()
        print(rm.list_resources())
    else:
        # Launch application
        app = QApplication(sys.argv)
        window = CryoCon_GUI.CryoCon_GUI(args)
        window.show()
        sys.exit(app.exec_())
