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
        
    def createReader(self):
      selectReader = PVSelectReaderDialog()
      selectReader.populateReaders(self._fileName)            
      selectReader.exec_()
      self._reader = selectReader.getSelectedReader()                        
  
      # Read part data only (default is read all the data) 
      if 'Stride' in dir(self._reader):                          
        self._reader.Stride = self._stride
                                      
      return self._reader;
    
    def getPointVariables(self):        
        return self._reader.PointVariables.Available
    
    def getCellVariables(self):        
        return self._reader.ElementVariables.Available

    def getVariables(self):
        # @NOTE: For now get only point data arrays
        variables = []
        numberOfPointDataArrays = self._reader.PointData.GetNumberOfArrays() 
        for i in range(0, numberOfPointDataArrays):
            array = str(self._reader.PointData.GetArray(i))            
            # GetArray returns array information in this format -> Array: Name
            variables.append(array.split(':')[1])
        return variables

    def getReader(self):
        return self._reader