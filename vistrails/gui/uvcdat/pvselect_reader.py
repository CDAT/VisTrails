from PyQt4 import QtCore, QtGui
from ui_pvselect_reader import Ui_PVSelectReaderDialog
from paraview.simple import *
from pvreadermanager import PVReaderFactory

class PVSelectReaderDialog(QtGui.QDialog, Ui_PVSelectReaderDialog):
    def __init__(self, parent=None):
        super(PVSelectReaderDialog, self).__init__(parent)                
        self.setupUi(self)
        self.root = self        
        self._currentReader = None
        self._session = None
        self._reader_factory = None
        self._filename = ''                
              
    def populateReaders(self, filename):      
        # incoming filename could be a Qt string
        self._filename = str(filename)
      
        # Clear old entries
        self.readersListWidget.clear()
      
        # First grab the session
        self._session = servermanager.ActiveConnection.Session
                
        # Get the factory
        self._reader_factory = servermanager.vtkSMProxyManager.GetProxyManager().GetReaderFactory()
        
        # Test for readability
        if not self._reader_factory.TestFileReadability(self._filename, self._session):
          msg = "File not readable: %s " % self._filename
          raise RuntimeError, msg
        
        # This is required
        if self._reader_factory.GetNumberOfRegisteredPrototypes() == 0:
          self._reader_factory.RegisterPrototypes("sources")

        # Get all the possible readers
        stringList = self._reader_factory.GetReaders(self._filename, self._session)
        for i in range(0, stringList.GetLength(),3):
          group = stringList.GetString(i)
          name = stringList.GetString(i+1)
          desc = stringList.GetString(i+2)
          print group, name, desc
          lwItem = QtGui.QListWidgetItem(desc, self.readersListWidget)
          lwItem.setData(QtCore.Qt.UserRole, group)
          lwItem.setData(QtCore.Qt.UserRole+1, name)

    def getSelectedReader(self):
      item = self.readersListWidget.currentItem()
      group = str(item.data(QtCore.Qt.UserRole).toString())
      name = str(item.data(QtCore.Qt.UserRole+1).toString())
            
      self._currentReader = PVReaderFactory.create_reader(group, name, 
                                                          self._filename)
        
      return self._currentReader
        