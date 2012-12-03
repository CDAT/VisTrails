# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui/uvcdat/reportErrorDialog.ui'
#
# Created: Mon Dec  3 13:58:04 2012
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_ReportErrorDialog(object):
    def setupUi(self, ReportErrorDialog):
        ReportErrorDialog.setObjectName(_fromUtf8("ReportErrorDialog"))
        ReportErrorDialog.resize(526, 459)
        font = QtGui.QFont()
        font.setKerning(False)
        ReportErrorDialog.setFont(font)
        self.gridLayout = QtGui.QGridLayout(ReportErrorDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(ReportErrorDialog)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Century Schoolbook L"))
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setKerning(False)
        self.label.setFont(font)
        self.label.setTextFormat(QtCore.Qt.AutoText)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.userComments = QtGui.QTextEdit(ReportErrorDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(self.userComments.sizePolicy().hasHeightForWidth())
        self.userComments.setSizePolicy(sizePolicy)
        self.userComments.setMinimumSize(QtCore.QSize(0, 30))
        self.userComments.setObjectName(_fromUtf8("userComments"))
        self.gridLayout.addWidget(self.userComments, 5, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(ReportErrorDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 7, 0, 1, 1)
        self.errorDetails = QtGui.QTextBrowser(ReportErrorDialog)
        self.errorDetails.setObjectName(_fromUtf8("errorDetails"))
        self.gridLayout.addWidget(self.errorDetails, 2, 0, 1, 1)
        self.label_2 = QtGui.QLabel(ReportErrorDialog)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Century Schoolbook L"))
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setKerning(False)
        self.label_2.setFont(font)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)
        self.label_4 = QtGui.QLabel(ReportErrorDialog)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Century Schoolbook L"))
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setKerning(False)
        self.label_4.setFont(font)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 6, 0, 1, 1)
        self.label_3 = QtGui.QLabel(ReportErrorDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)

        self.retranslateUi(ReportErrorDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ReportErrorDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ReportErrorDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ReportErrorDialog)

    def retranslateUi(self, ReportErrorDialog):
        ReportErrorDialog.setWindowTitle(QtGui.QApplication.translate("ReportErrorDialog", "Report Error", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("ReportErrorDialog", "UV-CDAT has encountered an error and needs to close.", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("ReportErrorDialog", "Additional comments about the actions that lead up to this error:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("ReportErrorDialog", "Would you like to send anonymous information about this error?", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("ReportErrorDialog", "We\'re sorry.", None, QtGui.QApplication.UnicodeUTF8))

