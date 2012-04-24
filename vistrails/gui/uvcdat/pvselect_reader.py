from PyQt4 import QtCore, QtGui
from ui_pvselect_reader import Ui_PVSelectReaderDialog
from paraview.simple import *

class PVSelectReaderDialog(QtGui.QDialog, Ui_PVSelectReaderDialog):
    def __init__(self, parent=None):
        super(PVSelectReaderDialog, self).__init__(parent)
        self.setupUi(self)
        self.root = self
        self._readers = ['NetCDF POP Reader','Foo']
        self._currentReader = ''
        self.buttonBox.accepted.connect(self.setCurrentReader)   
        self.populateReaders()     
              
    def populateReaders(self):
        self.readersListWidget.clear()
        for i in self._readers:           
          self.readersListWidget.addItem(i)
          
    def setCurrentReader(self):
      self._currentReader = self.readersListWidget.currentItem().text()
            
    def getSelectedReader(self):
        if self._currentReader == 'NetCDF POP Reader':
          return NetCDFPOPreader
        else:
          return None
        