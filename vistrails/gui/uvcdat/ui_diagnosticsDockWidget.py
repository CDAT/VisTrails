# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'diagnosticsDockWidget.ui'
#
# Created: Fri Aug 16 09:27:08 2013
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
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.comboBoxVariable = QtGui.QComboBox(self.dockWidgetContents)
        self.comboBoxVariable.setObjectName(_fromUtf8("comboBoxVariable"))
        self.gridLayout.addWidget(self.comboBoxVariable, 1, 0, 1, 1)
        self.comboBoxType = QtGui.QComboBox(self.dockWidgetContents)
        self.comboBoxType.setObjectName(_fromUtf8("comboBoxType"))
        self.gridLayout.addWidget(self.comboBoxType, 0, 0, 1, 1)
        self.comboBoxObservation = QtGui.QComboBox(self.dockWidgetContents)
        self.comboBoxObservation.setObjectName(_fromUtf8("comboBoxObservation"))
        self.gridLayout.addWidget(self.comboBoxObservation, 0, 1, 1, 1)
        self.comboBoxSeason = QtGui.QComboBox(self.dockWidgetContents)
        self.comboBoxSeason.setObjectName(_fromUtf8("comboBoxSeason"))
        self.gridLayout.addWidget(self.comboBoxSeason, 1, 1, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout)
        self.treeWidget = QtGui.QTreeWidget(self.dockWidgetContents)
        self.treeWidget.setAlternatingRowColors(True)
        self.treeWidget.setTextElideMode(QtCore.Qt.ElideRight)
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.treeWidget.header().setVisible(False)
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

