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

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QStatusBar,
    QSizePolicy
)


class TMon_GUI(QWidget):
    def __init__(self, args):
        super().__init__()
        QtGui.QFontDatabase.addApplicationFont('DSEG7Classic-Bold.ttf')
        self.setWindowTitle("QGridLayout Example")
        # Create a QGridLayout instance
        layout = QVBoxLayout()
        # Label widget
        self.labelObj = QLabel("W")
        self.labelObj.setAlignment(QtCore.Qt.AlignCenter)
        # Status bar
        self.statusObj = QStatusBar()
        self.statusObj.showMessage('Ready')
        # Set minimum size policy
        self.labelObj.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.labelObj.setMinimumHeight(100)
        self.labelObj.setMinimumWidth(100)
        # Add widgets
        layout.addWidget(self.labelObj, 1)
        layout.addWidget(self.statusObj, 0)
        # Set the layout on the application's window
        self.setLayout(layout)
        # Show window
        self.show()
        self.resize(120,120)

    # This function is invoked each time the window is resized.
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.resizeEvent(event)
    def resizeEvent(self, event):
        print("someFunction")
        style = "background-color: white; color: green; font-weight: bold; font-family: DSEG7Classic; font-size: 100px"
        self.labelObj.setStyleSheet(style)
        print(str(self.labelObj.width())+", "+str(self.labelObj.height()))
        
    # This function is invoked if user tried to close the window
    # Overrides the virtual function  PyQt5.QtWidgets.QWidget.closeEvent(event)
    def closeEvent(self, event):
        print("Bye!")


#if __name__ == "__main__":
#    app = QApplication(sys.argv)
#    window = Window()
#    sys.exit(app.exec_())
    
    
    
    
    
    
    
    
    
    
    
