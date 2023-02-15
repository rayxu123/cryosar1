#!/bin/python
# Python 3.6 or greater
'''
Ray Xu 
Nov 2022
cryosar1/TMon/pandasWriter.py

Wrapper class for pandas.  This standardizes table and file output format.

Requires the packages:
 - pandas
'''


import os.path
import pandas as pd
import sys
import time
import datetime
from pathlib import Path
import __main__

class pandasWriter:
    # Inputs:
    # userComments: dictionary of metadata (see setComments routine for more details)
    # csvFilePathPrefix: name appended to output file name
    # enableIdx: set to True to add a column with a monotonic incrementing row number (starting at 0)
    # maxRowsPerFile: maximum number of rows per csv file.  Once passed, the csv file is rotated: a new csv file is created (with the same basename) and the dataframe table is cleared, however idx keeps on incrementing
    def __init__(self, userComments={}, csvFilePrefix='', enableIdx=True, maxRowsPerFile=65536):
        # Create empty dataframe 
        self.df = pd.DataFrame()
        self.idx = 0
        self.fileNum = 0
        self.enableIdx = enableIdx
        self.maxRowsPerFile = maxRowsPerFile
        # Create system metadata dictionary
        # 'self.start' represents timestamp at which the python program was invoked.  Do not change this.
        self.start = datetime.datetime.now()
        self.start = self.start.strftime('%Y%m%d_T%H%M%S')
        # Set default csv file output path
        self.csvFilePrefix = csvFilePrefix
        self.csvFilePath = "./output/run_"+self.csvFilePrefix+"_"+self.start+"_file"+str(self.fileNum)+".csv"
        try:
            source = __main__.__file__
        except AttributeError:
            source = "(none)"
        self.metadata = {
            'start_YYMMDD_THHMMSS': self.start,   # When data taking started
            'now_YYMMDD_THHMMSS': self.start,     # Current time as of file write
            'source': source,                   # Which script made this
            'target': self.csvFilePath          # It's own file path
        }
        self.setComments(userComments)
        
    
    
    # Set comments associated with this dataset and append system-level comments.
    # Directly manipulating the 'self.comments' variable is strongly discouraged.
    # This reads in a dictionary of metadata and appends system-level metadata.
    # Reserved keywords: 'start_YYMMDD_THHMMSS', now_YYMMDD_THHMMSS', 'source', 'target'.
    # If userComments contains any reserved keywords, the values will be overwritten by userComments
    def setComments(self, userComments):
        self.comments = self.__merge(self.metadata, userComments)
        
            
    # Appends a row of data into the dataframe. 
    # Input: dict with keys (str datatype) representing column names and the values (any datatype) representing data to be inserted
    def appendData(self, mydict, flush=True):
        # Append idx row:
        if self.enableIdx:
            mydict_idx = {"idx": self.idx}
            self.idx = self.idx + 1
            mydict = self.__merge(mydict_idx, mydict)
        # New data is always appended to the end of the dataframe table
        mydict_df = pd.DataFrame([mydict])
        self.df = pd.concat([self.df, mydict_df], ignore_index=True)
        if flush: self.writeCSV()
        # Check if csv file needs to be rotated:
        if self.df.shape[0] >= self.maxRowsPerFile:
            self.writeCSV()
            self.fileNum = self.fileNum + 1
            self.csvFilePath = "./output/run_" + self.csvFilePrefix + "_" + self.start + "_file" + str(self.fileNum) + ".csv"
            self.df = pd.DataFrame()



    # Writes and flushes to CSV specified by self.csvFilePath
    def writeCSV(self):
        # Check if folder exists
        filepath = Path(self.csvFilePath)  
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Write data
        self.df.to_csv(self.csvFilePath+".gz", mode="w", index=False, compression="gzip")
        # Update timestamp
        now = datetime.datetime.now()
        now = now.strftime('%Y%m%d_T%H%M%S')
        self.comments['now_YYMMDD_THHMMSS'] = now
        # Write metadata
        comments_str = '\n'.join([f'{key} = {value}' for key, value in self.comments.items()])
        with open(self.csvFilePath+".metatxt", "w") as f:
            f.write(comments_str)
            f.close()

    # Gets current filename
    def csvFilepath(self):
        return self.csvFilePath+".gz"

    # Internal method to merge two dictionaries
    def __merge(self, dict1, dict2):
        res = {**dict1, **dict2}
        return res
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
