from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_dockvariable import Ui_DockVariable
from gui.uvcdat.variable import VariableProperties

class DockVariable(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockVariable, self).__init__(parent)
        self.ui = Ui_DockVariable()
        self.ui.setupUi(self)
        self.ui.btnNewVar.clicked.connect(self.newVariable)
        
    def newVariable(self):
        varProp = VariableProperties.instance()
        varProp.show()