###############################################################################
#                                                                             #
# Module:       mainwindow module                                             #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI mainwindow.                                       #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
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
from gui.uvcdat import animationWidget

from packages.spreadsheet.spreadsheet_controller import spreadsheetController
import gui.uvcdat.uvcdat_rc

import customizeUVCDAT
import commandsRecorderWidget
import preferencesWidget
import mainMenuWidget
import mainToolbarWidget
from colormapEditorWidget import QColormapEditor

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
        self.colormapEditor =QColormapEditor(self) 
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
        self.resize(1150,800)
        
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
        animate = animationWidget.QAnimationView(self)
        self.dockAnimate = QtGui.QDockWidget(self)
        self.dockAnimate.setWidget(animate)
        self.dockAnimate.setWindowTitle("Animation")
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
        self.plotProp = PlotProperties.instance(self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.workspace)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dockTemplate)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dockAnimate)
        #self.tabifyDockWidget(self.workspace, self.dockTemplate)
        self.tabifyDockWidget(self.dockTemplate, self.dockPlot)
        self.workspace.raise_()
        self.varProp.hide()
        self.plotProp.hide()
        self.dockAnimate.hide()

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockVariable)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.varProp)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockCalculator)
        self.tabifyDockWidget(self.dockCalculator, self.plotProp)


    def createActions(self):
        # Quit Action
        self.actionExit = QtGui.QAction("Quit", self,
                                        triggered=self.quit)
        #VisTrails Window
        self.showBuilderWindowAct = QtGui.QAction("Builder", self,
                                 triggered=self.showBuilderWindowActTriggered)
        self.showVistrailsConsoleAct = QtGui.QAction("Console", self,
                                triggered=self.showVistrailsConsoleActTriggered)
        #About Message
        self.showAboutMessageAct = QtGui.QAction("About UV-CDAT...", self,
                                triggered=self.showAboutMessageActTriggered)
        
    def updateMenuActions(self):
        #menu File Actions
        self.ui.menuFile.addAction(self.workspace.btnNewProject)
        self.ui.menuFile.addAction(self.workspace.btnOpenProject)
        self.ui.menuFile.addSeparator()
        self.ui.menuFile.addAction(self.workspace.btnCloseProject)
        self.ui.menuFile.addSeparator()
        self.ui.menuFile.addAction(self.workspace.btnSaveProject)
        self.ui.menuFile.addAction(self.workspace.btnSaveProjectAs)
        self.ui.menuFile.addSeparator()
        self.ui.menuFile.addAction(self.actionExit)
        #menu View Actions
        self.ui.menuView.addAction(self.workspace.toggleViewAction())
        self.ui.menuView.addAction(self.dockTemplate.toggleViewAction())
        self.ui.menuView.addAction(self.dockPlot.toggleViewAction())
        self.ui.menuView.addAction(self.dockVariable.toggleViewAction())
        self.ui.menuView.addAction(self.dockCalculator.toggleViewAction())
        self.ui.menuView.addAction(self.plotProp.toggleViewAction())
        #VisTrails Menu
        self.ui.menuVistrails.addAction(self.showBuilderWindowAct)
        self.ui.menuVistrails.addAction(self.showVistrailsConsoleAct)
        #About message
        self.ui.menuHelp.addAction(self.showAboutMessageAct)
        
    def showBuilderWindowActTriggered(self):
        from gui.vistrails_window import _app
        _app.show()
        _app.raise_()
        
    def showVistrailsConsoleActTriggered(self):
        from gui.shell import QShellDialog
        QShellDialog.instance().set_visible(True)
        
    def showAboutMessageActTriggered(self):
        import core.uvcdat
        import core.system
        class About(QtGui.QLabel):
            def mousePressEvent(self, e):
                self.emit(QtCore.SIGNAL("clicked()"))

        dlg = QtGui.QDialog(self, QtCore.Qt.FramelessWindowHint)
        layout = QtGui.QVBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(0)
        bgimage = About(dlg)
        #The application disclaimer image
        pixmap = QtGui.QPixmap(
            core.system.vistrails_root_directory() +
            '/gui/uvcdat/resources/images/disclaimer.png')
        bgimage.setPixmap(pixmap)
        layout.addWidget(bgimage)
        dlg.setLayout(layout)
        text = "<font color=\"#105E99\"><b>%s</b></font>" % \
            core.uvcdat.short_about_string()
        version = About(text, dlg)
        version.setGeometry(11,50,450,30)
        self.connect(bgimage,
                     QtCore.SIGNAL('clicked()'),
                     dlg,
                     QtCore.SLOT('accept()'))
        self.connect(version,
                     QtCore.SIGNAL('clicked()'),
                     dlg,
                     QtCore.SLOT('accept()'))
        dlg.setSizeGripEnabled(False)
        dlg.exec_()
        
    def connectSignals(self):
        
        self.connect(self.spreadsheetWindow.tabControllerStack,
                     QtCore.SIGNAL("add_tab"),
                     self.workspace.add_sheet_tab)
        self.connect(self.spreadsheetWindow.tabControllerStack,
                     QtCore.SIGNAL("remove_tab"),
                     self.workspace.remove_sheet_tab)
        self.connect(self.spreadsheetWindow.tabControllerStack,
                     QtCore.SIGNAL("change_tab_text"),
                     self.workspace.change_tab_text)
        
    def closeEvent(self, e):
        """ closeEvent(e: QCloseEvent) -> None
        Only hide the builder window

        """
        if not self.quit():
            e.ignore()
        
    def quit(self):
        #FIXME
        #ask to save projects
        print "quiting"
        if self.preferences.confirmB4Exit.isChecked():
            # put here code to confirm exit
            pass
        if self.preferences.saveB4Exit.isChecked():
            self.preferences.saveState()
        from gui.vistrails_window import _app
        _app._is_quitting = True
        if _app.close_all_vistrails():
            QtCore.QCoreApplication.quit()
            # In case the quit() failed (when Qt doesn't have the main
            # event loop), we have to return True still
            return True
        _app._is_quitting = False
        return False
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
#                    # Send information to controller so the Variable can be reconstructed
#                    # later. The best way is by emitting a signal to be processed by the
#                    # main window. When this panel becomes a global panel, then we will do
#                    # that. For now I will talk to the main window directly.
#        
#                    from api import get_current_project_controller
#                    from packages.uvcdat_cdms.init import CDMSVariable
#                    controller = get_current_project_controller()
#                    if controller.get_defined_variable(k) is None:
#                        cdmsVar = CDMSVariable(filename=None, name=k)
#                        controller.add_defined_variable(cdmsVar)
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
    
    def get_project_controller_by_name(self, name):
        return self.workspace.get_project_controller_by_name(name)
    
    def link_registry(self):
        self.dockPlot.link_registry()
