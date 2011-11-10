# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uvcdat/gui/dockcalculator.ui'
#
# Created: Tue Oct 11 14:51:50 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_DockCalculator(object):
    def setupUi(self, DockCalculator):
        DockCalculator.setObjectName(_fromUtf8("DockCalculator"))
        DockCalculator.resize(400, 300)
        self.mainWidget = QtGui.QWidget()
        self.mainWidget.setObjectName(_fromUtf8("mainWidget"))
        DockCalculator.setWidget(self.mainWidget)

        self.retranslateUi(DockCalculator)
        QtCore.QMetaObject.connectSlotsByName(DockCalculator)

    def retranslateUi(self, DockCalculator):
        DockCalculator.setWindowTitle(QtGui.QApplication.translate("DockCalculator", "Calculator", None, QtGui.QApplication.UnicodeUTF8))

import uvcdat_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    DockCalculator = QtGui.QDockWidget()
    ui = Ui_DockCalculator()
    ui.setupUi(DockCalculator)
    DockCalculator.show()
    sys.exit(app.exec_())

