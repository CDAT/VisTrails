# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'docktemplate.ui'
#
# Created: Fri Aug 26 10:38:54 2011
#      by: PyQt4 UI code generator 4.8.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_DockTemplate(object):
    def setupUi(self, DockTemplate):
        DockTemplate.setObjectName(_fromUtf8("DockTemplate"))
        DockTemplate.resize(240, 314)
        DockTemplate.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.widget = QtGui.QWidget()
        self.widget.setObjectName(_fromUtf8("widget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.listTemplates = QtGui.QListWidget(self.widget)
        self.listTemplates.setObjectName(_fromUtf8("listTemplates"))
        QtGui.QListWidgetItem(self.listTemplates)
        self.verticalLayout.addWidget(self.listTemplates)
        DockTemplate.setWidget(self.widget)

        self.retranslateUi(DockTemplate)
        QtCore.QMetaObject.connectSlotsByName(DockTemplate)

    def retranslateUi(self, DockTemplate):
        DockTemplate.setWindowTitle(QtGui.QApplication.translate("DockTemplate", "Templates", None, QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.listTemplates.isSortingEnabled()
        self.listTemplates.setSortingEnabled(False)
        self.listTemplates.item(0).setText(QtGui.QApplication.translate("DockTemplate", "CustomBoxFill", None, QtGui.QApplication.UnicodeUTF8))
        self.listTemplates.setSortingEnabled(__sortingEnabled)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    DockTemplate = QtGui.QDockWidget()
    ui = Ui_DockTemplate()
    ui.setupUi(DockTemplate)
    DockTemplate.show()
    sys.exit(app.exec_())

