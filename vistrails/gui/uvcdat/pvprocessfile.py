from paraview.simple import *
from paraview import servermanager
from pvselect_reader import PVSelectReaderDialog

class PVProcessFile:
    def __init__(self):
        self._fileName = ""
        self._reader = None
        self._stride = [1,1,1]
        
    def setFileName(self, fileName):
        self._fileName = fileName
        
    def setStride(self, stride):
        self._stride = stride
        
    def getOrCreateReader(self):
        # Assuming we are going to have one reader type for now.
        if not self._reader:
            print self._fileName
            selectReader = PVSelectReaderDialog()
            selectReader.exec_()
            readerCreateFunc = selectReader.getSelectedReader() 
            if readerCreateFunc is not None:
              self._reader = readerCreateFunc(FileName=str(self._fileName))            

              # Read part data only
              # \TODO Check if the reader has stride option
              self._reader.Stride = self._stride
            else:
              self._reader = None              
        return self._reader;
    
    def getPointVariables(self):
        self.getOrCreateReader()
        return self._reader.PointVariables.Available
    
    def getCellVariables(self):
        self.getOrCreateReader()
        return self._reader.ElementVariables.Available

    def getVariables(self):
        self.getOrCreateReader()
        
        # @NOTE: For now get only point data arrays
        variables = []
        numberOfPointDataArrays = self._reader.PointData.GetNumberOfArrays() 
        for i in range(0, numberOfPointDataArrays):
            array = str(self._reader.PointData.GetArray(i))            
            # GetArray returns array information in this format -> Array: Name
            variables.append(array.split(':')[1])
        return variables