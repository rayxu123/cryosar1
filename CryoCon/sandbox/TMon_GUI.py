#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/TMon/TMon_GUI.py

GUI for TMon.py

Requires the packages:
 - pyqt5
 - pyserial
 - pandas
'''


import sys
import time
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QStatusBar,
    QSizePolicy
)
# Import shared folder
sys.path.insert(0, '../shared')
import prologixUSBGPIB
import pandasWriter


class TMon_GUI(QWidget):
    def __init__(self, args):
        self.args = args
        ## Initialize GUI
        super().__init__()
        QtGui.QFontDatabase.addApplicationFont('DSEG14Classic-Regular.ttf')
        self.setWindowTitle("HP 3458A RTD100 Temperature Monitoring")
        # Create a QGridLayout instance
        layout = QVBoxLayout()
        # Label widget
        self.labelObj = QLabel("~~~~~~~~~~~~")
        self.labelObj.setAlignment(QtCore.Qt.AlignCenter)
        # Status bar
        self.statusObj = QStatusBar()
        self.statusObj.showMessage('Ready')
        # Set minimum size policy
        self.labelObj.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.labelObj.setMinimumHeight(100)
        self.labelObj.setMinimumWidth(100)
        # Add widgets; do not stretch status bar
        layout.addWidget(self.labelObj, 1)
        layout.addWidget(self.statusObj, 0)
        # Set the layout on the application's window
        self.setLayout(layout)
        # Show window
        self.resize(600,150)
        ## Initialize GPIB, perform one measurement to intialize instrument
        self.gpib = prologixUSBGPIB.prologixUSBGPIB(noConnect=self.args.noConnect, verbose=self.args.verbose)
        self.gpib.addInstr("hp3458a", self.args.addr)
        self.gpib.write("hp3458a", "PRESET NORM")   # Preset normal
        self.gpib.write("hp3458a", "TRIG HOLD")     # Pause data taking otherwise gpib input buffer will be filled
        self.gpib.resetBuffers()
        # Query twice to clear out crap in the hardware buffer
        self.gpibid = self.gpib.query("hp3458a","ID?")
        self.gpibid = self.gpib.query("hp3458a","ID?")
        if self.args.twowire:
            self.gpib.write("hp3458a", "OHM 200")
        else:
            self.gpib.write("hp3458a", "OHMF 200")
        self.gpib.query("hp3458a", "TRIG SGL")
        self.gpib.resetBuffers()
        ## Initialize pandas
        if self.args.disableOutfile:
            userCommentsDict = {"twowire": self.args.twowire,
                                "noconnect": self.args.noConnect,
                                "gpibidn": self.gpibid,
                                "userComments": self.args.userComments}
            self.pw = pandasWriter.pandasWriter(userComments=userCommentsDict, csvFilePrefix=self.args.filenamePrefix)
        else:
            self.pw = None
        ## Initialize and start timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.measure)
        self.timer.start(int(self.args.pollingInterval)*1000)
        # Async flags to prevent accessing serial after it's closed by closeEvent()
        self.measure = False
        self.exit = False
        self.measidx = 0


    def measure(self):
        if not self.exit:
            # Set async flag so as to not close the port if user exits until a measurement is finished
            self.measure = True
            # Take timestamp in seconds since epoch (Jan 1, 1970 00:00:00 UTC)
            self.now = float(time.time())
            ### Commented out so to not wear out relays
            # Take instrument temp
            #self.instrTemp = float(self.gpib.query("hp3458a", "TEMP?"))
            ###
            self.instrTemp = float("nan")
            ###
            # Take resistance
            self.gpib.write("hp3458a", "MATH OFF")
            if self.args.twowire:
                self.ohm = float(self.gpib.query("hp3458a", "TRIG SGL"))
            else:
                self.ohm = float(self.gpib.query("hp3458a", "TRIG SGL"))
            # Take temperature sensor reading
            self.gpib.write("hp3458a", "MATH CRTD85")
            self.sensorTemp = float(self.gpib.query("hp3458a", "TRIG SGL"))
            # Save data
            if self.args.disableOutfile:
                dataDict = {
                    "time": self.now,
                    "ohm": self.ohm,
                    "rtd_tempc": self.sensorTemp,
                    "instr_tempc": self.instrTemp
                    }
                self.pw.appendData(dataDict)
            # display temperature
            dispString = "{:+08.5f} ".format(self.sensorTemp)+u" \u00b0C"
            self.labelObj.setText(dispString)
            # Print status
            if self.args.twowire:
                if self.pw == None:
                    self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.gpibid + ', Two-wire, No Output File')
                else:
                    self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.gpibid + ', Two-wire, ' + self.pw.csvFilepath())
            else:
                if self.pw == None:
                    self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.gpibid + ', Four-wire, No Output File')
                else:
                    self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.gpibid + ', Four-wire, ' + self.pw.csvFilepath())
            # Update flag
            self.measure = False
            self.measidx = self.measidx + 1



    # This function is invoked each time the window is resized.
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.resizeEvent(event)
    def resizeEvent(self, event):
        numChars = 12   # Number of characters to fit onto the line
        # Calculate maximum horizontal space
        sizeWidthMax = self.labelObj.width()/numChars
        # maximum vertical space is same as self.labelObj.height() since it's only one row
        # Cast to int for roudning otherwise css may not be happy
        fontMax = int(min(sizeWidthMax, self.labelObj.height()))
        style = "background-color: white; color: green; font-family: DSEG14Classic; font-size: "+str(fontMax)+"px"
        self.labelObj.setStyleSheet(style)
        
    # This function is invoked if user tried to close the window
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.closeEvent(event)
    def closeEvent(self, event):
        self.exit = True
        while self.measure:
            pass
        self.gpib.close()
        if self.args.disableOutfile: self.pw.writeCSV()


    
    
    
    
    
    
    
    
