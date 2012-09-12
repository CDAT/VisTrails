from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, pyqtSlot

from ui_pvFileDialog import Ui_pvFileDialog

#from paraview.simple import *

import pvFileDialogModelWrapper

class PVFileDialog(QtGui.QDialog, Ui_pvFileDialog):
   #--------------------------------------------------------------------------
   def __init__(self, parent=None):
       super(PVFileDialog, self).__init__(parent)
       self.setupUi(self)
       self.wrapper = pvFileDialogModelWrapper.pvFileDialogModelWrapper()
       self.model = self.wrapper.getModel()
       self.Files.setModel(self.model)
       self.currentPath = self.wrapper.getCurrentPath()

       # List of file names in the FileName ui text edit
       self.fileNames = QtCore.QStringList()

       # List of files that selected by the user
       self.selectedFiles = []
       self.wrapper.setCurrentPath(QtCore.QString(self.currentPath))

       # Connect signal-slots
       QtCore.QObject.connect(self.Parents,
         QtCore.SIGNAL("activated(const QString&)"),
         self,
         QtCore.SLOT("onNavigate(const QString&)"));

       QtCore.QObject.connect(self.Files.selectionModel(),
         QtCore.SIGNAL(
           "selectionChanged(const QItemSelection&, const QItemSelection&)"),
           self,
           QtCore.SLOT("fileSelectionChanged()"));

       QtCore.QObject.connect(self.Files,
         QtCore.SIGNAL(
           "doubleClicked(const QModelIndex&)"),
           self,
           QtCore.SLOT("onDoubleClickFile(const QModelIndex&)"));

       QtCore.QObject.connect(self.model,
         QtCore.SIGNAL(
           "modelReset()"),
           self,
           QtCore.SLOT("onModelReset()"));

       # \TODO: Implement get start path
       self.wrapper.setCurrentPath(self.wrapper.getCurrentPath())

   #--------------------------------------------------------------------------
   @pyqtSlot(QtCore.QModelIndex)
   def onDoubleClickFile(self, index):
     self.accept()

   #--------------------------------------------------------------------------
   def accept(self):
     loadedFile = False
     loadedFile = self.acceptDefault(True)
     if loadedFile == True:
       self.emitFilesSelectionDone()

   #--------------------------------------------------------------------------
   def emitFilesSelectionDone(self):
     self.emit(QtCore.SIGNAL("fileAccepted"), self.selectedFiles)
     self.done(QtGui.QDialog.Accepted)

   #--------------------------------------------------------------------------
   def acceptDefault(self, checkForGrouping = False):
     loadedFiles = False
     filename = self.FileName.text()
     filename = filename.trimmed()

     fullFilePath = self.wrapper.absoluteFilePath(filename)

     self.emit(QtCore.SIGNAL("fileAccepted"), fullFilePath)

     files = QtCore.QStringList()
     if checkForGrouping:
       files = self.buildFileGroup(filename);
     else:
       files = QtCore.QStringList(fullFilePath)

     return self.acceptInternal(files, False);

   #--------------------------------------------------------------------------
   def buildFileGroup(self, filename):
     print 'called buildFileGroup'
     return self.wrapper.buildFileGroup(filename)

   #--------------------------------------------------------------------------
   def acceptInternal(self, selectedFiles, doubleClicked):
     if selectedFiles.count() <= 0:
       return False

     file = selectedFiles[0]

     # User chose an existing directory
     if self.wrapper.dirExists(file, file):
       self.onNavigate(file)
       self.FileName.clear()
       return False

     # User chose an existing file
     self.addToFilesSelected(selectedFiles)
     return True

   #--------------------------------------------------------------------------
   @pyqtSlot(str)
   def onNavigate(self, path):
     self.wrapper.setCurrentPath(path)

   #--------------------------------------------------------------------------
   @pyqtSlot()
   def fileSelectionChanged(self):
     print 'File selection changed'

     # Selection changed, update the FileName entry box
     # to reflect the current selection.
     fileString = QtCore.QString()
     indices = self.Files.selectionModel().selectedIndexes()

     if len(indices) == 0:
       # Do not change the FileName text if no selections
       return

     fileNames = QtCore.QStringList()
     name = QtCore.QString()

     for i in range(0, len(indices)):
       index = indices[i]
       if index.column() != 0:
         continue

       if(index.model() == self.wrapper.getModel()):
         name = self.wrapper.getModel().data(index).toString()
         fileString = fileString + name
         if i != len(indices) - 1:
           # Hard coded for now
           #fileString += this->Implementation->FileNamesSeperator
           fileString += '/'
         fileNames.append(self.wrapper.absoluteFilePath(name))

     # user is currently editing a name, don't change the text
     if(self.FileName.hasFocus() == False):
       self.FileName.blockSignals(True)
       self.FileName.setText(fileString)
       self.FileName.blockSignals(False)

     self.fileNames = fileNames

   #--------------------------------------------------------------------------
   @pyqtSlot()
   def onModelReset(self):
     self.Parents.clear()

     currentPath = self.wrapper.getCurrentPath()

     # Clean the path to always look like a unix path
     currentPath = QtCore.QDir.cleanPath(currentPath)

     # The separator is always the unix separator
     separator = '/'

     parents = currentPath.split(separator, QtCore.QString.SkipEmptyParts)

     # Put our root back in
     if(parents.count()):
       idx = currentPath.indexOf(parents[0])
       if(idx != 0 and idx != -1):
         parents.prepend(currentPath.left(idx))
     else:
       parents.prepend(separator);

     for i in range(0, (parents.count() + 1)):
       str = QtCore.QString()
       for j in range(0, i):
         str += parents[j]
         if str.endsWith(separator) == False :
           str += separator
       self.Parents.addItem(str);

     self.Parents.setCurrentIndex(parents.count())

   #--------------------------------------------------------------------------
   def getAllSelectedFiles(self):
     return self.selectedFiles

   #--------------------------------------------------------------------------
   def addToFilesSelected(self, files):
     self.setVisible(False)
     self.selectedFiles.extend(files)
