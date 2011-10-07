from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_docktemplate import Ui_DockTemplate

class DockTemplate(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockTemplate, self).__init__(parent)
        self.ui = Ui_DockTemplate()
        self.ui.setupUi(self)
        
    