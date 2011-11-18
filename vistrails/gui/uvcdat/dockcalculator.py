from PyQt4 import QtCore, QtGui

from commandLineWidget import QCommandLine


class DockCalculator(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockCalculator, self).__init__(parent)
        self.root=parent.root
        self.setWidget(QCommandLine(self))
        
