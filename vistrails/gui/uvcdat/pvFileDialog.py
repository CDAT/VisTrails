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
        self.fileNames = QtCore.QStringList()
        self.Files.setModel(self.model)
        mi = self.model.index(0,0)
        self.wrapper.setCurrentPath(self.wrapper.getCurrentPath())
        
        # For testing purposes        
        self.onModelReset()

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

    #--------------------------------------------------------------------------
    @pyqtSlot(QtCore.QModelIndex)
    def onDoubleClickFile(self, index):
      # NOTE: Not cosidering directory mode
      self.accept()

    #--------------------------------------------------------------------------
    def accept(self):
      # TODO: Do we really need mode stuff?
      loadedFile = False
      #switch(this->Implementation->Mode)
      #{
      #case AnyFile:
      #case Directory:
        #loadedFile = this->acceptDefault(false);
        #break;
      #case ExistingFiles:
      #case ExistingFile:
        #loadedFile = this->acceptExistingFiles();
        #break;
      #}

      loadedFile = self.acceptDefault(False)
      if loadedFile == True:
        self.emitFilesSelectionDone()

    #--------------------------------------------------------------------------
    def emitFilesSelectionDone(self):
      # TODO: Look at this later
      #emit filesSelected(this->Implementation->SelectedFiles);
      #if (this->Implementation->Mode != this->ExistingFiles
        #&& this->Implementation->SelectedFiles.size() > 0)
        #{
        #emit filesSelected(this->Implementation->SelectedFiles[0]);
        #}
      self.done(QtGui.QDialog.Accepted)

    #--------------------------------------------------------------------------
    def acceptDefault(self, checkForGrouping = False):
      filename = self.FileName.text()
      filename = filename.trimmed()

      fullFilePath = self.wrapper.absoluteFilePath(filename)

      print 'fullFilePath ', fullFilePath

      self.emit(QtCore.SIGNAL("fileAccepted"), fullFilePath)      

      # TODO: Implement later
      files = QtCore.QStringList()
      if checkForGrouping:
        pass
        #{
        #files = this->buildFileGroup(filename);
        #}
      else:
        files = QtCore.QStringList(fullFilePath)

      return self.acceptInternal(files, False);

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
          fileNames.append(name)

      # TODO: I am not sure if we need this
      #//if we are in directory mode we have to enable / disable the OK button
      #//based on if the user has selected a file.
      #if ( this->Implementation->Mode == pqFileDialog::Directory &&
        #indices[0].model() == &this->Implementation->FileFilter)
        #{
        #QModelIndex idx = this->Implementation->FileFilter.mapToSource(indices[0]);
        #bool enabled = this->Implementation->Model->isDir(idx);
        #this->Implementation->Ui.OK->setEnabled( enabled );
        #if ( enabled )
          #{
          #this->Implementation->Ui.FileName->setText(fileString);
          #}
        #else
          #{
          #this->Implementation->Ui.FileName->clear();
          #}
        #return;
        #}

      #user is currently editing a name, don't change the text
      self.FileName.blockSignals(True)
      self.FileName.setText(fileString)
      self.FileName.blockSignals(False)

      self.fileNames = fileNames;

    #--------------------------------------------------------------------------
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

      for i in range(0, parents.count()):
        str = ''
        for j in range(0, i):
          str += parents[j]
          if str.endsWith(separator) == False :
            str += separator
        self.Parents.addItem(str);

      self.Parents.setCurrentIndex(parents.count() - 1)
