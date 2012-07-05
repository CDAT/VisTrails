from PyQt4 import QtCore
from core.modules.module_registry import get_module_registry
from packages.vtk.vtkcell import QVTKWidget
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_cell import QCellWidget
#from PVBase import PVModule
import paraview.simple as pvsp
import paraview.pvfilters
import vtk

# We are using our own constant (though we are calling it a variable)
import pvvariable

# Needed for configuration
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from gui.modules.module_configure import StandardModuleConfigurationWidget

# Needed for port related stuff
from core.vistrail.port import PortEndPoint
import core.modules.basic_modules as basic_modules

# Needed to parse csv string into a list
import csv
import StringIO

class PVIsoSurfaceCell(SpreadsheetCell):
    def __init__(self):
        SpreadsheetCell.__init__(self)
        self.cellWidget = None
        self.sliceOffset = 0.0
        self.isoSurfaces = "8"

    def compute(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """
        # Fetch input variable
        proxies = self.forceGetInputListFromPort('variable')        

        # Fetch slice offset from input port
        if self.hasInputFromPort("sliceOffset"):
            self.sliceOffset = self.getInputFromPort("sliceOffset")
        else:
            pass

        # Fetch iso surfaces from input port
        if self.hasInputFromPort("isoSurfaces"):
            self.isoSurfaces = self.getInputFromPort("isoSurfaces")
        else:
            pass

        self.cellWidget = self.displayAndWait(QPVIsoSurfaceWidget, (proxies, self.sliceOffset, self.isoSurfaces))

    def persistParameterList( self, parameter_list, **args ):
        print "Getting Something"

    def setSliceOffset(self, value):
        self.sliceOffset = value

    def getSliceOffset(self):
        return self.sliceOffset

class QPVIsoSurfaceWidget(QVTKWidget):

    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QVTKWidget.__init__(self, parent, f)
        self.view = None

    def updateContents(self, inputPorts):
        if self.view==None:
            self.view = pvsp.CreateRenderView()
            renWin = self.view.GetRenderWindow()
            self.SetRenderWindow(renWin)
            iren = renWin.GetInteractor()
            print type(iren)
            iren.SetNonInteractiveRenderDelay(0)
            iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

        del self.view.Representations[:]

        # Fetch variables from the input port
        (pvvariables, sliceOffset, isoSurfaces) = inputPorts
        for var in pvvariables:
            print 'Hey ', var.getInputFromPort("file")
            print 'Hey ', var.getInputFromPort("name")
            reader = var.get_reader()
            variableName = var.get_variable_name()
            variableType = var.get_variable_type()
            #print reader
            #contour = pvsp.Contour(reader)
            #contour.ContourBy = [variableType, variableName]
            #contour.Isosurfaces = [0]
            #rep = pvsp.GetDisplayProperties(contour)
            # Now make a representation and add it to the view
            reader.Stride = [5,5,5]

            # Update pipeline
            reader.UpdatePipeline()

            # Get bounds
            bounds = reader.GetDataInformation().GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)           

            # Create a contour representation
            contour = pvsp.Contour(reader)
            contour.ContourBy = [variableType, variableName]

            isoSurfacesStringIO = StringIO.StringIO(isoSurfaces)
            csvReader = csv.reader(isoSurfacesStringIO, delimiter=',')
            isoSurfacesValues  = []
            for i in csvReader:
                for j in range(len(i)):
                    isoSurfacesValues.append(float(str(i[j])))
            contour.Isosurfaces = isoSurfacesValues
            contour.ComputeScalars = 1
            contour.ComputeNormals = 0

            #contour = pvsp.Transform(contour)
            #contour.Transform.Scale = [1,1,0.01]

            contourRep = pvsp.Show(view=self.view)
            contourRep.LookupTable =  pvsp.GetLookupTableForArray( variableName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[0.0, 0.23, 0.299, 0.754, 30.0, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
            contourRep.Scale  = [1,1,0.01]
            contourRep.Representation = 'Surface'
            contourRep.ColorArrayName = variableName

            #self.view.Representations.append(contourRep)
            #pvsp.servermanager.ProxyManager().SaveXMLState('/tmp/bar.xml')

            # Set view specific properties
            self.view.CenterAxesVisibility = 0
            self.view.Background = [0.5, 0.5, 0.5]

        self.view.ResetCamera()
        self.view.StillRender()

        QCellWidget.updateContents(self, inputPorts)

    def saveToPNG(self, filename):
        """ saveToPNG(filename: str) -> filename or vtkUnsignedCharArray

        Save the current widget contents to an image file. If
        str==None, then it returns the vtkUnsignedCharArray containing
        the PNG image. Otherwise, the filename is returned.

        """
        image = self.view.CaptureWindow(1)
        image.UnRegister(None)

        writer = vtk.vtkPNGWriter()
        writer.SetInput(image)
        if filename!=None:
            writer.SetFileName(filename)
        else:
            writer.WriteToMemoryOn()
        writer.Write()
        if filename:
            return filename
        else:
            return writer.GetResult()

    def deleteLater(self):
        QCellWidget.deleteLater(self)



def registerSelf():
    registry = get_module_registry()
    # For now, we don't have configuration widget
    #registry.add_module(PVIsoSurfaceCell, configureWidgetType=PVClimateCellConfigurationWidget)
    registry.add_module(PVIsoSurfaceCell)
    registry.add_input_port(PVIsoSurfaceCell, "Location", CellLocation)
    registry.add_input_port(PVIsoSurfaceCell, "variable", pvvariable.PVVariable)    
    registry.add_input_port(PVIsoSurfaceCell, "isoSurfaces", basic_modules.String)
    registry.add_output_port(PVIsoSurfaceCell, "self", PVIsoSurfaceCell)


#class PVClimateConfigurationWidget(StandardModuleConfigurationWidget):
#
#    newConfigurationWidget = None
#    currentConfigurationWidget = None
#    savingChanges = False
#
#    def __init__(self, module, controller, title, parent=None):
#        """ PVClimateConfigurationWidget(module: Module,
#                                       controller: VistrailController,
#                                       parent: QWidget)
#                                       -> LayerConfigurationWidget
#        Setup the dialog ...
#
#        """
#        StandardModuleConfigurationWidget.__init__(self, module, controller, parent)
#        self.setWindowTitle( title )
#        self.moduleId = module.id
#        self.getParameters( module )
#        self.createTabs()
#        self.createLayout()
#        self.addPortConfigTab()
#        if ( PVClimateConfigurationWidget.newConfigurationWidget == None ): PVClimateConfigurationWidget.setupSaveConfigurations()
#        PVClimateConfigurationWidget.newConfigurationWidget = self
#
#    def destroy( self, destroyWindow = True, destroySubWindows = True):
#        self.saveConfigurations()
#        StandardModuleConfigurationWidget.destroy( self, destroyWindow, destroySubWindows )
#
#    def sizeHint(self):
#        return QSize(400,200)
#
#    def createTabs( self ):
#        self.setLayout( QVBoxLayout() )
#        self.layout().setMargin(0)
#        self.layout().setSpacing(0)
#
#        self.tabbedWidget = QTabWidget()
#        self.layout().addWidget( self.tabbedWidget )
#        self.createButtonLayout()
#
#    def addPortConfigTab(self):
#        portConfigPanel = self.getPortConfigPanel()
#        self.tabbedWidget.addTab( portConfigPanel, 'ports' )
#
#    @staticmethod
#    def setupSaveConfigurations():
#        import api
#        ctrl = api.get_current_controller()
#        scene = ctrl.current_pipeline_view
#        scene.connect( scene, SIGNAL('moduleSelected'), PVClimateConfigurationWidget.saveConfigurations )
#
#    @staticmethod
#    def saveConfigurations( newModuleId=None, selectedItemList=None ):
#        rv = False
#        if not PVClimateConfigurationWidget.savingChanges:
#            if PVClimateConfigurationWidget.currentConfigurationWidget and PVClimateConfigurationWidget.currentConfigurationWidget.state_changed:
#                rv = PVClimateConfigurationWidget.currentConfigurationWidget.askToSaveChanges()
#            PVClimateConfigurationWidget.currentConfigurationWidget = PVClimateConfigurationWidget.newConfigurationWidget
#        return rv
#
#    @staticmethod
#    def saveNewConfigurations():
#        rv = False
#        if not PVClimateConfigurationWidget.savingChanges:
#            if PVClimateConfigurationWidget.newConfigurationWidget and PVClimateConfigurationWidget.newConfigurationWidget.state_changed:
#                rv = PVClimateConfigurationWidget.newConfigurationWidget.askToSaveChanges()
#            PVClimateConfigurationWidget.currentConfigurationWidget = PVClimateConfigurationWidget.newConfigurationWidget
#        return rv
#
#    def getPortConfigPanel( self ):
#        listContainer = QWidget( )
#        listContainer.setLayout(QGridLayout(listContainer))
#        listContainer.setFocusPolicy(Qt.WheelFocus)
#        self.inputPorts = self.module.destinationPorts()
#        self.inputDict = {}
#        self.outputPorts = self.module.sourcePorts()
#        self.outputDict = {}
#        label = QLabel('Input Ports')
#        label.setAlignment(Qt.AlignHCenter)
#        label.font().setBold(True)
#        label.font().setPointSize(12)
#        listContainer.layout().addWidget(label, 0, 0)
#        label = QLabel('Output Ports')
#        label.setAlignment(Qt.AlignHCenter)
#        label.font().setBold(True)
#        label.font().setPointSize(12)
#        listContainer.layout().addWidget(label, 0, 1)
#
#        for i in xrange(len(self.inputPorts)):
#            port = self.inputPorts[i]
#            checkBox = self.checkBoxFromPort(port, True)
#            checkBox.setFocusPolicy(Qt.StrongFocus)
#            self.connect(checkBox, SIGNAL("stateChanged(int)"),
#                         self.updateState)
#            self.inputDict[port.name] = checkBox
#            listContainer.layout().addWidget(checkBox, i+1, 0)
#
#        for i in xrange(len(self.outputPorts)):
#            port = self.outputPorts[i]
#            checkBox = self.checkBoxFromPort(port)
#            checkBox.setFocusPolicy(Qt.StrongFocus)
#            self.connect(checkBox, SIGNAL("stateChanged(int)"),
#                         self.updateState)
#            self.outputDict[port.name] = checkBox
#            listContainer.layout().addWidget(checkBox, i+1, 1)
#
#        listContainer.adjustSize()
#        listContainer.setFixedHeight(listContainer.height())
#        return listContainer
#
#    def closeEvent(self, event):
#        self.askToSaveChanges()
#        event.accept()
#
#    def updateState(self, state):
#        self.setFocus(Qt.MouseFocusReason)
#        self.saveButton.setEnabled(True)
#        self.resetButton.setEnabled(True)
#        if not self.state_changed:
#            self.state_changed = True
#            self.emit(SIGNAL("stateChanged"))
#
#    def saveTriggered(self, checked = False):
#        self.okTriggered()
#        for port in self.inputPorts:
#            if (port.optional and
#                self.inputDict[port.name].checkState()==Qt.Checked):
#                self.module.visible_input_ports.add(port.name)
#            else:
#                self.module.visible_input_ports.discard(port.name)
#
#        for port in self.outputPorts:
#            if (port.optional and
#                self.outputDict[port.name].checkState()==Qt.Checked):
#                self.module.visible_output_ports.add(port.name)
#            else:
#                self.module.visible_output_ports.discard(port.name)
#        self.saveButton.setEnabled(False)
#        #self.resetButton.setEnabled(False)
#        self.state_changed = False
#        self.emit(SIGNAL("stateChanged"))
#        #self.emit(SIGNAL('doneConfigure'), self.module.id)
#        #self.close()
#
#    def resetTriggered(self):
#        self.startOver();
#        self.setFocus(Qt.MouseFocusReason)
#        self.setUpdatesEnabled(False)
#        for i in xrange(len(self.inputPorts)):
#            port = self.inputPorts[i]
#            entry = (PortEndPoint.Destination, port.name)
#            checkBox = self.inputDict[port.name]
#            if not port.optional or entry in self.module.portVisible:
#                checkBox.setCheckState(Qt.Checked)
#            else:
#                checkBox.setCheckState(Qt.Unchecked)
#            if not port.optional or port.sigstring=='()':
#                checkBox.setEnabled(False)
#        for i in xrange(len(self.outputPorts)):
#            port = self.outputPorts[i]
#            entry = (PortEndPoint.Source, port.name)
#            checkBox = self.outputDict[port.name]
#            if not port.optional or entry in self.module.portVisible:
#                checkBox.setCheckState(Qt.Checked)
#            else:
#                checkBox.setCheckState(Qt.Unchecked)
#            if not port.optional:
#                checkBox.setEnabled(False)
#        self.setUpdatesEnabled(True)
#        self.saveButton.setEnabled(True)
#        self.resetButton.setEnabled(False)
#        self.state_changed = False
#        self.emit(SIGNAL("stateChanged"))
#        #self.close()
#
#    def stateChanged(self, changed = True ):
#        self.state_changed = changed
#        self.saveButton.setEnabled(True)
#        self.resetButton.setEnabled(True)
##        print " %s-> state changed: %s " % ( self.pmod.getName(), str(changed) )
#
#    def getParameters( self, module ):
#        pass
#
#    def createLayout( self ):
#        pass
#
#    def createButtonLayout(self):
#        """ createButtonLayout() -> None
#        Construct Save & Reset button
#
#        """
#        self.buttonLayout = QHBoxLayout()
#        self.buttonLayout.setMargin(5)
#        self.saveButton = QPushButton('&Save', self)
#        self.saveButton.setFixedWidth(100)
#        self.saveButton.setEnabled(True)
#        self.buttonLayout.addWidget(self.saveButton)
#        self.resetButton = QPushButton('&Reset', self)
#        self.resetButton.setFixedWidth(100)
#        self.resetButton.setEnabled(True)
#        self.buttonLayout.addWidget(self.resetButton)
#
#        self.layout().addLayout(self.buttonLayout)
#        self.connect(self.saveButton,SIGNAL('clicked(bool)'),  self.saveTriggered)
#        self.connect(self.resetButton,SIGNAL('clicked(bool)'),  self.resetTriggered)
#        self.setMouseTracking(True)
#        self.setFocusPolicy( Qt.WheelFocus )
#
#    def okTriggered(self):
#        pass
#
#    def checkBoxFromPort(self, port, input_=False):
#        checkBox = QCheckBox(port.name)
#        if input_:
#            port_visible = port.name in self.module.visible_input_ports
#        else:
#            port_visible = port.name in self.module.visible_output_ports
#        if not port.optional or port_visible:
#            checkBox.setCheckState(Qt.Checked)
#        else:
#            checkBox.setCheckState(Qt.Unchecked)
#        if not port.optional or (input_ and port.sigstring=='()'):
#            checkBox.setEnabled(False)
#        return checkBox
#
#    def persistParameterList( self, parameter_list, **args ):
#        print self.module
#        #self.module_descriptor.module.persistParameterList(parameter_list, **args)
#        #pass
#
#class PVClimateCellConfigurationWidget(PVClimateConfigurationWidget):
#    """
#    PVClimateCellConfigurationWidget ...
#
#    """
#
#    def __init__(self, module, controller, parent=None):
#        """ PVClimateCellConfigurationWidget(module: Module,
#                                       controller: VistrailController,
#                                       parent: QWidget)
#                                       -> DemoDataConfigurationWidget
#        Setup the dialog ...
#
#        """
#        self.cellAddress = 'A1'
#        self.sliceOffset = 0
#        PVClimateConfigurationWidget.__init__(self, module, controller, 'PVClimate Cell Configuration', parent)
#
#    def getParameters( self, module ):
#        pass
#
#    def updateVistrail(self):
#        print 'updateVistrail'
#        functions = []
#        # For now assume parameters changed everytime
#        if 1:
#            functions.append(("sliceOffset", [self.sliceOffset]))
#            #functions.append(("isoSurfaces", [self.isoSurfaces]))
#            self.controller.update_functions(self.module, functions)
#
#    def createLayout(self):
#        """ createEditor() -> None
#        Configure sections
#        """
#        print "Creating layout"
#        sliceWidget = QWidget()
#        self.tabbedWidget.addTab( sliceWidget, 'Slice' )
#        layout = QVBoxLayout()
#        sliceWidget.setLayout( layout )
#
#        sliceOffsetLayout = QHBoxLayout()
#        self.sliceOffsetLabel = QLabel( "Slice Offset:" )
#        self.sliceOffsetValue =  QLineEdit ( self.parent() )
#        sliceOffsetLayout.addWidget( self.sliceOffsetLabel )
#        sliceOffsetLayout.addWidget( self.sliceOffsetValue )
#        layout.addLayout(sliceOffsetLayout)
#        self.connect( self.sliceOffsetValue, SIGNAL("editingFinished()"), self.stateChanged )
#        self.setDefaults()
#
#
#    def setDefaults(self):
#        moduleInstance = self.module.module_descriptor.module()
#        self.sliceOffset = moduleInstance.getSliceOffset();
#        self.sliceOffsetValue.setText(str(self.sliceOffset))
#
#    def updateController(self, controller=None):
#        parmRecList = []
#        parmRecList.append( ( 'slice_offset' , [ self.sliceOffset ]  ), )
#        self.persistParameterList( parmRecList )
#        self.stateChanged(False)
#
#    def okTriggered(self, checked = False):
#        """ okTriggered(checked: bool) -> None
#        Update vistrail controller (if neccesssary) then close the widget
#
#        """
#        self.sliceOffset = str(self.sliceOffsetValue.text().toLocal8Bit().data())
#        print self.module
#        self.updateVistrail()
#        self.updateController(self.controller)
#        self.emit(SIGNAL('doneConfigure()'))
#
#    def startOver(self):
#        self.setDefaults();
