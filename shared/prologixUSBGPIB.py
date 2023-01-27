#!/bin/python3
# Python 3.6 or greater
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
    # Initializes the serial connection and instrument list.
    # Inputs:
    # noConnect: set to true for demo mode (useful for debugging)
    # serialResourcePath: Path for example '/dev/ttyUSB0' on unix systems
    # SN: USB serial number
    # If neither serialResourcePath nor serialNumber is specified, it will attempt to find the Prologix device.
    # If both serialResourcePath and serialNumber is specified, it will use device matching serialNumber
    def __init__(self, noConnect=False, serialResourcePath='', serialNumber='', verbose=False):
        # Initialize state variables
        self.prevAddr = 32
        self.noConnect = noConnect
        self.verbose = verbose
        # Initialize instrument list
        self.instrList = {}
        # Initialize GPIB controller
        self.s = None
        if not self.noConnect:
            if serialNumber:
                devices = serial.tools.list_ports.comports()
                for d in devices:
                    if d.serial_number == serialNumber:
                        self.s = serial.Serial(d.device, 9600, timeout=0.5)
                        if self.verbose: print("SERIAL: CONNECT "+d.device)
            if serialResourcePath:
                self.s = serial.Serial(serialResourcePath, 9600, timeout=0.5)
                if self.verbose: print("SERIAL: CONNECT " + serialResourcePath)
            if not serialResourcePath and not serialNumber:
                devices = serial.tools.list_ports.comports()
                for d in devices:
                    if "Prologix GPIB-USB" in d.description:
                        self.s = serial.Serial(d.device, 9600, timeout=0.5)
                        if self.verbose: print("SERIAL: CONNECT " + d.device)
            # If device hasn't been found yet:
            if self.s == None: raise KeyError("Prologix GPIB-USB not found!")
            # Initialize prologix controller: set mode
            cmd = '++mode 1'
            self.s.write((cmd + "\n").encode())
            if self.verbose: print("SERIAL: WRITE " + str((cmd + "\n").encode()))
            # Initialize prologix controller: set addr
            self.s.write(("++addr "+str(self.prevAddr)+"\n").encode())
            if self.verbose: print("SERIAL: WRITE " + str(("++addr "+str(self.prevAddr)+"\n").encode()))
            # Initialize prologix controller: set auto
            cmd = '++auto 1'
            self.s.write((cmd + "\n").encode())
            if self.verbose: print("SERIAL: WRITE " + str((cmd + "\n").encode()))
            self.resetBuffers()  # Clear buffer


        
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
            if not self.noConnect: self.s.write(("++addr "+str(instrAddr)+"\n").encode())
            if self.verbose: print("SERIAL: WRITE " + str(("++addr "+str(instrAddr)+"\n").encode()))
            self.prevAddr = instrAddr
            self.resetBuffers()
        # Write command
        if not self.noConnect:
            nBytes = self.s.write((cmd+"\n").encode())-1
        else:
            nBytes = len(cmd)
        if self.verbose: print("SERIAL: WRITE " + str((cmd+"\n").encode()))
        return nBytes
    
    # Read from instrument up to maxBytes or until CRLF is encountered.  The ending CRLF is stripped from the return string.
    # Returns the resulting string.
    def read(self, maxBytes=256):
        if not self.noConnect: 
            strRead = self.s.read(maxBytes)
        else: 
            strRead="+999.999E3\r\n".encode()
        if self.verbose: print("SERIAL: READ " + str(strRead))
        # Cast bytes to string and remove any CRLF
        strRead = strRead.decode()
        strRead = strRead.replace("\n", "").replace("\r", "")
        return strRead
        
    # Write then read with optional delay in between (in seconds)
    # Returns the resulting string.
    def query(self, instrName, cmdWrite, wait=0.01, maxReadBytes=256):
        self.write(instrName, cmdWrite)
        time.sleep(wait)
        return self.read(maxReadBytes)
        
    # Close the serial object
    def close(self):
        if not self.noConnect: self.s.close()

    # Reset buffers
    def resetBuffers(self):
        if not self.noConnect:
            self.s.reset_output_buffer()
            self.s.reset_input_buffer()
            # Reset hardware input buffer
            #while len(self.s.read()) > 0:
            #    time.sleep(0.1)
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
