###############################################################################
#                                                                             #
# Module:       calculator dock module                                        #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI calculator dock                                   #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
from PyQt4 import QtCore, QtGui

from commandLineWidget import QCommandLine


class DockCalculator(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockCalculator, self).__init__(parent)
        self.setWindowTitle("Calculator")
        self.root=parent.root
        self.setWidget(QCommandLine(self))
        
