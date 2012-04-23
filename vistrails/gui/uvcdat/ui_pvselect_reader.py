# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui/uvcdat/pvselect_reader.ui'
#
# Created: Mon Apr 23 17:24:32 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_PVSelectReaderDialog(object):
    def setupUi(self, PVSelectReaderDialog):
        PVSelectReaderDialog.setObjectName(_fromUtf8("PVSelectReaderDialog"))
        PVSelectReaderDialog.resize(400, 300)
        self.gridLayout = QtGui.QGridLayout(PVSelectReaderDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.readersListWidget = QtGui.QListWidget(PVSelectReaderDialog)
        self.readersListWidget.setObjectName(_fromUtf8("readersListWidget"))
        self.gridLayout.addWidget(self.readersListWidget, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(PVSelectReaderDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(PVSelectReaderDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), PVSelectReaderDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), PVSelectReaderDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(PVSelectReaderDialog)

    def retranslateUi(self, PVSelectReaderDialog):
        PVSelectReaderDialog.setWindowTitle(QtGui.QApplication.translate("PVSelectReaderDialog", "Select a reader", None, QtGui.QApplication.UnicodeUTF8))

