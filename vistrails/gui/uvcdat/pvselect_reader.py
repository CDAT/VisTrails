from PyQt4 import QtCore, QtGui
from ui_pvselect_reader import Ui_PVSelectReaderDialog
from paraview.simple import *

class PVSelectReaderDialog(QtGui.QDialog, Ui_PVSelectReaderDialog, filename):
    def __init__(self, parent=None):
        super(PVSelectReaderDialog, self).__init__(parent)
        self._filename = filename        
        self.setupUi(self)
        self.root = self
        self._readers = ['NetCDF POP Reader','Foo']
        self._currentReader = ''        
        self.buttonBox.accepted.connect(self.setCurrentReader)        
              
    def populateReaders(self):
        # Clear old entries
        self.readersListWidget.clear()
      
        # First grab the session
        session = servermanager.ActiveConnection.Session
                
        # Get the factory
        reader_factory = pv.servermanager.vtkSMProxyManager.GetProxyManager().GetReaderFactory()
        
        # Test for readability
        if not reader_factory.TestFileReadability(self._filename, session):
          msg = "File not readable: %s " % filename
          raise RuntimeError, msg
        
        # This is required
        if rf.GetNumberOfRegisteredPrototypes() == 0:
          rf.RegisterPrototypes("sources")

        # Print possible readers
        sl = rf.GetReaders(filename, sess)
        for i in range(0,sl.GetLength(),3):
          group = sl.GetString(i)
          name = sl.GetString(i+1)
          desc = sl.GetString(i+2)
                              
          lwItem = QtListWidgetItem(desc, self.readersListWidget)
          lwItem.setData(Qt.UserRole, group)
          lwItem.setData(Qt.UserRole+1, name)
          
    def setCurrentReader(self):
      self._currentReader = self.readersListWidget.currentItem().text()
            
    def getSelectedReader(self):
        if self._currentReader == 'NetCDF POP Reader':
          return NetCDFPOPreader
        else:
          return None
        