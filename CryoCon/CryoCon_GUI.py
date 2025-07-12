#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
June 2023
QRFCP1/CryoCon/CryoCon_GUI.py

GUI for CryoCon.py

This is specific for the System, GMX-20, GMX-4 ISO 160 Vacuum Shroud from Advanced Research Systems, Inc.

DT-670B-SD Sensor
DT-670-SD-1.4L Sensor
50 Watt, 50 Ohm Heater

TODO: Check this
Source A -> sample temperature, influenced by main heater on loop 1 (50 Ohm, 50 W resistor)
Source B -> stage temperature

Requires the packages:
 - pyqt5
 - pyvisa
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
    QGridLayout,
    QStatusBar,
    QSizePolicy,
    QComboBox,
    QPushButton,
    QLineEdit
)
from PyQt5.QtGui import QIntValidator, QFont, QFontMetrics
import re
import pyvisa
# Import shared folder
sys.path.insert(0, '../shared')
import pandasWriter


class CryoCon_GUI(QWidget):
    def __init__(self, args):
        self.args = args
        ## Initialize GUI
        super().__init__()
        QtGui.QFontDatabase.addApplicationFont("./DSEG14Classic-Regular.ttf")
        self.setWindowTitle("Cryo-Con 22C Temperature Monitoring")
        # Create a QGridLayout instance
        layout = QGridLayout()
        # Label widget for input A
        self.nameA = QLabel("Sensor A: Sample")   
        self.nameA.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Do not let name labels scale vertically
        self.valueA = QLabel("~~~~~~")
        self.valueA.setAlignment(QtCore.Qt.AlignCenter)
        self.valueA.setMinimumHeight(100)
        self.valueA.setMinimumWidth(100)
        layout.addWidget(self.nameA, 0, 0)
        layout.addWidget(self.valueA, 1, 0)
        # Label widget for input B
        self.nameB = QLabel("Sensor B: Baseplate")   
        self.nameB.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.valueB = QLabel("~~~~~~")
        self.valueB.setAlignment(QtCore.Qt.AlignCenter)
        self.valueB.setMinimumHeight(100)
        self.valueB.setMinimumWidth(100)
        layout.addWidget(self.nameB, 0, 1)
        layout.addWidget(self.valueB, 1, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(0, 0)
        # Another QGridLayout for loop control
        loopLayout = QGridLayout()
        # Dropdown for loop type
        self.loopTypeObj = QComboBox()
        self.loopTypeObj.addItems(["OFF", "PID"])
        self.loopTypeObj.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.loopTypeObj.setCurrentText(self.args.loop_type)
        self.loopTypeObj.setEnabled(not self.args.monOnly)
        self.loopTypeObj.currentIndexChanged.connect(self.setLoopUpdateFlag)
        loopLayout.addWidget(self.loopTypeObj, 0, 0)
        # Dropdown for loop range
        self.loopRangeObj = QComboBox()
        self.loopRangeObj.addItems(["LOW", "MID", "HI"])
        self.loopRangeObj.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.loopRangeObj.setCurrentText(self.args.loop_range)
        self.loopRangeObj.setEnabled(not self.args.monOnly)
        self.loopRangeObj.currentIndexChanged.connect(self.setLoopUpdateFlag)
        loopLayout.addWidget(self.loopRangeObj, 0, 1)
        # Field for temperature set
        self.loopSetObj = QLineEdit()
        self.loopSetObj.setPlaceholderText("Loop set temp. [K]")
        self.loopSetObj.setValidator(QIntValidator(0, 999, self))
        self.loopSetObj.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.loopSetObj.setText(self.args.loop_setTemp)
        self.loopSetObj.setEnabled(not self.args.monOnly)
        self.loopSetObj.textChanged.connect(self.setLoopUpdateFlag)
        loopLayout.addWidget(self.loopSetObj, 0, 2)
        # Push button to configure
        self.loopUpdate = QPushButton("Set Loop")
        self.loopUpdate.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.loopUpdateFlag = False # Flag to allow or disallow sending loop commands to insutrument, this prevents wearing out of relays in the machine.
        self.loopUpdate.setEnabled(not (self.args.monOnly or not self.args.control) and self.loopUpdateFlag)    # Update button state
        self.loopUpdate.clicked.connect(self.setLoop)
        loopLayout.addWidget(self.loopUpdate, 0, 3)
        # Label to monitor heater power
        self.loopStatus = QLabel("Heater Power Output: --.- %")
        self.loopStatus.setAlignment(QtCore.Qt.AlignCenter)
        loopLayout.addWidget(self.loopStatus, 1, 0, 1, -1)
        layout.addLayout(loopLayout, 2, 0, 1, -1, alignment=QtCore.Qt.AlignCenter)
        layout.setRowStretch(2, 0)
        # Status bar
        self.statusObj = QStatusBar()
        self.statusObj.showMessage('Ready')
        self.statusObj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.statusObj, 3, 0, 1, -1)
        layout.setRowStretch(3, 0)
        # Set the layout on the application's window
        self.setLayout(layout)
        # Show window
        self.resize(1200,150)
        ## Initialize instrument
        if not self.args.noConnect:
            rm = pyvisa.ResourceManager()
            self.cc = rm.open_resource(self.args.addr)
            self.cc.read_termination = '\n'
            self.cc.write_termination = '\n'
            self.id = self.cc.query('*IDN?')
            print(self.id)
            # Setup-specific instrument initialization
            self.cc.query("SYSTem:LOCKout ON")
            #self.cc.query("SYSTem:BEEP 0.25")
            self.cc.query("INPut A:UNITs K")
            self.cc.query("INPut B:UNITs K")
            self.cc.query("INPut A:SENSor 2")       # Lakeshore DT-670
            self.cc.query("INPut B:SENSor 2")
            if self.args.control: self.cc.query("control")
            self.cc.query("loop 1:source A") 
            self.cc.query("loop 1:load 50")
            self.cc.query("loop 1:type "+self.loopTypeObj.currentText())
            self.cc.query("loop 1:range "+self.loopRangeObj.currentText())
            self.cc.query("loop 1:setpt "+self.loopSetObj.text())
            try:
                self.cc.clear()
            except:
                pass
            # Disable D control (DGain was 7.5).  PI control recomended with diode type sensors.
            #self.cc.query("loop 1:DGA 0")
            self.cc.query("loop 1:PGA "+str(self.args.pgain))
            self.cc.query("loop 1:IGA "+str(self.args.igain))
            self.cc.query("loop 1:DGA "+str(self.args.dgain))
            print("==== PID parameters ====")
            print("P = "+str(self.cc.query("loop 1:PGA?")))
            print("I = "+str(self.cc.query("loop 1:IGA?")))
            print("D = "+str(self.cc.query("loop 1:DGA?")))
        else:
            self.cc = None
            self.id = "None"
        ## Initialize pandas
        if not self.args.disableOutfile:
            userCommentsDict = {"noconnect": self.args.noConnect,
                                "instrid": self.id,
                                "userComments": self.args.userComments,
                                "sensorA": self.nameA.text(),
                                "sensorB": self.nameB.text()}
            self.pw = pandasWriter.pandasWriter(userComments=userCommentsDict, csvFilePrefix=self.args.filenamePrefix)
        else:
            self.pw = None
        ## Initialize and start timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.measure)
        self.timer.start(int(self.args.pollingInterval)*1000)
        # Async flags to prevent accessing serial after it's closed by closeEvent()
        self.isMeasuring = False
        self.exit = False
        self.measidx = 0
        # First measurement
        self.measure()
        
    # Flag to allow or disallow sending loop commands to insutrument, this prevents wearing out of relays in the machine.
    def setLoopUpdateFlag(self):
        self.loopUpdateFlag = True
        self.loopUpdate.setEnabled(not (self.args.monOnly or not self.args.control) and self.loopUpdateFlag)    # Update button state

    def setLoop(self):
        if not self.args.noConnect:
            # Only send command if setting was changed.  This prevents wearing out of relays.
            if self.loopUpdateFlag:
                self.cc.query("loop 1:type "+self.loopTypeObj.currentText())
                self.cc.query("loop 1:range "+self.loopRangeObj.currentText())
                self.cc.query("loop 1:setpt "+self.loopSetObj.text())
                self.loopUpdateFlag = False
                self.loopUpdate.setEnabled(not (self.args.monOnly or not self.args.control) and self.loopUpdateFlag)    # Update button state

                

    def measure(self):
        if not self.exit:
            # Set async flag so as to not close the port if user exits until a measurement is finished
            self.isMeasuring = True
            # Take timestamp in seconds since epoch (Jan 1, 1970 00:00:00 UTC)
            self.now = float(time.time())
            # Query instrument
            if not self.args.noConnect:
                sensorA = self.str2float(self.cc.query('input? a'))
                sensorB = self.str2float(self.cc.query('input? b'))
                loopRange = self.cc.query("loop 1:range?")
                loopSet = self.str2float(self.cc.query("loop 1:setpt?"))
                loopType = self.cc.query("loop 1:type?")
                loopReadBackPwr = self.str2float(self.cc.query("loop 1:HTRRead?"))/100
            else:
                sensorA = 999.999
                sensorB = 999.999
                loopRange = "LOW"
                loopSet = 1
                loopType = "OFF"
                loopReadBackPwr = 0
            '''
            # Debug
            print(self.str2float(sensorA))
            print(self.str2float(sensorB))
            print(loopRange)
            print(self.str2float(loopSet))
            print(loopType)
            print(self.str2float(loopReadBackPwr))
            print("==")
            '''
            ## Save data
            if not self.args.disableOutfile:
                dataDict = {
                    "time": self.now,
                    "sensorA": sensorA,
                    "sensorB": sensorB,
                    "loopRange": loopRange,
                    "loopSet": loopSet,
                    "loopType": loopType,
                    "loopReadBackPwr": loopReadBackPwr
                    }
                self.pw.appendData(dataDict)
            ## Update labels
            self.valueA.setText("{:+03.3f} ".format(sensorA)+u" \u00b0K")
            self.valueB.setText("{:+03.3f} ".format(sensorB)+u" \u00b0K")
            self.loopStatus.setText(self.nameA.text()+" \u27f9 Heater Power Output: {:3.1%}".format(loopReadBackPwr))
            
            ## Print status
            if self.pw == None:
                self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.id + ', No Output File')
            else:
                self.statusObj.showMessage('Meas. '+ str(self.measidx) + ', '+self.id + ', ' + self.pw.csvFilepath())
            
            ## Update last measurement file
            with open("sensorA_last", "w") as f: f.write("{:03.3f}".format(sensorA))
            with open("sensorB_last", "w") as f: f.write("{:03.3f}".format(sensorB))

            ## Poll control file if specified
            if self.args.controlfile is not None:
                with open(self.args.controlfile, "r") as f:
                    firstline = f.readline().strip('\n').split(",")
                    # Update GUI elements
                    # First element: control type
                    # Second element: control range
                    # Third element: control setting
                    self.loopTypeObj.setCurrentText(firstline[0])
                    self.loopRangeObj.setCurrentText(firstline[1])
                    self.loopSetObj.setText(firstline[2])
                    # Send to insturment
                    self.setLoop()
            
            ## Update flag
            self.isMeasuring = False
            self.measidx = self.measidx + 1



    # This function is invoked each time the window is resized.
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.resizeEvent(event)
    def resizeEvent(self, event):
        numChars = 8   # Number of characters to fit onto the line
        # Calculate maximum horizontal space
        #sizeWidthMax = self.valueA.width()/numChars
        sizeWidthMax = self.valueA.width()/len(self.valueA.text())
        # maximum vertical space is same as self.labelObj.height() since it's only one row
        # Cast to int for roudning otherwise css may not be happy
        fontMax = int(min(sizeWidthMax, self.valueA.height()/2))
        #style = "background-color: white; color: green; font-family: DSEG14Classic; font-size: "+str(fontMax)+"px"
        style = "background-color: white; color: green"        
        self.valueA.setFont(QFont("DSEG14 Classic", fontMax))
        self.valueB.setFont(QFont("DSEG14 Classic", fontMax))     
        self.valueA.setStyleSheet(style)
        self.valueB.setStyleSheet(style)
        
        
    # This function is invoked if user tried to close the window
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.closeEvent(event)
    def closeEvent(self, event):
        self.exit = True
        # Do not close when measurement in progress
        while self.isMeasuring:
            pass
        # Instrument de-initialization routine
        if not self.args.noConnect:
            self.cc.query("stop")
            self.cc.query("SYSTem:LOCKout OFF")
            self.cc.close()
        if not self.args.disableOutfile: self.pw.writeCSV()
        
    # Converts a string to float, stripping away things like % signs or K (kelvins)
    def str2float(self, instr):
        return float(re.findall(r"[-+]?(?:\d*\.*\d+)", instr)[0])

    
    
    
    
    
    
    
    
