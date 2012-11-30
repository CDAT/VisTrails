from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem

from ui_reportErrorDialog import Ui_ReportErrorDialog

class ReportErrorDialog(QtGui.QDialog, Ui_ReportErrorDialog):

    def __init__(self, parent=None):
        super(ReportErrorDialog, self).__init__(parent)
        self.setupUi(self)
        
        #setup signals
        self.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.sendError)
        
    def setErrorMessage(self, string):
        self.errorDetails.setText(string)
        
    def sendError(self):
        #TODO: send error details to uvcdat server
        pass