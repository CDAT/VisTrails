# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'cdmsCacheWidget.ui'
#
# Created: Tue Nov 20 14:13:06 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_cdmsCacheWidget(object):
    def setupUi(self, cdmsCacheWidget):
        cdmsCacheWidget.setObjectName(_fromUtf8("cdmsCacheWidget"))
        cdmsCacheWidget.resize(400, 300)
        self.gridLayout = QtGui.QGridLayout(cdmsCacheWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.btnAll = QtGui.QPushButton(cdmsCacheWidget)
        self.btnAll.setObjectName(_fromUtf8("btnAll"))
        self.horizontalLayout_2.addWidget(self.btnAll)
        self.btnNone = QtGui.QPushButton(cdmsCacheWidget)
        self.btnNone.setObjectName(_fromUtf8("btnNone"))
        self.horizontalLayout_2.addWidget(self.btnNone)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.listWidget = QtGui.QListWidget(cdmsCacheWidget)
        self.listWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self.listWidget.setTabKeyNavigation(True)
        self.listWidget.setAlternatingRowColors(True)
        self.listWidget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.listWidget.setObjectName(_fromUtf8("listWidget"))
        self.verticalLayout.addWidget(self.listWidget)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.btnClear = QtGui.QPushButton(cdmsCacheWidget)
        self.btnClear.setObjectName(_fromUtf8("btnClear"))
        self.horizontalLayout.addWidget(self.btnClear)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.btnClose = QtGui.QPushButton(cdmsCacheWidget)
        self.btnClose.setObjectName(_fromUtf8("btnClose"))
        self.horizontalLayout.addWidget(self.btnClose)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(cdmsCacheWidget)
        QtCore.QMetaObject.connectSlotsByName(cdmsCacheWidget)

    def retranslateUi(self, cdmsCacheWidget):
        cdmsCacheWidget.setWindowTitle(QtGui.QApplication.translate("cdmsCacheWidget", "CDMS Cache Manager", None, QtGui.QApplication.UnicodeUTF8))
        self.btnAll.setText(QtGui.QApplication.translate("cdmsCacheWidget", "Select All", None, QtGui.QApplication.UnicodeUTF8))
        self.btnNone.setText(QtGui.QApplication.translate("cdmsCacheWidget", "Select None", None, QtGui.QApplication.UnicodeUTF8))
        self.btnClear.setText(QtGui.QApplication.translate("cdmsCacheWidget", "Delete", None, QtGui.QApplication.UnicodeUTF8))
        self.btnClose.setText(QtGui.QApplication.translate("cdmsCacheWidget", "Close", None, QtGui.QApplication.UnicodeUTF8))

