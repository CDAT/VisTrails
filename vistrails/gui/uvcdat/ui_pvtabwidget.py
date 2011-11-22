# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvtabwidget.ui'
#
# Created: Tue Nov 22 02:03:26 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_PVTabWidget(object):
    def setupUi(self, PVTabWidget):
        PVTabWidget.setObjectName("PVTabWidget")
        PVTabWidget.resize(104, 44)
        self.formLayout = QtGui.QFormLayout(PVTabWidget)
        self.formLayout.setObjectName("formLayout")
        self.serverConnectButton = QtGui.QPushButton(PVTabWidget)
        self.serverConnectButton.setObjectName("serverConnectButton")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.serverConnectButton)

        self.retranslateUi(PVTabWidget)
        QtCore.QMetaObject.connectSlotsByName(PVTabWidget)

    def retranslateUi(self, PVTabWidget):
        PVTabWidget.setWindowTitle(QtGui.QApplication.translate("PVTabWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.serverConnectButton.setText(QtGui.QApplication.translate("PVTabWidget", "Connect", None, QtGui.QApplication.UnicodeUTF8))

