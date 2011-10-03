from PyQt4 import QtCore, QtGui

from uvcdat.gui.ui_mainwindow import Ui_MainWindow
from uvcdat.gui.workspace import Workspace
from uvcdat.gui.docktemplate import DockTemplate
from uvcdat.gui.dockplot import DockPlot
from uvcdat.gui.dockvariable import DockVariable
from uvcdat.gui.variable import VariableProperties
from uvcdat.gui.plot import PlotProperties

import uvcdat.gui.uvcdat_rc
#from gui.theme import initializeCurrentTheme
#from packages.spreadsheet.spreadsheet_controller import spreadsheetController
#from packages.spreadsheet.spreadsheet_registry import spreadsheetRegistry
#from packages.spreadsheet.spreadsheet_window import SpreadsheetWindow
#from packages.spreadsheet.spreadsheet_tabcontroller import StandardWidgetTabController 

class UVCDATMainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(UVCDATMainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setDocumentMode(True)
        #initializeCurrentTheme()
        self.createDockWindows()
        self.createViewActions()
        self.connectSignals()
        
        
    def createDockWindows(self):
        self.workspace = Workspace()
        self.dockTemplate = DockTemplate()
        self.dockPlot = DockPlot()
        self.dockVariable = DockVariable()
        
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.workspace)
        self.tabifyDockWidget(self.workspace, self.dockTemplate)
        self.tabifyDockWidget(self.workspace, self.dockPlot)
        self.workspace.raise_()

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockVariable)

    def createViewActions(self):
        self.ui.menuView.addAction(self.workspace.toggleViewAction())
        self.ui.menuView.addAction(self.dockTemplate.toggleViewAction())
        self.ui.menuView.addAction(self.dockPlot.toggleViewAction())
        self.ui.menuView.addAction(self.dockVariable.toggleViewAction())
        
    def connectSignals(self):
        self.ui.tbVarInfo.clicked.connect(self.showVariableProperties)
        self.ui.tbPlotInfo.clicked.connect(self.showPlotProperties)
        self.ui.actionExit.triggered.connect(self.quit)
        
    def quit(self):
        #FIXME
        #ask to save projects
        QtGui.QApplication.instance().quit()
        
    def showVariableProperties(self):
        varProp = VariableProperties.instance()
        varProp.show()
        
    def showPlotProperties(self):
        plotProp = PlotProperties.instance()
        plotProp.show()
        