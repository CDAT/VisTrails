import sys, traceback, atexit
from PyQt4 import QtCore, QtGui
import gui.application
from ui_reportErrorDialog import Ui_ReportErrorDialog

def report_exception(exctype, value, tb):
    app = gui.application.get_vistrails_application()
    if app:
        app.uvcdatWindow.hide()
    s = ''.join(traceback.format_exception(exctype, value, tb))
    dialog = ReportErrorDialog(None)
    dialog.setErrorMessage(s);
    dialog.exec_()
    if app:
        app.finishSession()
    else:
        sys.exit(254)
    
def install_exception_hook():
    sys.excepthook = report_exception
    
def uninstall_exception_hook():
    sys.excepthook = sys.__excepthook__
    
atexit.register(uninstall_exception_hook)

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
        