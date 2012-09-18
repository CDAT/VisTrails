# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvsubmit_job.ui'
#
# Created: Tue Sep 18 15:01:24 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(580, 378)
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.localBrowserButton = QtGui.QToolButton(Dialog)
        self.localBrowserButton.setObjectName(_fromUtf8("localBrowserButton"))
        self.gridLayout.addWidget(self.localBrowserButton, 1, 2, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 4, 1, 1, 1)
        self.inputPath = QtGui.QLineEdit(Dialog)
        self.inputPath.setObjectName(_fromUtf8("inputPath"))
        self.gridLayout.addWidget(self.inputPath, 0, 1, 1, 1)
        self.remoteBrowserButton = QtGui.QToolButton(Dialog)
        self.remoteBrowserButton.setObjectName(_fromUtf8("remoteBrowserButton"))
        self.gridLayout.addWidget(self.remoteBrowserButton, 0, 2, 1, 1)
        self.outputPath = QtGui.QLineEdit(Dialog)
        self.outputPath.setObjectName(_fromUtf8("outputPath"))
        self.gridLayout.addWidget(self.outputPath, 1, 1, 1, 1)
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 3, 1, 1, 1)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.queueNames = QtGui.QComboBox(Dialog)
        self.queueNames.setObjectName(_fromUtf8("queueNames"))
        self.gridLayout.addWidget(self.queueNames, 2, 1, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Submit Job", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Input Directory", None, QtGui.QApplication.UnicodeUTF8))
        self.localBrowserButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.remoteBrowserButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Output Directory", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Submit Queue", None, QtGui.QApplication.UnicodeUTF8))

