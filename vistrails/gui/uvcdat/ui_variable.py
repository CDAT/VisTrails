# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'variable.ui'
#
# Created: Fri Aug 26 17:00:46 2011
#      by: PyQt4 UI code generator 4.8.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_VariableProperties(object):
    def setupUi(self, VariableProperties):
        VariableProperties.setObjectName(_fromUtf8("VariableProperties"))
        VariableProperties.resize(594, 614)
        self.verticalLayout = QtGui.QVBoxLayout(VariableProperties)
        self.verticalLayout.setSpacing(-1)
        self.verticalLayout.setMargin(10)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.lblName = QtGui.QLabel(VariableProperties)
        self.lblName.setObjectName(_fromUtf8("lblName"))
        self.horizontalLayout_2.addWidget(self.lblName)
        self.nameEdit = QtGui.QLineEdit(VariableProperties)
        self.nameEdit.setObjectName(_fromUtf8("nameEdit"))
        self.horizontalLayout_2.addWidget(self.nameEdit)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.lblLoadFrom = QtGui.QLabel(VariableProperties)
        self.lblLoadFrom.setObjectName(_fromUtf8("lblLoadFrom"))
        self.verticalLayout.addWidget(self.lblLoadFrom)
        self.originTabWidget = QtGui.QTabWidget(VariableProperties)
        self.originTabWidget.setDocumentMode(True)
        self.originTabWidget.setObjectName(_fromUtf8("originTabWidget"))
        self.tabFile = QtGui.QWidget()
        self.tabFile.setObjectName(_fromUtf8("tabFile"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.tabFile)
        self.verticalLayout_2.setMargin(10)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.lblFile = QtGui.QLabel(self.tabFile)
        self.lblFile.setObjectName(_fromUtf8("lblFile"))
        self.horizontalLayout_3.addWidget(self.lblFile)
        self.fileEdit = QtGui.QLineEdit(self.tabFile)
        self.fileEdit.setObjectName(_fromUtf8("fileEdit"))
        self.horizontalLayout_3.addWidget(self.fileEdit)
        self.tbOpenFile = QtGui.QToolButton(self.tabFile)
        self.tbOpenFile.setObjectName(_fromUtf8("tbOpenFile"))
        self.horizontalLayout_3.addWidget(self.tbOpenFile)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.lblVariable = QtGui.QLabel(self.tabFile)
        self.lblVariable.setObjectName(_fromUtf8("lblVariable"))
        self.horizontalLayout_4.addWidget(self.lblVariable)
        self.listWidget = QtGui.QListWidget(self.tabFile)
        self.listWidget.setObjectName(_fromUtf8("listWidget"))
        self.horizontalLayout_4.addWidget(self.listWidget)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.originTabWidget.addTab(self.tabFile, _fromUtf8(""))
        self.tabESGF = QtGui.QWidget()
        self.tabESGF.setObjectName(_fromUtf8("tabESGF"))
        self.originTabWidget.addTab(self.tabESGF, _fromUtf8(""))
        self.tabCalc = QtGui.QWidget()
        self.tabCalc.setObjectName(_fromUtf8("tabCalc"))
        self.originTabWidget.addTab(self.tabCalc, _fromUtf8(""))
        self.verticalLayout.addWidget(self.originTabWidget)
        self.gbDimensions = QtGui.QGroupBox(VariableProperties)
        self.gbDimensions.setObjectName(_fromUtf8("gbDimensions"))
        self.verticalLayout.addWidget(self.gbDimensions)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)
        self.btnSave = QtGui.QPushButton(VariableProperties)
        self.btnSave.setObjectName(_fromUtf8("btnSave"))
        self.horizontalLayout.addWidget(self.btnSave)
        self.btnSaveAs = QtGui.QPushButton(VariableProperties)
        self.btnSaveAs.setObjectName(_fromUtf8("btnSaveAs"))
        self.horizontalLayout.addWidget(self.btnSaveAs)
        self.btnRemove = QtGui.QPushButton(VariableProperties)
        self.btnRemove.setObjectName(_fromUtf8("btnRemove"))
        self.horizontalLayout.addWidget(self.btnRemove)
        self.btnCancel = QtGui.QPushButton(VariableProperties)
        self.btnCancel.setObjectName(_fromUtf8("btnCancel"))
        self.horizontalLayout.addWidget(self.btnCancel)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(VariableProperties)
        self.originTabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(VariableProperties)

    def retranslateUi(self, VariableProperties):
        VariableProperties.setWindowTitle(QtGui.QApplication.translate("VariableProperties", "Variable Properties", None, QtGui.QApplication.UnicodeUTF8))
        self.lblName.setText(QtGui.QApplication.translate("VariableProperties", "Name:", None, QtGui.QApplication.UnicodeUTF8))
        self.lblLoadFrom.setText(QtGui.QApplication.translate("VariableProperties", "Load variable from:", None, QtGui.QApplication.UnicodeUTF8))
        self.lblFile.setText(QtGui.QApplication.translate("VariableProperties", "File:", None, QtGui.QApplication.UnicodeUTF8))
        self.tbOpenFile.setText(QtGui.QApplication.translate("VariableProperties", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.lblVariable.setText(QtGui.QApplication.translate("VariableProperties", "Variable:", None, QtGui.QApplication.UnicodeUTF8))
        self.originTabWidget.setTabText(self.originTabWidget.indexOf(self.tabFile), QtGui.QApplication.translate("VariableProperties", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.originTabWidget.setTabText(self.originTabWidget.indexOf(self.tabESGF), QtGui.QApplication.translate("VariableProperties", "ESGF", None, QtGui.QApplication.UnicodeUTF8))
        self.originTabWidget.setTabText(self.originTabWidget.indexOf(self.tabCalc), QtGui.QApplication.translate("VariableProperties", "Calculator", None, QtGui.QApplication.UnicodeUTF8))
        self.gbDimensions.setTitle(QtGui.QApplication.translate("VariableProperties", "Dimensions", None, QtGui.QApplication.UnicodeUTF8))
        self.btnSave.setText(QtGui.QApplication.translate("VariableProperties", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.btnSaveAs.setText(QtGui.QApplication.translate("VariableProperties", "Save As", None, QtGui.QApplication.UnicodeUTF8))
        self.btnRemove.setText(QtGui.QApplication.translate("VariableProperties", "Remove", None, QtGui.QApplication.UnicodeUTF8))
        self.btnCancel.setText(QtGui.QApplication.translate("VariableProperties", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

import uvcdat_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    VariableProperties = QtGui.QWidget()
    ui = Ui_VariableProperties()
    ui.setupUi(VariableProperties)
    VariableProperties.show()
    sys.exit(app.exec_())

