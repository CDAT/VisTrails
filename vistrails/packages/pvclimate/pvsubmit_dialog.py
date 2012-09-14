# Qt modules
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, pyqtSlot

# Local modules
from ui_pvsubmit_job import Ui_Dialog

# System modules
import os

#
class PVSubmitFileDialog(QtGui.QDialog, Ui_Dialog):
   #--------------------------------------------------------------------------
   def __init__(self, parent=None):
       super(PVSubmitFileDialog, self).__init__(parent)
       self.setupUi(self)
       self.files = []
       self.connect(self.remoteBrowserButton, QtCore.SIGNAL("clicked(bool)"),
         self.open_remote_browser)
       self.connect(self.localBrowserButton, QtCore.SIGNAL("clicked(bool)"),
         self.open_local_browser)

   def accept(self):
      self.done(QtGui.QDialog.Accepted)

   def open_remote_browser(self):
     import gui.uvcdat.pvFileDialog as fd
     fileDialog = fd.PVFileDialog(self)
     if fileDialog.exec_():
       for file in fileDialog.getAllSelectedFiles():
         self.files.append(str(file))
       self.inputPath.setText(os.path.dirname(self.files[0]))

   def open_local_browser(self):
     directory = os.path.expanduser(unicode(self.outputPath.text()))
     fd = QtGui.QFileDialog(self, 'Select: Output Directory', directory)
     fd.setFileMode(QtGui.QFileDialog.DirectoryOnly)
     if fd.exec_() == 1:
       dir = str(fd.selectedFiles().first())
       self.outputPath.setText(dir)

   def get_remote_files(self):
     return self.files

   def get_output_directory(self):
     return self.outputPath.text()

   def get_queue_name(self):
     return self.queueLineEdit.text()

