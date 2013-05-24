import atexit
import hashlib
import os
import platform
import sys
import traceback

from PyQt4 import QtCore, QtGui
from urllib import urlencode
from urllib2 import urlopen

import gui.application
from core.configuration import get_vistrails_configuration
from ui_reportErrorDialog import Ui_ReportErrorDialog


def report_exception(exctype, value, tb):
    uninstall_exception_hook()
    app = gui.application.get_vistrails_application()
#    if app:
#        app.uvcdatWindow.hide()
    s = ''.join(traceback.format_exception(exctype, value, tb))
    dialog = ReportErrorDialog(None)
    try:
        eType = str(type(value)).split("'")[1].split(".")[1]
    except:
        eType = str(type(value))
    dialog.setDescription("%s: %s" % (eType, str(value)))
    dialog.setErrorMessage(s)
    dialog.exec_()
#    if app:
#        app.finishSession()
#    else:
#        sys.exit(254)
    
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
        self.description = ''
        
    def setErrorMessage(self, string):
        self.errorDetails.setText(string)
        
    def setDescription(self, string):
        self.description = string
        
    def getDescription(self):
        return self.description
        
    def sendError(self):
        data = {}
        data['platform'] = platform.uname()[0]
        data['platform_version'] = platform.uname()[2]
        data['hashed_hostname'] = hashlib.sha1(platform.uname()[1]).hexdigest()
        data['hashed_username'] = hashlib.sha1(os.getlogin()).hexdigest()
        data['source'] = 'UV-CDAT'
        data['source_version'] = '1.2.1'
        data['description'] = self.getDescription()
        data['stack_trace'] = self.errorDetails.toPlainText()
        data['severity'] = 'FATAL'
        data['comments'] = self.userComments.toPlainText()
        
        if get_vistrails_configuration().output != '':
            fname = get_vistrails_configuration().output
            # read at most last 5000 chars from output log
            with open(fname, "r") as f:
                f.seek (0, 2)           # Seek @ EOF
                fsize = f.tell()        # Get Size
                f.seek (max (fsize-5000, 0), 0) # Set pos @ last n chars
                data['execution_log'] = f.read()
        print urlencode(data)
        print "http://uvcdat.llnl.gov/UVCDATUsage/log/add/error/"
        result = urlopen("http://uvcdat.llnl.gov/UVCDATUsage/log/add/error/", 
                         urlencode(data))
        