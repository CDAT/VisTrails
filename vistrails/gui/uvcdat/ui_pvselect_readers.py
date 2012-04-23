# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui/uvcdat/pvselect_readers.ui'
#
# Created: Mon Apr 23 16:12:26 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_pvSelectReaders(object):
    def setupUi(self, pvSelectReaders):
        pvSelectReaders.setObjectName(_fromUtf8("pvSelectReaders"))
        pvSelectReaders.resize(400, 300)
        self.gridLayout = QtGui.QGridLayout(pvSelectReaders)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.readersListWidget = QtGui.QListWidget(pvSelectReaders)
        self.readersListWidget.setObjectName(_fromUtf8("readersListWidget"))
        self.gridLayout.addWidget(self.readersListWidget, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(pvSelectReaders)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(pvSelectReaders)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), pvSelectReaders.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), pvSelectReaders.reject)
        QtCore.QMetaObject.connectSlotsByName(pvSelectReaders)

    def retranslateUi(self, pvSelectReaders):
        pvSelectReaders.setWindowTitle(QtGui.QApplication.translate("pvSelectReaders", "Dialog", None, QtGui.QApplication.UnicodeUTF8))

