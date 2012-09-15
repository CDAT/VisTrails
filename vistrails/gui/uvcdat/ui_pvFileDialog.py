# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pvFileDialog.ui'
#
# Created: Fri Sep 14 21:53:59 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_pvFileDialog(object):
    def setupUi(self, pvFileDialog):
        pvFileDialog.setObjectName(_fromUtf8("pvFileDialog"))
        pvFileDialog.resize(683, 402)
        self.verticalLayout_3 = QtGui.QVBoxLayout(pvFileDialog)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_3 = QtGui.QLabel(pvFileDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setMinimumSize(QtCore.QSize(100, 0))
        self.label_3.setMaximumSize(QtCore.QSize(100, 16777215))
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout.addWidget(self.label_3)
        self.Parents = QtGui.QComboBox(pvFileDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Parents.sizePolicy().hasHeightForWidth())
        self.Parents.setSizePolicy(sizePolicy)
        self.Parents.setObjectName(_fromUtf8("Parents"))
        self.horizontalLayout.addWidget(self.Parents)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.mainSplitter = QtGui.QSplitter(pvFileDialog)
        self.mainSplitter.setOrientation(QtCore.Qt.Horizontal)
        self.mainSplitter.setObjectName(_fromUtf8("mainSplitter"))
        self.splitter = QtGui.QSplitter(self.mainSplitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.layoutWidget = QtGui.QWidget(self.mainSplitter)
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.Files = QtGui.QTreeView(self.layoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Files.sizePolicy().hasHeightForWidth())
        self.Files.setSizePolicy(sizePolicy)
        self.Files.setObjectName(_fromUtf8("Files"))
        self.verticalLayout.addWidget(self.Files)
        self.gridlayout = QtGui.QGridLayout()
        self.gridlayout.setMargin(0)
        self.gridlayout.setSpacing(6)
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self.label_2 = QtGui.QLabel(self.layoutWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridlayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.FileName = QtGui.QLineEdit(self.layoutWidget)
        self.FileName.setObjectName(_fromUtf8("FileName"))
        self.gridlayout.addWidget(self.FileName, 0, 1, 1, 1)
        self.OK = QtGui.QPushButton(self.layoutWidget)
        self.OK.setObjectName(_fromUtf8("OK"))
        self.gridlayout.addWidget(self.OK, 0, 2, 1, 1)
        self.Cancel = QtGui.QPushButton(self.layoutWidget)
        self.Cancel.setObjectName(_fromUtf8("Cancel"))
        self.gridlayout.addWidget(self.Cancel, 1, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridlayout)
        self.verticalLayout_2.addWidget(self.mainSplitter)
        self.verticalLayout_2.setStretch(1, 1)
        self.verticalLayout_3.addLayout(self.verticalLayout_2)

        self.retranslateUi(pvFileDialog)
        QtCore.QObject.connect(self.OK, QtCore.SIGNAL(_fromUtf8("clicked()")), pvFileDialog.accept)
        QtCore.QObject.connect(self.Cancel, QtCore.SIGNAL(_fromUtf8("clicked()")), pvFileDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(pvFileDialog)
        pvFileDialog.setTabOrder(self.FileName, self.OK)
        pvFileDialog.setTabOrder(self.OK, self.Cancel)
        pvFileDialog.setTabOrder(self.Cancel, self.Parents)
        pvFileDialog.setTabOrder(self.Parents, self.Files)

    def retranslateUi(self, pvFileDialog):
        pvFileDialog.setWindowTitle(QtGui.QApplication.translate("pvFileDialog", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("pvFileDialog", "Look in:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("pvFileDialog", "File name:", None, QtGui.QApplication.UnicodeUTF8))
        self.OK.setText(QtGui.QApplication.translate("pvFileDialog", "OK", None, QtGui.QApplication.UnicodeUTF8))
        self.Cancel.setText(QtGui.QApplication.translate("pvFileDialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

