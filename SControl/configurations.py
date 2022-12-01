#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SControl/configurations.py

Implements digital slow-control via INI-like configuration files.

Requires the packages:
 - python3-bitstring (via system package manager)



 - libusb (via system package manager)
 - pyftdi (see manual for installation and setup instructions)
'''

import os, sys
import datetime
import configparser
from bitstring import BitArray



class configurations:
    # Initializes the class from a INI-like configuration file.  The file must contain a category 'Default' with key 'order'.
    # 'order' is a comma separated list of other section names, which are called fields.  The order of comma-separated elements are MSB to LSB.
    #
    # Each field has the following keys: width (int, number of bits in this field), value (string of bits, from MSB to LSB), type (string), and label (string).  Type can be any of the following:
    #   'bool' -> GUI: checkbox
    #   'int' -> GUI: QSpinBox
    #   'bitstring' -> GUI: QPlainTextEdit
    #   'enum' -> GUI: QComboBox
    #   'none' (or any other type not listed) -> GUI: hidden
    # Label is a string that describes the field, purely for GUI purposes.
    # For type 'enum', there is an additional key 'options' which is a comma-separated string that list the enumerated values from the minimum index to the maximum index.
    #
    # Once a configurations class is initialized, only 'value' may be changed.
    def __init__(self, cfgFile):
        self.cfgFile = os.path.abspath(cfgFile)
        self.cfg = configparser.ConfigParser()
        self.cfg.read(self.cfgFile)
        self.order = self.cfg['Default']['order'].split(",")

    # Checks for input sanity.
    # Input: val (string of bits), width (int)
    # Output: val with zero padding to match width if sane, otherwise an exception is raised
    def check(self, val, width):
        obj_uint = BitArray(bin=val).uint
        obj_bin = BitArray(uint=obj_uint, length=width).bin
        return obj_bin

    # Retrieves configurations.
    # Input: list of fields.  Or if no input, assumes all fields in order.
    # Return: lists fields,width,value,type,label.  List elements are of type strings.
    def get(self, fieldList=None):
        if fieldList is None:
            fieldList = self.order
        widthList = []
        valueList = []
        typeList = []
        labelList = []
        for field in fieldList:
            widthList.append(self.cfg[field]['width'])
            valueList.append(self.cfg[field]['value'])
            typeList.append(self.cfg[field]['type'])
            labelList.append(self.cfg[field]['label'])
        return fieldList,widthList,valueList,typeList,labelList

    # Sets a value to a field
    # Input: list of field(s), list of value(s).  List elements are of type strings.
    # Return: none
    def set(self, fieldList, valueList):
        for field,value in zip(fieldList, valueList):
            self.cfg[field]['value'] = self.check(value, int(self.cfg[field]['width']))

    # Gets values for enumerated objects
    # Input: field name
    # Return: list of options from the least index to maximum index.  Empty list if not an enum type.
    def getEnum(self, field):
        if self.cfg[field]['type'] == 'enum':
            return self.cfg[field]['options'].split(",")
        else:
            return []

    # Returns a string of bits from MSB to LSB according to the order list
    def toBits(self):
        valueList = []
        for field in self.order:
            valueList.append(self.cfg[field]['value'])
        return "".join(valueList)

    # Gets number of bits in the class
    def len(self):
        return len(self.toBits())

    # Gets number of fields
    def numFields(self):
        return len(self.order)

    # Updates values from another config file according to the initialized order list
    # Input: path to file
    # Output: none
    def setFromFile(self, otherCfgFile):
        otherCfg = configparser.ConfigParser()
        otherCfg.read(otherCfgFile)
        for field in self.order:
            self.cfg[field]['value'] = self.check(otherCfg[field]['value'], int(self.cfg[field]['width']))

    # Writes current config to file.  For safety one cannot overwrite the cfg file the class was initialized with.
    # Input: path to file
    # Output: none
    def writeToFile(self, cfgFilepath):
        self.NewCfgFilepath = os.path.abspath(cfgFilepath)
        if self.NewCfgFilepath == self.cfgFile:
            raise ValueError("Cannot overwrite cfg file that was used in class initialization!")
        else:
            with open(self.NewCfgFilepath, 'w') as newCfgFile:
                now = datetime.datetime.now()
                now = now.strftime('%Y-%m-%d %H:%M:%S')
                newCfgFile.write("# "+self.NewCfgFilepath+"\n")
                newCfgFile.write("# YYYY-MM-DD HH:MM:SS = "+now+"\n")
                self.cfg.write(newCfgFile)

    # Compares an input bit string against the current configuration
    # Input: string of bits
    # Return: list of booleans corresponding to the order list.  True if values match, otherwise false.
    def compare(self, inBits):
        compareList = []
        ptr = 0     # Position of the MSB currently being checked
        for field in self.order:
            width = int(self.cfg[field]['width'])
            valueCfg = self.cfg[field]['value']
            valueInBits = inBits[ptr:(ptr+width)]
            ptr = ptr + width
            if valueCfg == valueInBits:
                compareList.append(True)
            else:
                compareList.append(False)
            # Last field: check if length of bits are same.  Set last boolean to false if not.
            if (field == self.order[-1]) and (len(inBits) != self.len()):
                compareList[-1] = False
        return compareList


