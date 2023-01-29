import sys

class logger(object):
    def __init__(self, fname):
        self.terminal = sys.stdout
        self.log = open(fname, "w")
   
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        self.log.flush()        
        pass  

    def close(self):
        self.log.close()  
