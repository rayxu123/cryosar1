# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 17:35:35 2020

@author: Eraguzin
"""

import pyvisa
import sys, os
import datetime
import csv
from shutil import copyfile

curr_file = os.path.dirname(os.path.abspath(__file__))
desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
name = input("Name of file?\n")
desktop_path = os.path.join(desktop, name + ".csv")
onedrive_path = os.path.join(curr_file, name + ".csv")
# ser = serial.Serial("COM1", 9600, bytesize=serial.EIGHTBITS, 
#                                 parity=serial.PARITY_NONE, 
#                                 stopbits=serial.STOPBITS_ONE, timeout=5)
# IDN_S = "*IDN?"
# def __write__(self, s):
#         ser.write(str.encode(s + "\r\n"))
        
# def __read__(self, s):
#     __write__(s)
#     ret = ser.readline().strip()
#     return ret.decode()

# def ident(self):
#     return self.__read__(IDN_S)

# print(__read__(IDN_S))


    
rm = pyvisa.ResourceManager()
rm.list_resources()
print(rm.list_resources())

ars = rm.open_resource('ASRL3::INSTR')
print("---")
print(ars.read_termination)
print(ars.write_termination)
print(ars.baud_rate)
print(ars.data_bits)
print(ars.encoding)
print(ars.stop_bits)
print(ars.parity)
print(ars.timeout)
print("---")
ars.read_termination = '\n'
ars.write_termination = '\n'
resp = ars.query('*IDN?')
print(resp)
print(ars.query('input? a'))
print(ars.query('input? b'))

time = datetime.datetime.now()
next_time = time
next_hour = time + datetime.timedelta(hours=1)
header = ["time", "input a", "input b"]
'''
while True:
    try:
        time = datetime.datetime.now()
        if (time > next_time):
            input_a = ars.query('input? a').strip()
            input_b = ars.query('input? b').strip()
            print("Input A is {}, Input B is {}".format(input_a, input_b))
            #temp_a = float(ars.query('input? a'))
            #temp_b = float(ars.query('input? b'))
            with open(desktop_path, 'a', newline='') as csvfile:
                spamwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
                spamwriter.writerow([time, input_a, input_b])
            
            next_time = time + datetime.timedelta(minutes=1)
        if (time > next_hour):
            copyfile(desktop_path, onedrive_path)
            next_hour = time + datetime.timedelta(hours=1)
    except KeyboardInterrupt:
        print("Done")
        break

sys.exit()
'''
print(ars.query('loop 1:setpt?'))
print(type(ars.query('loop 1:setpt?')))

print(ars.query('PIDTable 1:NENTry?'))
print(ars.query('SENS 1:TYP?'))
print(ars.query('SENS 2:name?'))
print(ars.query('SENS 2:nentry?'))
print(ars.query_ascii_values('CALCUR 1'))
ars.write('SENS 2:name?')
while True:
    print(ars.read_bytes(1))


