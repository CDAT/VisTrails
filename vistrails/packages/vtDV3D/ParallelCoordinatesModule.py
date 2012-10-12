'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, math, vtk.util.numpy_support as VN
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
VolumeSlicerModules = {}
                
class PM_ParallelCoordinateViewer(PersistentVisualizationModule):
    """
        This module generates a 3D Parallel Coordinates plot.
    """
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.addConfigurableLevelingFunction( 'colorScale', 'C', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True )
        self.addConfigurableLevelingFunction( 'range', 'R',    setLevel=self.setRange,    getLevel=self.getDataRangeBounds, layerDependent=True )

#        print " Volume Slicer init, id = %s " % str( id(self) )


    def setRange( self, range_data ):
        pass
                                                  
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """           
        # The 3 image plane widgets are used to probe the dataset.    
        print " Parallel Coordinates buildPipeline, id = %s " % str( id(self) ) 
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.centerPosition = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        dataType = self.input().GetScalarTypeAsString()
        bounds = list(self.input().GetBounds()) 
        origin = self.input().GetOrigin()
        if (dataType <> 'float') and (dataType <> 'double'):
             self.setMaxScalarValue( self.input().GetScalarType() )
        print "Data Type = %s, range = (%f,%f), extent = %s, origin = %s, bounds=%s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], str(self.input().GetWholeExtent()), str(origin), str(bounds) )         


    def updateModule(self, **args ):
        if self.inputModule():
            view = self.generateParallelCoordinatesChart()
            self.setChartDataOutput( view )
            
    def generateParallelCoordinatesChart( self ):
        input = self.inputModule().getOutput() 
        ptData = input.GetPointData()
        narrays = ptData.GetNumberOfArrays()
        arrays = []
        # Create a table with some points in it...
        table = vtk.vtkTable()
        for iArray in range( narrays ):
            table.AddColumn(  ptData.GetArray( iArray ) )                  
        
        # Set up a 2D scene, add an XY chart to it
        view = vtk.vtkContextView()
#        view.SetRenderer( self.renderer )    
#        view.SetRenderWindow( self.renderer.GetRenderWindow() )
        view.GetRenderer().SetBackground(1.0, 1.0, 1.0)
        view.GetRenderWindow().SetSize(600,300)
        
        chart = vtk.vtkChartParallelCoordinates()
        
        brush = vtk.vtkBrush()
        brush.SetColorF (0.1,0.1,0.1)
        chart.SetBackgroundBrush(brush)
        
        # Create a annotation link to access selection in parallel coordinates view
        annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        chart.SetAnnotationLink(annotationLink)
        
        view.GetScene().AddItem(chart)
                
        
        chart.GetPlot(0).SetInput(table)
        
        def selectionCallback(caller, event):
                annSel = annotationLink.GetCurrentSelection()
                if annSel.GetNumberOfNodes() > 0:
                        idxArr = annSel.GetNode(0).GetSelectionList()
                        if idxArr.GetNumberOfTuples() > 0:
                                print VN.vtk_to_numpy(idxArr)
        
        # Set up callback to update 3d render window when selections are changed in 
        #       parallel coordinates view
        annotationLink.AddObserver("AnnotationChangedEvent", selectionCallback)
                
#        view.ResetCamera()
#        view.Render()       
#        view.GetInteractor().Start()
        return view 

    def generateParallelCoordinatesPlot( self ):
        input = self.inputModule().getOutput() 
        ptData = input.GetPointData()
        narrays = ptData.GetNumberOfArrays()
        arrays = []
        # Create a table with some points in it...
        table = vtk.vtkTable()
        for iArray in range( narrays ):
            table.AddColumn(  ptData.GetArray( iArray ) )                  
        
        # Set up a 2D scene, add an XY chart to it
        view = vtk.vtkContextView()
#        view.SetRenderer( self.renderer )    
#        view.SetRenderWindow( self.renderer.GetRenderWindow() )
        view.GetRenderer().SetBackground(1.0, 1.0, 1.0)
        view.GetRenderWindow().SetSize(600,300)
        
        plot = vtk.vtkPlotParallelCoordinates()
        plot.SetInput(table)
                
        view.GetScene().AddItem(plot)
                                
        view.ResetCamera()
        view.Render()       
        # Start interaction event loop
        view.GetInteractor().Start()

    def generateParallelCoordinatesRepresentation( self ):
        input_data = self.inputModule().getOutput() 
        ptData = input_data.GetPointData()
        narrays = ptData.GetNumberOfArrays()                         
 
         # Set up the parallel coordinates Representation to be used in the View
        rep = vtk.vtkParallelCoordinatesRepresentation()
         
        # Plug your reader in here for your own data
        rep.SetInput( input_data )
         
        # List all of the attribute arrays you want plotted in parallel coordinates
        for iArray in range( narrays ):
            aname = ptData.GetArray( iArray ).GetName()
            print " ParallelCoordinates: Processing array ", aname
            rep.SetInputArrayToProcess( 0,0,0,0, aname )
         
        rep.SetUseCurves(0)        # set to 1 to use smooth curves
        rep.SetLineOpacity(0.5)
         
        # Set up the Parallel Coordinates View and hook in the Representation
        view = vtk.vtkParallelCoordinatesView()
        view.SetRepresentation(rep)
         
        # Inspect Mode determines whether your interactions manipulate the axes or select data
        # view.SetInspectMode(0)    # VTK_INSPECT_MANIPULATE_AXES = 0, 
        view.SetInspectMode(1)        # VTK_INSPECT_SELECT_DATA = 1 
         
        # Brush Mode determines the type of interaction you perform to select data
        view.SetBrushModeToLasso()
        # view.SetBrushModeToAngle()
        # view.SetBrushModeToFunction()
        # view.SetBrushModeToAxisThreshold()    # not implemented yet (as of 21 Feb 2010)
         
        # Brush Operator determines how each new selection interaction changes selected lines
        # view.SetBrushOperatorToAdd()
        # view.SetBrushOperatorToSubtract()
        # view.SetBrushOperatorToIntersect()
        view.SetBrushOperatorToReplace()
         
        # Define the callback routine which toggles between "Inspect Modes"
        def ToggleInspectors(obj,event):
            if (view.GetInspectMode() == 0):
                view.SetInspectMode(1)
            else:
                view.SetInspectMode(0)
         
        # Hook up the callback to toggle between inspect modes (manip axes & select data)
        view.GetInteractor().AddObserver("UserEvent", ToggleInspectors)
         
        # Set up render window
        view.GetRenderWindow().SetSize(600,300)
        view.ResetCamera()
        view.Render()
         
        # Start interaction event loop
        view.GetInteractor().Start()
          
    def TestObserver( self, caller=None, event = None ):
        print " TestObserver: event = %s, " % ( event )

          
        
    def initColorScale( self, caller, event ): 
        x, y = caller.GetEventPosition()
        self.ColorLeveler.startWindowLevel( x, y )

    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        self.imageRange = self.getImageValues( ctf_data[0:2], cmap_index ) 
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setScale( self.imageRange, ctf_data )
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec() } )
        
    def finalizeLeveling( self, cmap_index = 0 ):
        isLeveling =  PersistentVisualizationModule.finalizeLeveling( self )
        if isLeveling:
            ispec = self.inputSpecs[ cmap_index ] 
            ispec.addMetadata( { 'colormap' : self.getColormapSpec() } ) 
#            self.updateSliceOutput()

    def initializeConfiguration(self, cmap_index=0):
        PersistentModule.initializeConfiguration(self)
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec() } ) 
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
              
    def onKeyRelease( self, caller, event ):
        pass


class ParallelCoordinateViewer(WorkflowModule):
    
    PersistentModuleClass = PM_ParallelCoordinateViewer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
              
if __name__ == '__main__':
    executeVistrail( 'ParallelCoordinatesDemo' )
    
    
    
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

