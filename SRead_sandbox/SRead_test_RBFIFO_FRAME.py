#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Nov 2022
cryosar1/SRead/SRead_test.py

The path to libokFrontPanel.so must be exported as an environment variable to $LD_LIBRARY_PATH
'''



import sys
import ok
import time
import numpy as np
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from PyQt5 import QtWidgets, QtCore, QtGui #pyqt stuff
from bitstring import BitArray

if __name__ == "__main__":
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) #enable highdpi scaling
    #QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True) #use highdpi icons

    defWeights = [32768, 1940, 1110, 635, 365, 210, 120, 70, 40, 24, 14, 8, 5, 3, 2, 1];

    xem = ok.FrontPanel()
    xem.OpenBySerial("")
    #xem.LoadDefaultPLLConfiguration()
    xem.ConfigureFPGA('RBFIFO_FRAME.bit')


    # Reset, testmode
    #xem.SetWireInValue(0x00, 0x00000005)
    #xem.UpdateWireIns()
    #time.sleep(0.1)
    #xem.SetWireInValue(0x00, 0x00000004)
    #xem.UpdateWireIns()

    # Reset, mode 0
    #xem.SetWireInValue(0x00, 0x00000001)
    #xem.UpdateWireIns()
    #time.sleep(0.1)
    #xem.SetWireInValue(0x00, 0x00000000)
    #xem.UpdateWireIns()

    # Reset, mode 1
    xem.SetWireInValue(0x00, 0x00000003)
    xem.UpdateWireIns()
    time.sleep(0.1)
    xem.SetWireInValue(0x00, 0x00000002)
    xem.UpdateWireIns()

    # Fill FIFO
    time.sleep(2*(32768/(200000000/8)))

    values = []
    # depth 32768 -> actual 32771 (32772 spaces?).  Breaks at 32768+5, which is expected.
    for value in range(4096):
        addr = BitArray(uint=value, length=16)
        data = xem.ReadRegister(addr.uint)
        data = BitArray(uint=data, length=16)
        #print(str(addr.hex)+": "+str(data.uint))
        dataw = [*data.bin]
        dataw = [eval(i) for i in dataw]
        #dataw = [abs(i-1) for i in dataw]   # Swap 0 and 1's
        #dataw = [(2*i)-1 for i in dataw]   # convert to bipolar
        #dataw = [-i for i in dataw]   # Swap 0 and 1's, bipolar
        dataw = np.dot(dataw, defWeights)
        values.append(dataw)
        #print(dataw)
        print(data.hex)

    unique = np.unique(values)
    #print(list(set(np.diff(values))))
    print(unique)
    print(np.average(values))

    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.hist(values, bins=len(unique), edgecolor = "black")
    plt.show()
    

    # Reset, mode 0
    #xem.SetWireInValue(0x00, 0x00000001)
    #xem.UpdateWireIns()
    #time.sleep(0.1)
    #xem.SetWireInValue(0x00, 0x00000000)
    #xem.UpdateWireIns()

    #for value in range(128):
    #    addr = BitArray(uint=value, length=32)
    #    data = xem.ReadRegister(addr.uint)
    #    data = BitArray(uint=data, length=32)
    #    print(str(addr.hex)+": "+str(data.hex))

    







    
    
