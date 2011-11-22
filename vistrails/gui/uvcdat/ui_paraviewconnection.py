# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'paraviewconnection.ui'
#
# Created: Mon Nov 21 21:09:20 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_paraviewConnectionDialog(object):
    def setupUi(self, paraviewConnectionDialog):
        paraviewConnectionDialog.setObjectName("paraviewConnectionDialog")
        paraviewConnectionDialog.resize(301, 94)
        self.formLayout = QtGui.QFormLayout(paraviewConnectionDialog)
        self.formLayout.setObjectName("formLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setMargin(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtGui.QLabel(paraviewConnectionDialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.host = QtGui.QLineEdit(paraviewConnectionDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.host.sizePolicy().hasHeightForWidth())
        self.host.setSizePolicy(sizePolicy)
        self.host.setMinimumSize(QtCore.QSize(120, 10))
        self.host.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.host.setBaseSize(QtCore.QSize(120, 10))
        self.host.setObjectName("host")
        self.horizontalLayout.addWidget(self.host)
        self.label_2 = QtGui.QLabel(paraviewConnectionDialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.port = QtGui.QSpinBox(paraviewConnectionDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.port.sizePolicy().hasHeightForWidth())
        self.port.setSizePolicy(sizePolicy)
        self.port.setMaximum(65535)
        self.port.setProperty("value", 11111)
        self.port.setObjectName("port")
        self.horizontalLayout.addWidget(self.port)
        self.formLayout.setLayout(0, QtGui.QFormLayout.LabelRole, self.horizontalLayout)
        self.buttonBox = QtGui.QDialogButtonBox(paraviewConnectionDialog)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.buttonBox)

        self.retranslateUi(paraviewConnectionDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), paraviewConnectionDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), paraviewConnectionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(paraviewConnectionDialog)

    def retranslateUi(self, paraviewConnectionDialog):
        paraviewConnectionDialog.setWindowTitle(QtGui.QApplication.translate("paraviewConnectionDialog", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("paraviewConnectionDialog", "Host", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("paraviewConnectionDialog", "Port", None, QtGui.QApplication.UnicodeUTF8))

