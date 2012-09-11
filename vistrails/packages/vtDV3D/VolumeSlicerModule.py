'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, math
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
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.primaryInputPorts = [ 'volume', 'contours' ]
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', units='data', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRange=True )
        self.addConfigurableLevelingFunction( 'opacity', 'O', label='Slice Plane Opacity',    setLevel=self.setOpacity, activeBound='min',  getLevel=self.getOpacity, isDataValue=False, layerDependent=True, bound = False )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
        self.addConfigurableLevelingFunction( 'contourDensity', 'g', label='Contour Density', activeBound='max', setLevel=self.setContourDensity, getLevel=self.getContourDensity, layerDependent=True, windowing=False, rangeBounds=[ 3.0, 30.0, 1 ], bound=False, isValid=self.hasContours )
        self.addConfigurableLevelingFunction( 'contourColorScale', 'S', label='Contour Colormap Scale', units='data', setLevel=lambda data: self.scaleColormap(data,1), getLevel=lambda:self.getDataRangeBounds(1), layerDependent=True, adjustRange=True, isValid=self.hasContours )
        self.addConfigurableGuiFunction( 'contourColormap', ColormapConfigurationDialog, 'K', label='Choose Contour Colormap', setValue=lambda data: self.setColormap(data,1) , getValue=lambda: self.getColormap(1), layerDependent=True, isValid=self.hasContours )
        self.sliceOutputShape = args.get( 'slice_shape', [ 100, 50 ] )
        self.opacity = [ 0.75, 1.0 ]
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
#        self.contourInput = None
#        self.contourMetadata = None
#        self.contour_units = ""
        self.NumContours = 10.0
#        self.imageRescale = None
        print " Volume Slicer init, id = %x " % id(self)
        VolumeSlicerModules[mid] = self

    def __del__(self):
        self.planeWidgetX.RemoveAllObservers()
        self.planeWidgetY.RemoveAllObservers()
        self.planeWidgetZ.RemoveAllObservers()
        del VolumeSlicerModules[ self.moduleID ]
        
    def hasContours(self):
        return self.generateContours
        
    def setContourDensity( self, ctf_data ):
        self.NumContours = ctf_data[1]
        self.updateContourDensity()

    def getContourDensity( self ):
        return [ 3.0, self.NumContours, 1 ]
    
    def setZScale( self, zscale_data, **args ):
        if self.setInputZScale( zscale_data ):
            if self.planeWidgetX <> None:
                bounds = list( self.input().GetBounds() ) 
                self.planeWidgetX.PlaceWidget( bounds )        
                self.planeWidgetY.PlaceWidget( bounds )                

    def setInputZScale( self, zscale_data, **args  ): 
        ispec = self.getInputSpec(  1 )       
        if (ispec <> None) and (ispec.input <> None):
            contourInput = ispec.input 
            ix, iy, iz = contourInput.GetSpacing()
            sz = zscale_data[1]
            contourInput.SetSpacing( ix, iy, sz )  
            contourInput.Modified() 
        return PersistentVisualizationModule.setInputZScale(self,  zscale_data, **args )
                
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
        print "  ---> Set Opacity = %s " % str( self.opacity )
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
        self.planeWidgetX.EnableInteraction()                                                
        self.planeWidgetY.EnableInteraction()                                                
        self.planeWidgetZ.EnableInteraction()  

    def disableVisualizationInteraction(self): 
        self.planeWidgetX.DisableInteraction()                                                
        self.planeWidgetY.DisableInteraction()                                                
        self.planeWidgetZ.DisableInteraction()  

#    def updateContourMetadata(self):
#        if self.contourMetadata == None:
#            scalars = None
#            self.newDataset = False
#            self.contourInput.Update()
#            contourFieldData = self.contourInput.GetFieldData()                 
#            self.contourMetadata = extractMetadata( contourFieldData )            
#            if self.contourMetadata <> None:    
#                attributes = self.contourMetadata.get( 'attributes' , None )
#                if attributes:
#                    self.contour_units = attributes.get( 'units' , '' )
                                                            
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
        contour_ispec = self.getInputSpec(  1 )       
        contourInput = contour_ispec.input if contour_ispec <> None else None

#        self.contourInput = None if contourModule == None else contourModule.getOutput() 
        # The 3 image plane widgets are used to probe the dataset.    
        print " Volume Slicer buildPipeline, id = %s " % str( id(self) )
        self.sliceOutput = vtk.vtkImageData()  
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.slicePosition = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        dataType = self.input().GetScalarTypeAsString()
        bounds = list(self.input().GetBounds()) 
        origin = self.input().GetOrigin()
        if (dataType <> 'float') and (dataType <> 'double'):
             self.setMaxScalarValue( self.input().GetScalarType() )
#        print "Data Type = %s, range = (%f,%f), extent = %s, origin = %s, bounds=%s, slicePosition=%s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], str(self.input().GetWholeExtent()), str(origin), str(bounds), str(self.slicePosition)  )
      
        # The shared picker enables us to use 3 planes at one time
        # and gets the picking order right
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
        lut = self.getLut()
        useVtkImagePlaneWidget = False
        
        self.planeWidgetX = ImagePlaneWidget( self, 0 )
#        self.planeWidgetX.DisplayTextOff()
        self.planeWidgetX.SetRenderer( self.renderer )
        self.planeWidgetX.SetInput( self.input(), contourInput )
        self.planeWidgetX.SetPlaneOrientationToXAxes()
        self.planeWidgetX.SetSliceIndex( self.slicePosition[0] )
        self.planeWidgetX.SetPicker(picker)
        prop1 = self.planeWidgetX.GetPlaneProperty()
        prop1.SetColor(1, 0, 0)
        self.planeWidgetX.SetUserControlledLookupTable(1)
        self.planeWidgetX.SetLookupTable( lut )
#        self.planeWidgetX.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 0 ) )
#            self.planeWidgetX.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
#            self.planeWidgetX.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
        self.planeWidgetX.PlaceWidget( bounds )       

#        if bounds[0] < 0.0: self.planeWidgetX.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
#        self.planeWidgetX.SetOrigin( self.input().GetOrigin() )
#        self.planeWidgetX.AddObserver( 'AnyEvent', self.TestObserver )
                
        self.planeWidgetY = ImagePlaneWidget( self, 1)
#        self.planeWidgetY.DisplayTextOff()
        self.planeWidgetY.SetRenderer( self.renderer )
        self.planeWidgetY.SetInput( self.input(), contourInput )
        self.planeWidgetY.SetPlaneOrientationToYAxes()
        self.planeWidgetY.SetUserControlledLookupTable(1)
        self.planeWidgetY.SetSliceIndex( self.slicePosition[1] )
        self.planeWidgetY.SetPicker(picker)
#        self.planeWidgetY.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 1 ) )
#        self.planeWidgetY.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 1 ) )
#        self.planeWidgetY.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 1 ) )
#        self.planeWidgetY.AddObserver( 'AnyEvent', self.TestObserver )
        prop2 = self.planeWidgetY.GetPlaneProperty()
        prop2.SetColor(1, 1, 0)
#        if bounds[0] < 0.0: self.planeWidgetY.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
        self.planeWidgetY.PlaceWidget(  bounds  )        
        self.planeWidgetY.SetUserControlledLookupTable(1)
        self.planeWidgetY.SetLookupTable( lut )
        
        self.planeWidgetZ = ImagePlaneWidget( self, 2 )
#        self.planeWidgetZ.DisplayTextOff()
        self.planeWidgetZ.SetRenderer( self.renderer )
        self.planeWidgetZ.SetInput( self.input(), contourInput )
        self.planeWidgetZ.SetPlaneOrientationToZAxes()
        self.planeWidgetZ.SetSliceIndex( self.slicePosition[2] )
        self.planeWidgetZ.SetPicker(picker)
#        self.planeWidgetZ.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 2 ) )
#        self.planeWidgetZ.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 2 ) )
#        self.planeWidgetZ.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 2 ) )
#        self.planeWidgetZ.AddObserver( 'AnyEvent', self.TestObserver )
#        self.planeWidgetZ.AddObserver( 'LeftButtonPressEvent', self.onSlicerLeftButtonPress )
#        self.planeWidgetZ.AddObserver( 'RightButtonPressEvent', self.onSlicerRightButtonPress )
                
        prop3 = self.planeWidgetZ.GetPlaneProperty()
        prop3.SetColor(0, 0, 1)
#        if bounds[0] < 0.0: self.planeWidgetZ.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
        self.planeWidgetZ.PlaceWidget( bounds )

        self.planeWidgetZ.SetUserControlledLookupTable(1)
        self.planeWidgetZ.SetLookupTable( lut )
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.updateOpacity() 
        
        if (contour_ispec <> None) and (contour_ispec.input <> None):
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

#    def buildPipeline0(self):
#        """ execute()  None
#        Dispatch the vtkRenderer to the actual rendering widget
#        """           
#        # The 3 image plane widgets are used to probe the dataset.    
#        print " Volume Slicer buildPipeline, id = %s " % str( id(self) )
#        self.sliceOutput = vtk.vtkImageData()  
#        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
#        self.slicePosition = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
#        dataType = self.input().GetScalarTypeAsString()
#        bounds = list(self.input().GetBounds()) 
#        origin = self.input().GetOrigin()
#        if (dataType <> 'float') and (dataType <> 'double'):
#             self.setMaxScalarValue( self.input().GetScalarType() )
#        print "Data Type = %s, range = (%f,%f), extent = %s, origin = %s, bounds=%s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], str(self.input().GetWholeExtent()), str(origin), str(bounds) )
#      
#        # The shared picker enables us to use 3 planes at one time
#        # and gets the picking order right
#        picker = vtk.vtkCellPicker()
#        picker.SetTolerance(0.005) 
#
#        self.planeWidgetX = vtk.vtkImagePlaneWidget()
#        self.planeWidgetX.DisplayTextOff()
#        self.planeWidgetX.SetInput( self.input() )
#        self.planeWidgetX.SetPlaneOrientationToXAxes()
#        self.planeWidgetX.SetSliceIndex( self.slicePosition[0] )
#        self.planeWidgetX.SetPicker(picker)
#        self.planeWidgetX.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        prop1 = self.planeWidgetX.GetPlaneProperty()
#        prop1.SetColor(1, 0, 0)
#        self.planeWidgetX.SetUserControlledLookupTable(1)
#        self.planeWidgetX.SetLookupTable( self.lut )
#        self.planeWidgetX.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 0 ) )
#        self.planeWidgetX.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
#        self.planeWidgetX.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 0 ) )
#        self.planeWidgetX.PlaceWidget(  bounds  )
#   
#
##        if bounds[0] < 0.0: self.planeWidgetX.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
##        self.planeWidgetX.SetOrigin( self.input().GetOrigin() )
##        self.planeWidgetX.AddObserver( 'AnyEvent', self.TestObserver )
#                
#        self.planeWidgetY = vtk.vtkImagePlaneWidget()
#        self.planeWidgetY.DisplayTextOff()
#        self.planeWidgetY.SetInput( self.input() )
#        self.planeWidgetY.SetPlaneOrientationToYAxes()
#        self.planeWidgetY.SetUserControlledLookupTable(1)
#        self.planeWidgetY.SetSliceIndex( self.slicePosition[1] )
#        self.planeWidgetY.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        self.planeWidgetY.SetPicker(picker)
#        self.planeWidgetY.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 1 ) )
#        self.planeWidgetY.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 1 ) )
#        self.planeWidgetY.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 1 ) )
##        self.planeWidgetY.AddObserver( 'AnyEvent', self.TestObserver )
#        prop2 = self.planeWidgetY.GetPlaneProperty()
#        prop2.SetColor(1, 1, 0)
##        if bounds[0] < 0.0: self.planeWidgetY.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
#        self.planeWidgetY.PlaceWidget(  bounds  )        
#        self.planeWidgetY.SetUserControlledLookupTable(1)
#        self.planeWidgetY.SetLookupTable( self.lut )
#        
#        self.planeWidgetZ = vtk.vtkImagePlaneWidget()
#        self.planeWidgetZ.DisplayTextOff()
#        self.planeWidgetZ.SetInput( self.input() )
#        self.planeWidgetZ.SetPlaneOrientationToZAxes()
#        self.planeWidgetZ.SetSliceIndex( self.slicePosition[2] )
#        self.planeWidgetZ.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        self.planeWidgetZ.SetPicker(picker)
#        self.planeWidgetZ.AddObserver( 'EndInteractionEvent', callbackWrapper( self.SliceObserver, 2 ) )
#        self.planeWidgetZ.AddObserver( 'InteractionEvent', callbackWrapper( self.PickObserver, 2 ) )
#        self.planeWidgetZ.AddObserver( 'StartInteractionEvent', callbackWrapper( self.PickObserver, 2 ) )
##        self.planeWidgetZ.AddObserver( 'AnyEvent', self.TestObserver )
#        self.planeWidgetZ.AddObserver( 'LeftButtonPressEvent', self.onSlicerLeftButtonPress )
#        self.planeWidgetZ.AddObserver( 'RightButtonPressEvent', self.onSlicerRightButtonPress )
#                
#        prop3 = self.planeWidgetZ.GetPlaneProperty()
#        prop3.SetColor(0, 0, 1)
##        if bounds[0] < 0.0: self.planeWidgetZ.GetProp3D().AddPosition ( 360.0, 0.0, 0.0 )
#        self.planeWidgetZ.PlaceWidget( bounds )
#
#        self.planeWidgetZ.SetUserControlledLookupTable(1)
#        self.planeWidgetZ.SetLookupTable( self.lut )
#        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
#        self.updateOpacity() 
##        self.imageRescale = vtk.vtkImageReslice() 
##        self.imageRescale.SetOutputDimensionality(2) 
##        self.imageRescale.SetInterpolationModeToLinear() 
##        self.imageRescale.SetResliceAxesDirectionCosines( [-1, 0, 0], [0, -1, 0], [0, 0, -1] )
#
##        self.set2DOutput( port=self.imageRescale.GetOutputPort(), name='slice' ) 
#        self.set3DOutput() 

#    def SliceObserver(self, index, caller, event ):
#        iS = caller.GetSliceIndex()
#        self.slicePosition[index] = iS
#        print "Volume Slicer[%d], set slice index = %d" % ( index, iS )

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
         
#    def updateModule1(self):
#        self.transferInputLayer( self.sliceInput ) 
#        self.SliceObserver( self.planeWidgetZ ) 

#    def applyConfiguration( self ):
#        PersistentVisualizationModule.applyConfiguration( self )
#        self.planeWidgetX.SetSliceIndex( self.slicePosition[0] ) 
#        self.planeWidgetY.SetSliceIndex( self.slicePosition[1] )
#        self.planeWidgetZ.SetSliceIndex( self.slicePosition[2] )
                
    def updateModule(self, **args ):
        contour_ispec = self.getInputSpec(  1 )       
        contourInput = contour_ispec.input if contour_ispec <> None else None
        self.planeWidgetX.SetInput( self.input(), contourInput )         
        self.planeWidgetY.SetInput( self.input(), contourInput )         
        self.planeWidgetZ.SetInput( self.input(), contourInput ) 
        self.planeWidgetX.SetSliceIndex( self.slicePosition[0] ) 
        self.planeWidgetY.SetSliceIndex( self.slicePosition[1] )
        self.planeWidgetZ.SetSliceIndex( self.slicePosition[2] )
        self.set3DOutput()

#        print " Volume Slicer: updateModule, cachable: %s " % str( self.is_cacheable() )
#        print " ******** Input extent: %s, origin: %s, spacing: %s " % ( self.input().GetExtent(), self.input().GetOrigin(), self.input().GetSpacing() )
        p1 = self.planeWidgetX.GetPoint1()
#        print " >++++++++++++++++++> UpdateModule: sliceIndex0 = %d, xpos = %.2f " % ( self.slicePosition[0], p1[0] )

#        na1 = self.input().GetPointData().GetNumberOfArrays()
#        self.setActiveScalars()
#        na2 = self.input().GetPointData().GetNumberOfArrays()
#        self.SliceObserver( 2, self.planeWidgetZ )
        
#        if not self.updatingPlacement:
#            self.UpdateWidgetPlacement()
           
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
                image_value = caller.GetCurrentImageValue() 
                cpos = caller.GetCurrentCursorPosition()     
                dataValue = self.getDataValue( image_value )
                wpos = ispec.getWorldCoords( cpos )
                if self.generateContours:
                    contour_image_value = caller.GetCurrentImageValue2() 
                    contour_value = self.getDataValue( contour_image_value, 1 )
                    contour_units = self.getUnits(1)
                    textDisplay = " Position: (%s, %s, %s), Value: %.3G %s, Contour Value: %.3G %s" % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units, contour_value, contour_units )
                else:
                    textDisplay = " Position: (%s, %s, %s), Value: %.3G %s." % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units )
                sliceIndex = caller.GetSliceIndex() 
                self.slicePosition[iAxis] = sliceIndex
                self.updateTextDisplay( textDisplay )
                
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
                pos1 = caller.GetPoint1()
                pos2 = caller.GetPoint2()
                origin = caller.GetOrigin()
                contourLineActor = self.getContourActor( iAxis )
                contourLineActor.SetPosition( origin[0], origin[1], origin[2] )
#                contourLineActor.SetOrigin( origin[0] + 0.1, origin[1] + 0.1, origin[2] + 0.1 )
                self.setVisibleContour( iAxis )
                
            self.render()
#                print " Generate Contours, data dims = %s, pos = %s %s %s " % ( str( slice_data.GetDimensions() ), str(pos1), str(pos2), str(origin) )

    def getContourActor( self, iAxis, **args ):
        contourLineActor = self.contourLineActors.get( iAxis, None )
        if contourLineActor == None:
            contourLineActor = vtk.vtkActor()
            contourLineActor.SetMapper(self.contourLineMapperer)
            contourLineActor.GetProperty().SetLineWidth(2)     
            self.renderer.AddActor( contourLineActor ) 
            self.contourLineActors[iAxis] = contourLineActor
#            print " GetContourActor %d, origin = %s, position = %s " % ( iAxis, str( contourLineActor.GetOrigin() ), str( contourLineActor.GetPosition() ) )
            if iAxis == 1: 
                contourLineActor.SetOrientation(90,0,0)
            elif iAxis == 0: 
                contourLineActor.SetOrientation(90,0,90)                              
        return contourLineActor

#    def createColorBarActor(self):
#        PersistentVisualizationModule.createColorBarActor( self )
#        self.createContourColorBarActor()
#
#    def createContourColorBarActor( self ):
#        if self.contourColorBarActor == None:
#            self.contourColormapManager = ColorMapManager( self.contour_lut ) 
#            self.contourColorBarActor = vtk.vtkScalarBarActor()
#            self.contourColorBarActor.SetMaximumWidthInPixels( 50 )
#            self.contourColorBarActor.SetNumberOfLabels(9)
#            labelFormat = vtk.vtkTextProperty()
#            labelFormat.SetFontSize( 160 )
#            labelFormat.SetColor(  VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2] ) 
#            titleFormat = vtk.vtkTextProperty()
#            titleFormat.SetFontSize( 160 )
#            titleFormat.SetColor(  VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2]  ) 
#            self.contourColorBarActor.SetPosition( 0.02, 0.2 )    
#            self.contourColorBarActor.SetLabelTextProperty( labelFormat )
#            self.contourColorBarActor.SetTitleTextProperty( titleFormat )
#            self.contourColorBarActor.SetTitle( self.contour_units )
#            self.contourColorBarActor.SetLookupTable( self.contourColormapManager.getDisplayLookupTable() )
#            self.contourColorBarActor.SetVisibility(0)
#            self.renderer.AddActor( self.contourColorBarActor )
#        else:
#            if self.contourColorBarActor == None:
#                self.contour_lut = self.contourColorBarActor.GetLookupTable()
#                self.contourColorBarActor = ColorMapManager( self.contour_lut ) 
#            else:
#                self.contourColorBarActor.SetLookupTable( self.contourColormapManager.getDisplayLookupTable() )
#                self.contourColorBarActor.Modified()
            
    def setVisibleContour( self, iAxis ):
        for contourLineActorItem in self.contourLineActors.items():
            if iAxis == contourLineActorItem[0]:    contourLineActorItem[1].VisibilityOn( )
            else:                                   contourLineActorItem[1].VisibilityOff( )

                    
#    def getSlice( self, iAxis ):
#        import api
#        self.iOrientation = caller.GetPlaneOrientation()
#        resliceOutput = caller.GetResliceOutput()
#        resliceOutput.Update()
#        self.imageRescale.RemoveAllInputs()
#        sliceIndex = caller.GetSliceIndex() 
##        print " Slice Orientation: %s " % self.iOrientation
#        if self.iOrientation == 0: self.imageRescale.SetResliceAxesDirectionCosines( [ 1, 0, 0], [0, -1, 0], [0, 0, -1] )
#        if self.iOrientation == 1: self.imageRescale.SetResliceAxesDirectionCosines( [ 0, 1, 0], [ -1, 0, 0], [0, 0,  1] )
#        if self.iOrientation == 2: self.imageRescale.SetResliceAxesDirectionCosines( [ 1, 0, 0], [0, -1, 0], [0, 0, -1] )
#        output_slice_extent = self.getAdjustedSliceExtent()
#        self.imageRescale.SetOutputExtent( output_slice_extent )
#        output_slice_spacing = self.getAdjustedSliceSpacing( resliceOutput )
#        self.imageRescale.SetOutputSpacing( output_slice_spacing )
#        self.imageRescale.SetInput( resliceOutput )
#        self.updateSliceOutput()
#        self.endInteraction()
#        HyperwallManager.getInstance().setInteractionState( None )
#        self.isSlicing = False
#        
#        active_irens = self.getActiveIrens()        
#        for module in VolumeSlicerModules.values():
#            if module.iren in active_irens:
#                if   (iAxis == 0) and module.planeWidgetX: module.planeWidgetX.SetSliceIndex( sliceIndex )
#                elif (iAxis == 1) and module.planeWidgetY: module.planeWidgetY.SetSliceIndex( sliceIndex )
#                elif (iAxis == 2) and module.planeWidgetZ: module.planeWidgetZ.SetSliceIndex( sliceIndex )
#                  
#        
#    def updateSliceOutput(self):
#        sliceOutput = self.imageRescale.GetOutput()
#        sliceOutput.Update()
#        self.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } )
#        self.set2DOutput( name='slice', output=sliceOutput )
#        sliceOutput.InvokeEvent("RenderEvent")
#        self.refreshCells()
##        imageWriter = vtk.vtkJPEGWriter()
##        imageWriter.SetFileName ("~/sliceImage.jpg")
##        imageWriter.SetInput( sliceOutput )
##        imageWriter.Write()    
##        print " Slice Output: extent: %s, spacing: %s " % ( str( sliceOutput.GetExtent() ), str( sliceOutput.GetSpacing() ) )

       
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
                
#    def activateWidgets( self, iren ):    
#        self.planeWidgetX.SetInteractor( iren )
#        self.planeWidgetX.On()
#        self.planeWidgetY.SetInteractor( iren )
#        self.planeWidgetY.On() 
#        self.planeWidgetZ.SetInteractor( iren )     
#        self.planeWidgetZ.On() 
#        print "Initial Camera Position = %s\n Origins: " % str( self.renderer.GetActiveCamera().GetPosition() )
#        for widget in [ self.planeWidgetX, self.planeWidgetY, self.planeWidgetZ ]: 
#            print " slice-%d: %s %s %s %s " % ( widget.GetPlaneOrientation(), str( widget.GetOrigin() ), str( widget.GetPoint1 () ), str( widget.GetPoint2 () ), str( widget.GetCenter() ) )
       
    def initColorScale( self, caller, event ): 
        x, y = caller.GetEventPosition()
        self.ColorLeveler.startWindowLevel( x, y )

    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        ispec = self.inputSpecs[ cmap_index ]
        if ispec and ispec.input: 
            imageRange = self.getImageValues( ctf_data[0:2], cmap_index ) 
            colormapManager = self.getColormapManager( index=cmap_index )
            colormapManager.setScale( imageRange, ctf_data )
            if self.contourLineMapperer: 
                self.contourLineMapperer.Modified()
            ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } )
    #        print " Volume Slicer[%d]: Scale Colormap: [ %d, %d ] ( %.2g, %.2g ) " % ( self.moduleID, int(self.imageRange[0]), int(self.imageRange[1]), ctf_data[0], ctf_data[1] )
                
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
        if ( key == 'x' ): 
            self.planeWidgetX.SetPlaneOrientationToXAxes() 
            self.planeWidgetX.SetSliceIndex( 0 ) #self.slicePosition[0] )
            self.render()      
        elif ( key == 'y' ):  
            self.planeWidgetY.SetPlaneOrientationToYAxes()
            self.planeWidgetY.SetSliceIndex( 0 ) #self.slicePosition[1] )
            self.render()       
        elif ( key == 'z' ):  
            self.planeWidgetZ.SetPlaneOrientationToZAxes()
            self.planeWidgetZ.SetSliceIndex( 0 ) #self.slicePosition[2] )
            self.render() 
             
              
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

