from paraview.simple import *
from paraview import servermanager

class PVProcessFile:
    def __init__(self):
        self._fileName = ""
        self._reader = None
        
    def setFileName(self, fileName):
        self._fileName = fileName
        
    def getOrCreateReader(self):
        # Assuming we are going to have one reader type for now.
        if not self._reader:
            print self._fileName
            self._reader = ExodusIIReader(FileName=str(self._fileName))
        return self._reader;
    
    def getPointVariables(self):
        self.getOrCreateReader()
        return self._reader.PointVariables.Available
    
    def getCellVariables(self):
        self.getOrCreateReader()
        return self._reader.ElementVariables.Available

    def getVariables(self):
        self.getOrCreateReader()
        return self._reader.Variables.Available