from PyQt4 import QtCore, QtGui
import os
import cdms2
import vcs
import __main__

from gui.uvcdat.ui_mainwindow import Ui_MainWindow
from gui.uvcdat.workspace import Workspace
from gui.uvcdat.docktemplate import DockTemplate
from gui.uvcdat.dockplot import DockPlot
from gui.uvcdat.dockvariable import DockVariable
from gui.uvcdat.variable import VariableProperties
from gui.uvcdat.plot import PlotProperties
from gui.uvcdat.dockcalculator import DockCalculator

from packages.spreadsheet.spreadsheet_controller import spreadsheetController
import gui.uvcdat.uvcdat_rc

import customizeUVCDAT
import commandsRecorderWidget
import preferencesWidget
import mainMenuWidget
import mainToolbarWidget

class UVCDATMainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None,customPath=None,styles=None):
        super(UVCDATMainWindow, self).__init__(parent)
        self.root=self
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setDocumentMode(True)
        #init user options
        self.initCustomize(customPath,styles)
        self.root = self
        #self.tool_bar = mainToolbarWidget.QMainToolBarContainer(self)
        self.canvas=[]
        
        self.canvas.append(vcs.init())
        # Create the command recorder widget
        self.recorder = commandsRecorderWidget.QCommandsRecorderWidget(self)
        #Adds a shortcut to the record function
        self.record = self.recorder.record
        self.preferences = preferencesWidget.QPreferencesDialog(self)
        self.preferences.hide()
        ###########################################################
        # Init Menu Widget
        ###########################################################
        self.mainMenu = mainMenuWidget.QMenuWidget(self)
        self.createDockWindows()
        self.createActions()
        self.updateMenuActions()
        self.embedSpreadsheet()
        self.connectSignals()
        
    def initCustomize(self,customPath,styles):
        if customPath is None:
            customPath=os.path.join(os.environ["HOME"],"PCMDI_GRAPHICS","customizeUVCDAT.py")
            
        if os.path.exists(customPath):
            execfile(customPath,customizeUVCDAT.__dict__,customizeUVCDAT.__dict__)

        if styles is None:
            styles=customizeUVCDAT.appStyles
            
        icon = QtGui.QIcon(customizeUVCDAT.appIcon)
        self.setWindowIcon(icon)

        ## cdms2 setup section
        cdms2.axis.time_aliases+=customizeUVCDAT.timeAliases
        cdms2.axis.level_aliases+=customizeUVCDAT.levelAliases
        cdms2.axis.latitude_aliases+=customizeUVCDAT.latitudeAliases
        cdms2.axis.longitude_aliases+=customizeUVCDAT.longitudeAliases
        cdms2.setNetcdfShuffleFlag(customizeUVCDAT.ncShuffle)
        cdms2.setNetcdfDeflateFlag(customizeUVCDAT.ncDeflate)
        cdms2.setNetcdfDeflateLevelFlag(customizeUVCDAT.ncDeflateLevel)
        
        ## StylesSheet
        st=""
        if isinstance(styles,str):
            st = styles
        elif isinstance(styles,dict):
            for k in styles.keys():
                val = styles[k]
                if isinstance(val,QtGui.QColor):
                    val = str(val.name())
                st+="%s:%s; " % (k,val)
        if len(st)>0: self.setStyleSheet(st)

        ###########################################################
        ###########################################################
        ## Prettyness
        ###########################################################
        ###########################################################
        #self.setGeometry(0,0, 1100,800)
        self.setWindowTitle('The Ultrascale Visualization Climate Data Analysis Tools - (UV-CDAT)')
        ## self.resize(1100,800)
        #self.setMinimumWidth(1100)
        self.main_window_placement()
     
    def main_window_placement(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/4, (screen.height()-size.height())/5)

    def createDockWindows(self):
        self.dockTemplate = DockTemplate(self)
        self.dockPlot = DockPlot(self)
        self.dockVariable = DockVariable(self)
        self.workspace = Workspace(self)
        self.varProp = VariableProperties(self)
        #self.workspace.addProject("Relative Humidity")
        #self.workspace.addProject("Total Cloudiness")
        #self.workspace.addProject("Temperature Anomaly")
        #self.workspace.addProject()
        self.dockCalculator = DockCalculator(self)
        
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.workspace)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dockTemplate)
        #self.tabifyDockWidget(self.workspace, self.dockTemplate)
        self.tabifyDockWidget(self.dockTemplate, self.dockPlot)
        self.workspace.raise_()
        self.varProp.hide()
        

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockVariable)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.varProp)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockCalculator)

    def createActions(self):
        #VisTrails Window
        self.showBuilderWindowAct = QtGui.QAction("VisTrails Builder", self,
                                 triggered=self.showBuilderWindowActTriggered)
    def updateMenuActions(self):
        #menu View Actions
        self.ui.menuView.addAction(self.workspace.toggleViewAction())
        self.ui.menuView.addAction(self.dockTemplate.toggleViewAction())
        self.ui.menuView.addAction(self.dockPlot.toggleViewAction())
        self.ui.menuView.addAction(self.dockVariable.toggleViewAction())
        self.ui.menuView.addAction(self.dockCalculator.toggleViewAction())
        
        #Window Menu
        self.ui.menuWindow.addAction(self.showBuilderWindowAct)
        
    def showBuilderWindowActTriggered(self):
        from gui.vistrails_window import _app
        _app.show()
        
    def connectSignals(self):
        self.ui.actionExit.triggered.connect(self.quit)
        self.connect(self.spreadsheetWindow.tabControllerStack,
                     QtCore.SIGNAL("add_tab"),
                     self.workspace.add_sheet_tab)
        self.connect(self.spreadsheetWindow.tabControllerStack,
                     QtCore.SIGNAL("remove_tab"),
                     self.workspace.remove_sheet_tab)
        
    def quit(self):
        #FIXME
        #ask to save projects
        print "quiting"
        if self.preferences.confirmB4Exit.isChecked():
            # put here code to confirm exit
            pass
        if self.preferences.saveB4Exit.isChecked():
            self.preferences.saveState()
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
        self.spreadsheetWindow.setVisible(True)
        
    def cleanup(self):
        self.setCentralWidget(QtGui.QWidget())
        self.spreadsheetWindow.setParent(None)

    def stick_defvar_into_main_dict(self,var):
        __main__.__dict__[var.id]=var

    def stick_main_dict_into_defvar(self,results=None):
        #First evaluate if there's any var in the result
        res = None
        if results is not None:
            tmp = __main__.__dict__[results]
        else:
            tmp=None
        added = []
        remove =[]
        if isinstance(tmp,cdms2.tvariable.TransientVariable):
            __main__.__dict__[tmp.id]=tmp
            added.append(tmp.id)
            res = tmp.id
        elif tmp is not None:
            self.processList(tmp,added)
            
        if results is not None:
            del(__main__.__dict__[results])
        for k in __main__.__dict__:
            if isinstance(__main__.__dict__[k],cdms2.tvariable.TransientVariable):
                if __main__.__dict__[k].id in added and k!=__main__.__dict__[k].id:
                    remove.append( __main__.__dict__[k].id)
                    res = k
                if not k in remove:
                    __main__.__dict__[k].id=k
                    self.dockVariable.widget().addVariable(__main__.__dict__[k])
        for r in remove:
            del(__main__.__dict__[r])

        return res
    
    def processList(self,myList,added):
        for v in myList:
            if isinstance(v,cdms2.tvariable.TransientVariable):
                __main__.__dict__[v.id]=v
                added.append(v.id)
            elif isinstance(v,(list,tuple)):
                self.processList(v,added)
            elif isinstance(v,dict):
                self.processList(dict.values(),added)
        return

    def get_current_project_controller(self):
        return self.workspace.get_current_project_controller()
    
    def link_registry(self):
        self.dockPlot.link_registry()
