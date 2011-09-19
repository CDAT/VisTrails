'''
Created on Feb 14, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
from gui.qt import qt_super
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_base import StandardSheetReference, StandardSingleCellSheetReference
from packages.vtk.vtkcell import QVTKWidget
from PersistentModule import AlgorithmOutputModule3D, PersistentVisualizationModule
from InteractiveConfiguration import *
from WorkflowModule import WorkflowModule
from HyperwallManager import HyperwallManager
from vtUtilities import *
import os

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultMapFile = os.path.join( defaultMapDir,  'world_huge.jpg' )
defaultMapCut = 0

def get_coords_from_cell_address( row, col):
    try:
        col = ord(col)-ord('A')
        row = int(row)-1
        return ( col, row )
    except:
        raise Exception('ColumnRowAddress format error: %s ' % str( [ row, col ] ) )

def parse_cell_address( address ):
    if len(address)>1:
        if address[0] >= 'A' and address[0] <= 'Z':
            return get_coords_from_cell_address( address[1:], address[0] )
        else:
            return get_coords_from_cell_address( address[:-1], address[-1] )

class QVTKServerWidget(QVTKWidget):
    """
    QVTKWidget with interaction observers
    
    """
    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QVTKWidget.__init__(self, parent, f )
        self.location = None
        
    def setLocation( self, location ):
        self.location = location

    def event(self, e): 
        dims = [ self.width(), self.height() ]   
        if   e.type() == QtCore.QEvent.KeyPress:           self.processInteractionEvent('keyPress',e,dims)  
        elif e.type() == QtCore.QEvent.MouseButtonPress:   self.processInteractionEvent('buttonPress',e,dims) 
        elif e.type() == QtCore.QEvent.MouseMove:          self.processInteractionEvent('mouseMove',e,dims) 
        elif e.type() == QtCore.QEvent.MouseButtonRelease: self.processInteractionEvent('buttonRelease',e,dims) 
        elif e.type() == QtCore.QEvent.KeyRelease:         self.processInteractionEvent('keyRelease',e,dims)         
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
        screen_pos = ( self.location.row, self.location.col )
        HyperwallManager.processInteractionEvent( name, event, screen_pos, dims, camera_pos ) 
        
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
    """
    VTKCell is a VisTrails Module that can display vtkRenderWindow inside a cell
    
    """
    baseMapDirty = True

    def __init__( self, mid, **args ):
        SpreadsheetCell.__init__(self)
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, **args )
        self.addConfigurableFunction( 'resetCamera', None, 'A', open=self.resetCamera )
        if self.isClient:  self.location = ( 0, 0 )
        self.allowMultipleInputs = True
        self.renderers = []
        self.fieldData = []
        self.cellWidget = None
        self.imageInfo = None
        self.baseMapActor = None
        self.enableBasemap = True
        self.renWin = None
        self.builtCellWidget = False
        
    @classmethod
    def clearCache(cls):
        cls.baseMapDirty = True
        
#    def get_output(self, port):
#        module = Module.get_output(self, port)
#        output_id = id( module )    
#        print " WorldFrame.get_output: output Module= %s " % str(output_id)
#        return module

#        # if self.outputPorts.has_key(port) or not self.outputPorts[port]: 
#        if port not in self.outputPorts:
#            raise ModuleError(self, "output port '%s' not found" % port)
#        return self.outputPorts[port]

    def getSheetTabWidget( self ):   
        return self.cellWidget.findSheetTabWidget() if self.cellWidget else None
    
#    def setSelectionStatus( self, selected ):
#        for fd in self.fieldData:
#            fd.AddArray( getIntDataArray(  'selected', [ selected, ] ) )      
    
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
        cells = self.getSelectedCells()
        cell_coords = ( self.location.row, self.location.col )
        for cell in cells:
            if cell == cell_coords: return True
        return False
    
    def syncCamera( self, cpos, cfol, cup ):
#        print " @@@ syncCamera, module: %s  @@@" % str( self.moduleID )
        rens = self.renWin.GetRenderers()
        rens.InitTraversal()
        for i in xrange(rens.GetNumberOfItems()):
            ren = rens.GetNextItem()
            dcam = ren.GetActiveCamera()
            if dcam:
                dcam.SetPosition(cpos)
                dcam.SetFocalPoint(cfol)
                dcam.SetViewUp(cup)
        
#    def processInteractionEvent(self, istyle, name):
#        iren = self.renWin.GetInteractor()
#        pos = iren.GetLastEventPosition ()
#        key = iren.GetKeyCode ()
#        rp = iren.GetRepeatCount()
#        keysym = iren.GetKeySym()
#        ctrl = iren.GetControlKey ()
#        shift = iren.GetShiftKey ()
##        iren.SetEventInformation( pos[0], pos[1], ctrl, shift, key, rp, keysym )
#        if name == 'MouseMoveEvent':
#            iren.MouseMoveEvent()
#        if name ==  'LeftButtonReleaseEvent': 
#            iren.LeftButtonReleaseEvent()      
#        if name ==  'CharEvent':
#            iren.CharEvent()
#        if name ==  'KeyReleaseEvent':
#            iren.KeyReleaseEvent()
#        if name ==  'LeftButtonPressEvent':
#            iren.LeftButtonPressEvent()
#        if name ==  'RightButtonReleaseEvent':
#            iren.RightButtonReleaseEvent()
#        if name ==  'RightButtonPressEvent':
#            iren.RightButtonPressEvent()           
#
#        print " processInteractionEvent: %s, pos = %s, key = %s " % ( name, str(pos), str(key) )

    def setCellLocation( self, moduleId ):
        cellLocation = CellLocation()
        cellLocation.rowSpan = 1
        cellLocation.colSpan = 1
        if self.isClient:            
            cellLocation.sheetReference = StandardSheetReference()
            cellLocation.sheetReference.sheetName = HyperwallManager.deviceName

        cell_coordinates = None
            
        address = getItem( self.getInputValue( "cell_location", None ) )
        if address:
            address = address.replace(' ', '').upper()
            cell_coordinates = parse_cell_address( address )
        else:
            cell_coordinates = HyperwallManager.getCellCoordinatesForModule( moduleId )
            if cell_coordinates == None: return None
        cellLocation.col = cell_coordinates[0]
        cellLocation.row = cell_coordinates[1]
         
#        print " --- Set cell location[%s]: %s, address: %s "  % ( str(moduleId), str( [ cellLocation.col, cellLocation.row ] ), str(address) )
        self.overrideLocation( cellLocation )
        self.adjustSheetDimensions( cellLocation.row, cellLocation.col )
        return [ cellLocation.col, cellLocation.row, 1, 1 ]

    def updateHyperwall(self):
        dimensions = self.setCellLocation( self.moduleID )  
        if dimensions:      
            HyperwallManager.addCell( self.moduleID, self.datasetId, str(0), dimensions )
            HyperwallManager.executeCurrentWorkflow( self.moduleID )

    def updateModule(self):
        self.buildPipeline()
        if self.baseMapActor: self.baseMapActor.SetVisibility( self.enableBasemap )
        if self.renWin: self.renWin.Render()
        
    def activateWidgets( self, iren ):
        widget = self.baseMapActor
        bounds = [ 0.0 for i in range(6) ]
        widget.GetBounds(bounds)
#        printArgs( " MAP: ", pos=widget.GetPosition(), bounds=bounds, origin=widget.GetOrigin() )
    
    def ComputeCornerPosition( self ):
        if (self.roi[0] >= -180) and (self.roi[1] <= 180) and (self.roi[1] > self.roi[0]):
            self.x0 = -180
            return 180
        if (self.roi[0] >= 0) and (self.roi[1] <= 360) and (self.roi[1] > self.roi[0]):
            self.x0 = 0
            return 0
        self.x0 = int( round( self.roi[0] / 10.0 ) ) * 10
#        print "Set Corner pos: %s, extent: %s " % ( str(self.x0), str(self.roi) )
        
    def GetScaling( self, image_dims ):
        return 360.0/image_dims[0], 180.0/image_dims[1],  1

    def GetFilePath( self, cut ):
        filename = "%s_%d.jpg" % ( self.world_image, cut )
        return os.path.join( self.data_dir, filename ) 
    
    def NormalizeCut( self, cut ): 
        while cut < 0: cut = cut + 360
        return cut % 360  
    
    def RollMap( self, baseImage ):
        baseImage.Update()
        if self.world_cut  == self.map_cut: return baseImage
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        newCut = NormalizeLon( self.world_cut )
        delCut = NormalizeLon( self.map_cut - newCut )
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

    def getBoundedMap( self, baseImage, dataLocation, map_cut_size ):
        baseImage.Update()
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        y0 = baseExtent[2]
        y1 = baseExtent[3]
        imageLen = [ x1 - x0 + 1, y1 - y0 + 1 ]
        selectionDim = [ map_cut_size[0]/2, map_cut_size[1]/2 ]
        dataXLoc = NormalizeLon( dataLocation[0] ) 
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
                   
        if (( dataXLoc > selectionDim[0] ) and ( dataXLoc < ( 360 - selectionDim[0]) )):

            cut0 = dataXLoc - selectionDim[0] 
            sliceSize =  imageLen[0] * ( cut0 / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0] = x0 + sliceCoord - 1
        
            cut1 = dataXLoc + selectionDim[0] 
            sliceSize =  imageLen[0] * ( cut1 / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[1] = x0 + sliceCoord
            clip = vtk.vtkImageClip()
            clip.SetInput( baseImage )
            clip.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            self.x0 = cut0
            bounded_dims = ( extent[1] - extent[0] + 1, vertExtent[1] - vertExtent[0] + 1 )

            imageInfo.SetInputConnection( clip.GetOutputPort() ) 
            
        else:
            cut0 = NormalizeLon( dataXLoc + selectionDim[0] )
            sliceSize =  imageLen[0] * ( cut0 / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0:2] = [ x0, x0 + sliceCoord - 1 ]
            clip0 = vtk.vtkImageClip()
            clip0.SetInput( baseImage )
            clip0.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size0 = extent[1] - extent[0] + 1
        
            cut1 = NormalizeLon( dataLocation[0] - selectionDim[0] )
            sliceSize =  imageLen[0] * ( cut1 / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[0:2] = [ x0 + sliceCoord, x1 ]
            clip1 = vtk.vtkImageClip()
            clip1.SetInput( baseImage )
            clip1.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size1 = extent[1] - extent[0] + 1
            self.x0 = cut1
        
            append = vtk.vtkImageAppend()
            append.SetAppendAxis( 0 )
            append.AddInput( clip1.GetOutput() )          
            append.AddInput( clip0.GetOutput() )
            bounded_dims = ( size0 + size1, vertExtent[1] - vertExtent[0] + 1 )
            
            imageInfo.SetInputConnection( append.GetOutputPort() ) 
            
        imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
        imageInfo.SetOutputExtentStart( 0, 0, 0 )
        imageInfo.SetOutputSpacing( baseSpacing[0], baseSpacing[1], baseSpacing[2] )
        
        result = imageInfo.GetOutput() 
        result.Update()
        return result, bounded_dims
        
    def isBuilt(self):
        return ( self.cellWidget <> None )
   
    def buildPipeline(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        self.buildRendering()
        if not self.builtCellWidget:
            self.buildWidget()
   
    def execute(self, **args ):
        self.builtCellWidget = False
        PersistentVisualizationModule.execute(self, **args)
        
    def buildRendering(self):
        module = self.getRegisteredModule()
        self.enableBasemap = self.getInputValue( "enable_basemap", True )

#        print " DV3DCell compute, id = %s, cachable: %s " % ( str( id(self) ), str( self.is_cacheable() ) )
        self.renderers = []
        self.fieldData = []
        self.renderer = None
        for inputModule in self.inputModuleList:
            if inputModule <> None:
                renderer1 = inputModule.getRenderer() 
                if  renderer1 <> None: 
                    if not self.renderer: self.renderer = renderer1
                    self.renderers.append( wrapVTKModule( 'vtkRenderer', renderer1 ) )
                    self.fieldData.append( inputModule.fieldData )
#                        renderer.SetNearClippingPlaneTolerance(0.0001)
#                        print "NearClippingPlaneTolerance: %f" % renderer.GetNearClippingPlaneTolerance()
#        self.setSelectionStatus( self.isSelected() )
        if self.enableBasemap and self.renderers and ( self.newDataset or not self.baseMapActor or PM_DV3DCell.baseMapDirty):
            if self.baseMapActor <> None: self.renderer.RemoveActor( self.baseMapActor )               
            world_map =  None # wmod.forceGetInputFromPort( "world_map", None ) if wmod else None
            opacity =  self.getInputValue( "opacity",   0.4  ) #  wmod.forceGetInputFromPort( "opacity",   0.4  )  if wmod else 0.4  
            map_border_size = self.getInputValue( "map_border_size", 20  ) # wmod.forceGetInputFromPort( "map_border_size", 20  )  if wmod else 20  
                
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
            data_origin = self.input.GetOrigin() if self.input else [ 0, 0, 0 ]
          
            if self.world_cut == -1: 
                if  (self.roi <> None): 
                    if roi_size[0] > 180:             
                        self.ComputeCornerPosition()
                        self.world_cut = NormalizeLon( self.x0 )
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
                baseImage, new_dims = self.getBoundedMap( baseImage, dataPosition, map_cut_size )             
                scale = [ map_cut_size[0]/new_dims[0], map_cut_size[1]/new_dims[1], 1 ]
    #        printArgs( " baseMap: ", extent=baseImage.GetExtent(), spacing=baseImage.GetSpacing(), origin=baseImage.GetOrigin() )        
                      
            self.baseMapActor = vtk.vtkImageActor()
            self.baseMapActor.SetOrigin( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetScale( scale )
            self.baseMapActor.SetOrientation( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetOpacity( opacity )
    #        self.baseMapActor.SetDisplayExtent( -1,  0,  0,  0,  0,  0 )
#            print "Positioning map at location %s, size = %s, roi = %s" % ( str( ( self.x0, self.y0) ), str( map_cut_size ), str( ( NormalizeLon( self.roi[0] ), NormalizeLon( self.roi[1] ), self.roi[2], self.roi[3] ) ) )
            self.baseMapActor.SetPosition( self.x0, self.y0, 0.1 )
            self.baseMapActor.SetInput( baseImage )
            self.mapCenter = [ self.x0 + map_cut_size[0]/2.0, self.y0 + map_cut_size[1]/2.0 ]            
            self.resetCamera()
#            PM_DV3DCell.baseMapDirty = False           
            self.renderer.AddActor( self.baseMapActor )
        pass


    def resetCamera(self):
            aCamera = self.renderer.GetActiveCamera()
            aCamera.SetViewUp( 0, 0, 1 )
            aCamera.SetPosition( 0.0, 0.0, ( self.mapCenter[0] + self.mapCenter[1] ) / 4.0 )
            aCamera.SetFocalPoint( self.mapCenter[0], self.mapCenter[1], 0.0 )
            aCamera.ComputeViewPlaneNormal()
            self.renderer.ResetCamera()                
        
    def buildWidget(self):                        
        if self.renderers:
            renderViews = []
            renderView = None
            iHandlers = []
            iStyle = None
            picker = None
            
            if self.isServer:
                self.cellWidget = self.displayAndWait( QVTKServerWidget, (self.renderers, renderView, iHandlers, iStyle, picker ) )
                self.cellWidget.setLocation( self.location )
            elif self.isClient:
                self.cellWidget = self.displayAndWait( QVTKWidget, (self.renderers, renderView, iHandlers, iStyle, picker) )
            else:
                self.cellWidget = self.displayAndWait( QVTKWidget, (self.renderers, renderView, iHandlers, iStyle, picker) )
            #in mashup mode, self.displayAndWait will return None
            if self.cellWidget:
                self.renWin = self.cellWidget.GetRenderWindow()
            self.builtCellWidget = True
        else:               
            print>>sys.stderr, "Error, no renderers supplied to DV3DCell"  

class DV3DCellConfigurationWidget(DV3DConfigurationWidget):
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
        DV3DConfigurationWidget.__init__(self, module, controller, 'DV3D Cell Configuration', parent)
                
    def getParameters( self, module ):
        basemapParams = getFunctionParmStrValues( module, "enable_basemap" )
        if basemapParams: self.enableBasemap = bool( basemapParams[0] )
        basemapParams = getFunctionParmStrValues( module, "map_border_size" )
        if basemapParams:  self.mapBorderSize = float( basemapParams[0] )
        celllocParams = getFunctionParmStrValues( module, "cell_location" )
        if celllocParams:  self.cellAddress = str( celllocParams[0] )

    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """        
        basemapTab = QWidget()        
        self.tabbedWidget.addTab( basemapTab, 'base map' )                 
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
        
        sheet_dims = HyperwallManager.getDimensions()

        locationTab = QWidget()        
        self.tabbedWidget.addTab( locationTab, 'cell location' )                 
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
        
    def basemapStateChanged( self, enabled ):
        self.stateChanged()

    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'enable_basemap' , [ self.enableBasemap ]  ), )      
        parmRecList.append( ( 'map_border_size' , [ self.mapBorderSize ]  ), )  
        parmRecList.append( ( 'cell_location' , [ self.cellAddress ]  ), )  
        self.persistParameterList( parmRecList )
        self.stateChanged(False)         
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.enableBasemap = self.enableCheckBox.isChecked() 
        self.mapBorderSize = float( self.borderSizeEdit.text() )
        self.cellAddress = "%s%s" % ( str( self.colCombo.currentText() ), str( self.rowCombo.currentText() ) )
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()
 
class DV3DCell(WorkflowModule):
    
    PersistentModuleClass = PM_DV3DCell
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
    def syncCamera( self, cpos, cfol, cup ):
        if self.pmod: self.pmod.syncCamera( cpos, cfol, cup )  
