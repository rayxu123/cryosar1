#!/bin/python
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
    def __init__(self, userComments={}, csvFilePrefix=''):
        # Create empty dataframe 
        self.df = pd.DataFrame()
        # Create system metadata dictionary
        # 'now' represents timestamp at which the python program was invoked.  Do not change this.
        now = datetime.datetime.now()
        now = now.strftime('%Y%m%d_T%H%M%S')
        # Set default csv file output path
        self.csvFilePath = "./output/run_"+csvFilePrefix+"_"+now+".csv"
        try:
            source = __main__.__file__
        except AttributeError:
            source = "(none)"
        self.metadata = {
            'start_YYMMDD_THHMMSS': now,
            'source': source,
            'target': self.csvFilePath
        }
        self.setComments(userComments)
        
    
    
    # Set comments associated with this dataset and append system-level comments.
    # Directly manipulating the 'self.comments' variable is strongly discouraged.
    # This reads in a dictionary of metadata and appends system-level metadata.
    # Reserved keywords: 'start_YYMMDD_THHMMSS', 'source', 'target'.  
    # If userComments contains any reserved keywords, the values will be overwritten by userComments
    def setComments(self, userComments):
        self.comments = self.metadata | userComments
        
            
    # Appends a row of data into the dataframe. 
    # Input: dict with keys as column names and values as data to be inserted
    def appendData(self, mydict, flush=True):
        mydict_df = pd.DataFrame([mydict])
        self.df = pd.concat([self.df, mydict_df], ignore_index=True)
        if flush: self.writeCSV()
        
        
    # Writes to CSV specified by self.csvFilePath
    def writeCSV(self):
        # Check if folder exists
        filepath = Path(self.csvFilePath)  
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Write data
        self.df.to_csv(self.csvFilePath+".gz", mode="w", index=False, compression="gzip")
        # Write metadata
        comments_str = '\n'.join([f'{key} = {value}' for key, value in self.comments.items()])
        with open(self.csvFilePath+".metadata", "w") as f:
            f.write(comments_str)
            f.close()

        
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
