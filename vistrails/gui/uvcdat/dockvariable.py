from PyQt4 import QtCore, QtGui

from gui.uvcdat.variable import VariableProperties
from gui.uvcdat.definedVariableWidget import QDefinedVariableWidget

from qtbrowser import customizeVCDAT


class DockVariable(QtGui.QDockWidget):
    def __init__(self, parent=None):
        QtGui.QDockWidget.__init__(self, parent)
        self.root=parent.root
        self.lastDirectory=customizeVCDAT.lastDirectory
        self.setWidget(QDefinedVariableWidget(self))
        self.connectSignals()
        
    def connectSignals(self):
        #self.ui.btnNewVar.clicked.connect(self.newVariable)
        pass
        
    def newVariable(self):
        varProp = VariableProperties(self)
        varProp.show()
        
