#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
July 2023
CryoSAR1/SControl/SControl_ADC.py

Quick class to read AD7888's
'''

import sys
import os
import time
import math
import ftdispi
from bitstring import BitArray
import configparser
import csv

class SControl_ADC:
    def __init__(self, args):
        self.args = args
        # Initiate hardware
        self.spi = ftdispi.ftdispi(self.args.addr, self.args.noConnect, mode=1, SPIMUX=True)
        # Set LDAC high
        self.spi.setgpio(1)
        
        # Read from ADC1
        self.spi.setSPIMUX(3)
        adcVal = []
        for i in range(8):
            # Do a dummy read 
            adcRead = self.spi.readAD7188(self.spi.adc1, i)
            # Read 
            adcRead = self.spi.readAD7188(self.spi.adc1, i)
            adcVal.append(adcRead)
        adc1 = {    'ADC_TESTPOINT' : adcVal[0],
                    'ADC_VBN_TX' : adcVal[1],
                    'VBP_SET' : adcVal[2],
                    'VBN_SET' : adcVal[3],
                    '3.3VDUT_SENSE_P' : adcVal[4],
                    '3.3VDUT_SENSE_N' : adcVal[5],
                    '1.2VDUT_SENSE_P' : adcVal[6],
                    '1.2VDUT_SENSE_N' : adcVal[7]
                }
        if self.args.quiet is False: print(adc1)
        
        # Read from ADC2
        self.spi.setSPIMUX(0)
        adcVal = []
        for i in range(8):
            # Do a dummy read 
            adcRead = self.spi.readAD7188(self.spi.adc2, i)
            # Read 
            adcRead = self.spi.readAD7188(self.spi.adc2, i)
            adcVal.append(adcRead)
        adc2 = {    'ADC_VBP_SW' : adcVal[0],
                    'ADC_VBP_REF' : adcVal[1],
                    'ADC_VBP_CMP' : adcVal[2],
                    'ADC_VBP_TX' : adcVal[3],
                    'AVDD_REF_P_SENSE' : adcVal[4],
                    'AVDD_CMP_SENSE' : adcVal[5],
                    'AVDD_REF_CN_SENSE' : adcVal[6],
                    'AVDD_SAMP_SENSE' : adcVal[7]
                }
        if self.args.quiet is False: print(adc2)
        
        # Read from ADC3
        self.spi.setSPIMUX(1)
        adcVal = []
        for i in range(8):
            # Do a dummy read 
            adcRead = self.spi.readAD7188(self.spi.adc3, i)
            # Read 
            adcRead = self.spi.readAD7188(self.spi.adc3, i)
            adcVal.append(adcRead)
        adc3 = {    'ADC_VBN_CMP' : adcVal[0],
                    'ADC_VBN_REF' : adcVal[1],
                    'ADC_VBN_SW' : adcVal[2],
                    'ADC_VBN_SAMP' : adcVal[3],
                    'DVDD_TX_SENSE' : adcVal[4],
                    'DVDD_CLK_SENSE' : adcVal[5],
                    'DVDD_SAR_SENSE' : adcVal[6],
                    '1.2VDD' : adcVal[7]
                }
        if self.args.quiet is False: print(adc3)
        
        # Write to file
        with open('./output/adc.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            for key,value in adc1.items(): writer.writerow([key, value])
            for key,value in adc2.items(): writer.writerow([key, value])
            for key,value in adc3.items(): writer.writerow([key, value])
        
                    
                    
                    
                    
                    
                    