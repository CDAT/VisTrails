from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_mainwindow import Ui_MainWindow
from gui.uvcdat.workspace import Workspace
from gui.uvcdat.docktemplate import DockTemplate
from gui.uvcdat.dockplot import DockPlot
from gui.uvcdat.dockvariable import DockVariable
from gui.uvcdat.variable import VariableProperties
from gui.uvcdat.plot import PlotProperties

from packages.spreadsheet.spreadsheet_controller import spreadsheetController
import gui.uvcdat.uvcdat_rc
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
        self.embedSpreadsheet()
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
        
    def embedSpreadsheet(self):
        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        self.setCentralWidget(self.spreadsheetWindow)
        self.spreadsheetWindow.tabController.currentWidget().setDimension(2,2)
        self.spreadsheetWindow.tabController.currentWidget().rowSpinBoxChanged()
        self.spreadsheetWindow.tabController.currentWidget().colSpinBoxChanged()
        self.spreadsheetWindow.tabController.setDocumentMode(True)
        self.spreadsheetWindow.tabController.setTabPosition(QtGui.QTabWidget.North)
        self.spreadsheetWindow.setVisible(True)
        
    def cleanup(self):
        self.setCentralWidget(QtGui.QWidget())
        self.spreadsheetWindow.setParent(None)