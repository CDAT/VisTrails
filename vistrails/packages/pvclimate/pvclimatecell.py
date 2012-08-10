from PyQt4 import QtCore
from core.modules.module_registry import get_module_registry
from packages.vtk.vtkcell import QVTKWidget
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_cell import QCellWidget
from core.interpreter.default import get_default_interpreter

#from PVBase import PVModule
import paraview.simple as pvsp
import paraview.pvfilters
import vtk
from pvtransformation import Ui_pvtransformationeditor
# We are using our own constant (though we are calling it a variable)
import pvvariable

# Needed for configuration
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from gui.modules.module_configure import StandardModuleConfigurationWidget
from gui.common_widgets import QDockPushButton

# Needed for port related stuff
from core.vistrail.port import PortEndPoint
import core.modules.basic_modules as basic_modules
import core.db.action


# Needed to parse csv string into a list
import csv
import StringIO

class Transformation():
    def __init__(self):
        self.scale = [1.0, 1.0, 0.01]
        self.position = [0.0, 0.0, 0.0]
        self.origin = [0.0, 0.0, 0.0]
        self.orientation = [0.0, 0.0, 0.0]


class PVClimateCell(SpreadsheetCell):
    def __init__(self):
        SpreadsheetCell.__init__(self)
        self.cellWidget = None
        self.sliceOffset = 0.0
        self.isoSurfaces = "8"
        self.tranformation = Transformation()

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

        self.cellWidget = self.displayAndWait(QParaViewWidget, (proxies, self.sliceOffset, self.isoSurfaces))

    def persistParameterList( self, parameter_list, **args ):
        print "Getting Something"

    def setSliceOffset(self, value):
        self.sliceOffset = value

    def getSliceOffset(self):
        return self.sliceOffset

class QParaViewWidget(QVTKWidget):

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
            reader = var.get_reader()
            variableName = var.get_variable_name()
            variableType = var.get_variable_type()

            print 'reader is ', reader
            print 'variableName is ', variableName
            print 'variableType is ', variableType

            # Update pipeline
            reader.UpdatePipeline()

            # Get bounds
            bounds = reader.GetDataInformation().GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)

            # Create a slice representation
            sliceFilter = pvsp.Slice(reader)
            sliceFilter.SliceType.Normal = [0,0,1]
            sliceFilter.SliceType.Origin = origin
            sliceFilter.SliceOffsetValues = [float(sliceOffset)]

            #sliceFilter = pvsp.Transform(sliceFilter)
            #sliceFilter.Transform.Scale = [1,1,0.01]

            # \TODO:
            # 1. Fix saturation
            # 2. Add scalar bar
            rep = pvsp.Show(view=self.view)
            rep.LookupTable =  pvsp.GetLookupTableForArray( variableName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[0.0, 0.23, 0.299, 0.754, 30.0, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
            rep.ColorArrayName = variableName

            # Apply scale (squish in Z)
            rep.Scale  = [1,1,0.01]

            #self.view.Representations = []
            #self.view.Representations.append(rep)

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

    def test(self):
        print 'test'


def registerSelf():
    registry = get_module_registry()
    registry.add_module(PVClimateCell, configureWidgetType=PVClimateCellConfigurationWidget)
    registry.add_input_port(PVClimateCell, "Location", CellLocation)
    registry.add_input_port(PVClimateCell, "variable", pvvariable.PVVariable)
    registry.add_input_port(PVClimateCell, "sliceOffset", basic_modules.String)
    registry.add_input_port(PVClimateCell, "isoSurfaces", basic_modules.String)
    registry.add_output_port(PVClimateCell, "self", PVClimateCell)


class PVClimateConfigurationWidget(StandardModuleConfigurationWidget):

    newConfigurationWidget = None
    currentConfigurationWidget = None
    savingChanges = False

    def __init__(self, module, controller, title, parent=None):
        """ PVClimateConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> LayerConfigurationWidget
        Setup the dialog ...

        """
        StandardModuleConfigurationWidget.__init__(self, module, controller, parent)
        self.setWindowTitle( title )
        self.moduleId = module.id
        self.getParameters( module )
        self.createLayout()
        self.createButtonLayout()
        if ( PVClimateConfigurationWidget.newConfigurationWidget == None ): PVClimateConfigurationWidget.setupSaveConfigurations()
        PVClimateConfigurationWidget.newConfigurationWidget = self

    def destroy( self, destroyWindow = True, destroySubWindows = True):
        self.saveConfigurations()
        StandardModuleConfigurationWidget.destroy( self, destroyWindow, destroySubWindows )

    def sizeHint(self):
        return QSize(400,200)

        self.createButtonLayout()

    def addTransformationTab(self):
        transformationPanel = self.getTransformationPanel()
        self.tabbedWidget.addTab( transformationPanel, 'Transformation' )

    @staticmethod
    def setupSaveConfigurations():
        import api
        ctrl = api.get_current_controller()
        scene = ctrl.current_pipeline_view
        scene.connect( scene, SIGNAL('moduleSelected'), PVClimateConfigurationWidget.saveConfigurations )

    @staticmethod
    def saveConfigurations( newModuleId=None, selectedItemList=None ):
        rv = False
        if not PVClimateConfigurationWidget.savingChanges:
            if PVClimateConfigurationWidget.currentConfigurationWidget and PVClimateConfigurationWidget.currentConfigurationWidget.state_changed:
                rv = PVClimateConfigurationWidget.currentConfigurationWidget.askToSaveChanges()
            PVClimateConfigurationWidget.currentConfigurationWidget = PVClimateConfigurationWidget.newConfigurationWidget
        return rv

    @staticmethod
    def saveNewConfigurations():
        rv = False
        if not PVClimateConfigurationWidget.savingChanges:
            if PVClimateConfigurationWidget.newConfigurationWidget and PVClimateConfigurationWidget.newConfigurationWidget.state_changed:
                rv = PVClimateConfigurationWidget.newConfigurationWidget.askToSaveChanges()
            PVClimateConfigurationWidget.currentConfigurationWidget = PVClimateConfigurationWidget.newConfigurationWidget
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

    def getTransformationPanel(self):
        container = QGroupBox()
        pvtransformationeditor = Ui_pvtransformationeditor()
        pvtransformationeditor.setupUi(container)
        return container

    def closeEvent(self, event):
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
        self.setLayout( QVBoxLayout() )
        self.layout().setMargin(0)
        self.layout().setSpacing(0)


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
        print self.module
        #self.module_descriptor.module.persistParameterList(parameter_list, **args)
        #pass

class PVClimateCellConfigurationWidget(PVClimateConfigurationWidget):
    """
    PVClimateCellConfigurationWidget ...

    """

    def __init__(self, module, controller, parent=None):
        """ PVClimateCellConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...

        """
        self.cellAddress = 'A1'
        self.sliceOffset = 0
        self.representation_modules = []
        self.controller = controller
        self.moduleId = module.id
        self.init_representations()
        PVClimateConfigurationWidget.__init__(self, module, controller, 'PVClimate Cell Configuration', parent)

    def getParameters( self, module ):
        pass

    def updateVistrail(self):
        print 'controller.current_version', self.controller.current_version

        functions = []
        action = None
        functions.append(("sliceOffset", [self.sliceOffset]))
        action = self.controller.update_functions(self.module, functions)
        return action

    def init_representations(self):
        pipeline = self.controller.current_pipeline
        representation_ids = pipeline.get_inputPort_modules(self.moduleId, 'representation')
        for i, rep_id in enumerate(representation_ids):
            rep_module = pipeline.get_module_by_id(rep_id)
            self.representation_modules.append(rep_module)

    def create_remove_button(self):
        widget = QWidget()
        self.btn_del_var = QDockPushButton("Remove")
        self.btn_del_var.setEnabled(False)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(3)
        btn_layout.setMargin(0)
        btn_layout.addWidget(self.btn_del_var)
        btn_layout.addStretch()
        widget.setLayout(btn_layout)

        self.connect(self.btn_del_var, SIGNAL('clicked(bool)'), self.delete_clicked)

        return widget

    def delete_clicked(self):
        if self.representations_table.selectedItems():
            item = self.representations_table.selectedItems()[0]
            row = item.row()
            self.representations_table.removeRow(row)
            pv_generic_cell = self.get_workflow_module(self.moduleId)
            pv_generic_cell.removeRepresentation(row)
#            self.controller.execute_current_workflow()

    def create_representation_table(self):
        self.representations_table = PVRepresentationPlotTableWidget(self)
        self.representations_table.setRowCount(len(self.representation_modules))
        self.connect(self.representations_table, SIGNAL('itemSelectionChanged()'),
                     self.itemSelectionChanged)

        for i, rep_module in enumerate(self.representation_modules):
            # call static method to name to display
            display_name = rep_module.module_descriptor.module.name()
            item = PVRepresentationTableWidgetItem(rep_module,
                                                   display_name)
            item.setText(display_name)
            self.representations_table.setItem(i, 0, item)

            rep_config_widget = rep_module.module_descriptor.module.configuration_widget(self,
                                                                                         rep_module)
            self.connect(self, SIGNAL('okTriggered()'), rep_config_widget.okTriggered)
            self.config_panel_layout.addWidget(rep_config_widget)

        return self.representations_table

    def create_config_panel(self):
        self.config_panel = QWidget()
        self.config_panel_layout = QStackedLayout()
        self.config_panel.setLayout( self.config_panel_layout )

        return self.config_panel

    def createLayout(self):
        """ createlayout() -> None
        Configure sections
        """
        super(PVClimateCellConfigurationWidget, self).createLayout()
        representations_panel = QWidget()
        self.layout().addWidget( representations_panel )
        layout = QVBoxLayout()
        representations_panel.setLayout( layout )


        self.create_config_panel()
        self.create_representation_table()

        layout.addWidget(self.representations_table)
        layout.addWidget(self.create_remove_button())
        layout.addWidget(self.config_panel);

        self.setDefaults()

    def itemSelectionChanged(self):
        if self.representations_table.selectedItems():
            self.btn_del_var.setEnabled(True)
            item = self.representations_table.selectedItems()[0]
            self.config_panel.layout().setCurrentIndex(item.row())
        else:
            self.btn_del_var.setEnabled(False)

    def setDefaults(self):
        moduleInstance = self.module.module_descriptor.module()
        #self.sliceOffset = moduleInstance.getSliceOffset();
        #self.slice_offset_value.setText(str(self.sliceOffset))

    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'slice_offset' , [ self.sliceOffset ]  ), )
        self.persistParameterList( parmRecList )
        self.stateChanged(False)

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget

        """
        self.emit(SIGNAL('okTriggered()'))
        self.controller.execute_current_workflow()

    def startOver(self):
        self.setDefaults();

    def get_workflow_module(self, module_id):
        vistrails_interpreter = get_default_interpreter()
        object_map = vistrails_interpreter.find_persistent_entities(
                         self.controller.current_pipeline )[0]
        module_instance = object_map.get(module_id)

        return module_instance


class PVRepresentationTableWidgetItem(QTableWidgetItem):
    def __init__(self, module, plot_type):
        QTableWidgetItem.__init__(self)
        self.module = module
        self.plot_type = plot_type

class PVRepresentationPlotTableWidget(QTableWidget):
    def __init__(self, parent=None):
        QTableWidget.__init__(self, parent)
        self.setColumnCount(1)
        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Expanding)
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(QStringList() << "Representation Type")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
