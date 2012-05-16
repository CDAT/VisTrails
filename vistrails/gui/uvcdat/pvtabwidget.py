from PyQt4 import QtCore, QtGui
from ui_pvtabwidget import Ui_PVTabWidget
from paraview.simple import *

class PVTabWidget(QtGui.QTabWidget, Ui_PVTabWidget):
    def __init__(self, parent=None):
        super(PVTabWidget, self).__init__(parent)
        self.setupUi(self)
        self.applyButton.setDisabled(True)
        self.disableStride()
        self.root = self
              
    def populateVars(self, variables):
        self.cbVar.clear()
        for variable in variables:
            self.cbVar.addItem(variable)

    def getStride(self):
        newList = []
        newList.append(self.strideLineEditX.text().toDouble()[0])
        newList.append(self.strideLineEditY.text().toDouble()[0])
        newList.append(self.strideLineEditZ.text().toDouble()[0])
        return newList

    def disableStride(self):
        self.strideLabel.setDisabled(True)
        self.strideLineEditX.setDisabled(True)
        self.strideLineEditY.setDisabled(True)
        self.strideLineEditZ.setDisabled(True)

    def enableStride(self):
        self.strideLabel.setDisabled(False)
        self.strideLineEditX.setEnabled(True)
        self.strideLineEditY.setEnabled(True)
        self.strideLineEditZ.setEnabled(True)