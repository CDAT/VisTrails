from info import identifier
from PyQt4 import QtCore
from PyQt4 import QtGui
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core.modules.module_registry import get_module_registry
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_cell import QCellWidget

# Needed for configuration
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from gui.modules.module_configure import StandardModuleConfigurationWidget

# Needed for port related stuff
from core.vistrail.port import PortEndPoint
import core.modules.basic_modules as basic_modules

from packages.uvcdat.init import Variable, Plot
from packages.uvcdat_cdms.init import CDMSVariable
from packages.uvcdat.init import expand_port_specs as _expand_port_specs

import sys
import visit
import visit.pyqt_gui


from core.modules.vistrails_module import Module, NotCacheable, ModuleError
from packages.spreadsheet.spreadsheet_base import (StandardSheetReference,
                              StandardSingleCellSheetReference)
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_event import DisplayCellEvent

sys.argv.append("-embedded")
viswin = visit.pyqt_gui.PyQtGUI(sys.argv)
visit.Launch()

viswin.GetUIWindow().hide()
viswin.GetRenderWindow(1).hide()

viswinmapper = {}
availWindows = []
availWindows.append((viswin.GetRenderWindow(1),1))



class VisItParams(Module):
    def __init__(self):
        Module.__init__(self)
        self.renderType = "Pseudocolor Plot"

    def compute(self):
        self.renderType = self.getInputFromPort("renderType")

class VisItCell(SpreadsheetCell):
    def __init__(self):
        SpreadsheetCell.__init__(self)
        self.cellWidget = None
        self.location = None
        self.cdms_var = None
        self.renderType = None

    def GetVars():
        return self.cellWidget

    def compute(self):
        """ compute() -> None
        Dispatch the QVisItWidget to do the actual rendering 
        """
        self.location = self.getInputFromPort("Location")
        self.cdms_var = self.getInputFromPort("variable")
        self.params = self.getInputFromPort("visitparams")
        self.cellWidget = self.displayAndWait(QVisItWidget,(self.cdms_var,self.location,self.params))

    def LoadPseudocolorPlot(self):
        print "Loading Pseudocolor Plot"
        self.cellWidget.LoadPseudocolorPlot()

    def LoadContourPlot(self):
        print "Loading Contour Plot"
        self.cellWidget.LoadContourPlot()

class QVisItWidget(QCellWidget):
    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QCellWidget.__init__(self,parent,f)
        self.layout = QVBoxLayout(self)
        self.view = None
        self.location = None
        self.cdms_var = None
        self.params = None

    def showEvent(self,event):
        print "show event"
        if self.view is not None:
            self.view.setParent(self)
            self.view.show()
            self.layout.addWidget(self.view)

    def closeEvent(self,event):
        print "closing called"
        #QMainWidget.setCentralWidget(self.view)

    def hideEvent(self,event):
        print "hiding event"
        if self.view is not None:
            self.view.setParent(None)
            self.view.hide()

    def GetDetails(self):
        windowid = self.getKey()
        filename = self.cdms_var.filename
        var = self.cdms_var.varNameInFile
        return (windowid,filename,var)
        
    def LoadPseudocolorPlot(self):
        (windowid,filename,var) = self.GetDetails()
        wid = viswinmapper[windowid]
        visit.SetActiveWindow(wid)
        visit.DeleteAllPlots()
        visit.OpenDatabase(filename)
        visit.AddPlot("Pseudocolor",var)
        visit.DrawPlots()

    def LoadContourPlot(self):
        (windowid,filename,var) = self.GetDetails() 
        wid = viswinmapper[windowid]
        visit.SetActiveWindow(wid)
        visit.DeleteAllPlots()
        visit.OpenDatabase(filename)
        visit.AddPlot("Contour",var)
        visit.DrawPlots()

    def LoadExtremeValueAnalysisPlot(self):
        (windowid,filename,var) = self.GetDetails() 
        wid = viswinmapper[windowid]
        visit.SetActiveWindow(wid)
        visit.DeleteAllPlots()
        visit.OpenDatabase(filename, 0)
        visit.AddPlot("Pseudocolor", var, 1, 1)
        #visit.AddOperator("Box", 1)
        #visit.SetActivePlots(0)
        #visit.SetActivePlots(0)
        #BoxAtts = visit.BoxAttributes()
        #BoxAtts.amount = BoxAtts.Some # Some, All
        #BoxAtts.minx = 90
        #BoxAtts.maxx = 100
        #BoxAtts.miny = -10
        #BoxAtts.maxy = 10
        #BoxAtts.minz = 0
        #BoxAtts.maxz = 1
        #visit.SetOperatorOptions(BoxAtts, 1)
        visit.AddOperator("ExtremeValueAnalysis")
        visit.DrawPlots()

    def updateContents(self, inputPorts):
        global viswin
        global viswinmapper
        global availWindows

        (self.cdms_var,self.location,self.params) = inputPorts

        windowkey = self.getKey()
        windowid  = 0

        if self.view is None:
            a = set(viswin.GetRenderWindowIDs())
            if len(availWindows) > 0:
                (self.view,windowid) = availWindows[0]
                availWindows = availWindows[1:]
            else:
                a = set(viswin.GetRenderWindowIDs())
                visit.AddWindow()
                b = set(viswin.GetRenderWindowIDs())
                res = tuple(b - a)
                windowid = res[0]
                self.view = viswin.GetRenderWindow(windowid)  

            self.layout.addWidget(self.view)
            self.view.show()
            viswinmapper[windowkey] = windowid

        if "Pseudocolor" in self.params.renderType :
            self.LoadPseudocolorPlot()

        if "Contour" in self.params.renderType :
            self.LoadContourPlot()

        if "Extreme Value Analysis" in self.params.renderType :
            self.LoadExtremeValueAnalysisPlot()

        QCellWidget.updateContents(self, inputPorts)

    def saveToPNG(self, filename):
        print "save VisIt file to PNG"

    def dumpToFile(self,filename):
        print "writing to file."

    def deleteLater(self):
        global viswinmapper
        print "deleting" 
        if self.view is not None:
            self.view.setParent(None)
            windowKey = self.getKey()
            availWindows.append((self.view,viswinmapper[windowKey]))
            del viswinmapper[windowKey]
        QCellWidget.deleteLater(self)

    def getKey(self):
        return str(self.location.row) + "_" + str(self.location.col)

def registerSelf():
    registry = get_module_registry()

    registry.add_module(VisItParams)
    registry.add_input_port(VisItParams,"renderType", basic_modules.String)
    registry.add_output_port(VisItParams,"self",VisItParams)

    registry.add_module(VisItCell, configureWidgetType=VisItCellConfigurationWidget)
    registry.add_input_port(VisItCell, "Location", CellLocation)
    registry.add_input_port(VisItCell, "variable", CDMSVariable)
    registry.add_input_port(VisItCell, "visitparams", VisItParams)
    registry.add_output_port(VisItCell, "self", VisItCell)


class VisItConfigurationWidget(StandardModuleConfigurationWidget):

    newConfigurationWidget = None
    currentConfigurationWidget = None
    savingChanges = False

    def __init__(self, module, controller, title, parent=None):
        """ VisItConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> LayerConfigurationWidget
        Setup the dialog ...

        """

        StandardModuleConfigurationWidget.__init__(self, module, controller, parent)
        self.setWindowTitle( title )
        self.moduleId = module.id
        self.getParameters( module )
        self.createTabs()
        self.createLayout()
        self.addPortConfigTab()

        if ( VisItConfigurationWidget.newConfigurationWidget == None ): VisItConfigurationWidget.setupSaveConfigurations()
        VisItConfigurationWidget.newConfigurationWidget = self

    def destroy( self, destroyWindow = True, destroySubWindows = True):
        self.saveConfigurations()
        StandardModuleConfigurationWidget.destroy( self, destroyWindow, destroySubWindows )

    def sizeHint(self):
        return QSize(400,200)

    def createTabs( self ):
        self.setLayout( QVBoxLayout() )
        self.layout().setMargin(0)
        self.layout().setSpacing(0)

        self.tabbedWidget = QTabWidget()
        self.layout().addWidget( self.tabbedWidget )
        self.createButtonLayout()

    def addPortConfigTab(self):
        portConfigPanel = self.getPortConfigPanel()
        self.tabbedWidget.addTab( portConfigPanel, 'ports' )

    @staticmethod
    def setupSaveConfigurations():
        import api
        ctrl = api.get_current_controller()
        scene = ctrl.current_pipeline_view
        scene.connect( scene, SIGNAL('moduleSelected'), VisItConfigurationWidget.saveConfigurations )

    @staticmethod
    def saveConfigurations( newModuleId=None, selectedItemList=None ):
        rv = False
        if not VisItConfigurationWidget.savingChanges:
            if VisItConfigurationWidget.currentConfigurationWidget and VisItConfigurationWidget.currentConfigurationWidget.state_changed:
                rv = VisItConfigurationWidget.currentConfigurationWidget.askToSaveChanges()
            VisItConfigurationWidget.currentConfigurationWidget = VisItConfigurationWidget.newConfigurationWidget
        return rv

    @staticmethod
    def saveNewConfigurations():
        rv = False
        #if not VisItConfigurationWidget.savingChangesVisItWidget
       #     if VisItConfigurationWidget.newConfigurationWidget and VisItConfigurationWidget.newConfigurationWidget.state_changed:
       #         rv = VisItConfigurationWidget.newConfigurationWidget.askToSaveChanges()
       #     VisItConfigurationWidget.currentConfigurationWidget = VisItConfigurationWidget.newConfigurationWidget
        return rv

    def getPortConfigPanel( self ):
        listContainer = QWidget( )
        listContainer.setLayout(QGridLayout(listContainer))
        listContainer.setFocusPolicy(Qt.WheelFocus)
        self.inputPorts = self.module.destinationPorts()
        self.inputDict = {}
        self.outputPorts = self.module.sourcePorts()
        self.outputDict = {}
        label = QLabel('Input Ports')
        label.setAlignment(Qt.AlignHCenter)
        label.font().setBold(True)
        label.font().setPointSize(12)
        listContainer.layout().addWidget(label, 0, 0)
        label = QLabel('Output Ports')
        label.setAlignment(Qt.AlignHCenter)
        label.font().setBold(True)
        label.font().setPointSize(12)
        listContainer.layout().addWidget(label, 0, 1)

        for i in xrange(len(self.inputPorts)):
            port = self.inputPorts[i]
            checkBox = self.checkBoxFromPort(port, True)
            checkBox.setFocusPolicy(Qt.StrongFocus)
            self.connect(checkBox, SIGNAL("stateChanged(int)"),
                         self.updateState)
            self.inputDict[port.name] = checkBox
            listContainer.layout().addWidget(checkBox, i+1, 0)

        for i in xrange(len(self.outputPorts)):
            port = self.outputPorts[i]
            checkBox = self.checkBoxFromPort(port)
            checkBox.setFocusPolicy(Qt.StrongFocus)
            self.connect(checkBox, SIGNAL("stateChanged(int)"),
                         self.updateState)
            self.outputDict[port.name] = checkBox
            listContainer.layout().addWidget(checkBox, i+1, 1)

        listContainer.adjustSize()
        listContainer.setFixedHeight(listContainer.height())
        return listContainer

    def closeEvent(self, event):
        print "close event set"
        self.askToSaveChanges()
        event.accept()

    def updateState(self, state):
        self.setFocus(Qt.MouseFocusReason)
        self.saveButton.setEnabled(True)
        self.resetButton.setEnabled(True)
        if not self.state_changed:
            self.state_changed = True
            self.emit(SIGNAL("stateChanged"))

    def saveTriggered(self, checked = False):
        self.okTriggered()
        for port in self.inputPorts:
            if (port.optional and
                self.inputDict[port.name].checkState()==Qt.Checked):
                self.module.visible_input_ports.add(port.name)
            else:
                self.module.visible_input_ports.discard(port.name)

        for port in self.outputPorts:
            if (port.optional and
                self.outputDict[port.name].checkState()==Qt.Checked):
                self.module.visible_output_ports.add(port.name)
            else:
                self.module.visible_output_ports.discard(port.name)
        self.saveButton.setEnabled(False)
        #self.resetButton.setEnabled(False)
        self.state_changed = False
        self.emit(SIGNAL("stateChanged"))
        #self.emit(SIGNAL('doneConfigure'), self.module.id)
        #self.close()

    def resetTriggered(self):
        self.startOver();
        self.setFocus(Qt.MouseFocusReason)
        self.setUpdatesEnabled(False)
        for i in xrange(len(self.inputPorts)):
            port = self.inputPorts[i]
            entry = (PortEndPoint.Destination, port.name)
            checkBox = self.inputDict[port.name]
            if not port.optional or entry in self.module.portVisible:
                checkBox.setCheckState(Qt.Checked)
            else:
                checkBox.setCheckState(Qt.Unchecked)
            if not port.optional or port.sigstring=='()':
                checkBox.setEnabled(False)
        for i in xrange(len(self.outputPorts)):
            port = self.outputPorts[i]
            entry = (PortEndPoint.Source, port.name)
            checkBox = self.outputDict[port.name]
            if not port.optional or entry in self.module.portVisible:
                checkBox.setCheckState(Qt.Checked)
            else:
                checkBox.setCheckState(Qt.Unchecked)
            if not port.optional:
                checkBox.setEnabled(False)
        self.setUpdatesEnabled(True)
        self.saveButton.setEnabled(True)
        self.resetButton.setEnabled(False)
        self.state_changed = False
        self.emit(SIGNAL("stateChanged"))
        #self.close()

    def stateChanged(self, changed = True ):
        self.state_changed = changed
        self.saveButton.setEnabled(True)
        self.resetButton.setEnabled(True)
#        print " %s-> state changed: %s " % ( self.pmod.getName(), str(changed) )

    def getParameters( self, module ):
        pass

    def createLayout( self ):
        self.groupBox = QGroupBox()
        self.groupBoxLayout = QHBoxLayout(self.groupBox)
        self.fileLabel = QLabel("Filename: ")
        self.fileEntry = QLineEdit();
        self.groupBoxLayout.addWidget(self.fileLabel)
        self.groupBoxLayout.addWidget(self.fileEntry)

    def createButtonLayout(self):
        """ createButtonLayout() -> None
        Construct Save & Reset button

        """
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setMargin(5)
        self.saveButton = QPushButton('&Save', self)
        self.saveButton.setFixedWidth(100)
        self.saveButton.setEnabled(True)
        self.buttonLayout.addWidget(self.saveButton)
        self.resetButton = QPushButton('&Reset', self)
        self.resetButton.setFixedWidth(100)
        self.resetButton.setEnabled(True)
        self.buttonLayout.addWidget(self.resetButton)

        self.layout().addLayout(self.buttonLayout)
        self.connect(self.saveButton,SIGNAL('clicked(bool)'),  self.saveTriggered)
        self.connect(self.resetButton,SIGNAL('clicked(bool)'),  self.resetTriggered)
        self.setMouseTracking(True)
        self.setFocusPolicy( Qt.WheelFocus )

    def okTriggered(self):
        pass

    def checkBoxFromPort(self, port, input_=False):
        checkBox = QCheckBox(port.name)
        if input_:
            port_visible = port.name in self.module.visible_input_ports
        else:
            port_visible = port.name in self.module.visible_output_ports
        if not port.optional or port_visible:
            checkBox.setCheckState(Qt.Checked)
        else:
            checkBox.setCheckState(Qt.Unchecked)
        if not port.optional or (input_ and port.sigstring=='()'):
            checkBox.setEnabled(False)
        return checkBox

    def persistParameterList( self, parameter_list, **args ):
        #print self.module
        #self.module_descriptor.module.persistParameterList(parameter_list, **args)
        pass

class VisItCellConfigurationWidget(VisItConfigurationWidget):
    """
    VisItCellConfigurationWidget ...
    """

    def __init__(self, module, controller, parent=None):
        """ VisItCellConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        """
        self.cellAddress = 'A1'
        VisItConfigurationWidget.__init__(self, module, controller, 'VisIt Cell Configuration', parent)

    def getParameters( self, module ):
        pass

    def updateVistrail(self):
        print 'updateVistrail'
        #functions = []
        # For now assume parameters changed everytime
        #if 1:
        #    functions.append(("sliceOffset", [self.sliceOffset]))
        #    #functions.append(("isoSurfaces", [self.isoSurfaces]))
        #    self.controller.update_functions(self.module, functions)

    def createLayout(self):
        """ createLayout() -> None
        Configure sections
        """
        VisItWidget = QGroupBox()
        self.tabbedWidget.addTab( VisItWidget, 'VisIt' )
        self.layout = QVBoxLayout()
        VisItWidget.setLayout( self.layout )
    
        
        #self.groupBox = QGroupBox()
        #self.groupBoxLayout = QHBoxLayout(self.groupBox)
        #self.fileLabel = QLabel("Filename: ")
        #self.fileEntry = QLineEdit();
        #self.groupBoxLayout.addWidget(self.fileLabel)
        #self.groupBoxLayout.addWidget(self.fileEntry)
        #self.layout.addWidget(self.groupBox)
        
        self.groupChoice = QGroupBox()
        self.groupChoiceLayout = QVBoxLayout(self.groupChoice)
        self.pseudocolor = QRadioButton("Pseudocolor Plot");
        self.pseudocolor.setChecked(True)
        self.contour = QRadioButton("Contour Plot");
        self.eva = QRadioButton("Extreme Value Analysis");
        self.groupChoiceLayout.addWidget(self.pseudocolor)
        self.groupChoiceLayout.addWidget(self.contour)
        self.groupChoiceLayout.addWidget(self.eva)
        self.layout.addWidget(self.groupChoice)
        moduleInstance = self.module.module_descriptor.module()
        #print moduleInstance
        QObject.connect(self.pseudocolor,SIGNAL("clicked()"),moduleInstance.LoadPseudocolorPlot)
        QObject.connect(self.contour,SIGNAL("clicked()"),moduleInstance.LoadContourPlot)


    def setDefaults(self):
        moduleInstance = self.module.module_descriptor.module()
        #self.sliceOffset = moduleInstance.getSliceOffset();
        #self.sliceOffsetValue.setText(str(self.sliceOffset))

    def updateController(self, controller=None):
        parmRecList = []
        #parmRecList.append( ( 'slice_offset' , [ self.sliceOffset ]  ), )
        #self.persistParameterList( parmRecList )
        #self.stateChanged(False)
        print "updating controller"

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget

        """
        #self.sliceOffset = str(self.sliceOffsetValue.text().toLocal8Bit().data())
        print "self module = ", self.module
        self.updateVistrail()
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))

    def startOver(self):
        self.setDefaults();
