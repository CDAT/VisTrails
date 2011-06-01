'''
Created on Jan 24, 2011

@author: tpmaxwel
'''


import vtk
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from packages.vtk.base_module import vtkBaseModule
from ColorMapManager import ColorMapManager 
from InteractiveConfiguration import QtWindowLeveler 
from PersistentModule import * 
from vtUtilities import *
        
class PM_VectorCutPlane(PersistentVisualizationModule):
    """Takes an arbitrary slice of the input data using an implicit cut
    plane and places glyphs according to the vector field data.  The
    glyphs may be colored using either the vector magnitude or the scalar
    attributes.
    """    
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.glyphScale = 15.0 
        self.glyphDecimationFactor = 2.0 
        self.primaryInputPort = 'vector'
        self.addConfigurableLevelingFunction( 'colorScale', 'C', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True )
        self.addConfigurableLevelingFunction( 'glyphRange', 'T', setLevel=self.setGlyphRange, getLevel=self.getDataRangeBounds, layerDependent=True )
        self.addConfigurableLevelingFunction( 'glyphScale', 'G', setLevel=self.setGlyphScale, getLevel=self.getGlyphScale, layerDependent=True )
      
    def scaleColormap( self, ctf_data ):
        print " PM_VectorCutPlane-> Scale Colormap: range = %s " % str( ctf_data )
        self.lut.SetTableRange( ctf_data[0], ctf_data[1] ) 
        self.addMetadata( { 'colormap' : self.getColormapSpec() } )
        self.glyphMapper.Modified()
        self.glyph.Update()
        self.glyphMapper.Update()
        self.render()

    def setGlyphRange( self, ctf_data ):
        self.glyph.SetRange ( ctf_data[0], ctf_data[1] )
        self.glyph.Update()
        self.render()

    def setGlyphScale( self, ctf_data ):
        self.glyphDecimationFactor = ctf_data[0] 
        self.glyphScale = ctf_data[1]  
        self.ApplyGlyphDecimationFactor()
        
    def getGlyphScale(self):
        return [ self.glyphDecimationFactor, self.glyphScale ]
                              
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """       
        self.sliceOutput = vtk.vtkImageData()
        self.colorInputModule = self.wmod.forceGetInputFromPort( "colors", None )
        
        if self.input == None: 
            print>>sys.stderr, "Must supply 'volume' port input to VectorCutPlane"
            return
              
        xMin, xMax, yMin, yMax, zMin, zMax = self.input.GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input.GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input.GetOrigin()
        ox, oy, oz = origin
        
        cellData = self.input.GetCellData()  
        pointData = self.input.GetPointData()     
        vectorsArray = pointData.GetVectors()
        
        if vectorsArray == None: 
            print>>sys.stderr, "Must supply point vector data for 'volume' port input to VectorCutPlane"
            return

        self.rangeBounds = list( vectorsArray.GetRange(-1) )
        self.nComponents = vectorsArray.GetNumberOfComponents()
        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
        
        self.plane = vtk.vtkPlane()      

        self.initialOrigin = self.input.GetOrigin()
        self.initialExtent = self.input.GetExtent()
        self.initialSpacing = self.input.GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
        centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
#        self.plane.SetOrigin( centroid[0], centroid[1], centroid[2]   )
#        self.plane.SetNormal( 0.0, 0.0, 1.0 )

        self.resample = vtk.vtkExtractVOI()
        self.resample.SetInput( self.input ) 
        self.resample.SetVOI( self.initialExtent )
        sampleRate = int( round( self.glyphDecimationFactor) )
        self.resample.SetSampleRate( sampleRate, sampleRate, 1 )
        
        if self.colorInputModule <> None:
            colorInput = self.colorInputModule.getOutput()
            self.color_resample = vtk.vtkExtractVOI()
            self.color_resample.SetInput( colorInput ) 
            self.color_resample.SetVOI( self.initialExtent )
            self.color_resample.SetSampleRate( sampleRate, sampleRate, 1 )
#            self.probeFilter = vtk.vtkProbeFilter()
#            self.probeFilter.SetSourceConnection( self.resample.GetOutputPort() )           
#            colorInput = self.colorInputModule.getOutput()
#            self.probeFilter.SetInput( colorInput )
            resampledColorInput = self.color_resample.GetOutput()
            shiftScale = vtk.vtkImageShiftScale()
            shiftScale.SetOutputScalarTypeToFloat ()           
            shiftScale.SetInput( resampledColorInput ) 
            valueRange = self.scalarRange
            shiftScale.SetShift( valueRange[0] )
            shiftScale.SetScale ( (valueRange[1] - valueRange[0]) / 65535 )
            colorFloatInput = shiftScale.GetOutput() 
            colorFloatInput.Update()
            colorInput_pointData = colorFloatInput.GetPointData()     
            self.colorScalars = colorInput_pointData.GetScalars()
            self.colorScalars.SetName('color')
            self.lut.SetTableRange( valueRange ) 
         
        self.cutterInput = self.resample.GetOutput() 
        self.planeWidget = vtk.vtkImplicitPlaneWidget()
        self.planeWidget.SetInput( self.cutterInput  )
#        self.planeWidget.SetInput( self.input  )
        self.planeWidget.DrawPlaneOff()
        self.planeWidget.ScaleEnabledOff()
        self.planeWidget.PlaceWidget( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] )
        self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
        self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
        self.planeWidget.AddObserver( 'InteractionEvent', self.SliceObserver )
        print "Data bounds %s, origin = %s, spacing = %s, extent = %s, widget origin = %s " % ( str( self.dataBounds ), str( self.initialOrigin ), str( self.initialSpacing ), str( self.initialExtent ), str( self.planeWidget.GetOrigin( ) ) )
        self.cutter = vtk.vtkCutter()
        self.cutter.SetInput( self.cutterInput )
#        if self.inputPort <> None: self.cutter.SetInputConnection( self.inputPort  )
#        else: self.cutter.SetInput( self.input  )
        
        self.cutter.SetGenerateCutScalars(0)
        self.glyph = vtk.vtkGlyph3D() 
        if self.colorInputModule <> None:   self.glyph.SetColorModeToColorByScalar()            
        else:                          self.glyph.SetColorModeToColorByVector()          
#        combined_pointData = self.cutterInput.GetPointData()     
#        combined_vectorsArray = combined_pointData.GetVectors()
#        combined_scalarsArray = combined_pointData.GetScalars()

        self.glyph.SetVectorModeToUseVector()
        self.glyph.SetOrient( 1 ) 
        self.glyph.SetRange ( self.rangeBounds[0], self.rangeBounds[1] )
        self.glyph.ClampingOn()
        sliceOutputPort = self.cutter.GetOutputPort()
        self.glyph.SetInputConnection( sliceOutputPort )
        self.arrow = vtk.vtkArrowSource()
        self.glyph.SetSourceConnection( self.arrow.GetOutputPort() )
        self.glyphMapper = vtk.vtkPolyDataMapper()
        self.glyphMapper.SetInputConnection( self.glyph.GetOutputPort() ) 
        self.glyphMapper.SetLookupTable( self.lut )
        self.glyphActor = vtk.vtkActor() 
        self.glyphActor.SetMapper( self.glyphMapper )
        self.renderer.AddActor( self.glyphActor )
        self.planeWidget.GetPlane( self.plane )
        self.UpdateCut()
        self.set3DOutput(wmod=wmod) 
        self.set2DOutput( port=sliceOutputPort, name='slice', wmod = wmod ) 
        
    def ApplyGlyphDecimationFactor(self):
        sampleRate = int( round( self.glyphDecimationFactor) )
        self.resample.SetSampleRate( sampleRate, sampleRate, 1 )
#        spacing = [ self.initialSpacing[i]*self.glyphDecimationFactor for i in range(3) ]
#        extent = [ int( (self.dataBounds[i] - self.initialOrigin[i/2]) / spacing[i/2] ) for i in range( 6 )  ]
#        self.resample.SetOutputExtent( extent )
#        self.resample.SetOutputSpacing( spacing )
#        resampleOutput = self.resample.GetOutput()
#        resampleOutput.Update()
#        ptData = resampleOutput.GetPointData()
#        ptScalars = ptData.GetScalars()
#        np = resampleOutput.GetNumberOfPoints()
#        print " decimated ImageData: npoints= %d, vectors: ncomp=%d, ntup=%d " % ( np, ptScalars.GetNumberOfComponents(), ptScalars.GetNumberOfTuples() )
        
#        ncells = resampleOutput.GetNumberOfCells()
        self.UpdateCut()
    
    def SliceObserver(self, caller, event = None ): 
        caller.GetPlane( self.plane )
        self.UpdateCut()
        
#        import api
#        iOrientation = caller.GetPlaneOrientation()
#        outputData = caller.GetResliceOutput()
#        outputData.Update()
#        self.imageRescale.SetInput( outputData )
#        output_slice_extent = self.getAdjustedSliceExtent( iOrientation )
#        self.imageRescale.SetOutputExtent( output_slice_extent )
#        output_slice_spacing = self.getAdjustedSliceSpacing( iOrientation, outputData )
#        self.imageRescale.SetOutputSpacing( output_slice_spacing )
#        self.updateSliceOutput()
#        print " Slice Output: extent: %s, spacing: %s " % ( str(output_slice_extent), str(output_slice_spacing) )
        
    def UpdateCut(self): 
        print " Cut Plane: origin = %s, normal = %s" % ( str( self.plane.GetOrigin() ), str( self.plane.GetNormal() ) ) 
        self.cutter.SetCutFunction ( self.plane  )
        self.cutterInput.Update()
        if self.colorInputModule <> None:
            pointData = self.cutterInput.GetPointData()
            pointData.AddArray( self.colorScalars ) 
            pointData.SetActiveScalars( 'color' )
        cutterOutput = self.cutter.GetOutput()
        cutterOutput.Update()
        points = cutterOutput.GetPoints()
        if points <> None:
            np = points.GetNumberOfPoints()
            if np > 0:
#                resampleOutput = self.resample.GetOutput()
#                ptData = resampleOutput.GetPointData()
#                print " UpdateCut, Points: %s " % '  '.join( [ str( points.GetPoint(id) ) for id in range(5) ]  )
                pointData = cutterOutput.GetPointData()
                ptScalarsArray = pointData.GetVectors()
                self.glyph.SetScaleFactor( self.glyphScale )
                self.glyph.Update()
                print " UpdateCut: npoints= %d, vectors: ncomp=%d, ntup=%d " % ( np, ptScalarsArray.GetNumberOfComponents(), ptScalarsArray.GetNumberOfTuples() )
                self.render()

    def activateWidgets( self, iren ):
        self.planeWidget.SetInteractor( iren )
        self.planeWidget.SetEnabled( 1 )
        print "Initial Camera Position = %s\n --- Widget Origin = %s " % ( str( self.renderer.GetActiveCamera().GetPosition() ), str( self.planeWidget.GetOrigin() ) )
 
    def getUnscaledWorldExtent( self, extent, spacing, origin ):
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]



from WorkflowModule import WorkflowModule

class VectorCutPlane(WorkflowModule):
    
    PersistentModuleClass = PM_VectorCutPlane
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
            
if __name__ == '__main__':
    from packages.spreadsheet.spreadsheet_config import configuration
    configuration.rowCount=1
    configuration.columnCount=2
    executeVistrail( 'VectorSlicePlaneDemo' ) 
    
        
#        self.planeWidgetX.SetSliceIndex( self.sliceCenter[0] )
#        self.planeWidgetX.SetPicker(picker)
#        self.planeWidgetX.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        prop1 = self.planeWidgetX.GetPlaneProperty()
#        prop1.SetColor(1, 0, 0)
#        self.planeWidgetX.SetLookupTable( self.lut )
#        self.planeWidgetX.AddObserver( 'EndInteractionEvent', self.SliceObserver )
        
        # The 3 image plane widgets are used to probe the dataset.
#        self.planeWidgetX = vtk.vtkImagePlaneWidget()
#        self.planeWidgetX.DisplayTextOn()
#        self.planeWidgetX.SetInput( self.input )
#        self.planeWidgetX.SetPlaneOrientationToXAxes()
#        self.planeWidgetX.SetSliceIndex( self.sliceCenter[0] )
#        self.planeWidgetX.SetPicker(picker)
#        self.planeWidgetX.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        prop1 = self.planeWidgetX.GetPlaneProperty()
#        prop1.SetColor(1, 0, 0)
#        self.planeWidgetX.SetLookupTable( self.lut )
#        self.planeWidgetX.AddObserver( 'EndInteractionEvent', self.SliceObserver )
#                
#        self.planeWidgetY = vtk.vtkImagePlaneWidget()
#        self.planeWidgetY.DisplayTextOn()
#        self.planeWidgetY.SetInput( self.input )
#        self.planeWidgetY.SetPlaneOrientationToYAxes()
#        self.planeWidgetY.SetSliceIndex( self.sliceCenter[1] )
#        self.planeWidgetY.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        self.planeWidgetY.SetPicker(picker)
#        self.planeWidgetY.AddObserver( 'EndInteractionEvent', self.SliceObserver )
#        prop2 = self.planeWidgetY.GetPlaneProperty()
#        prop2.SetColor(1, 1, 0)
#        self.planeWidgetY.SetLookupTable( self.lut )
#        
#        self.planeWidgetZ = vtk.vtkImagePlaneWidget()
#        self.planeWidgetZ.DisplayTextOn()
#        self.planeWidgetZ.SetInput( self.input )
#        self.planeWidgetZ.SetPlaneOrientationToZAxes()
#        self.planeWidgetZ.SetSliceIndex( self.sliceCenter[2] )
#        self.planeWidgetZ.SetRightButtonAction( VTK_SLICE_MOTION_ACTION )
#        self.planeWidgetZ.SetPicker(picker)
#        self.planeWidgetZ.AddObserver( 'EndInteractionEvent', self.SliceObserver )
#        prop3 = self.planeWidgetZ.GetPlaneProperty()
#        prop3.SetColor(0, 0, 1)
#        self.planeWidgetZ.SetLookupTable( self.lut )
#        self.setMarginSize( 0.0 )  
#        self.renderer.SetBackground(0.1, 0.1, 0.2)  
#        self.imageRescale = vtk.vtkImageReslice()     
#        self.SliceObserver( self.planeWidgetZ )
#        self.setOutputPort( self.imageRescale.GetOutputPort(), 'slice' ) 
#               
#    def SliceObserver( self, caller, event = None ):
#        import api
#        iOrientation = caller.GetPlaneOrientation()
#        outputData = caller.GetResliceOutput()
#        outputData.Update()
#        self.imageRescale.SetInput( outputData )
#        output_slice_extent = self.getAdjustedSliceExtent( iOrientation )
#        self.imageRescale.SetOutputExtent( output_slice_extent )
#        output_slice_spacing = self.getAdjustedSliceSpacing( iOrientation, outputData )
#        self.imageRescale.SetOutputSpacing( output_slice_spacing )
#        self.updateSliceOutput()
#        print " Slice Output: extent: %s, spacing: %s " % ( str(output_slice_extent), str(output_slice_spacing) )

## Author: Prabhu Ramachandran <prabhu_r@users.sf.net>
## Copyright (c) 2005, Enthought, Inc.
## License: BSD Style.
#
#
## Enthought library imports.
#from enthought.traits.api import Instance
#from enthought.traits.ui.api import View, Group, Item
#
## Local imports
#from enthought.mayavi.core.pipeline_info import PipelineInfo
#from enthought.mayavi.core.module import Module
#from enthought.mayavi.components.implicit_plane import ImplicitPlane
#from enthought.mayavi.components.cutter import Cutter
#from enthought.mayavi.components.glyph import Glyph
#from enthought.mayavi.components.actor import Actor
#
#
######################################################################
# `VectorCutPlane` class.
######################################################################
#class VectorCutPlane(Module):
#
#    # The version of this class.  Used for persistence.
#    __version__ = 0
#
#    # The implicit plane widget used to place the implicit function.
#    implicit_plane = Instance(ImplicitPlane, allow_none=False,
#                              record=True)
#
#    # The cutter.  Takes a cut of the data on the implicit plane.
#    cutter = Instance(Cutter, allow_none=False, record=True)
#
#    # The Glyph component.
#    glyph = Instance(Glyph, allow_none=False, record=True)
#
#    # The Glyph component.
#    actor = Instance(Actor, allow_none=False, record=True)
#
#    input_info = PipelineInfo(datasets=['any'],
#                              attribute_types=['any'],
#                              attributes=['vectors'])    
#
#    ########################################
#    # View related traits.
#
#    view = View(Group(Item(name='implicit_plane', style='custom'),
#                      label='ImplicitPlane',
#                      show_labels=False),
#                Group(Item(name='glyph', style='custom', resizable=True),
#                      label='Glyph',
#                      show_labels=False),
#                Group(Item(name='actor', style='custom'),
#                      label='Actor',
#                      show_labels=False),
#                )
#
#    ######################################################################
#    # `Module` interface
#    ######################################################################
#    def setup_pipeline(self):
#        """Override this method so that it *creates* the tvtk
#        pipeline.
#
#        This method is invoked when the object is initialized via
#        `__init__`.  Note that at the time this method is called, the
#        tvtk data pipeline will *not* yet be setup.  So upstream data
#        will not be available.  The idea is that you simply create the
#        basic objects and setup those parts of the pipeline not
#        dependent on upstream sources and filters.  You should also
#        set the `actors` attribute up at this point.
#        """
#        # Create the objects and set them up.
#        self.implicit_plane = ImplicitPlane()
#        self.cutter = Cutter()
#        self.glyph = Glyph(module=self,
#                           scale_mode='scale_by_vector',
#                           color_mode='color_by_vector',
#                           show_scale_mode=False)
#        self.glyph.glyph_source.glyph_position='tail'
#        actor = self.actor = Actor()
#        actor.mapper.scalar_visibility = 1
#        actor.property.set(line_width=2, backface_culling=False,
#                           frontface_culling=False)
#
#    def update_pipeline(self):
#        """Override this method so that it *updates* the tvtk pipeline
#        when data upstream is known to have changed.
#
#        This method is invoked (automatically) when any of the inputs
#        sends a `pipeline_changed` event.
#        """
#        mm = self.module_manager
#        if mm is None:
#            return
#        
#        self.implicit_plane.inputs = [mm.source]
#
#        # Set the LUT for the mapper.
#        self._color_mode_changed(self.glyph.color_mode)
#
#        self.pipeline_changed = True
#
#    def update_data(self):
#        """Override this method so that it flushes the vtk pipeline if
#        that is necessary.
#
#        This method is invoked (automatically) when any of the inputs
#        sends a `data_changed` event.
#        """
#        # Just set data_changed, the other components should do the rest.
#        self.data_changed = True
#
#    #####################################################################
#     Non-public traits.
#    #####################################################################
#    def _color_mode_changed(self, value):
#        # This is a listner for the glyph component's color_mode trait
#        # so that the the lut can be changed when the a different
#        # color mode is requested.
#        actor = self.actor
#        if value == 'color_by_scalar': 
#            actor.mapper.scalar_visibility = 1
#            lut_mgr = self.module_manager.scalar_lut_manager
#            actor.set_lut(lut_mgr.lut)
#        elif value == 'color_by_vector':
#            lut_mgr = self.module_manager.vector_lut_manager
#            actor.set_lut(lut_mgr.lut)
#        else:
#            actor.mapper.scalar_visibility = 0            
#
#        self.render()
#
#    def _implicit_plane_changed(self, old, new):
#        cutter = self.cutter
#        if cutter is not None:
#            cutter.cut_function = new.plane
#            cutter.inputs = [new]
#        self._change_components(old, new)
#
#    def _cutter_changed(self, old, new):
#        ip = self.implicit_plane
#        if ip is not None:
#            new.cut_function = ip.plane
#            new.inputs = [ip]
#        g = self.glyph
#        if g is not None:
#            g.inputs = [new]
#        self._change_components(old, new)
#        
#    def _glyph_changed(self, old, new):
#        if old is not None:
#            old.on_trait_change(self._color_mode_changed,
#                                'color_mode',
#                                remove=True)        
#        new.module = self
#        cutter = self.cutter
#        if cutter:
#            new.inputs = [cutter]
#        new.on_trait_change(self._color_mode_changed,
#                            'color_mode')
#        self._change_components(old, new)
#        
#    def _actor_changed(self, old, new):
#        new.scene = self.scene
#        glyph = self.glyph
#        if glyph is not None:
#            new.inputs = [glyph]
#        self._change_components(old, new)
#        
