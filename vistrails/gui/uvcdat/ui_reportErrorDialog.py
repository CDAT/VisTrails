# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'vistrails/gui/uvcdat/reportErrorDialog.ui'
#
# Created: Fri Nov 30 14:02:09 2012
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
        self.gridLayout = QtGui.QGridLayout(ReportErrorDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(ReportErrorDialog)
        self.label.setTextFormat(QtCore.Qt.AutoText)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.userComments = QtGui.QTextEdit(ReportErrorDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(self.userComments.sizePolicy().hasHeightForWidth())
        self.userComments.setSizePolicy(sizePolicy)
        self.userComments.setMinimumSize(QtCore.QSize(0, 30))
        self.userComments.setObjectName(_fromUtf8("userComments"))
        self.gridLayout.addWidget(self.userComments, 4, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(ReportErrorDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 6, 0, 1, 1)
        self.errorDetails = QtGui.QTextBrowser(ReportErrorDialog)
        self.errorDetails.setObjectName(_fromUtf8("errorDetails"))
        self.gridLayout.addWidget(self.errorDetails, 1, 0, 1, 1)
        self.label_2 = QtGui.QLabel(ReportErrorDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.label_3 = QtGui.QLabel(ReportErrorDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)
        self.label_4 = QtGui.QLabel(ReportErrorDialog)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 5, 0, 1, 1)

        self.retranslateUi(ReportErrorDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ReportErrorDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ReportErrorDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ReportErrorDialog)

    def retranslateUi(self, ReportErrorDialog):
        ReportErrorDialog.setWindowTitle(QtGui.QApplication.translate("ReportErrorDialog", "Report Error", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("ReportErrorDialog", "UV-CDAT has encountered an error.", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("ReportErrorDialog", "Please provide additional comments about what actions you were", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("ReportErrorDialog", "performing when this error occured.", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("ReportErrorDialog", "Send anonymous information about this error?", None, QtGui.QApplication.UnicodeUTF8))

