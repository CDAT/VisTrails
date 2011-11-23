# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvtabwidget.ui'
#
# Created: Wed Nov 23 15:32:37 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_PVTabWidget(object):
    def setupUi(self, PVTabWidget):
        PVTabWidget.setObjectName(_fromUtf8("PVTabWidget"))
        PVTabWidget.resize(257, 198)
        self.widget = QtGui.QWidget(PVTabWidget)
        self.widget.setGeometry(QtCore.QRect(29, 8, 191, 65))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.widget)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.serverConnectButton = QtGui.QPushButton(self.widget)
        self.serverConnectButton.setObjectName(_fromUtf8("serverConnectButton"))
        self.verticalLayout.addWidget(self.serverConnectButton)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lVar = QtGui.QLabel(self.widget)
        self.lVar.setObjectName(_fromUtf8("lVar"))
        self.horizontalLayout.addWidget(self.lVar)
        self.cbVar = QtGui.QComboBox(self.widget)
        self.cbVar.setObjectName(_fromUtf8("cbVar"))
        self.horizontalLayout.addWidget(self.cbVar)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(PVTabWidget)
        QtCore.QMetaObject.connectSlotsByName(PVTabWidget)

    def retranslateUi(self, PVTabWidget):
        PVTabWidget.setWindowTitle(QtGui.QApplication.translate("PVTabWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.serverConnectButton.setText(QtGui.QApplication.translate("PVTabWidget", "Connect", None, QtGui.QApplication.UnicodeUTF8))
        self.lVar.setText(QtGui.QApplication.translate("PVTabWidget", "Variables:", None, QtGui.QApplication.UnicodeUTF8))


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    PVTabWidget = QtGui.QWidget()
    ui = Ui_PVTabWidget()
    ui.setupUi(PVTabWidget)
    PVTabWidget.show()
    sys.exit(app.exec_())

