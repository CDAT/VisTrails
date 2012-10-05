'''
Created on Feb 14, 2011

@author: tpmaxwel
'''
ENABLE_JOYSTICK = False
from PyQt4 import QtCore, QtGui
from gui.qt import qt_super
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_base import StandardSheetReference, StandardSingleCellSheetReference
from packages.vtk.vtkcell import QVTKWidget
from packages.vtDV3D.PersistentModule import AlgorithmOutputModule3D, PersistentVisualizationModule
from packages.vtDV3D.InteractiveConfiguration import *
from packages.vtDV3D.CaptionManager import *
from packages.vtDV3D.WorkflowModule import WorkflowModule
if ENABLE_JOYSTICK: from packages.vtDV3D.JoystickInterface import *
else:               ControlEventType = None
from packages.vtDV3D import ModuleStore
from packages.vtDV3D import HyperwallManager
from packages.vtDV3D.vtUtilities import *
import os, math, sys

vmath = vtk.vtkMath()
packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultLogoFile = os.path.join( defaultMapDir,  'uvcdat.jpg' )
defaultMapFile = os.path.join( defaultMapDir,  'earth2k.jpg' )
defaultMapCut = -180
# defaultMapFile = os.path.join( defaultMapDir,  'world_huge.jpg' )
# defaultMapCut1 = 0
SLIDER_MAX_VALUE = 100
MAX_IMAGE_SIZE = 1000000

def get_coords_from_cell_address( row, col):
    try:
        col = ord(col)-ord('A')
        row = int(row)-1
        return ( col, row )
    except:
        raise Exception('ColumnRowAddress format error: %s ' % str( [ row, col ] ) )

def parse_cell_address( address ):
    try:
        if len(address)>1:
            if '!' in address: address = address.split('!')[1]
            if address[0] >= 'A' and address[0] <= 'Z':
                return get_coords_from_cell_address( address[1:], address[0] )
            else:
                return get_coords_from_cell_address( address[:-1], address[-1] )
    except TypeError:
        return ( address.row, address.col )

class QVTKClientWidget(QVTKWidget):
    """
    QVTKWidget with interaction observers
    
    """
    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QVTKWidget.__init__(self, parent, f )
        self.iRenderCount = 0
        self.iRenderPeriod = 10
        self.current_button = QtCore.Qt.NoButton
        self.current_pos = QtCore.QPoint( 50, 50 )

    def event(self, e): 
        if ENABLE_JOYSTICK and ( e.type() == ControlEventType ):   
            self.processControllerEvent( e, [ self.width(), self.height() ] ) 
        if e.type() == QtCore.QEvent.MouseButtonPress:     
            self.current_button = e.button()  
            self.current_pos = e.globalPos()   
        elif e.type() == QtCore.QEvent.MouseButtonRelease: 
            self.current_button = QtCore.Qt.NoButton
        return qt_super(QVTKClientWidget, self).event(e) 
    
    def processControllerEvent(self, event, size ):
        renWin = self.GetRenderWindow()
        iren = renWin.GetInteractor()
        renderers = renWin.GetRenderers()
        renderer = renderers.GetFirstRenderer()
        if event.controlEventType == 'J':
            doRender = ( self.iRenderCount == self.iRenderPeriod )
            self.iRenderCount = 0 if doRender else self.iRenderCount + 1
            dx = event.jx
            dy = event.jy
            while renderer <> None:
              center = [ size[0]/2, size[1]/2]           
              vp = renderer.GetViewport()         
              delta_elevation = -700.0/((vp[3] - vp[1])*size[1])
              delta_azimuth = -700.0/((vp[2] - vp[0])*size[0])             
              rxf = dx * delta_azimuth
              ryf = dy * delta_elevation 
#              print "Processing Rotate Event: ( %.2f, %.2f )" % ( rxf, ryf )         
              camera = renderer.GetActiveCamera()
              camera.Azimuth(rxf)
              camera.Elevation(ryf)
                                               
              if doRender:
                  camera.OrthogonalizeViewUp()     
                  renderer.ResetCameraClippingRange()
                  iren.Render()
              renderer = renderers.GetNextItem()
              
        elif event.controlEventType == 'j':
            doRender = ( self.iRenderCount == self.iRenderPeriod )
            self.iRenderCount = 0 if doRender else self.iRenderCount + 1
            dx = event.jx
            dy = event.jy
            if dy <> 0.0: 
                while renderer <> None:                                               
                  if doRender:
                      camera = renderer.GetActiveCamera()
                      if dy > 0.0: camera.Dolly( 0.9 )
                      if dy < 0.0: camera.Dolly( 1.1 )    
                      renderer.ResetCameraClippingRange()
                      iren.Render()
                  renderer = renderers.GetNextItem()
                               
        elif event.controlEventType == 'P':
            i0 = event.buttonId[0]
            i1 = event.buttonId[1]
            while renderer <> None:          
              if i0 == 1:  
                  camera = renderer.GetActiveCamera()  
                  if i1 == 4: camera.Dolly( 1.1 )         
                  if i1 == 6: camera.Dolly( 0.9 ) 
                  renderer.ResetCameraClippingRange()     
                  iren.Render()
                  renderer = renderers.GetNextItem()
       
#              newAngle = vmath.DegreesFromRadians( math.asin( dy ) )
#              camera.Roll( newAngle )
#              camera.OrthogonalizeViewUp()  
#              if dy > 0:
#                  camera.Dolly( 1.1 )
#              else:
#                  camera.Dolly( 0.9 )

#                    ViewFocus = camera.GetFocalPoint()
#                    renderer.SetWorldPoint(ViewFocus[0], ViewFocus[1], ViewFocus[2], 1.0)
#                    renderer.WorldToDisplay()
#                    ViewFocus = renderer.GetDisplayPoint()
#                    focalDepth = ViewFocus[2]
#
#                    renderer.SetDisplayPoint(iren.GetEventPosition()[0], iren.GetEventPosition()[1], focalDepth )
#                    renderer.DisplayToWorld()
#                    newPickPoint = renderer.GetWorldPoint()
#                    if newPickPoint[3] > 0.0:
#                        newPickPoint = [ newPickPoint[0] / newPickPoint[3],  newPickPoint[1] / newPickPoint[3], newPickPoint[2] / newPickPoint[3], 1.0]                    
#                    ViewFocus = camera.GetFocalPoint()
#                    ViewPoint = camera.GetPosition()
#                    scale = 0.1                        
#                    MotionVector = [ scale * (ViewFocus[0] - newPickPoint[0]), scale * (ViewFocus[1] - newPickPoint[1]), scale * (ViewFocus[2] - newPickPoint[2]) ]         
#                    camera.SetFocalPoint(MotionVector[0] + ViewFocus[0], MotionVector[1] + ViewFocus[1], MotionVector[2] + ViewFocus[2])           
#                    camera.SetPosition(MotionVector[0] + ViewPoint[0], MotionVector[1] + ViewPoint[1], MotionVector[2] + ViewPoint[2])
        

class QVTKServerWidget( QVTKClientWidget ):
    """
    QVTKWidget with interaction observers
    
    """
    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QVTKClientWidget.__init__(self, parent, f )
        self.location = 'A1'
        
    def setLocation( self, location ):
        self.location = location

    def updateContents( self, inputPorts ):
        if len( inputPorts ) > 5:
            if inputPorts[5]:
                self.SetRenderWindow( inputPorts[5] )
        QVTKWidget.updateContents(self, inputPorts )

    def event(self, e): 
        dims = [ self.width(), self.height() ]   
        if   e.type() == QtCore.QEvent.KeyPress:           self.processInteractionEvent('keyPress',e,dims)  
        elif e.type() == QtCore.QEvent.MouseButtonPress:   self.processInteractionEvent('buttonPress',e,dims) 
        elif e.type() == QtCore.QEvent.MouseMove:          self.processInteractionEvent('mouseMove',e,dims) 
        elif e.type() == QtCore.QEvent.MouseButtonRelease: self.processInteractionEvent('buttonRelease',e,dims) 
        elif e.type() == QtCore.QEvent.KeyRelease:         self.processInteractionEvent('keyRelease',e,dims)         
        elif e.type() == ControlEventType:                 self.processInteractionEvent('joystick',e,dims)         
        return qt_super(QVTKServerWidget, self).event(e)

    def getSelectedCells(self):
        cells = []
        sheet = self.findSheetTabWidget()
        if sheet: cells = sheet.getSelectedLocations()
        return cells

    def getCamera(self):
        rens = self.mRenWin.GetRenderers()
        rens.InitTraversal()
        for i in xrange(rens.GetNumberOfItems()):
            ren = rens.GetNextItem()
            dcam = ren.GetActiveCamera()
            if dcam: return dcam
        return None
        
    def processInteractionEvent( self, name, event, dims ):
        cam = self.getCamera()
        camera_pos = None
        if cam:
            cpos = cam.GetPosition()
            cfol = cam.GetFocalPoint()
            cup = cam.GetViewUp()
            camera_pos = (cpos,cfol,cup)
        screen_pos = parse_cell_address( self.location )
        HyperwallManager.getInstance().processInteractionEvent( name, event, screen_pos, dims, camera_pos ) 
        
        
        
#    def interactionEvent(self, istyle, name):
#        """ interactionEvent(istyle: vtkInteractorStyle, name: str) -> None
#        Make sure interactions sync across selected renderers
#        
#        """
#        if name=='MouseWheelForwardEvent':
#            istyle.OnMouseWheelForward()
#        if name=='MouseWheelBackwardEvent':
#            istyle.OnMouseWheelBackward()
#        ren = self.interacting
#        if not ren:
#            ren = self.getActiveRenderer(istyle.GetInteractor())
#        if ren:
#            cam = ren.GetActiveCamera()
#            cpos = cam.GetPosition()
#            cfol = cam.GetFocalPoint()
#            cup = cam.GetViewUp()
#            for cell in self.getSelectedCellWidgets():
#                if cell!=self and hasattr(cell, 'getRendererList'): 
#                    rens = cell.getRendererList()
#                    for r in rens:
#                        if r!=ren:
#                            dcam = r.GetActiveCamera()
#                            dcam.SetPosition(cpos)
#                            dcam.SetFocalPoint(cfol)
#                            dcam.SetViewUp(cup)
#                            r.ResetCameraClippingRange()
#                    cell.update()


class PM_DV3DCell( SpreadsheetCell, PersistentVisualizationModule ):

    def __init__( self, mid, **args ):
        SpreadsheetCell.__init__(self)
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, **args )
        self.fieldData = []
#        self.addConfigurableMethod( 'resetCamera', self.resetCamera, 'A' )
#        self.addConfigurableMethod( 'showLogo', self.toggleLogoVisibility, 'L' )
        if self.isClient:  
            self.location = CellLocation()
            self.location.row = 0
            self.location.col = 0
            self.acceptsGenericConfigs = True
        self.allowMultipleInputs[0] = True
        self.renderers = []
        self.cellWidget = None
        self.imageInfo = None
        self.renWin = None
        self.builtCellWidget = False
        self.logoActor = None
        self.logoVisible = True
        self.logoRepresentation = None 
        self.captionManager = None 
        self.addConfigurableFunction( CaptionManager.config_name, [ ( String, 'data') ], 'k', label='Add Caption', open=self.editCaption )
        
    def editCaption( self, caption=None ): 
        if self.captionManager:  
            self.captionManager.editCaption( caption )

    def getSheetTabWidget( self ):   
        return self.cellWidget.findSheetTabWidget() if self.cellWidget else None
    
    def toggleLogoVisibility1( self ):
        self.logoVisible = not self.logoVisible
        self.logoActor.SetVisibility( self.logoVisible ) 
        self.logoActor.Modified()
        self.renWin.Render() 

    def toggleLogoVisibility( self ):
        if self.logoRepresentation:
            self.logoVisible = not self.logoVisible
            if self.logoVisible: self.logoWidget.On()
            else: self.logoWidget.Off()
            self.renWin.Render() 

    def addLogo(self):
        if self.logoRepresentation == None:
            reader = vtk.vtkJPEGReader()
            reader.SetFileName( defaultLogoFile )
            logo_input = reader.GetOutput()
            logo_input.Update()
            self.logoRepresentation = vtk.vtkLogoRepresentation()
            self.logoRepresentation.SetImage(logo_input)
            self.logoRepresentation.ProportionalResizeOn ()
            self.logoRepresentation.SetPosition( 0.82, 0.0 )
            self.logoRepresentation.SetPosition2( 0.18, 0.08 )
            self.logoRepresentation.GetImageProperty().SetOpacity( 0.9 )
            self.logoRepresentation.GetImageProperty().SetDisplayLocationToBackground() 
            self.logoWidget = vtk.vtkLogoWidget()
            self.logoWidget.SetInteractor( self.iren )
            self.logoWidget.SetRepresentation(self.logoRepresentation)
            self.logoWidget.On()
            self.render() 
     
    def addLogo1(self):
        upper_corner = False
        if len(self.renderers) and self.renWin:
            if self.logoActor == None:
                reader = vtk.vtkJPEGReader()
                reader.SetFileName( defaultLogoFile )
                self.logoMapper = vtk.vtkImageMapper()
                input = reader.GetOutput()
                self.logoMapper.SetInput( input )

                input.Update()
                self.logoDims = input.GetDimensions()
                range = input.GetScalarRange()
                self.logoMapper.SetColorWindow( 0.5 * ( range[1] - range[0] ) )
                self.logoMapper.SetColorLevel( 0.5 * (range[1] + range[0]) )
            else:
                self.renderer.RemoveActor2D( self.logoActor )
                self.logoActor = None
                           
            self.logoActor = vtk.vtkActor2D()
            properties = self.logoActor.GetProperty()  
            properties.SetDisplayLocationToBackground() 
            properties.SetOpacity( 0.5 )          
            self.logoActor.SetMapper( self.logoMapper )
            self.renderer.AddActor2D( self.logoActor )
            viewport_dims = self.renWin.GetSize() 
            if upper_corner:
                self.logoActor.SetDisplayPosition( viewport_dims[0]-self.logoDims[0], viewport_dims[1]-self.logoDims[1] )
            else:
                self.logoActor.SetDisplayPosition( viewport_dims[0]-self.logoDims[0], 0 )
            self.logoActor.SetVisibility( self.logoVisible )
            self.logoActor.Modified()
#            imageActor.SetWidth( 0.25 )      
#            imageActor.SetHeight( 0.1 ) 
#            coord = self.logoActor.GetPositionCoordinate()  
#            coord.SetCoordinateSystemToNormalizedViewport()
#            coord.SetValue( 0.75, 0.9 ) 
            
        
    def onRender( self, caller, event ):
        self.addLogo()
        PersistentVisualizationModule.onRender( self, caller, event  )

    def processKeyEvent( self, key, caller=None, event=None ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper            
        if (  key == 'k'  ):
            if self.GetRenWinID() in DV3DPipelineHelper.getActiveRenWinIds():
                self.captionManager.addCaption()
                ( interactionState, persisted ) =  self.getInteractionState( key )
                if state <> None: self.updateInteractionState( state, self.isAltMode  )                 
                self.render() 
        else:
            PersistentVisualizationModule.processKeyEvent( self, key, caller, event ) 
                        
    def adjustSheetDimensions(self, row, col ):
        sheetTabWidget = getSheetTabWidget()
        ( rc, cc ) = sheetTabWidget.getDimension()
        rowChanged, colChanged = False, False
        if row >= rc: 
            rc = row + 1
            rowChanged = True
        if col >= cc: 
            cc = col + 1
            colChanged = True
        if rowChanged or colChanged:    sheetTabWidget.setDimension( rc, cc )
        if rowChanged:                  sheetTabWidget.rowSpinBoxChanged()            
        if colChanged:                  sheetTabWidget.colSpinBoxChanged()

    def getSelectedCells(self):
        cells = []
        if self.cellWidget:
            sheet = self.cellWidget.findSheetTabWidget()
            if sheet: cells = sheet.getSelectedLocations()
        return cells
        
    def isSelected(self):
        if self.location:
            cells = self.getSelectedCells()
            cell_coords = ( self.location.row, self.location.col )
            for cell in cells:
                if cell == cell_coords: return True
        return False
    
    def syncCamera( self, cpos, cfol, cup ):
        if self.renWin:
            rens = self.renWin.GetRenderers()
            rens.InitTraversal()
            for i in xrange(rens.GetNumberOfItems()):
                ren = rens.GetNextItem()
                dcam = ren.GetActiveCamera()
                if dcam:
                    dcam.SetPosition(cpos)
                    dcam.SetFocalPoint(cfol)
                    dcam.SetViewUp(cup)
        
    def setCellLocation( self, moduleId ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper   
        cellLocation = CellLocation()
        cellLocation.rowSpan = 1
        cellLocation.colSpan = 1
        cell_coordinates = None
        ( sheetName, address ) = DV3DPipelineHelper.getCellAddress( self.pipeline ) 
        if self.isClient:            
            cellLocation.sheetReference = StandardSheetReference()
            cellLocation.sheetReference.sheetName = HyperwallManager.getInstance().deviceName
        elif not address: 
            address_input = self.getInputValue( "cell_location", None )
            address = getItem(  address_input )
            
        if address:
            print "Setting Cell Address from Input: %s " % ( address )
            address = address.replace(' ', '').upper()
            address = address.split('!')[-1]
            cell_coordinates = parse_cell_address( address )
        else:
            cell_coordinates = HyperwallManager.getInstance().getCellCoordinatesForModule( moduleId )
            if cell_coordinates == None: return None
        cellLocation.col = cell_coordinates[0]
        cellLocation.row = cell_coordinates[1]
         
        print " --- Set cell location[%s]: %s, address: %s "  % ( str(moduleId), str( [ cellLocation.col, cellLocation.row ] ), str(address) )
        self.overrideLocation( cellLocation )
        self.adjustSheetDimensions( cellLocation.row, cellLocation.col )
        return [ cellLocation.col, cellLocation.row, 1, 1 ]
    
    def updateHyperwall(self):
        dimensions = self.setCellLocation( self.moduleID )  
        if dimensions:  
            ispec = self.inputSpecs[ 0 ]    
            HyperwallManager.getInstance().addCell( self.moduleID, ispec.datasetId, str(0), dimensions )
            HyperwallManager.getInstance().executeCurrentWorkflow( self.moduleID )

    def isBuilt(self):
        return ( self.cellWidget <> None )
   
    def buildPipeline(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        self.buildRendering()

        if not self.builtCellWidget:
            self.buildWidget()
            if self.renWin: self.renWin.Render() 
   
    def execute(self, **args ):
        if self.builtCellWidget:  self.builtCellWidget = args.get( 'animate', False )
        PersistentVisualizationModule.execute(self, **args)
        self.recordCameraPosition()
        
    def addTitle(self):    
        title = getItem( self.getInputValue( "title", None ) )
        if title: self.titleBuffer = title
        if self.titleBuffer and self.renderer:
            self.getTitleActor().VisibilityOn() 
                      
    def recordCameraPosition(self):
        aCamera = self.renderer.GetActiveCamera()
        self.cameraPosition = aCamera.GetPosition()
        self.cameraFocalPoint = aCamera.GetFocalPoint()
        self.cameraViewUp = aCamera.GetViewUp()
         
    def resetCamera(self):
        aCamera = self.renderer.GetActiveCamera()
        aCamera.SetViewUp( *self.cameraViewUp )
        aCamera.SetPosition( *self.cameraPosition )
        aCamera.SetFocalPoint( *self.cameraFocalPoint )
        aCamera.ComputeViewPlaneNormal()
        self.renderer.ResetCamera() 
        self.render()                            
        
    def buildWidget(self):                        
        if self.renderers and not self.isBuilt():
            renderViews = []
            renderView = None
            iStyle = None
            iHandlers = []
            picker = None
            style = vtk.vtkInteractorStyleTrackballCamera()
            style_name = style.__class__.__name__
            iStyle = wrapVTKModule( style_name, style )   
            
            if self.isServer:
                self.cellWidget = self.displayAndWait( QVTKServerWidget, (self.renderers, renderView, iHandlers, iStyle, picker ) )
                self.cellWidget.setLocation( self.location )
            elif self.isClient:
                self.cellWidget = self.displayAndWait( QVTKClientWidget, (self.renderers, renderView, iHandlers, iStyle, picker ) )
            else:
                self.cellWidget = self.displayAndWait( QVTKClientWidget, (self.renderers, renderView, iHandlers, iStyle, picker ) )
            #in mashup mode, self.displayAndWait will return None
            if self.cellWidget:
                self.renWin = self.cellWidget.GetRenderWindow() 
                self.iren = self.renWin.GetInteractor()
                self.navigationInteractorStyle = self.iren.GetInteractorStyle()
                caption_data = self.getInputValue( CaptionManager.config_name, None )
                self.captionManager = CaptionManager( self.cellWidget, self.iren, data=caption_data )
                self.connect(self.captionManager, CaptionManager.persist_captions_signal, self.persistCaptions )  
                
                if ENABLE_JOYSTICK: 
                    if joystick.enabled():
                        joystick.addTarget( self.cellWidget )   
            else: 
                print "  --- Error creating cellWidget --- "   
                sys.stdout.flush()     
            
            cell_location = "%s%s" % ( chr(ord('A') + self.location.col ), self.location.row + 1 )   
            PersistentVisualizationModule.renderMap[ cell_location ] = self.iren
            self.builtCellWidget = True
        else:               
            print>>sys.stderr, "Error, no renderers supplied to DV3DCell" 
     
    def persistCaptions( self, serializedCaptions ): 
        parmList = []
        parmList.append( ( CaptionManager.config_name, [ serializedCaptions ] ) )
        print " ---> Persisting captions: ", serializedCaptions
        self.persistParameterList( parmList ) 
                   
    def updateStereo( self, enableStereo ):  
        if enableStereo <> self.stereoEnabled:  
            self.toggleStereo()   
            self.stereoEnabled = not self.stereoEnabled 
 
    def toggleStereo(self):
        iren = self.renWin.GetInteractor()
        keycode = QString('3').unicode().toLatin1()
        iren.SetKeyEventInformation( 0, 0, keycode, 0, "3" )     
        iren.InvokeEvent( vtk.vtkCommand.KeyPressEvent )

    def updateModule( self, **args ):
        animate = args.get( 'animate', False )
        if not animate: self.buildPipeline()
        
    def activateWidgets( self, iren ):
        pass

    def buildRendering(self):
        module = self.getRegisteredModule()

        self.renderers = []
        self.renderer = None
        self.fieldData = []
        moduleList = self.inputModuleList() 
        if not moduleList: 
            moduleList = [ self.inputModule() ]
        for inputModule in moduleList:
            if inputModule <> None:
                renderer1 = inputModule.getRenderer() 
                if  renderer1 <> None: 
                    if not self.renderer: self.renderer = renderer1
                    self.renderers.append( wrapVTKModule( 'vtkRenderer', renderer1 ) )
                    if inputModule.fieldData: self.fieldData.append( inputModule.fieldData )
        self.addTitle()

class PM_ChartCell( PM_DV3DCell ):

    def __init__( self, mid, **args ):
        PM_DV3DCell.__init__( self, mid, **args)
        self.primaryInputPorts = [ "chart" ]
        
class ChartCellConfigurationWidget(DV3DConfigurationWidget):
    """
    CDMSDatasetConfigurationWidget ...
    
    """

    def __init__(self, module, controller, parent=None):
        """ DV3DCellConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        
        """
        self.cellAddress = 'A1'
        self.title = ""
        DV3DConfigurationWidget.__init__(self, module, controller, 'Chart Cell Configuration', parent)
                
    def getParameters( self, module ):
        titleParms = getFunctionParmStrValues( module, "title" )
        if titleParms: self.title = str( titleParms[0] )
        if not self.title: self.title = self.pmod.getTitle()
        celllocParams = getFunctionParmStrValues( module, "cell_location" )
        if celllocParams:  self.cellAddress = str( celllocParams[0] )
        opacityParams = getFunctionParmStrValues( module, "opacity" )
        if opacityParams:  self.mapOpacity = float( opacityParams[0] )

    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """ 

        titleTab = QWidget()        
        self.tabbedWidget.addTab( titleTab, 'title' )                 
        self.tabbedWidget.setCurrentWidget(titleTab)
        layout = QVBoxLayout()
        titleTab.setLayout( layout ) 

        title_layout = QHBoxLayout()
        title_label = QLabel( "Title:" )
        title_layout.addWidget( title_label )
        self.titleEdit =  QLineEdit ( self.parent() )
        if self.title: self.titleEdit.setText( self.title )
        self.connect( self.titleEdit, SIGNAL("editingFinished()"), self.stateChanged ) 
        title_label.setBuddy( self.titleEdit )
#        self.titleEdit.setFrameStyle( QFrame.Panel|QFrame.Raised )
#        self.titleEdit.setLineWidth(2)
        title_layout.addWidget( self.titleEdit  )        
        layout.addLayout( title_layout )
        
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel( "Opacity:" )
        opacity_layout.addWidget( opacity_label )
        self.opacitySlider = QSlider( Qt.Horizontal )
        self.opacitySlider.setRange( 0, SLIDER_MAX_VALUE )
        self.opacitySlider.setSliderPosition( int( self.mapOpacity * SLIDER_MAX_VALUE ) )
        self.connect(self.opacitySlider, SIGNAL('sliderMoved()'), self.stateChanged )
        opacity_layout.addWidget( self.opacitySlider )
        layout.addLayout( opacity_layout )
        
        sheet_dims = HyperwallManager.getInstance().getDimensions()

        locationTab = QWidget()        
        self.tabbedWidget.addTab( locationTab, 'cell location' )                 
        self.tabbedWidget.setCurrentWidget(locationTab)
        location_layout = QVBoxLayout()
        locationTab.setLayout( location_layout ) 

        cell_coordinates = parse_cell_address( self.cellAddress )
        cell_selection_layout = QHBoxLayout()
        cell_selection_label = QLabel( "Cell Address:" )
        cell_selection_layout.addWidget( cell_selection_label ) 

        self.colCombo =  QComboBox ( self.parent() )
        self.colCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.colCombo  )        
        for iCol in range( 5 ):  self.colCombo.addItem( chr( ord('A') + iCol ) )
        self.colCombo.setCurrentIndex( cell_coordinates[0] )

        self.rowCombo =  QComboBox ( self.parent() )
        self.rowCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.rowCombo  )        
        for iRow in range( 5 ):  self.rowCombo.addItem( str(iRow+1) )
        self.rowCombo.setCurrentIndex( cell_coordinates[1] )
        location_layout.addLayout(cell_selection_layout)
        
    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'cell_location' , [ self.cellAddress ]  ), )  
        parmRecList.append( ( 'title' , [ self.title ]  ), )  
        parmRecList.append( ( 'opacity' , [ float( self.opacitySlider.value() ) / SLIDER_MAX_VALUE ]  ), )  
        self.persistParameterList( parmRecList )
        self.stateChanged(False)         

           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.cellAddress = "%s%s" % ( str( self.colCombo.currentText() ), str( self.rowCombo.currentText() ) )
        self.title = str( self.titleEdit.text() ) 
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()
 
class ChartCell( WorkflowModule ):
    
    PersistentModuleClass = PM_ChartCell
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
    def syncCamera( self, cpos, cfol, cup ):
        if self.pmod: self.pmod.syncCamera( cpos, cfol, cup )  

class PM_CloudCell3D( PM_DV3DCell ):

    def __init__( self, mid, **args ):
        PM_DV3DCell.__init__( self, mid, **args)
        self.primaryInputPorts = [ "pointcloud" ]

    def updateModule( self, **args ):
        PM_DV3DCell.updateModule( self, **args )
        if self.renWin: self.renWin.Render()
        
    def buildRendering(self):
        PM_DV3DCell.buildRendering( self )
        print " CloudCell3D.buildRendering  ****** "

class CloudCell3DConfigurationWidget(DV3DConfigurationWidget):
    """
    CDMSDatasetConfigurationWidget ...
    
    """

    def __init__(self, module, controller, parent=None):
        """ DV3DCellConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        
        """
        self.cellAddress = 'A1'
        self.title = ""
        DV3DConfigurationWidget.__init__(self, module, controller, 'DV3D Cloud Cell Configuration', parent)
                
    def getParameters( self, module ):
        titleParms = getFunctionParmStrValues( module, "title" )
        if titleParms: self.title = str( titleParms[0] )
        if not self.title: self.title = self.pmod.getTitle()
        celllocParams = getFunctionParmStrValues( module, "cell_location" )
        if celllocParams:  self.cellAddress = str( celllocParams[0] )

    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """   
             
        basemapTab = QWidget()        
        self.tabbedWidget.addTab( basemapTab, 'base map' )                 
        self.tabbedWidget.setCurrentWidget(basemapTab)
        layout = QVBoxLayout()
        basemapTab.setLayout( layout ) 
                
        title_layout = QHBoxLayout()
        title_label = QLabel( "Title:" )
        title_layout.addWidget( title_label )
        self.titleEdit =  QLineEdit ( self.parent() )
        if self.title: self.titleEdit.setText( self.title )
        self.connect( self.titleEdit, SIGNAL("editingFinished()"), self.stateChanged ) 
        title_label.setBuddy( self.titleEdit )
#        self.titleEdit.setFrameStyle( QFrame.Panel|QFrame.Raised )
#        self.titleEdit.setLineWidth(2)
        title_layout.addWidget( self.titleEdit  )        
        layout.addLayout( title_layout )
                
        sheet_dims = HyperwallManager.getInstance().getDimensions()
        locationTab = QWidget()        
        self.tabbedWidget.addTab( locationTab, 'cell location' )                 
        self.tabbedWidget.setCurrentWidget(locationTab)
        location_layout = QVBoxLayout()
        locationTab.setLayout( location_layout ) 

        cell_coordinates = parse_cell_address( self.cellAddress )
        cell_selection_layout = QHBoxLayout()
        cell_selection_label = QLabel( "Cell Address:" )
        cell_selection_layout.addWidget( cell_selection_label ) 

        self.colCombo =  QComboBox ( self.parent() )
        self.colCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.colCombo  )        
        for iCol in range( 5 ):  self.colCombo.addItem( chr( ord('A') + iCol ) )
        self.colCombo.setCurrentIndex( cell_coordinates[0] )

        self.rowCombo =  QComboBox ( self.parent() )
        self.rowCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.rowCombo  )        
        for iRow in range( 5 ):  self.rowCombo.addItem( str(iRow+1) )
        self.rowCombo.setCurrentIndex( cell_coordinates[1] )
        location_layout.addLayout(cell_selection_layout)
        
    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'cell_location' , [ self.cellAddress ]  ), )  
        parmRecList.append( ( 'title' , [ self.title ]  ), )  
        self.persistParameterList( parmRecList )
        self.stateChanged(False)         
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget       
        """
        self.cellAddress = "%s%s" % ( str( self.colCombo.currentText() ), str( self.rowCombo.currentText() ) )
        self.title = str( self.titleEdit.text() ) 
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()

class PM_MapCell3D( PM_DV3DCell ):

    baseMapDirty = True

    def __init__( self, mid, **args ):
        PM_DV3DCell.__init__( self, mid, **args)
        self.baseMapActor = None
        self.enableBasemap = True

    def updateModule( self, **args ):
        PM_DV3DCell.updateModule( self, **args )
        if self.baseMapActor: self.baseMapActor.SetVisibility( int( self.enableBasemap ) )
        if self.renWin: self.renWin.Render()

    def activateWidgets( self, iren ):
        if self.baseMapActor:
            bounds = [ 0.0 for i in range(6) ]
            self.baseMapActor.GetBounds( bounds )

    def decimateImage( self, image, decx, decy ):
        image.Update()
        dims = image.GetDimensions()
        image_size = dims[0] * dims[1]
        result = image
        if image_size > MAX_IMAGE_SIZE:
            resample = vtk.vtkImageShrink3D()
            resample.SetInput( image )
            resample.SetShrinkFactors( decx, decy, 1 )
            result = resample.GetOutput() 
            result.Update()
        return result
        
    def buildRendering(self):
        PM_DV3DCell.buildRendering( self )
        self.enableBasemap = self.getInputValue( "enable_basemap", True )
        if self.enableBasemap and self.renderers and ( self.newDataset or not self.baseMapActor or PM_MapCell3D.baseMapDirty):
            if self.baseMapActor <> None: self.renderer.RemoveActor( self.baseMapActor )               
            world_map =  None # wmod.forceGetInputFromPort( "world_map", None ) if wmod else None
            opacity =  self.getInputValue( "opacity",   0.4  ) #  wmod.forceGetInputFromPort( "opacity",   0.4  )  if wmod else 0.4  
            map_border_size = self.getInputValue( "map_border_size", 20  ) # wmod.forceGetInputFromPort( "map_border_size", 20  )  if wmod else 20  
            cell_location = self.getInputValue( "cell_location", "00"  )
                
            self.y0 = -90.0  
            dataPosition = None
            if world_map == None:
                self.map_file = defaultMapFile
                self.map_cut = defaultMapCut
            else:
                self.map_file = world_map[0].name
                self.map_cut = world_map[1]
            
            self.world_cut = self.getInputValue( "world_cut", -1 ) # wmod.forceGetInputFromPort( "world_cut", -1 )  if wmod else getFunctionParmStrValues( module, "world_cut", -1 )
            roi_size = [ self.roi[1] - self.roi[0], self.roi[3] - self.roi[2] ] 
            map_cut_size = [ roi_size[0] + 2*map_border_size, roi_size[1] + 2*map_border_size ]
            if map_cut_size[0] > 360.0: map_cut_size[0] = 360.0
            if map_cut_size[1] > 180.0: map_cut_size[1] = 180.0
            data_origin = self.input().GetOrigin() if self.input() else [ 0, 0, 0 ]
                      
            if self.world_cut == -1: 
                if  (self.roi <> None): 
                    if roi_size[0] > 180:             
                        self.ComputeCornerPosition()
                        self.world_cut = self.NormalizeMapLon( self.x0 )
                    else:
                        dataPosition = [ ( self.roi[1] + self.roi[0] ) / 2.0, ( self.roi[3] + self.roi[2] ) / 2.0 ]
                else:
                    self.world_cut = self.map_cut
            
            self.imageInfo = vtk.vtkImageChangeInformation()        
            image_reader = vtk.vtkJPEGReader()      
            image_reader.SetFileName(  self.map_file )
            baseImage = image_reader.GetOutput() 
            new_dims, scale = None, None
            if dataPosition == None:    
                baseImage = self.RollMap( baseImage ) 
                new_dims = baseImage.GetDimensions()
                scale = [ 360.0/new_dims[0], 180.0/new_dims[1], 1 ]
            else:                       
                baseImage, new_dims = self.getBoundedMap( baseImage, dataPosition, map_cut_size, map_border_size )             
                scale = [ map_cut_size[0]/new_dims[0], map_cut_size[1]/new_dims[1], 1 ]
    #        printArgs( " baseMap: ", extent=baseImage.GetExtent(), spacing=baseImage.GetSpacing(), origin=baseImage.GetOrigin() )        
                              
            self.baseMapActor = vtk.vtkImageActor()
            self.baseMapActor.SetOrigin( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetScale( scale )
            self.baseMapActor.SetOrientation( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetOpacity( opacity )
    #        self.baseMapActor.SetDisplayExtent( -1,  0,  0,  0,  0,  0 )
#            print "Positioning map at location %s, size = %s, roi = %s" % ( str( ( self.x0, self.y0) ), str( map_cut_size ), str( ( NormalizeLon( self.roi[0] ), NormalizeLon( self.roi[1] ), self.roi[2], self.roi[3] ) ) )
            mapCorner = [ self.x0, self.y0 ]
#            if ( ( self.roi[0]-map_border_size ) < 0.0 ): mapCorner[0] = mapCorner[0] - 360.0
#            print " DV3DCell, mapCorner = %s, dataPosition = %s, cell_location = %s " % ( str(mapCorner), str(dataPosition), cell_location )
                    
            self.baseMapActor.SetPosition( mapCorner[0], mapCorner[1], 0.1 )
            self.baseMapActor.SetInput( baseImage )
            self.mapCenter = [ self.x0 + map_cut_size[0]/2.0, self.y0 + map_cut_size[1]/2.0 ]        
            self.renderer.AddActor( self.baseMapActor )


    def ComputeCornerPosition( self ):
        if (self.roi[0] >= -180) and (self.roi[1] <= 180) and (self.roi[1] > self.roi[0]):
            self.x0 = -180
            return 180
        if (self.roi[0] >= 0) and (self.roi[1] <= 360) and (self.roi[1] > self.roi[0]):
            self.x0 = 0
            return 0
        self.x0 = int( round( self.roi[0] / 10.0 ) ) * 10
#        print "Set Corner pos: %s, roi: %s " % ( str(self.x0), str(self.roi) )
        
    def GetScaling( self, image_dims ):
        return 360.0/image_dims[0], 180.0/image_dims[1],  1

    def GetFilePath( self, cut ):
        filename = "%s_%d.jpg" % ( self.world_image, cut )
        return os.path.join( self.data_dir, filename ) 
        
    def RollMap( self, baseImage ):
        baseImage.Update()
        if self.world_cut  == self.map_cut: return baseImage
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        newCut = self.NormalizeMapLon( self.world_cut )
        delCut = newCut - self.map_cut
#        print "  %%%%%% Roll Map %%%%%%: world_cut=%.1f, map_cut=%.1f, newCut=%.1f " % ( float(self.world_cut), float(self.map_cut), float(newCut) )
        imageLen = x1 - x0 + 1
        sliceSize =  imageLen * ( delCut / 360.0 )
        sliceCoord = int( round( x0 + sliceSize) )        
        extent = list( baseExtent ) 
        
        extent[0:2] = [ x0, x0 + sliceCoord - 1 ]
        clip0 = vtk.vtkImageClip()
        clip0.SetInput( baseImage )
        clip0.SetOutputWholeExtent( extent[0], extent[1], extent[2], extent[3], extent[4], extent[5] )
        
        extent[0:2] = [ x0 + sliceCoord, x1 ]
        clip1 = vtk.vtkImageClip()
        clip1.SetInput( baseImage )
        clip1.SetOutputWholeExtent( extent[0], extent[1], extent[2], extent[3], extent[4], extent[5] )
        
        append = vtk.vtkImageAppend()
        append.SetAppendAxis( 0 )
        append.AddInput( clip1.GetOutput() )          
        append.AddInput( clip0.GetOutput() )
        
        imageInfo = vtk.vtkImageChangeInformation()
        imageInfo.SetInputConnection( append.GetOutputPort() ) 
        imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
        imageInfo.SetOutputExtentStart( 0, 0, 0 )
        imageInfo.SetOutputSpacing( baseSpacing[0], baseSpacing[1], baseSpacing[2] )
        
        result = imageInfo.GetOutput() 
        result.Update()
        return result

    def NormalizeMapLon( self, lon ): 
        while ( lon < ( self.map_cut - 0.01 ) ): lon = lon + 360
        return ( ( lon - self.map_cut ) % 360 ) + self.map_cut

    def getBoundedMap( self, baseImage, dataLocation, map_cut_size, map_border_size ):
        baseImage.Update()
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        y0 = baseExtent[2]
        y1 = baseExtent[3]
        imageLen = [ x1 - x0 + 1, y1 - y0 + 1 ]
        selectionDim = [ map_cut_size[0]/2, map_cut_size[1]/2 ]
        dataXLoc = dataLocation[0]
        imageInfo = vtk.vtkImageChangeInformation()
        dataYbounds = [ dataLocation[1]-selectionDim[1], dataLocation[1]+selectionDim[1] ]
        vertExtent = [ y0, y1 ]
        bounded_dims = None
        if dataYbounds[0] > -90.0:
            yOffset = dataYbounds[0] + 90.0
            extOffset = int( round( ( yOffset / 180.0 ) * imageLen[1] ) )
            vertExtent[0] = y0 + extOffset
            self.y0 = dataYbounds[0]
        if dataYbounds[1] < 90.0:
            yOffset = 90.0 - dataYbounds[1]
            extOffset = int( round( ( yOffset / 180.0 ) * imageLen[1] ) )
            vertExtent[1] = y1 - extOffset
            
        overlapsBorder = ( self.NormalizeMapLon(dataLocation[0]-selectionDim[0]) > self.NormalizeMapLon(dataLocation[0]+selectionDim[0]) )
        if overlapsBorder:
            cut0 = self.NormalizeMapLon( dataXLoc + selectionDim[0] )
            sliceSize =  imageLen[0] * ( ( cut0 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0:2] = [ x0, x0 + sliceCoord - 1 ]
            clip0 = vtk.vtkImageClip()
            clip0.SetInput( baseImage )
            clip0.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size0 = extent[1] - extent[0] + 1
        
            self.x0 = dataLocation[0] - selectionDim[0]
            cut1 = self.NormalizeMapLon( self.x0 ) 
            sliceSize =  imageLen[0] * ( ( cut1 - self.map_cut )/ 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[0:2] = [ x0 + sliceCoord, x1 ]
            clip1 = vtk.vtkImageClip()
            clip1.SetInput( baseImage )
            clip1.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size1 = extent[1] - extent[0] + 1
#            print "Set Corner pos: %s, cuts: %s " % ( str(self.x0), str( (cut0, cut1) ) )
        
            append = vtk.vtkImageAppend()
            append.SetAppendAxis( 0 )
            append.AddInput( clip1.GetOutput() )          
            append.AddInput( clip0.GetOutput() )
            bounded_dims = ( size0 + size1, vertExtent[1] - vertExtent[0] + 1 )
            
            imageInfo.SetInputConnection( append.GetOutputPort() ) 

        else:
                        
            self.x0 = dataXLoc - selectionDim[0]
            cut0 = self.NormalizeMapLon( self.x0 )
            sliceSize =  imageLen[0] * ( ( cut0 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0] = x0 + sliceCoord - 1
        
            cut1 = self.NormalizeMapLon( dataXLoc + selectionDim[0] )
            sliceSize =  imageLen[0] * ( ( cut1 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[1] = x0 + sliceCoord
            clip = vtk.vtkImageClip()
            clip.SetInput( baseImage )
            clip.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            bounded_dims = ( extent[1] - extent[0] + 1, vertExtent[1] - vertExtent[0] + 1 )
#            print "Set Corner pos: %s, dataXLoc: %s " % ( str(self.x0), str( (dataXLoc, selectionDim[0]) ) )

            imageInfo.SetInputConnection( clip.GetOutputPort() ) 
                       
        imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
        imageInfo.SetOutputExtentStart( 0, 0, 0 )
        imageInfo.SetOutputSpacing( baseSpacing[0], baseSpacing[1], baseSpacing[2] )
        
        result = imageInfo.GetOutput() 
        result.Update()
        return result, bounded_dims
        

class MapCell3DConfigurationWidget(DV3DConfigurationWidget):
    """
    CDMSDatasetConfigurationWidget ...
    
    """

    def __init__(self, module, controller, parent=None):
        """ DV3DCellConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        
        """
        self.enableBasemap = True
        self.mapBorderSize = 20.0
        self.cellAddress = 'A1'
        self.title = ""
        self.mapOpacity = 0.5
        DV3DConfigurationWidget.__init__(self, module, controller, 'DV3D Cell Configuration', parent)
                
    def getParameters( self, module ):
        titleParms = getFunctionParmStrValues( module, "title" )
        if titleParms: self.title = str( titleParms[0] )
        if not self.title: self.title = self.pmod.getTitle()
        basemapParams = getFunctionParmStrValues( module, "enable_basemap" )
        if basemapParams: self.enableBasemap = bool( basemapParams[0] )
        basemapParams = getFunctionParmStrValues( module, "map_border_size" )
        if basemapParams:  self.mapBorderSize = float( basemapParams[0] )
        celllocParams = getFunctionParmStrValues( module, "cell_location" )
        if celllocParams:  self.cellAddress = str( celllocParams[0] )
        opacityParams = getFunctionParmStrValues( module, "opacity" )
        if opacityParams:  self.mapOpacity = float( opacityParams[0] )

    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """   
             
        basemapTab = QWidget()        
        self.tabbedWidget.addTab( basemapTab, 'base map' )                 
        self.tabbedWidget.setCurrentWidget(basemapTab)
        layout = QVBoxLayout()
        basemapTab.setLayout( layout ) 
                
        self.enableCheckBox = QCheckBox( "Enable Basemap:"  )
        self.enableCheckBox.setChecked( self.enableBasemap )
        self.connect( self.enableCheckBox, SIGNAL("stateChanged(int)"), self.basemapStateChanged ) 
        layout.addWidget( self.enableCheckBox )

        border_layout = QHBoxLayout()
        enable_label = QLabel( "Border size:" )
        border_layout.addWidget( enable_label )
        self.borderSizeEdit =  QLineEdit ( self.parent() )
        self.borderSizeEdit.setValidator( QDoubleValidator(self) )
        self.borderSizeEdit.setText( "%.2f" % self.mapBorderSize )
        self.connect( self.borderSizeEdit, SIGNAL("editingFinished()"), self.stateChanged ) 
        enable_label.setBuddy( self.borderSizeEdit )
#        self.borderSizeEdit.setFrameStyle( QFrame.Panel|QFrame.Raised )
#        self.borderSizeEdit.setLineWidth(2)
        border_layout.addWidget( self.borderSizeEdit  )        
        layout.addLayout( border_layout )

        title_layout = QHBoxLayout()
        title_label = QLabel( "Title:" )
        title_layout.addWidget( title_label )
        self.titleEdit =  QLineEdit ( self.parent() )
        if self.title: self.titleEdit.setText( self.title )
        self.connect( self.titleEdit, SIGNAL("editingFinished()"), self.stateChanged ) 
        title_label.setBuddy( self.titleEdit )
#        self.titleEdit.setFrameStyle( QFrame.Panel|QFrame.Raised )
#        self.titleEdit.setLineWidth(2)
        title_layout.addWidget( self.titleEdit  )        
        layout.addLayout( title_layout )
        
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel( "Map Opacity:" )
        opacity_layout.addWidget( opacity_label )
        self.opacitySlider = QSlider( Qt.Horizontal )
        self.opacitySlider.setRange( 0, SLIDER_MAX_VALUE )
        self.opacitySlider.setSliderPosition( int( self.mapOpacity * SLIDER_MAX_VALUE ) )
        self.connect(self.opacitySlider, SIGNAL('sliderMoved()'), self.stateChanged )
        opacity_layout.addWidget( self.opacitySlider )
        layout.addLayout( opacity_layout )
        
        sheet_dims = HyperwallManager.getInstance().getDimensions()

        locationTab = QWidget()        
        self.tabbedWidget.addTab( locationTab, 'cell location' )                 
        self.tabbedWidget.setCurrentWidget(locationTab)
        location_layout = QVBoxLayout()
        locationTab.setLayout( location_layout ) 

        cell_coordinates = parse_cell_address( self.cellAddress )
        cell_selection_layout = QHBoxLayout()
        cell_selection_label = QLabel( "Cell Address:" )
        cell_selection_layout.addWidget( cell_selection_label ) 

        self.colCombo =  QComboBox ( self.parent() )
        self.colCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.colCombo  )        
        for iCol in range( 5 ):  self.colCombo.addItem( chr( ord('A') + iCol ) )
        if cell_coordinates: 
            self.colCombo.setCurrentIndex( cell_coordinates[0] )

        self.rowCombo =  QComboBox ( self.parent() )
        self.rowCombo.setMaximumHeight( 30 )
        cell_selection_layout.addWidget( self.rowCombo  )        
        for iRow in range( 5 ):  self.rowCombo.addItem( str(iRow+1) )
        self.rowCombo.setCurrentIndex( cell_coordinates[1] )
        location_layout.addLayout(cell_selection_layout)
        
    def basemapStateChanged( self, enabled ):
        self.stateChanged()

    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'enable_basemap' , [ self.enableBasemap ]  ), )      
        parmRecList.append( ( 'map_border_size' , [ self.mapBorderSize ]  ), )  
        parmRecList.append( ( 'cell_location' , [ self.cellAddress ]  ), )  
        parmRecList.append( ( 'title' , [ self.title ]  ), )  
        parmRecList.append( ( 'opacity' , [ float( self.opacitySlider.value() ) / SLIDER_MAX_VALUE ]  ), )  
        self.persistParameterList( parmRecList )
        self.stateChanged(False)         

           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.enableBasemap = self.enableCheckBox.isChecked() 
        self.mapBorderSize = float( self.borderSizeEdit.text() )
        self.cellAddress = "%s%s" % ( str( self.colCombo.currentText() ), str( self.rowCombo.currentText() ) )
        self.title = str( self.titleEdit.text() ) 
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()
 
class MapCell3D( WorkflowModule ):
    
    PersistentModuleClass = PM_MapCell3D
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
    def syncCamera( self, cpos, cfol, cup ):
        if self.pmod: self.pmod.syncCamera( cpos, cfol, cup )  
              
class CloudCell3D( WorkflowModule ):
    
    PersistentModuleClass = PM_CloudCell3D
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
    def syncCamera( self, cpos, cfol, cup ):
        if self.pmod: self.pmod.syncCamera( cpos, cfol, cup )  
              


