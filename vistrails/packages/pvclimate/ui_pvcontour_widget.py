# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvcontour_widget.ui'
#
# Created: Thu Dec 13 22:18:32 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_PVContourWidget(object):
    def setupUi(self, PVContourWidget):
        PVContourWidget.setObjectName(_fromUtf8("PVContourWidget"))
        PVContourWidget.resize(506, 336)
        self.gridLayout = QtGui.QGridLayout(PVContourWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.isoValuesListView = QtGui.QListView(PVContourWidget)
        self.isoValuesListView.setObjectName(_fromUtf8("isoValuesListView"))
        self.horizontalLayout.addWidget(self.isoValuesListView)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.groupBox_2 = QtGui.QGroupBox(PVContourWidget)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.label_4 = QtGui.QLabel(self.groupBox_2)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.verticalLayout_2.addWidget(self.label_4)
        self.valuesLineEdit = QtGui.QLineEdit(self.groupBox_2)
        self.valuesLineEdit.setObjectName(_fromUtf8("valuesLineEdit"))
        self.verticalLayout_2.addWidget(self.valuesLineEdit)
        self.verticalLayout_3.addWidget(self.groupBox_2)
        self.groupBox = QtGui.QGroupBox(PVContourWidget)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.firstValueLineEdit = QtGui.QLineEdit(self.groupBox)
        self.firstValueLineEdit.setText(_fromUtf8(""))
        self.firstValueLineEdit.setObjectName(_fromUtf8("firstValueLineEdit"))
        self.verticalLayout.addWidget(self.firstValueLineEdit)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout.addWidget(self.label_2)
        self.lastValueLineEdit = QtGui.QLineEdit(self.groupBox)
        self.lastValueLineEdit.setText(_fromUtf8(""))
        self.lastValueLineEdit.setObjectName(_fromUtf8("lastValueLineEdit"))
        self.verticalLayout.addWidget(self.lastValueLineEdit)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.verticalLayout.addWidget(self.label_3)
        self.stepValueEdit = QtGui.QLineEdit(self.groupBox)
        self.stepValueEdit.setObjectName(_fromUtf8("stepValueEdit"))
        self.verticalLayout.addWidget(self.stepValueEdit)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.verticalLayout_4 = QtGui.QVBoxLayout()
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.applyButton = QtGui.QPushButton(PVContourWidget)
        self.applyButton.setObjectName(_fromUtf8("applyButton"))
        self.verticalLayout_4.addWidget(self.applyButton)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem1)
        self.gridLayout.addLayout(self.verticalLayout_4, 0, 1, 1, 1)

        self.retranslateUi(PVContourWidget)
        QtCore.QMetaObject.connectSlotsByName(PVContourWidget)

    def retranslateUi(self, PVContourWidget):
        PVContourWidget.setWindowTitle(QtGui.QApplication.translate("PVContourWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(QtGui.QApplication.translate("PVContourWidget", "List", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("PVContourWidget", "Values", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("PVContourWidget", "Range", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("PVContourWidget", "First Value", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("PVContourWidget", "Last Value", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("PVContourWidget", "Step", None, QtGui.QApplication.UnicodeUTF8))
        self.applyButton.setText(QtGui.QApplication.translate("PVContourWidget", "Apply", None, QtGui.QApplication.UnicodeUTF8))

