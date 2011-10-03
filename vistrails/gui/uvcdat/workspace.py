from PyQt4 import QtCore, QtGui

from uvcdat.gui.ui_workspace import Ui_Workspace

class Workspace(QtGui.QDockWidget, Ui_Workspace):
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.setupUi(self)
        
    