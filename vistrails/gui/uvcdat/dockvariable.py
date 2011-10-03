from PyQt4 import QtCore, QtGui

from uvcdat.gui.ui_dockvariable import Ui_DockVariable
from uvcdat.gui.variable import VariableProperties

class DockVariable(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockVariable, self).__init__(parent)
        self.ui = Ui_DockVariable()
        self.ui.setupUi(self)
        self.ui.btnNewVar.clicked.connect(self.newVariable)
        
    def newVariable(self):
        varProp = VariableProperties.instance()
        varProp.show()