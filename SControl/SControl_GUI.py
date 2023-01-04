#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SControl/SControl_GUI.py

GUI to implement slow-control settings

Requires the packages:
 - pyqt5
 - python3-bitstring (via system package manager)
 - libusb (via system package manager)
 - pyftdi (see manual for installation and setup instructions)
'''

import sys
import os
import time
import math
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
# Application dependent dependencies
import configurations
import ftdispi
from bitstring import BitArray
import configparser

class SControl_GUI(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        # Initiate configurations
        self.cfg = configurations.configurations(self.args.cfgFile)
        self.cfgPrevBits = self.cfg.toBits()    # Used in determining which menu items to highlight
        # Populate GUI
        self.setCentralWidget(self.populateGUI())
        # Set up file path
        self.filepathWidget.setText(os.path.abspath(self.args.cfgFile))
        self.resize(100, 100)
        # Initiate hardware
        self.spi = ftdispi.ftdispi(self.args.addr, self.args.noConnect)
        # Flush shift register.  Program in a bit string of length that is equal to or greater than the shift register size.  Discard the output.
        bitlen = len(self.cfg.toBits())
        flushBits = BitArray(uint=0,length=bitlen)
        self.spi.query(flushBits.bin)
        # Initial programming.  
        # A 'query' is a full-duplex, atomic transaction.  It programs in the bits and reads back the bits that were there previously.
        # So to program and read back the bits, do two queries back to back:
        # the first query programs the bits and reads back the previous bits (which could be garbage)
        # The second query programs the same bits and reads back the bits from the first query (which should be valid) 
        returnBits = self.spi.query(self.cfg.toBits())
        returnBits = self.spi.query(self.cfg.toBits())
        # Check if the read back is valid
        compare = self.cfg.compare(returnBits)[0]
        if False in compare:
            self.showError("Readback incorrect!  Initial programming.  Is the chip powered on?")
        if self.args.batch:
            sys.exit()
        

    def showError(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()


    def populateGUI(self):
        ## Populates GUI according to configuration items.  Everything is nested inside a single QGridLayout.
        # Aspect ratio: approximate number of rows to number of columns
        aspectRatio = 3
        ## Get number of rows and columns needed to populate menu items.  Each row,col represents a pair of QLabel and a QSpinBox/QPlainTextEdit/QCheckBox/QComboBox item.
        numMenuRows = int(math.ceil(math.sqrt(self.cfg.numFields())*aspectRatio))
        numMenuCols = numMenuRows
        ## Main GUI widget: QGridLayout
        mainWidget = QWidget()
        mainWidget.setLayout(QGridLayout())
        mainLayout = mainWidget.layout()
        ## Menu items: QFormLayout is used to fill row-wise.
        # Multiple QFormLayout's run from the left-most column to the right-most column
        # Numbering of elements increases up to down, left to right.
        self.labelList = []
        self.menuList = []
        self.ptrList = []
        for i in range(numMenuCols):
            formLayout = QFormLayout()
            for j in range(numMenuRows):
                ptr = int(i * numMenuCols + j)
                # Check for under-filled column
                if ptr < self.cfg.numFields():
                    # Add label object
                    fieldtype = self.cfg.typeList[ptr]
                    labelObj = QLabel(self.cfg.labelList[ptr])
                    # Hide this field otherwise it will show up with a label but no field
                    if fieldtype == "hidden":
                        labelObj.hide()
                    # Add menu item
                    menuObj = self.makeMenuElement(ptr)
                    # Add objects into list
                    self.labelList.append(labelObj)
                    self.menuList.append(menuObj)
                    self.ptrList.append(ptr)
                    # Initialize value
                    self.setMenuElement(ptr, self.cfg.valueList[ptr])
                    # Add objects into layout
                    formLayout.addRow(labelObj, menuObj)
            if formLayout.rowCount() > 0:
                # Add form layout into main widget
                mainLayout.addLayout(formLayout, 0, 2*i)
            # Construct a vertical line (the same widget cannot have multiple parents, hence this widget is generated dynamically in this loop
            # Only put a vline if another column will be added
            if ptr < self.cfg.numFields():
                vline = QFrame()
                vline.setFrameShape(QFrame.VLine)
                vline.setFrameShadow(QFrame.Raised)
                vline.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
                vline.setLineWidth(3)
                mainLayout.addWidget(vline, 0, (2*i)+1)
        ### hline
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Raised)
        hline.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        hline.setLineWidth(3)
        mainLayout.addWidget(hline, 1, 0, 1, -1, QtCore.Qt.AlignBottom)
        ### Load/save buttons
        self.loadBtn = QPushButton("&Load...")
        self.saveBtn = QPushButton("&Save...")
        self.loadBtn.clicked.connect(self.loadCfg)
        self.saveBtn.clicked.connect(self.saveCfg)
        loadsaveLayout = QGridLayout()
        loadsaveLayout.addWidget(self.loadBtn, 0, 0)
        loadsaveLayout.addWidget(self.saveBtn, 0, 1)
        mainLayout.addLayout(loadsaveLayout, 2, 0, 1, -1, QtCore.Qt.AlignHCenter)
        ### File path field
        self.filepathWidget = QLineEdit(self)
        self.filepathWidget.setReadOnly(True)
        self.filepathWidget.setStyleSheet("background-color: silver; font-style: italic;")
        mainLayout.addWidget(self.filepathWidget, 3, 0, 1, -1)
        ### FTDI buttons
        self.readBtn = QPushButton("&Read (Overwrite)")
        self.progBtn = QPushButton("&Program")
        self.verifyBtn = QPushButton("&Verify")
        self.readBtn.clicked.connect(self.ftdiRead)
        self.progBtn.clicked.connect(self.ftdiProg)
        self.verifyBtn.clicked.connect(self.ftdiVerify)
        ftdiLayout = QGridLayout()
        ftdiLayout.addWidget(self.readBtn, 0, 0)
        ftdiLayout.addWidget(self.progBtn, 0, 1)
        ftdiLayout.addWidget(self.verifyBtn, 0, 2)
        mainLayout.addLayout(ftdiLayout, 4, 0, 1, -1, QtCore.Qt.AlignHCenter)
        return mainWidget

    # Creates and returns a Qt GUI menu item for the 'ptr' (int) element in the configurations class
    # Initializes the GUI menu item to the value in configurations class.
    def makeMenuElement(self, ptr):
        field = self.cfg.fieldList[ptr]
        width = int(self.cfg.widthList[ptr])
        value = self.cfg.valueList[ptr]
        fieldtype = self.cfg.typeList[ptr]
        menuObj = None
        # Set up validator
        regex = QtCore.QRegExp("^[0-1]*$")
        validator = QtGui.QRegExpValidator(regex)
        # Set up manu object
        if fieldtype == "bool":
            menuObj = QCheckBox(self)
            menuObj.stateChanged.connect(lambda:self.guiStateChanged())
            menuObj.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        elif fieldtype == "int":
            menuObj = QSpinBox(self)
            menuObj.setMinimum(0)
            menuObj.setMaximum(int((2**width)-1))
            menuObj.valueChanged.connect(lambda: self.guiStateChanged())
            menuObj.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
            menuObj.setMinimumWidth(10 * (len(str((2**width)-1))+3))  # Set a minimum width for the field, assuming 12 px font ...  Add additional size for the up/down buttons that is part of QSpinBox.
        elif fieldtype == "bitstring":
            menuObj = QLineEdit(self)
            menuObj.setValidator(validator)
            menuObj.setMaxLength(width)
            menuObj.textChanged.connect(lambda: self.guiStateChanged())
            menuObj.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
            menuObj.setMinimumWidth(10 * width)  # Set a minimum width for the field, assuming 12 px font ...
        elif fieldtype == "enum":
            menuObj = QComboBox(self)
            menuObj.addItems(self.cfg.getEnum(field))
            menuObj.currentIndexChanged.connect(lambda: self.guiStateChanged())
            menuObj.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
            menuObj.setMinimumWidth(10 * max([len(i) for i in self.cfg.getEnum(field)]))  # Set a minimum width for the field, assuming 12 px font ...
        elif fieldtype == "hidden":
            menuObj = QLineEdit(self)
            menuObj.setReadOnly(True)
            menuObj.hide()
        else:
            menuObj = QLineEdit(self)
            menuObj.setValidator(validator)
            menuObj.setMaxLength(width)
            menuObj.setReadOnly(True)
            #menuObj.setEnabled(False)
            menuObj.textChanged.connect(lambda: self.guiStateChanged())
            menuObj.setMinimumWidth(10*width)       # Set a minimum width for the field, assuming 12 px font ...
            # To distinguish read only
            menuObj.setStyleSheet("background-color: silver; font-style: italic;")
        return menuObj

    # Accesses a GUI menu item and returns its value
    # Input: ptr (int), index of the menu item in the configurations class lists
    # Output: string of bits of the appropriate width
    def getMenuElement(self, ptr):
        fieldtype = self.cfg.typeList[ptr]
        menuObj = self.menuList[ptr]
        width = int(self.cfg.widthList[ptr])
        if fieldtype == "bool":
            if menuObj.isChecked():
                return '1'
            else:
                return '0'
        elif fieldtype == "int":
            value = menuObj.value()
            value = BitArray(uint=value, length=width)
            return value.bin
        elif fieldtype == "bitstring":
            value = menuObj.text()
            # Zero extend where appropriate
            value = BitArray(bin=value).uint
            value = BitArray(uint=value, length=width)
            return value.bin
        elif fieldtype == "enum":
            value = menuObj.currentIndex()
            value = BitArray(uint=value, length=width)
            return value.bin
        elif fieldtype == "hidden":
            value = menuObj.text()
            # Zero extend where appropriate
            value = BitArray(bin=value).uint
            value = BitArray(uint=value, length=width)
            return value.bin
        else:
            value = menuObj.text()
            # Zero extend where appropriate
            value = BitArray(bin=value).uint
            value = BitArray(uint=value, length=width)
            return value.bin


    # Sets a GUI menu item
    # Input: ptr (int) index of the menu item in the configurations class lists; value (string) string of bits
    # Output: none
    def setMenuElement(self, ptr, value):
        fieldtype = self.cfg.typeList[ptr]
        menuObj = self.menuList[ptr]
        if fieldtype == "bool":
            if value == '1':
                menuObj.setChecked(True)
            else:
                menuObj.setChecked(False)
        elif fieldtype == "int":
            value_uint = BitArray(bin=value).uint
            menuObj.setValue(value_uint)
        elif fieldtype == "bitstring":
            menuObj.setText(value)
        elif fieldtype == "enum":
            value_uint = BitArray(bin=value).uint
            menuObj.setCurrentIndex(value_uint)
        elif fieldtype == "hidden":
            menuObj.setText(value)
        else:
            menuObj.setText(value)
        return None

    # Highlights a manu item if value is True.  Otherwise, it restores it to system defaults.
    # Input: ptr (int) index of the menu item, value (boolean) whether to highlight or restore, and level of severity (warn or error)
    def highlightMenuElement(self, ptr, value, level="warn"):
        labelObj = self.labelList[ptr]
        if value:
            if level == "warn":
                labelObj.setStyleSheet("background-color: yellow; ")
            elif level == "error":
                labelObj.setStyleSheet("background-color: red; ")
        else:
            labelObj.setStyleSheet("")

    # What to do if a GUI item state has changed.
    # Synchronize configurations state to GUI state
    # Highlight menu item if current selection differs from previously programmed bits
    def guiStateChanged(self):
        # Synchronize configurations state to GUI state
        for ptr in self.ptrList:
            menuValue = self.getMenuElement(ptr)
            cfgValue = self.cfg.valueList[ptr]
            if menuValue != cfgValue:
                # Flush to configurations class
                self.cfg.set(self.cfg.fieldList[ptr], menuValue)
        # Highlight menu items where they are different from the previously programmed bits.
        # Do this comparison after configurations state has been synchronized
        diffFields = self.cfg.compare(self.cfgPrevBits)[0]
        for ptr in self.ptrList:
            if diffFields[ptr] is False:
                self.highlightMenuElement(ptr, True, level="warn")
        return None

    # Prompts user to browse and saves current configuration to a file
    def saveCfg(self):
        fileName = QFileDialog.getSaveFileName(self, "Save Config")
        if fileName[0] is not '':
            try:
                self.cfg.writeToFile(fileName[0])
            except ValueError:
                print("Cannot overwrite initial cfg!  Configurations did not save.")
                return None
            self.filepathWidget.setText(os.path.abspath(fileName[0]))

    # Prompts user to browse and loads cfg from file
    def loadCfg(self):
        fileName = QFileDialog.getOpenFileName(self, "Open Config")
        if fileName[0] is not '':
            fields, values = self.cfg.readFromFile(fileName[0])
            self.filepathWidget.setText(os.path.abspath(fileName[0]))
            # Synchronize GUI elements to configurations state
            for ptr in self.ptrList:
                self.setMenuElement(ptr, values[ptr])
            diffFields = self.cfg.compare(self.cfgPrevBits)[0]
            for ptr in self.ptrList:
                self.highlightMenuElement(ptr, not diffFields[ptr], level="warn")
        return None

    # Reads from FTDI SPI
    def ftdiRead(self):
        readBitsList = self.ftdiVerify()
        for ptr in self.ptrList:
            self.setMenuElement(ptr, readBitsList[ptr])
        return None

    # Programs FTDI SPI using current configurations state
    def ftdiProg(self):
        # Clear highlights from changing menu items
        self.cfgPrevBits = self.cfg.toBits()
        for ptr in self.ptrList:
            self.highlightMenuElement(ptr, False)
        # Program.  See the class initializer function for more info.
        returnBits = self.spi.query(self.cfg.toBits())
        returnBits = self.spi.query(self.cfg.toBits())
        # Check if the read back is valid
        compare = self.cfg.compare(returnBits)[0]
        if False in compare:
            self.showError("Readback incorrect!")
        for ptr in self.ptrList:
            if compare[ptr] is False:
                self.highlightMenuElement(ptr, True, level="error")
        return None

    # Verifies FTDI SPI against current configurations state
    def ftdiVerify(self):
        # Clear highlights from changing menu items
        self.cfgPrevBits = self.cfg.toBits()
        for ptr in self.ptrList:
            self.highlightMenuElement(ptr, False)
        # First query: program current bits as bogus bits; read back present configuration
        readBits = self.spi.query(self.cfg.toBits())
        # Second query: program read back configuration to restore state
        returnBits = self.spi.query(readBits)
        # Compare read bits against current configurations
        compare, readBitsList = self.cfg.compare(readBits)
        if False in compare:
            self.showError("Read bits are different from GUI!")
        for ptr in self.ptrList:
            if compare[ptr] is False:
                self.highlightMenuElement(ptr, True, level="error")
        return readBitsList



