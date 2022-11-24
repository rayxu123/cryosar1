#!/bin/python
'''
Ray Xu 
Nov 2022
cryosar1/TMon/prologixUSBGPIB.py

Wrapper class for Prologix USB-GPIB module.

Requires the packages:
 - pyserial
'''


import os.path
import serial
import serial.tools.list_ports
import sys
import time

class prologixUSBGPIB:
    def __init__(self, noConnect=False, serialResourcePath=''):
        # Initialize state variables
        self.prevAddr = 32
        self.noConnect = noConnect
        # Initialize instrument list
        self.instrList = {}
        # Initialize GPIB controller
        if not self.noConnect:
            if serialResourcePath:
                # TODO: Resource name manually specified
                s = serial.Serial(serialResourcePath, 9600, timeout=0.5)
            else:
                pass
                # TODO: Attempt to automatically find resource name
        
    # Add instrument into dictionary
    def addInstr(self, name, addr):
        # Adds an instrument 'name' with GPIB address 'addr'
        if name in self.instrList: raise KeyError("Instrument name '"+name+"' already exists.")
        if addr in self.instrList.values(): raise ValueError("GPIB address "+str(addr)+" already claimed.")
        self.instrList[name] = addr
    
    # Write to instrument.  Linefeed (\n) is automatically appended at the end of write.
    # Returns number of bytes written sans LF
    def write(self, instrName, cmd):
        # Check if address needs to be updated
        if instrName not in self.instrList: raise KeyError("Instrument name '"+instrName+"' at GPIB address does not exist or was not instantiated.")
        instrAddr = self.instrList[instrName]
        if instrAddr != self.prevAddr:
            if not self.noConnect: s.write(("++addr "+str(instrAddr)+"\n").encode())
            self.prevAddr = instrAddr
        # Write command
        if not self.noConnect: return s.write((cmd+"\n").encode())-1
        return len(cmd)
    
    # Read from instrument up to maxBytes or until CRLF is encountered.  The ending CRLF is stripped from the return string.
    # Returns the resulting string.
    def read(self, maxBytes=256):
        if not self.noConnect: 
            strRead = s.read(maxBytes) 
        else: 
            strRead="TEST\n"
        return strRead[:-1]
        
    # Write then read with optional delay in between (in seconds)
    # Returns the resulting string.
    def query(self, instrName, cmdWrite, wait=0.01, maxReadBytes=256):
        self.write(instrName, cmdWrite)
        time.sleep(wait)
        return self.read(maxReadBytes)
        
    # Close the serial object
    def close(self)
        if not self.noConnect: s.close()
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
