# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'diagnosticsDockWidget.ui'
#
# Created: Wed Aug  7 13:32:50 2013
#      by: PyQt4 UI code generator 4.10
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_DiagnosticDockWidget(object):
    def setupUi(self, DiagnosticDockWidget):
        DiagnosticDockWidget.setObjectName(_fromUtf8("DiagnosticDockWidget"))
        DiagnosticDockWidget.resize(465, 496)
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.labelType = QtGui.QLabel(self.dockWidgetContents)
        self.labelType.setObjectName(_fromUtf8("labelType"))
        self.horizontalLayout.addWidget(self.labelType)
        self.comboBox = QtGui.QComboBox(self.dockWidgetContents)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.horizontalLayout.addWidget(self.comboBox)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.treeWidget = QtGui.QTreeWidget(self.dockWidgetContents)
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.verticalLayout_2.addWidget(self.treeWidget)
        self.buttonBox = QtGui.QDialogButtonBox(self.dockWidgetContents)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout_2.addWidget(self.buttonBox)
        DiagnosticDockWidget.setWidget(self.dockWidgetContents)

        self.retranslateUi(DiagnosticDockWidget)
        QtCore.QMetaObject.connectSlotsByName(DiagnosticDockWidget)

    def retranslateUi(self, DiagnosticDockWidget):
        DiagnosticDockWidget.setWindowTitle(_translate("DiagnosticDockWidget", "Diagnostics", None))
        self.labelType.setText(_translate("DiagnosticDockWidget", "Diagnostic", None))

