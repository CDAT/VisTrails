# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvslice_widget.ui'
#
# Created: Mon Dec 17 18:55:17 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(585, 352)
        self.gridLayout = QtGui.QGridLayout(Form)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.groupBox = QtGui.QGroupBox(Form)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.sliceNormalXLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceNormalXLineEdit.setObjectName(_fromUtf8("sliceNormalXLineEdit"))
        self.horizontalLayout_2.addWidget(self.sliceNormalXLineEdit)
        self.sliceNormalYLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceNormalYLineEdit.setObjectName(_fromUtf8("sliceNormalYLineEdit"))
        self.horizontalLayout_2.addWidget(self.sliceNormalYLineEdit)
        self.sliceNormalZLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceNormalZLineEdit.setObjectName(_fromUtf8("sliceNormalZLineEdit"))
        self.horizontalLayout_2.addWidget(self.sliceNormalZLineEdit)
        self.horizontalLayout_2.setStretch(0, 1)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.sliceOriginXLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceOriginXLineEdit.setObjectName(_fromUtf8("sliceOriginXLineEdit"))
        self.horizontalLayout.addWidget(self.sliceOriginXLineEdit)
        self.sliceOriginYLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceOriginYLineEdit.setObjectName(_fromUtf8("sliceOriginYLineEdit"))
        self.horizontalLayout.addWidget(self.sliceOriginYLineEdit)
        self.sliceOriginZLineEdit = QtGui.QLineEdit(self.groupBox)
        self.sliceOriginZLineEdit.setObjectName(_fromUtf8("sliceOriginZLineEdit"))
        self.horizontalLayout.addWidget(self.sliceOriginZLineEdit)
        self.horizontalLayout.setStretch(0, 1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_4.addLayout(self.verticalLayout)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.verticalLayout_4 = QtGui.QVBoxLayout()
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem)
        self.applyButton = QtGui.QPushButton(Form)
        self.applyButton.setObjectName(_fromUtf8("applyButton"))
        self.verticalLayout_4.addWidget(self.applyButton)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem1)
        self.gridLayout.addLayout(self.verticalLayout_4, 0, 1, 2, 1)
        self.groupBox_2 = QtGui.QGroupBox(Form)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.sliceOffsetListWidget = QtGui.QListWidget(self.groupBox_2)
        self.sliceOffsetListWidget.setObjectName(_fromUtf8("sliceOffsetListWidget"))
        self.horizontalLayout_3.addWidget(self.sliceOffsetListWidget)
        self.groupBox_3 = QtGui.QGroupBox(self.groupBox_2)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.label_3 = QtGui.QLabel(self.groupBox_3)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.verticalLayout_3.addWidget(self.label_3)
        self.sliceOffCSVLineEdit = QtGui.QLineEdit(self.groupBox_3)
        self.sliceOffCSVLineEdit.setObjectName(_fromUtf8("sliceOffCSVLineEdit"))
        self.verticalLayout_3.addWidget(self.sliceOffCSVLineEdit)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem2)
        self.verticalLayout_5.addLayout(self.verticalLayout_3)
        self.horizontalLayout_3.addWidget(self.groupBox_3)
        self.verticalLayout_6 = QtGui.QVBoxLayout()
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.horizontalLayout_3.addLayout(self.verticalLayout_6)
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Form", "Slice Base Parameters", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Normal", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Origin", None, QtGui.QApplication.UnicodeUTF8))
        self.applyButton.setText(QtGui.QApplication.translate("Form", "Apply", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(QtGui.QApplication.translate("Form", "Slice Offset Values", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_3.setTitle(QtGui.QApplication.translate("Form", "Input", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Comma Separated Values", None, QtGui.QApplication.UnicodeUTF8))

