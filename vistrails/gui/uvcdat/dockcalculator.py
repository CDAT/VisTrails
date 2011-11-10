from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_dockcalculator import Ui_DockCalculator
from qtbrowser.commandLineWidget import QCommandLine


class DockCalculator(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockCalculator, self).__init__(parent)
        self.ui = Ui_DockCalculator()
        self.ui.setupUi(self)
        self.root=parent.root
        self.setWidget(QCommandLine(self))
        
