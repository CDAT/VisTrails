# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvtabwidget.ui'
#
# Created: Fri Nov 25 10:29:11 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_PVTabWidget(object):
    def setupUi(self, PVTabWidget):
        PVTabWidget.setObjectName("PVTabWidget")
        PVTabWidget.resize(510, 127)
        self.gridLayout = QtGui.QGridLayout(PVTabWidget)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtGui.QLabel(PVTabWidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.pvSelectedFileLineEdit = QtGui.QLineEdit(PVTabWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pvSelectedFileLineEdit.sizePolicy().hasHeightForWidth())
        self.pvSelectedFileLineEdit.setSizePolicy(sizePolicy)
        self.pvSelectedFileLineEdit.setMinimumSize(QtCore.QSize(400, 20))
        self.pvSelectedFileLineEdit.setObjectName("pvSelectedFileLineEdit")
        self.gridLayout.addWidget(self.pvSelectedFileLineEdit, 0, 1, 1, 1)
        self.pvPickLocalFileButton = QtGui.QToolButton(PVTabWidget)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/16x16/browse"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pvPickLocalFileButton.setIcon(icon)
        self.pvPickLocalFileButton.setObjectName("pvPickLocalFileButton")
        self.gridLayout.addWidget(self.pvPickLocalFileButton, 0, 2, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lVar = QtGui.QLabel(PVTabWidget)
        self.lVar.setObjectName("lVar")
        self.horizontalLayout_2.addWidget(self.lVar)
        self.cbVar = QtGui.QComboBox(PVTabWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbVar.sizePolicy().hasHeightForWidth())
        self.cbVar.setSizePolicy(sizePolicy)
        self.cbVar.setMinimumSize(QtCore.QSize(100, 20))
        self.cbVar.setObjectName("cbVar")
        self.horizontalLayout_2.addWidget(self.cbVar)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 2, 3, 1, 1)

        self.retranslateUi(PVTabWidget)
        QtCore.QMetaObject.connectSlotsByName(PVTabWidget)

    def retranslateUi(self, PVTabWidget):
        PVTabWidget.setWindowTitle(QtGui.QApplication.translate("PVTabWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("PVTabWidget", "File:", None, QtGui.QApplication.UnicodeUTF8))
        self.pvPickLocalFileButton.setText(QtGui.QApplication.translate("PVTabWidget", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.lVar.setText(QtGui.QApplication.translate("PVTabWidget", "Variables:", None, QtGui.QApplication.UnicodeUTF8))

import pv_rc
import pv_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    PVTabWidget = QtGui.QWidget()
    ui = Ui_PVTabWidget()
    ui.setupUi(PVTabWidget)
    PVTabWidget.show()
    sys.exit(app.exec_())

