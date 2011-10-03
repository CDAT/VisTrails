# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dockvariable.ui'
#
# Created: Fri Aug 26 13:49:11 2011
#      by: PyQt4 UI code generator 4.8.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_DockVariable(object):
    def setupUi(self, DockVariable):
        DockVariable.setObjectName(_fromUtf8("DockVariable"))
        DockVariable.resize(400, 300)
        DockVariable.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.toolsProject = QtGui.QFrame(self.dockWidgetContents)
        self.toolsProject.setFrameShape(QtGui.QFrame.StyledPanel)
        self.toolsProject.setFrameShadow(QtGui.QFrame.Raised)
        self.toolsProject.setObjectName(_fromUtf8("toolsProject"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.toolsProject)
        self.horizontalLayout.setSpacing(1)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.btnNewVar = QtGui.QPushButton(self.toolsProject)
        self.btnNewVar.setObjectName(_fromUtf8("btnNewVar"))
        self.horizontalLayout.addWidget(self.btnNewVar)
        self.verticalLayout.addWidget(self.toolsProject)
        self.varTree = QtGui.QTreeWidget(self.dockWidgetContents)
        self.varTree.setIndentation(20)
        self.varTree.setRootIsDecorated(False)
        self.varTree.setObjectName(_fromUtf8("varTree"))
        item_0 = QtGui.QTreeWidgetItem(self.varTree)
        item_0 = QtGui.QTreeWidgetItem(self.varTree)
        item_0 = QtGui.QTreeWidgetItem(self.varTree)
        item_0 = QtGui.QTreeWidgetItem(self.varTree)
        self.varTree.header().setVisible(False)
        self.verticalLayout.addWidget(self.varTree)
        DockVariable.setWidget(self.dockWidgetContents)

        self.retranslateUi(DockVariable)
        QtCore.QMetaObject.connectSlotsByName(DockVariable)

    def retranslateUi(self, DockVariable):
        DockVariable.setWindowTitle(QtGui.QApplication.translate("DockVariable", "Variables", None, QtGui.QApplication.UnicodeUTF8))
        self.btnNewVar.setText(QtGui.QApplication.translate("DockVariable", "New Variable", None, QtGui.QApplication.UnicodeUTF8))
        self.varTree.headerItem().setText(0, QtGui.QApplication.translate("DockVariable", "1", None, QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.varTree.isSortingEnabled()
        self.varTree.setSortingEnabled(False)
        self.varTree.topLevelItem(0).setText(0, QtGui.QApplication.translate("DockVariable", "clt", None, QtGui.QApplication.UnicodeUTF8))
        self.varTree.topLevelItem(1).setText(0, QtGui.QApplication.translate("DockVariable", "var 2", None, QtGui.QApplication.UnicodeUTF8))
        self.varTree.topLevelItem(2).setText(0, QtGui.QApplication.translate("DockVariable", "var 3", None, QtGui.QApplication.UnicodeUTF8))
        self.varTree.topLevelItem(3).setText(0, QtGui.QApplication.translate("DockVariable", "var 4", None, QtGui.QApplication.UnicodeUTF8))
        self.varTree.setSortingEnabled(__sortingEnabled)

import uvcdat_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    DockVariable = QtGui.QDockWidget()
    ui = Ui_DockVariable()
    ui.setupUi(DockVariable)
    DockVariable.show()
    sys.exit(app.exec_())

