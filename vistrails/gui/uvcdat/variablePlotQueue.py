from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QListWidgetItem

from gui.application import get_vistrails_application

from ui_variablePlotQueueWidget import Ui_variablePlotQueueWidget

class VariablePlotQueueWidget(QtGui.QDialog, Ui_variablePlotQueueWidget):

    def __init__(self, parent=None):
        super(VariablePlotQueueWidget, self).__init__(parent)
        self.setupUi(self)
        self.uvcdatWindow = None
        self.itemPlots = {}
        
        #setup signals
        self.connect(self.btnAllPlots, QtCore.SIGNAL("clicked()"), self.listWidgetPlots.selectAll)
        self.connect(self.btnNonePlots, QtCore.SIGNAL("clicked()"), self.listWidgetPlots.clearSelection)
        self.connect(self.btnRemovePlots, QtCore.SIGNAL("clicked()"), self.clearSelectedPlotItems)
        self.connect(self.btnAllVars, QtCore.SIGNAL("clicked()"), self.listWidgetVariables.selectAll)
        self.connect(self.btnNoneVars, QtCore.SIGNAL("clicked()"), self.listWidgetVariables.clearSelection)
        self.connect(self.btnRemoveVars, QtCore.SIGNAL("clicked()"), self.clearSelectedVarItems)
        self.connect(self.btnClose, QtCore.SIGNAL("clicked()"), self.close)
        
    def showEvent(self, event):
        super(VariablePlotQueueWidget, self).showEvent(event)
        self.setListsFromCell()
            
    def setListsFromCell(self):
        self.itemPlots = {}
        self.listWidgetPlots.clear()
        self.listWidgetVariables.clear()
        
        cell = self._getCell()
        if cell is None:
            return
        
        for plot in cell.plots:
            if plot.varnum > len(plot.variables):
                item = QListWidgetItem("%s-%s"%(plot.parent,plot.name), self.listWidgetPlots)
                self.itemPlots[item] = plot
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.listWidgetPlots.addItem(item)
                
        for variable in cell.variableQ:
            item = QListWidgetItem(variable, self.listWidgetVariables)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.listWidgetVariables.addItem(item)
            
    def clearSelectedPlotItems(self):
        cell = self._getCell() 
        for i in reversed(range(self.listWidgetPlots.count())):
            item =self.listWidgetPlots.item(i) 
            if item.isSelected():
                cell.remove_plot(self.itemPlots[item])
        #TODO: update spreadsheet prompt
        self.setListsFromCell()
            
    def clearSelectedVarItems(self): 
        cell = self._getCell() 
        for i in reversed(range(self.listWidgetVariables.count())):
            item =self.listWidgetVariables.item(i) 
            if item.isSelected():
                del cell.variableQ[i]
        #TODO: update spreadsheet prompt
        self.setListsFromCell()
        
    def _getProjectController(self):
        return self._getUvcdatWindow().get_current_project_controller()
    
    def _getUvcdatWindow(self):
        if self.uvcdatWindow is None:
            _app = get_vistrails_application()
            self.uvcdatWindow = _app.uvcdatWindow
        return self.uvcdatWindow
    
    def _getCell(self):
        ctrl = self._getProjectController()
        sheetName = ctrl.current_sheetName
        (row, col) = ctrl.current_cell_coords
        if sheetName in ctrl.sheet_map:
            if (row, col) in ctrl.sheet_map[sheetName]:
                return ctrl.sheet_map[sheetName][(row,col)]
        return None
                
            