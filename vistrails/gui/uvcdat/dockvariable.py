###############################################################################
#                                                                             #
# Module:       variable dock module                                          #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI variable dock                                     #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
from PyQt4 import QtCore, QtGui

from gui.uvcdat.variable import VariableProperties
from gui.uvcdat.definedVariableWidget import QDefinedVariableWidget

import customizeUVCDAT


class DockVariable(QtGui.QDockWidget):
    def __init__(self, parent=None):
        QtGui.QDockWidget.__init__(self, parent)
        self.setWindowTitle("Variables")
        self.root=parent.root
        self.lastDirectory=customizeUVCDAT.lastDirectory
        self.setWidget(QDefinedVariableWidget(self))
        self.connectSignals()

    def connectSignals(self):
        #self.ui.btnNewVar.clicked.connect(self.newVariable)
        pass

    def newVariable(self):
        varProp = VariableProperties(self)
        varProp.show()

