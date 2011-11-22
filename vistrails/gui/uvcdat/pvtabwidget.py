from PyQt4 import QtCore, QtGui
from ui_pvtabwidget import Ui_PVTabWidget
from paraview.simple import *

class PVTabWidget(QtGui.QTabWidget, Ui_PVTabWidget):
    def __init__(self, parent=None):
        super(PVTabWidget, self).__init__(parent)
        self.setupUi(self)
        self.root = self        
        #self.connectSignals()

    #def connectSignals(self):
    #    self.buttonBox.accepted.connect(self.onAccepted)
    #    self.buttonBox.rejected.connect(self.close)  