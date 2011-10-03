from PyQt4 import QtCore, QtGui
from qtbrowser.plotViewWidget import QPlotOptionsWidget
from qtbrowser.vcsPlotControllerWidget import QVCSPlotController
from qtbrowser.vcsPageLayoutWidget import QPageLayoutWidget
import vcs

class PlotProperties(QtGui.QWidget):
    def __init__(self, parent=None):
        super(PlotProperties, self).__init__(parent)
        self.setWindowTitle("Isofill Properties")
        self.canvas = []
        self.canvas.append(vcs.init())
        self.root = self
        self.plotsSetup=QPageLayoutWidget(parent=self)
        self.plotsSetup.hide()
        self.plotOptions = QPlotOptionsWidget(self)
        self.plotOptions.setVisible(False)
        self.plotOptions.plotTypeCombo.setCurrentIndex(1)
        self.plotProp = QVCSPlotController(self)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.plotOptions)
        layout.addWidget(self.plotProp)
        self.setLayout(layout)
        
    @classmethod
    def instance(klass):
        if not hasattr(klass, '_instance'):
            klass._instance = klass()
        return klass._instance
    
    def plot(self):
        pass