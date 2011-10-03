# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'workspace.ui'
#
# Created: Fri Aug 26 10:36:18 2011
#      by: PyQt4 UI code generator 4.8.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Workspace(object):
    def setupUi(self, Workspace):
        Workspace.setObjectName(_fromUtf8("Workspace"))
        Workspace.resize(404, 623)
        Workspace.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
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
        self.btnNewProject = QtGui.QToolButton(self.toolsProject)
        self.btnNewProject.setText(_fromUtf8(""))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icons/resources/icons/new.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btnNewProject.setIcon(icon)
        self.btnNewProject.setIconSize(QtCore.QSize(22, 22))
        self.btnNewProject.setObjectName(_fromUtf8("btnNewProject"))
        self.horizontalLayout.addWidget(self.btnNewProject)
        self.btnOpenProject = QtGui.QToolButton(self.toolsProject)
        self.btnOpenProject.setText(_fromUtf8(""))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(_fromUtf8(":/icons/resources/icons/open.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btnOpenProject.setIcon(icon1)
        self.btnOpenProject.setIconSize(QtCore.QSize(22, 22))
        self.btnOpenProject.setObjectName(_fromUtf8("btnOpenProject"))
        self.horizontalLayout.addWidget(self.btnOpenProject)
        spacerItem = QtGui.QSpacerItem(229, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.toolsProject)
        self.treeProjects = QtGui.QTreeWidget(self.dockWidgetContents)
        self.treeProjects.setRootIsDecorated(True)
        self.treeProjects.setExpandsOnDoubleClick(False)
        self.treeProjects.setObjectName(_fromUtf8("treeProjects"))
        item_0 = QtGui.QTreeWidgetItem(self.treeProjects)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/icons/resources/icons/folder_blue_open.png")), QtGui.QIcon.Normal, QtGui.QIcon.On)
        item_0.setIcon(0, icon2)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_0 = QtGui.QTreeWidgetItem(self.treeProjects)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(_fromUtf8(":/icons/resources/icons/folder_blue.png")), QtGui.QIcon.Normal, QtGui.QIcon.On)
        item_0.setIcon(0, icon3)
        item_0 = QtGui.QTreeWidgetItem(self.treeProjects)
        item_0.setIcon(0, icon3)
        item_0 = QtGui.QTreeWidgetItem(self.treeProjects)
        item_0.setIcon(0, icon3)
        self.treeProjects.header().setVisible(False)
        self.verticalLayout.addWidget(self.treeProjects)
        Workspace.setWidget(self.dockWidgetContents)

        self.retranslateUi(Workspace)
        QtCore.QMetaObject.connectSlotsByName(Workspace)

    def retranslateUi(self, Workspace):
        Workspace.setWindowTitle(QtGui.QApplication.translate("Workspace", "Projects", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.headerItem().setText(0, QtGui.QApplication.translate("Workspace", "1", None, QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.treeProjects.isSortingEnabled()
        self.treeProjects.setSortingEnabled(False)
        self.treeProjects.topLevelItem(0).setText(0, QtGui.QApplication.translate("Workspace", "Project 1", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(0).child(0).setText(0, QtGui.QApplication.translate("Workspace", "Cloudness Plot", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(0).child(1).setText(0, QtGui.QApplication.translate("Workspace", "Plot 2", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(0).child(2).setText(0, QtGui.QApplication.translate("Workspace", "Analysis 3", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(0).child(3).setText(0, QtGui.QApplication.translate("Workspace", "Animation", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(1).setText(0, QtGui.QApplication.translate("Workspace", "Project 2", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(2).setText(0, QtGui.QApplication.translate("Workspace", "Project 3", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.topLevelItem(3).setText(0, QtGui.QApplication.translate("Workspace", "Project 4", None, QtGui.QApplication.UnicodeUTF8))
        self.treeProjects.setSortingEnabled(__sortingEnabled)

import uvcdat_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Workspace = QtGui.QDockWidget()
    ui = Ui_Workspace()
    ui.setupUi(Workspace)
    Workspace.show()
    sys.exit(app.exec_())

