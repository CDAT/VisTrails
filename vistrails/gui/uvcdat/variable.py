from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_variable import Ui_VariableProperties
from qtbrowser.esgf import QEsgfBrowser
from qtbrowser.commandLineWidget import QCommandLine
class VariableProperties(QtGui.QWidget):
    def __init__(self, parent=None):
        super(VariableProperties, self).__init__(parent)
        self.ui = Ui_VariableProperties()
        self.ui.setupUi(self)
        self.root = self
        self.createESGFTab()
        self.createCalculatorTab()
        self.connectSignals()
        
    @classmethod
    def instance(klass):
        if not hasattr(klass, '_instance'):
            klass._instance = klass()
        return klass._instance

    def connectSignals(self):
        self.ui.btnCancel.clicked.connect(self.close)
        
    def createESGFTab(self):
        layout = QtGui.QVBoxLayout()
        self.esgfBrowser = QEsgfBrowser(self)
        layout.addWidget(self.esgfBrowser)
        self.ui.tabESGF.setLayout(layout)
    
    def createCalculatorTab(self):
        layout = QtGui.QVBoxLayout()
        self.calculator = QCommandLine(self)
        layout.addWidget(self.calculator)
        self.ui.tabCalc.setLayout(layout)