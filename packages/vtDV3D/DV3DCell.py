'''
Created on Feb 14, 2011

@author: tpmaxwel
'''

from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.vtk.vtkcell import QVTKWidget
from PersistentModule import AlgorithmOutputModule3D, PersistentVisualizationModule
from InteractiveConfiguration import *
from WorkflowModule import WorkflowModule
from vtUtilities import *
import os

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultMapFile = os.path.join( defaultMapDir,  'world_huge.jpg' )
defaultMapCut = 0
        
class PM_DV3DCell( SpreadsheetCell, PersistentVisualizationModule ):
    """
    VTKCell is a VisTrails Module that can display vtkRenderWindow inside a cell
    
    """

    def __init__( self, mid, **args ):
        SpreadsheetCell.__init__(self)
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, **args )
        self.allowMultipleInputs = True
        self.renderers = []
        self.cellWidget = None
        self.imageInfo = None
        self.enableBasemap = True
        self.baseMapActor = None
        self.renWin = None

#    def get_output(self, port):
#        module = Module.get_output(self, port)
#        output_id = id( module )    
#        print " WorldFrame.get_output: output Module= %s " % str(output_id)
#        return module

#        # if self.outputPorts.has_key(port) or not self.outputPorts[port]: 
#        if port not in self.outputPorts:
#            raise ModuleError(self, "output port '%s' not found" % port)
#        return self.outputPorts[port]


    def updateModule(self):
        self.buildRendering()
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
        self.buildWidget()
   
    def buildRendering(self):
#        wmod = self.getWorkflowModule() 
        controller, module = self.getRegisteredModule()
        self.enableBasemap = self.getInputValue( "enable_basemap", True )

#        print " DV3DCell compute, id = %s, cachable: %s " % ( str( id(self) ), str( self.is_cacheable() ) )
        self.renderers = []
        self.renderer = None
        for inputModule in self.inputModuleList:
            if inputModule <> None:
                renderer1 = inputModule.getRenderer() 
                if  renderer1 <> None: 
                    if not self.renderer: self.renderer = renderer1
                    self.renderers.append( wrapVTKModule( 'vtkRenderer', renderer1 ) )
#                        renderer.SetNearClippingPlaneTolerance(0.0001)
#                        print "NearClippingPlaneTolerance: %f" % renderer.GetNearClippingPlaneTolerance()
        
        if self.enableBasemap and self.renderers and ( self.newDataset or not self.baseMapActor ):
             
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
            print "Positioning map at location %s, size = %s, roi = %s" % ( str( ( self.x0, self.y0) ), str( map_cut_size ), str( ( NormalizeLon( self.roi[0] ), NormalizeLon( self.roi[1] ), self.roi[2], self.roi[3] ) ) )
            self.baseMapActor.SetPosition( self.x0, self.y0, 0.1 )
            self.baseMapActor.SetInput( baseImage )
            map_center = [ self.x0 + map_cut_size[0]/2.0, self.y0 + map_cut_size[1]/2.0 ]
            
            self.renderer.AddActor( self.baseMapActor )

            aCamera = self.renderer.GetActiveCamera()
            aCamera.SetViewUp( 0, 0, 1 )
            aCamera.SetPosition( 0.0, 0.0, ( map_center[0] + map_center[1] ) / 4.0 )
            aCamera.SetFocalPoint( map_center[0], map_center[1], 0.0 )
            aCamera.ComputeViewPlaneNormal()
            self.renderer.ResetCamera()                
        
    def buildWidget(self):                        
        if not self.cellWidget:
            if self.renderers:
                renderViews = []
                renderView = None
                iHandlers = []
                iStyle = None
                picker = None
                
                self.cellWidget = self.displayAndWait(QVTKWidget, (self.renderers, renderView, iHandlers, iStyle, picker))
                self.renWin = self.cellWidget.GetRenderWindow()
                
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
        DV3DConfigurationWidget.__init__(self, module, controller, 'DV3D Cell Configuration', parent)
                
    def getParameters( self, module ):
        basemapParams = getFunctionParmStrValues( module, "enable_basemap" )
        if basemapParams: self.enableBasemap = bool( basemapParams[0] )
        basemapParams = getFunctionParmStrValues( module, "map_border_size" )
        if basemapParams:  self.mapBorderSize = float( basemapParams[0] )

    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """
        self.setLayout( QVBoxLayout() )
        self.layout().setMargin(0)
        self.layout().setSpacing(0)

        self.tabbedWidget = QTabWidget()
        self.layout().addWidget( self.tabbedWidget ) 

        self.createButtonLayout() 
        
        basemapTab = QWidget()        
        self.tabbedWidget.addTab( basemapTab, 'basemap' )                 
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
        self.borderSizeEdit.setValidator( QDoubleValidator() )
        self.borderSizeEdit.setText( "%.2f" % self.mapBorderSize )
        self.connect( self.borderSizeEdit, SIGNAL("editingFinished()"), self.stateChanged ) 
        enable_label.setBuddy( self.borderSizeEdit )
#        self.borderSizeEdit.setFrameStyle( QFrame.Panel|QFrame.Raised )
#        self.borderSizeEdit.setLineWidth(2)
        border_layout.addWidget( self.borderSizeEdit  )        
        layout.addLayout( border_layout )
        
    def basemapStateChanged( self, enabled ):
        self.stateChanged()

    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'enable_basemap' , [ self.enableBasemap ]  ), )      
        parmRecList.append( ( 'map_border_size' , [ self.mapBorderSize ]  ), )  
        self.persistParameterList( parmRecList )
        self.stateChanged(False)         
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.enableBasemap = self.enableCheckBox.isChecked() 
        self.mapBorderSize = float( self.borderSizeEdit.text() )
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()
 
class DV3DCell(WorkflowModule):
    
    PersistentModuleClass = PM_DV3DCell
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
