# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dockplot.ui'
#
# Created: Fri Aug 26 11:47:48 2011
#      by: PyQt4 UI code generator 4.8.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_DockPlot(object):
    def setupUi(self, DockPlot):
        DockPlot.setObjectName(_fromUtf8("DockPlot"))
        DockPlot.resize(400, 300)
        self.mainWidget = QtGui.QWidget()
        self.mainWidget.setObjectName(_fromUtf8("mainWidget"))
        DockPlot.setWidget(self.mainWidget)

        self.retranslateUi(DockPlot)
        QtCore.QMetaObject.connectSlotsByName(DockPlot)

    def retranslateUi(self, DockPlot):
        DockPlot.setWindowTitle(QtGui.QApplication.translate("DockPlot", "Plots and Analyses", None, QtGui.QApplication.UnicodeUTF8))

import uvcdat_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    DockPlot = QtGui.QDockWidget()
    ui = Ui_DockPlot()
    ui.setupUi(DockPlot)
    DockPlot.show()
    sys.exit(app.exec_())

