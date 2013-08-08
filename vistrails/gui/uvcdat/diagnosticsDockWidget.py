from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget

class DiagnosticsDockWidget(QtGui.QDockWidget, Ui_DiagnosticDockWidget):
    
    Types = ["AMWG", "LMWG"]
    DisabledTypes = ["OMWG", "PCWG", "MPAS", "Metrics"]
    AllTypes = Types + DisabledTypes

    def __init__(self, parent=None):
        super(DiagnosticsDockWidget, self).__init__(parent)
        self.setupUi(self)
        
        #initialize data
        #@todo: move data to external file to be read in
        self.groups = {'AMWG': {'AMWG Group 1': ['Diagnostics 1', 
                                                 'Diagnostics 2', 
                                                 'Diagnostics 3'],
                                'AMWG Group 2': ['Diagnostics 4',
                                                 'Diagnostics 5', 
                                                 'Diagnostics 6',],
                                'AMWG Group 3': ['Diagnostics 7',
                                                 'Diagnostics 8', 
                                                 'Diagnostics 9',]},
                       'LMWG': {'LMWG Group 1': ['Diagnostics 10', 
                                                 'Diagnostics 11', 
                                                 'Diagnostics 12'],
                                'LMWG Group 2': ['Diagnostics 13',
                                                 'Diagnostics 14', 
                                                 'Diagnostics 15',],
                                'LMWG Group 3': ['Diagnostics 16',
                                                 'Diagnostics 17', 
                                                 'Diagnostics 18',]}}
        
        #setup signals
        self.comboBox.currentIndexChanged.connect(self.setupDiagnosticTree)
        self.buttonBox.clicked.connect(self.buttonClicked)
        self.treeWidget.itemChanged.connect(self.itemChecked)
        
        #keep track of checked item so we can unckeck it if another is checked
        self.checkedItem = None
        
        self.setupDiagnosticsMenu()
        
        self.comboBox.addItems(DiagnosticsDockWidget.Types)
        
    def setupDiagnosticsMenu(self):
        menu = self.parent().menuBar().addMenu('&Diagnostics')
        
        def generateCallBack(x):
            def callBack():
                self.diagnosticTriggered(x)
            return callBack
        
        for diagnosticType in DiagnosticsDockWidget.AllTypes:
            action = QtGui.QAction(diagnosticType, self)
            action.setEnabled(diagnosticType in DiagnosticsDockWidget.Types)
            action.setStatusTip(diagnosticType + " Diagnostics")
            action.triggered.connect(generateCallBack(diagnosticType))
            menu.addAction(action)
            
    def diagnosticTriggered(self, diagnosticType):
        index = self.comboBox.findText(diagnosticType)
        self.comboBox.setCurrentIndex(index)
        self.show()
        self.raise_()
        
    def setupDiagnosticTree(self, index):
        diagnosticType = str(self.comboBox.itemText(index))
        self.treeWidget.clear()
        for groupName, groupValues in self.groups[diagnosticType].items():
            groupItem = QtGui.QTreeWidgetItem(self.treeWidget, [groupName])
            for diagnostic in groupValues:
                diagnosticItem = QtGui.QTreeWidgetItem(groupItem, [diagnostic])
                diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
                diagnosticItem.setCheckState(0, Qt.Unchecked)
        
    def buttonClicked(self, button):
        role = self.buttonBox.buttonRole(button) 
        if role == QtGui.QDialogButtonBox.ApplyRole:
            pass
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.close()
            
    def itemChecked(self, item, column):
        if item.checkState(column) == Qt.Checked:
            if self.checkedItem is not None:
                self.treeWidget.blockSignals(True)
                self.checkedItem.setCheckState(column, Qt.Unchecked)
                self.treeWidget.blockSignals(False)
            self.checkedItem = item
        else:
            self.checkedItem = None