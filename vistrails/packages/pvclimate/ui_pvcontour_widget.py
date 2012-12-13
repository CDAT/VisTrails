# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvcontour_widget.ui'
#
# Created: Thu Dec 13 12:00:54 2012
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
        PVContourWidget.resize(400, 298)
        self.gridLayout = QtGui.QGridLayout(PVContourWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.isoValuesListView = QtGui.QListView(PVContourWidget)
        self.isoValuesListView.setObjectName(_fromUtf8("isoValuesListView"))
        self.gridLayout.addWidget(self.isoValuesListView, 0, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(PVContourWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.firstValueLineEdit = QtGui.QLineEdit(PVContourWidget)
        self.firstValueLineEdit.setObjectName(_fromUtf8("firstValueLineEdit"))
        self.verticalLayout.addWidget(self.firstValueLineEdit)
        self.label_2 = QtGui.QLabel(PVContourWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout.addWidget(self.label_2)
        self.lastValueLineEdit = QtGui.QLineEdit(PVContourWidget)
        self.lastValueLineEdit.setObjectName(_fromUtf8("lastValueLineEdit"))
        self.verticalLayout.addWidget(self.lastValueLineEdit)
        self.label_3 = QtGui.QLabel(PVContourWidget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.verticalLayout.addWidget(self.label_3)
        self.stepValueEdit = QtGui.QLineEdit(PVContourWidget)
        self.stepValueEdit.setObjectName(_fromUtf8("stepValueEdit"))
        self.verticalLayout.addWidget(self.stepValueEdit)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.verticalLayout, 0, 1, 1, 1)
        self.applyButton = QtGui.QPushButton(PVContourWidget)
        self.applyButton.setObjectName(_fromUtf8("applyButton"))
        self.gridLayout.addWidget(self.applyButton, 1, 1, 1, 1)
        self.gridLayout.setColumnStretch(0, 1)

        self.retranslateUi(PVContourWidget)
        QtCore.QMetaObject.connectSlotsByName(PVContourWidget)

    def retranslateUi(self, PVContourWidget):
        PVContourWidget.setWindowTitle(QtGui.QApplication.translate("PVContourWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("PVContourWidget", "First Value", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("PVContourWidget", "Last Value", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("PVContourWidget", "Step", None, QtGui.QApplication.UnicodeUTF8))
        self.applyButton.setText(QtGui.QApplication.translate("PVContourWidget", "Apply", None, QtGui.QApplication.UnicodeUTF8))

