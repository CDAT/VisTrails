# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'vistrails/gui/uvcdat/variablePlotQueueWidget.ui'
#
# Created: Wed Jan  2 14:29:36 2013
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_variablePlotQueueWidget(object):
    def setupUi(self, variablePlotQueueWidget):
        variablePlotQueueWidget.setObjectName(_fromUtf8("variablePlotQueueWidget"))
        variablePlotQueueWidget.resize(422, 440)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icons/resources/icons/list_view.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        variablePlotQueueWidget.setWindowIcon(icon)
        self.gridLayout = QtGui.QGridLayout(variablePlotQueueWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(variablePlotQueueWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.btnAllPlots = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnAllPlots.setObjectName(_fromUtf8("btnAllPlots"))
        self.horizontalLayout_2.addWidget(self.btnAllPlots)
        self.btnNonePlots = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnNonePlots.setObjectName(_fromUtf8("btnNonePlots"))
        self.horizontalLayout_2.addWidget(self.btnNonePlots)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.btnRemovePlots = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnRemovePlots.setObjectName(_fromUtf8("btnRemovePlots"))
        self.horizontalLayout_2.addWidget(self.btnRemovePlots)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.listWidgetPlots = QtGui.QListWidget(variablePlotQueueWidget)
        self.listWidgetPlots.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self.listWidgetPlots.setTabKeyNavigation(True)
        self.listWidgetPlots.setAlternatingRowColors(True)
        self.listWidgetPlots.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.listWidgetPlots.setObjectName(_fromUtf8("listWidgetPlots"))
        self.verticalLayout.addWidget(self.listWidgetPlots)
        self.label_2 = QtGui.QLabel(variablePlotQueueWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout.addWidget(self.label_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.btnAllVars = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnAllVars.setObjectName(_fromUtf8("btnAllVars"))
        self.horizontalLayout_3.addWidget(self.btnAllVars)
        self.btnNoneVars = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnNoneVars.setObjectName(_fromUtf8("btnNoneVars"))
        self.horizontalLayout_3.addWidget(self.btnNoneVars)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.btnRemoveVars = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnRemoveVars.setObjectName(_fromUtf8("btnRemoveVars"))
        self.horizontalLayout_3.addWidget(self.btnRemoveVars)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.listWidgetVariables = QtGui.QListWidget(variablePlotQueueWidget)
        self.listWidgetVariables.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self.listWidgetVariables.setTabKeyNavigation(True)
        self.listWidgetVariables.setAlternatingRowColors(True)
        self.listWidgetVariables.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.listWidgetVariables.setObjectName(_fromUtf8("listWidgetVariables"))
        self.verticalLayout.addWidget(self.listWidgetVariables)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.btnClose = QtGui.QPushButton(variablePlotQueueWidget)
        self.btnClose.setObjectName(_fromUtf8("btnClose"))
        self.horizontalLayout.addWidget(self.btnClose)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(variablePlotQueueWidget)
        QtCore.QMetaObject.connectSlotsByName(variablePlotQueueWidget)

    def retranslateUi(self, variablePlotQueueWidget):
        variablePlotQueueWidget.setWindowTitle(QtGui.QApplication.translate("variablePlotQueueWidget", "Variable Plot Queue Manager", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Plot Queue", None, QtGui.QApplication.UnicodeUTF8))
        self.btnAllPlots.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Select All", None, QtGui.QApplication.UnicodeUTF8))
        self.btnNonePlots.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Select None", None, QtGui.QApplication.UnicodeUTF8))
        self.btnRemovePlots.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Remove", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Variable Queue", None, QtGui.QApplication.UnicodeUTF8))
        self.btnAllVars.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Select All", None, QtGui.QApplication.UnicodeUTF8))
        self.btnNoneVars.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Select None", None, QtGui.QApplication.UnicodeUTF8))
        self.btnRemoveVars.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Remove", None, QtGui.QApplication.UnicodeUTF8))
        self.btnClose.setText(QtGui.QApplication.translate("variablePlotQueueWidget", "Close", None, QtGui.QApplication.UnicodeUTF8))

import uvcdat_rc
