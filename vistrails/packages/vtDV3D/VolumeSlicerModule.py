'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, math, traceback
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from packages.vtk.base_module import vtkBaseModule
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D.WorkflowModule import WorkflowModule 
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.ImagePlaneWidget import *
from packages.vtDV3D import HyperwallManager
VolumeSlicerModules = {}

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultOutlineMapFile = os.path.join( defaultMapDir,  'political_map.png' )

class PM_VolumeSlicer(PersistentVisualizationModule):
    """
        This module generates dragable slices through 3D volumetric (<i>vtkImagedata</i>) data.  Three slice planes are provided 
        ( perpendicular to the three axes ) which are dragable along the corresponding axis (by default) with a right mouse click.
        More general plane orientations are possible by enabling margins (see command keys).  Colormap scaling is controlled using 
        the <b>colorRangeScale</b> leveling function.  Left clicking on a slice plane displays the coordinates and data value at the picked point.
        <h3>  Command Keys </h3> 
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> l </td> <td> Toggle show colorbar. </td>
        <tr> <td> x </td> <td> Snap the 'x' slice back to its default (perpendicular to 'x' axis) position. </td>
        <tr> <td> y </td> <td> Snap the 'y' slice back to its default (perpendicular to 'y' axis) position. </td>
        <tr> <td> z </td> <td> Snap the 'z' slice back to its default (perpendicular to 'z' axis) position. </td>
        <tr> <td> m </td> <td> Enable margins. Right-clicking and dragging the slice margins enables rotations and translations of the planes </td>
        </table>
    """
    # used to export the interactive time series
    global_coords = [-1, -1, -1]

    def __init__( self, mid, **args ):
        import api
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.primaryInputPorts = [ 'volume', 'contours' ]
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', units='data', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRangeInput=0, group=ConfigGroup.Color )
        self.addConfigurableLevelingFunction( 'opacity', 'O', label='Slice Plane Opacity', rangeBounds=[ 0.0, 1.0 ],  setLevel=self.setOpacity, activeBound='min',  getLevel=self.getOpacity, isDataValue=False, layerDependent=True, bound = False, group=ConfigGroup.Rendering )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ], group=ConfigGroup.Display )
        self.addConfigurableLevelingFunction( 'contourDensity', 'g', label='Contour Density', activeBound='max', setLevel=self.setContourDensity, getLevel=self.getContourDensity, layerDependent=True, windowing=False, rangeBounds=[ 3.0, 30.0, 1 ], bound=False, isValid=self.hasContours, group=ConfigGroup.Rendering )
        self.addConfigurableLevelingFunction( 'contourColorScale', 'S', label='Contour Colormap Scale', units='data', setLevel=self.scaleContourColormap, getLevel=lambda:self.getDataRangeBounds(1), layerDependent=True, adjustRangeInput=1, isValid=self.hasContours, group=ConfigGroup.Color )
        self.addConfigurableBooleanFunction('toggleOutlineMap', self.toggleOutlineMap, 'm', labels='Show Outline Map|Hide Outline Map', initVal=True, group=ConfigGroup.Display )
        self.addUVCDATConfigGuiFunction( 'contourColormap', ColormapConfigurationDialog, 'K', label='Choose Contour Colormap', setValue=lambda data: self.setColormap(data,1) , getValue=lambda: self.getColormap(1), layerDependent=True, isValid=self.hasContours, group=ConfigGroup.Color )
        self.sliceOutputShape = args.get( 'slice_shape', [ 100, 50 ] )
        self.opacity = [ 1.0, 1.0 ]
        self.iOrientation = 0
        self.updatingPlacement = False
        self.isSlicing = False
        self.planeWidgetX = None
        self.planeWidgetY = None
        self.planeWidgetZ = None
        self.opacityUpdateCount = 0
        self.generateContours = False
        self.contourLineActors = {}
        self.contourLineMapperer = None
        self.contours = None
        self.NumContours = 10.0
        self.showOutlineMap = True
        try:
            controller = api.get_current_controller()
#            print " Volume Slicer init, id = %x " % id(self)
            VolumeSlicerModules[mid] = self
        except api.NoVistrail:
            pass

    def __del__(self):
        print " **************************************** Deleting VolumeSlicer module, id = %d  **************************************** " % self.moduleID
#        self.planeWidgetX.RemoveAllObservers()
#        self.planeWidgetY.RemoveAllObservers()
#        self.planeWidgetZ.RemoveAllObservers()
        PersistentVisualizationModule.__del__(self)

    def clearReferrents(self):
        PersistentVisualizationModule.clearReferrents(self)
        del VolumeSlicerModules[ self.moduleID ]
        del self.planeWidgetX
        del self.planeWidgetY
        del self.planeWidgetZ
        self.planeWidgetX = None
        self.planeWidgetY = None
        self.planeWidgetZ = None
        del self.sliceOutput
        self.sliceOutput = None 
        if self.contours:
            del self.contours
            self.contours = None    
            del self.contourLineMapperer 
            self.contourLineMapperer = None
        
    def toggleOutlineMap( self, enabled ):
        self.showOutlineMap = enabled
        self.planeWidgetZ.planeActor.SetVisibility(self.showOutlineMap)
        self.render()
        
    def scaleContourColormap(self, data, **args ):
        return self.scaleColormap( data, 1, **args )
        
    def hasContours(self):
        return self.generateContours
        
    def setContourDensity( self, ctf_data, **args ):
        if self.NumContours <> ctf_data[1]:
            self.NumContours = ctf_data[1]
            self.updateContourDensity()

    def getContourDensity( self ):
        return [ 3.0, self.NumContours, 1 ]
    
    def setZScale( self, zscale_data, **args ):
        if self.setInputZScale( zscale_data ):
            if self.planeWidgetX <> None:
                primaryInput = self.input()
                bounds = list( primaryInput.GetBounds() ) 
                if not self.planeWidgetX.MatchesBounds( bounds ):
                    self.planeWidgetX.PlaceWidget( bounds )        
                    self.planeWidgetY.PlaceWidget( bounds ) 
                    self.render()               

    def setInputZScale( self, zscale_data, **args  ):
        rv = PersistentVisualizationModule.setInputZScale(self,  zscale_data, **args ) 
        if rv:
            ispec = self.getInputSpec(  1 )       
            if (ispec <> None) and (ispec.input() <> None):
                contourInput = ispec.input() 
                ix, iy, iz = contourInput.GetSpacing()
                sz = zscale_data[1]
                contourInput.SetSpacing( ix, iy, sz )  
                contourInput.Modified() 
        return rv
                
    def getOpacity(self):
        return self.opacity
    
    def setOpacity(self, range, **args ):
        self.opacity = range
#        printArgs( " Leveling: ", opacity=self.opacity, range=range ) 
        self.updateOpacity() 

    def updateOpacity(self, cmap_index=0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setAlphaRange( [ bound( self.opacity[i], [ 0.0, 1.0 ] ) for i in (0,1) ] )
        if (self.opacityUpdateCount % 5) == 0: self.render()
        self.opacityUpdateCount = self.opacityUpdateCount + 1  
#        self.lut.SetAlpha( self.opacity[1] )
#        self.lut.SetAlphaRange ( self.opacity[0], self.opacity[1] )
#        print "  ---> Set Opacity = %s " % str( self.opacity )
#        self.UpdateWidgetPlacement()
        
#    def UpdateWidgetPlacement(self):
#        self.updatingPlacement = True
#        self.planeWidgetX.UpdatePlacement() 
#        self.planeWidgetX.PlaceWidget()
#        self.planeWidgetY.UpdatePlacement() 
#        self.planeWidgetY.PlaceWidget()
#        self.planeWidgetZ.UpdatePlacement() 
#        self.planeWidgetZ.PlaceWidget()
#        self.updatingPlacement = False

    def enableVisualizationInteraction(self): 
#        print>>sys.stderr, "enable Visualization Interaction"
        self.planeWidgetX.EnableInteraction()                                                
        self.planeWidgetY.EnableInteraction()                                                
        self.planeWidgetZ.EnableInteraction()  

    def disableVisualizationInteraction(self):
#        print>>sys.stderr, "disable Visualization Interaction" 
        self.planeWidgetX.DisableInteraction()                                                
        self.planeWidgetY.DisableInteraction()                                                
        self.planeWidgetZ.DisableInteraction()  

    def updatingColormap( self, cmap_index, colormapManager ):
        if cmap_index == 0:
            self.planeWidgetX.SetTextureInterpolate( colormapManager.smoothColormap )
            self.planeWidgetY.SetTextureInterpolate( colormapManager.smoothColormap )
            self.planeWidgetZ.SetTextureInterpolate( colormapManager.smoothColormap )
            self.updateModule()
                                                                        
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """     
#        contourModule = self.wmod.forceGetInputFromPort( "contours", None )
#        if self.input() == None:
#            if contourModule <> None:
#                self.input() = contourModule.getOutput() 
#            else:
#                print>>sys.stderr, "Error, must provide an input to the Volume Slicer module!"
 #       self.intersectInputExtents()
        contour_ispec = self.getInputSpec(  1 )       

        contourInput = contour_ispec.input() if contour_ispec <> None else None
        primaryInput = self.input()

#        self.contourInput = None if contourModule == None else contourModule.getOutput() 
        # The 3 image plane widgets are used to probe the dataset.    
#        print " Volume Slicer buildPipeline, id = %s " % str( id(self) )
        self.sliceOutput = vtk.vtkImageData()  
        xMin, xMax, yMin, yMax, zMin, zMax = primaryInput.GetWholeExtent()       
        self.slicePosition = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        dataType = primaryInput.GetScalarTypeAsString()
        bounds = list(primaryInput.GetBounds()) 
        origin = primaryInput.GetOrigin()
        if (dataType <> 'float') and (dataType <> 'double'):
             self.setMaxScalarValue( primaryInput.GetScalarType() )
#        print "Data Type = %s, range = (%f,%f), extent = %s, origin = %s, bounds=%s, slicePosition=%s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], str(self.input().GetWholeExtent()), str(origin), str(bounds), str(self.slicePosition)  )
      
        # The shared picker enables us to use 3 planes at one time
        # and gets the picking order right
        lut = self.getLut()
        picker = None
        useVtkImagePlaneWidget = False
        textureColormapManager = self.getColormapManager( index=0 )
        
        if self.planeWidgetX == None: 
            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.005) 
            self.planeWidgetX = ImagePlaneWidget( self, 0 )
            self.planeWidgetX.SetPicker(picker)
            self.observerTargets.add( self.planeWidgetX )
            self.planeWidgetX.SetRenderer( self.renderer )
            prop1 = self.planeWidgetX.GetPlaneProperty()
            prop1.SetColor(1, 0, 0)
            self.planeWidgetX.SetUserControlledLookupTable(1)
            self.planeWidgetX.SetLookupTable( lut )
            
#            self.planeWidgetX.SetSliceIndex( self.slicePosition[0] )
        self.planeWidgetX.SetInput( primaryInput, contourInput )
        self.planeWidgetX.SetPlaneOrientationToXAxes()
#        self.planeWidgetX.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 0 ) )
#            self.planeWidgetX.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
#            self.planeWidgetX.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
        self.planeWidgetX.PlaceWidget( bounds )       

#        if bounds[0] < 0.0: self.planeWidgetX.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
#        self.planeWidgetX.SetOrigin( primaryInput.GetOrigin() )
#        self.planeWidgetX.AddObserver( 'AnyEvent', self.TestObserver )
                
        if self.planeWidgetY == None: 
            self.planeWidgetY = ImagePlaneWidget( self, 1)
            self.planeWidgetY.SetPicker(picker)
            self.planeWidgetY.SetRenderer( self.renderer )
            self.planeWidgetY.SetUserControlledLookupTable(1)
            self.observerTargets.add( self.planeWidgetY )
#            self.planeWidgetY.SetSliceIndex( self.slicePosition[1] )
            prop2 = self.planeWidgetY.GetPlaneProperty()
            prop2.SetColor(1, 1, 0)
            self.planeWidgetY.SetUserControlledLookupTable(1)
            self.planeWidgetY.SetLookupTable( lut )
        
        self.planeWidgetY.SetInput( primaryInput, contourInput )
        self.planeWidgetY.SetPlaneOrientationToYAxes()       
        self.planeWidgetY.PlaceWidget(  bounds  ) 
        
        if self.planeWidgetZ == None:
            self.planeWidgetZ = ImagePlaneWidget( self, 2 )
            self.planeWidgetZ.SetPicker(picker)
            self.planeWidgetZ.SetRenderer( self.renderer )
            self.observerTargets.add( self.planeWidgetZ )
#            self.planeWidgetZ.SetSliceIndex( self.slicePosition[2] )
            prop3 = self.planeWidgetZ.GetPlaneProperty()
            prop3.SetColor(0, 0, 1)
            self.planeWidgetZ.SetUserControlledLookupTable(1)
            self.planeWidgetZ.SetLookupTable( lut )
       
        self.planeWidgetZ.SetInput( primaryInput, contourInput )
        self.planeWidgetZ.SetPlaneOrientationToZAxes()
        self.planeWidgetZ.PlaceWidget( bounds )
        outlineMap = self.buildOutlineMap()
        if outlineMap: self.planeWidgetZ.SetOutlineMap( outlineMap )

        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.updateOpacity() 
        
        if (contour_ispec <> None) and (contour_ispec.input() <> None) and (self.contours == None):
            rangeBounds = self.getRangeBounds(1)
            colormapManager = self.getColormapManager( index=1 )
            self.generateContours = True   
            self.contours = vtk.vtkContourFilter()
            self.contours.GenerateValues( self.NumContours, rangeBounds[0], rangeBounds[1] )
     
            self.contourLineMapperer = vtk.vtkPolyDataMapper()
            self.contourLineMapperer.SetInputConnection( self.contours.GetOutputPort() )
            self.contourLineMapperer.SetScalarRange( rangeBounds[0], rangeBounds[1] )
            self.contourLineMapperer.SetColorModeToMapScalars()
            self.contourLineMapperer.SetLookupTable( colormapManager.lut )
            self.contourLineMapperer.UseLookupTableScalarRangeOn()

#        self.imageRescale = vtk.vtkImageReslice() 
#        self.imageRescale.SetOutputDimensionality(2) 
#        self.imageRescale.SetInterpolationModeToLinear() 
#        self.imageRescale.SetResliceAxesDirectionCosines( [-1, 0, 0], [0, -1, 0], [0, 0, -1] )

#        self.set2DOutput( port=self.imageRescale.GetOutputPort(), name='slice' ) 
        self.set3DOutput() 

        # Add the times series only in regular volume slicer and not in Hovmoller Slicer
        if self.getInputSpec().getMetadata()['plotType']=='xyz':
            self.addConfigurableFunction('Show Time Series', None, 't' )

    def buildOutlineMap(self):
        # This function load a binary image (black and white)
        # and create a default grid for it. Then it uses re-gridding algorithms 
        # to scale in the correct domain.
        from pylab import imread
        import vtk.util.vtkImageImportFromArray as vtkUtil

        # read outline image and convert to gray scale
        try:
            data = imread(defaultOutlineMapFile)
            data = data.mean(axis=2)
    
    #        # create a variable using the data loaded in the image and an uniform grid
            dims = data.shape
            reso = [180.0/dims[0], 360.0/dims[1]]
            var = cdms2.createVariable(data)
            lat = cdms2.createUniformLatitudeAxis(90, dims[0], -reso[0])
            lon = cdms2.createUniformLongitudeAxis(-180, dims[1], reso[1])
            var.setAxis(0, lat)
            var.setAxis(1, lon)
    
            # create the final map using the ROI
            ROI = self.roi[:]
            if ROI[2] < -90.0: ROI[2] = -90.0
            if ROI[3] >  90.0: ROI[3] =  90.0
            odims = [ (ROI[3]-ROI[2])/reso[0] , (ROI[1]-ROI[0])/reso[1] ]
            ogrid = cdms2.createUniformGrid( ROI[2], odims[0], reso[0], ROI[0], odims[1], reso[1] )
            ovar = var.regrid(ogrid, regridTool='regrid2')
            
            # replace outlier numbers
            d = ovar.data
            d[d==1e+20] = d[d<>1e+20].max()
            
            img = vtkUtil.vtkImageImportFromArray()
            img.SetArray(ovar.data)
            img.Update()
            
        except Exception:
            print>>sys.stderr, "Error building Outline Map"
            traceback.print_exc()
            return None
        
        # convert to vtkImageData       
        return img.GetOutput()
    
    def updateContourDensity(self):
        if self.generateContours:
            rangeBounds = self.getRangeBounds(1)
            self.contours.GenerateValues( self.NumContours, rangeBounds[0], rangeBounds[1] )
            self.contours.Modified()
            self.render()
        
    def onSlicerLeftButtonPress( self, caller, event ):
        self.currentButton = self.LEFT_BUTTON   
        return 0

    def onSlicerRightButtonPress( self, caller, event ):
        self.currentButton = self.RIGHT_BUTTON
        return 0
                
    def updateModule(self, **args ):
        primaryInput = self.input()
        contour_ispec = self.getInputSpec(  1 )       
        contourInput = contour_ispec.input() if contour_ispec <> None else None
        self.planeWidgetX.SetInput( primaryInput, contourInput )         
        self.planeWidgetY.SetInput( primaryInput, contourInput )         
        self.planeWidgetZ.SetInput( primaryInput, contourInput ) 
        self.set3DOutput()
           
    def TestObserver( self, caller=None, event = None ):
        print " Volume Slicer TestObserver: event = %s, " % ( event )
        
    def getAxes(self):
        pass

    def ProcessIPWAction( self, caller, event, **args ):
        action = caller.State
        iAxis = caller.PlaneIndex

        if event == ImagePlaneWidget.InteractionUpdateEvent:
            
            if action == ImagePlaneWidget.Cursoring:   
                if not self.isSlicing:
                    HyperwallManager.getInstance().setInteractionState( 'VolumeSlicer.Slicing' )
                    self.isSlicing = True
                ispec = self.inputSpecs[ 0 ] 
                cursor_data = caller.GetCursorData()
                image_value = cursor_data[3] 
                cpos = cursor_data[0:3]     
                dataValue = self.getDataValue( image_value )
                wpos = ispec.getWorldCoords( cpos )
                if self.generateContours:
                    contour_image_value = cursor_data[4]
                    if  contour_image_value:
                        contour_value = self.getDataValue( contour_image_value, 1 )
                        contour_units = self.getUnits(1)
                        textDisplay = " Position: (%s, %s, %s), Value: %.3G %s, Contour Value: %.3G %s" % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units, contour_value, contour_units )
                    else:
                        textDisplay = " Position: (%s, %s, %s), Value: %.3G %s" % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units )
#                    print " >>>>> Current Image Value: %d %d, data value: %.3G, contour value: %.3G, pos = %s, (%s) " % ( image_value, contour_image_value, dataValue, contour_value, str(cpos), str(wpos) )
                else:
                    textDisplay = " Position: (%s, %s, %s), Value: %.3G %s." % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units )
#                    print " >>>>> Current Image Value: %d, data value: %.3G, pos = %s, (%s) " % ( image_value, dataValue, str(cpos), str(wpos) )
                sliceIndex = caller.GetSliceIndex() 
                self.slicePosition[iAxis] = sliceIndex
                self.updateTextDisplay( textDisplay )
                
                coord = ispec.getWorldCoordsAsFloat(cpos)
                PM_VolumeSlicer.global_coords = coord
                screenPos = caller.GetCurrentScreenPosition()
                self.updateLensDisplay(screenPos, coord)
                
            if action == ImagePlaneWidget.Pushing: 
                ispec = self.inputSpecs[ 0 ]  
                if not self.isSlicing:
                    HyperwallManager.getInstance().setInteractionState( 'VolumeSlicer.Slicing' )
                    self.isSlicing = True 
                sliceIndex = caller.GetSliceIndex() 
                axisName, spos = ispec.getWorldCoord( sliceIndex, iAxis )
                textDisplay = " %s = %s ." % ( axisName, spos )
                if iAxis == 0:
                    p1 = caller.GetPoint1()
#                    print " >++++++++++++++++++> Slicing: Set Slice[%d], index=%d, pos=%.2f, " % ( iAxis, sliceIndex, p1[0] ), textDisplay
                self.slicePosition[ iAxis ] = sliceIndex                  
                self.updateTextDisplay( textDisplay ) 
            
            if self.generateContours:
                slice_data = caller.GetReslice2Output()
                slice_data.Update()                
                self.contours.SetInput( slice_data )
                self.contours.Modified()
                origin = caller.GetOrigin()
                contourLineActor = self.getContourActor( iAxis )
                contourLineActor.SetPosition( origin[0], origin[1], origin[2] )
#                contourLineActor.SetOrigin( origin[0], origin[1], origin[2] )
                self.setVisibleContour( iAxis )
#                print " Generate Contours, data dims = %s, origin = %s, pos = %s, extent = %s" % ( str( slice_data.GetDimensions() ), str(slice_data.GetOrigin()), str(origin), str(slice_data.GetExtent()) )
                
            self.render()
#                print " Generate Contours, data dims = %s, pos = %s %s %s " % ( str( slice_data.GetDimensions() ), str(pos1), str(pos2), str(origin) )

    def setContourActorOrientation( self, iAxis, contourLineActor ):
        if iAxis == 1: 
            contourLineActor.SetOrientation(90,0,0)
        elif iAxis == 0: 
            contourLineActor.SetOrientation(90,0,90)   

    def updateContourActorOrientations( self ):
        for contourLineActorItem in self.contourLineActors.items():
            if contourLineActorItem[1].GetVisibility( ): 
                self.setContourActorOrientation( contourLineActorItem[0], contourLineActorItem[1] )
        self.render()
        pass

                                     
    def getContourActor( self, iAxis, **args ):
        contourLineActor = self.contourLineActors.get( iAxis, None )
        if contourLineActor == None:
            contourLineActor = vtk.vtkActor()
            contourLineActor.SetMapper(self.contourLineMapperer)
            contourLineActor.GetProperty().SetLineWidth(2)     
            self.renderer.AddActor( contourLineActor ) 
            self.contourLineActors[iAxis] = contourLineActor
            self.setContourActorOrientation( iAxis, contourLineActor )
#            print " GetContourActor %d, origin = %s, position = %s " % ( iAxis, str( contourLineActor.GetOrigin() ), str( contourLineActor.GetPosition() ) )
        return contourLineActor

            
    def setVisibleContour( self, iAxis ):
        for contourLineActorItem in self.contourLineActors.items():
            if iAxis == contourLineActorItem[0]:    contourLineActorItem[1].VisibilityOn( )
            else:                                   contourLineActorItem[1].VisibilityOff( )


       
    def getAdjustedSliceExtent( self ):
        ext = None
        if self.iOrientation == 1:      ext = [ 0, self.sliceOutputShape[1]-1,  0, self.sliceOutputShape[0]-1, 0, 0 ]  
        else:                           ext = [ 0, self.sliceOutputShape[0]-1,  0, self.sliceOutputShape[1]-1, 0, 0 ]  
#        print " Slice Extent = %s " % str( ext )
        return ext       

    def getAdjustedSliceSpacing( self, outputData ):
        padded_extent = outputData.GetWholeExtent()
        padded_shape = [ padded_extent[1]-padded_extent[0]+1, padded_extent[3]-padded_extent[2]+1, 1 ]
        padded_spacing = outputData.GetSpacing()
        scale_factor = [ padded_shape[0]/float(self.sliceOutputShape[0]), padded_shape[1]/float(self.sliceOutputShape[1]) ]
        if self.iOrientation == 1:      spacing = [ padded_spacing[1]*scale_factor[1], padded_spacing[0]*scale_factor[0], 1.0 ]
        else:                           spacing = [ padded_spacing[0]*scale_factor[0], padded_spacing[1]*scale_factor[1], 1.0 ]
#        print " Slice Spacing = %s " % str( spacing )
        return spacing
                       
    def initColorScale( self, caller, event ): 
        x, y = caller.GetEventPosition()
        self.ColorLeveler.startWindowLevel( x, y )

    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        ispec = self.inputSpecs[ cmap_index ]
        if ispec and ispec.input(): 
            colormapManager = self.getColormapManager( index=cmap_index )
#            if not colormapManager.matchDisplayRange( ctf_data ):
            imageRange = self.getImageValues( ctf_data[0:2], cmap_index ) 
            colormapManager.setScale( imageRange, ctf_data )
            if self.contourLineMapperer: 
                self.contourLineMapperer.Modified()
            ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } )
#            print '-'*50
#            print " Volume Slicer[%d]: Scale Colormap: ( %.4g, %.4g ) " % ( self.moduleID, ctf_data[0], ctf_data[1] )
#            print '-'*50
                
    def finalizeLeveling( self, cmap_index=0 ):
        isLeveling =  PersistentVisualizationModule.finalizeLeveling( self )
        if isLeveling:
            ispec = self.inputSpecs[ cmap_index ] 
            ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
#            self.updateSliceOutput()

    def initializeConfiguration( self, cmap_index=0 ):
        PersistentModule.initializeConfiguration(self)
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
#        self.updateSliceOutput()

    def updateColorScale( self, caller, event ):
        x, y = caller.GetEventPosition()
        wsize = self.renderer.GetSize()
        range = self.ColorLeveler.windowLevel( x, y, wsize )
        return range
              
    def onKeyPress( self, caller, event ):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        alt = ( keysym.lower().find('alt') == 0 )
        ctrl = caller.GetControlKey() 
        shift = caller.GetShiftKey() 
#        print " -- Key Press: %c ( %d: %s ), ctrl: %s, shift: %s, alt: %s, event = %s " % ( key, ord(key), str(keysym), bool(ctrl), bool(shift), bool(alt), str( event ) )
#        if ( key == 'x' ): 
#            self.planeWidgetX.SetPlaneOrientationToXAxes() 
#            self.planeWidgetX.SetSliceIndex( 0 ) #self.slicePosition[0] )
#            self.render()      
#        elif ( key == 'y' ):  
#            self.planeWidgetY.SetPlaneOrientationToYAxes()
#            self.planeWidgetY.SetSliceIndex( 0 ) #self.slicePosition[1] )
#            self.render()       
#        elif ( key == 'z' ):  
#            self.planeWidgetZ.SetPlaneOrientationToZAxes()
#            self.planeWidgetZ.SetSliceIndex( 0 ) #self.slicePosition[2] )
#            self.render() 
             
              
    def onKeyRelease( self, caller, event ):
        key = caller.GetKeyCode()

class VolumeSlicer(WorkflowModule):
    
    PersistentModuleClass = PM_VolumeSlicer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)    
              
if __name__ == '__main__':
    executeVistrail( 'VolumeSlicerDemo' )
    
    
    
#        self.spacing = self.input().GetSpacing()
#        sx, sy, sz = self.spacing       
#        origin = self.input().GetOrigin()
#        ox, oy, oz = origin
#        center = [ origin[0] + self.spacing[0] * 0.5 * (xMin + xMax), origin[1] + self.spacing[1] * 0.5 * (yMin + yMax), origin[2] + self.spacing[2] * 0.5 * (zMin + zMax)]
#        self.sliceMatrix = [ vtk.vtkMatrix4x4(), vtk.vtkMatrix4x4(), vtk.vtkMatrix4x4() ]
#        self.sliceMatrix[0].DeepCopy( (0, 1, 0, center[0],    0,  0, 1, center[1],     1, 0, 0, center[2],    0, 0, 0, 1) )
#        self.sliceMatrix[1].DeepCopy( (1, 0, 0, center[0],    0,  0, 1, center[1],     0, 1, 0, center[2],    0, 0, 0, 1) )
#        self.sliceMatrix[2].DeepCopy( (1, 0, 0, center[0],    0, -1, 0, center[1],     0, 0, 1, center[2],    0, 0, 0, 1) )
         
#        self._range = self.rangeBounds[0:2]           

