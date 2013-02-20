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
from packages.vtDV3D.ColorMapManager import ColorMapManager 
# from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.vtUtilities import *
        
class PM_ScaledVectorCutPlane(PersistentVisualizationModule):
    """Takes an arbitrary slice of the input data using an implicit cut
    plane and places glyphs according to the vector field data.  The
    glyphs may be colored using either the vector magnitude or the scalar
    attributes.
    """    
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.glyphScale = [ 0.0, 2.0 ] 
        self.glyphRange = None
        self.planeWidget = None
        self.glyphDecimationFactor = [ 1.0, 5.0 ] 
        self.primaryInputPorts = [ 'volume' ]
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', units='data', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRangeInput=0 )
        self.addConfigurableLevelingFunction( 'glyphScale', 'ZS', label='Glyph Size', setLevel=self.setGlyphScale, getLevel=self.getGlyphScale, layerDependent=True, bound=False  )
        self.addConfigurableLevelingFunction( 'glyphDensity', 'G', label='Glyph Density', setLevel=self.setGlyphDensity, getLevel=self.getGlyphDensity, layerDependent=True, windowing=False, bound=False  )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setZScale, getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )

    def setZScale( self, zscale_data, **args ):
        if self.setInputZScale( zscale_data ):
            if self.planeWidget <> None:
                bounds = list( self.input().GetBounds() ) 
                self.planeWidget.PlaceWidget(  bounds[0], bounds[1], bounds[2], bounds[3], bounds[4], bounds[5]   )        
                self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
                
    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setScale( ctf_data, ctf_data )
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec() } )
        self.glyph.SetLookupTable( colormapManager.lut )
#        self.glyph.Modified()
#        self.glyph.Update()
        self.render()

    def setGlyphScale( self, ctf_data, **args ):
        self.glyphScale = ctf_data        
        self.glyph.SetScaleFactor( self.glyphScale[1] )
        self.glyph.Update()
        self.render()

    def getGlyphScale( self ):
        return self.glyphScale

    def setGlyphDensity( self, ctf_data, **args ):
        self.glyphDecimationFactor = ctf_data
        self.ApplyGlyphDecimationFactor()
        
    def getGlyphDensity(self):
        return self.glyphDecimationFactor
                              
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """       
        self.sliceOutput = vtk.vtkImageData()
        self.colorInputModule = self.wmod.forceGetInputFromPort( "colors", None )
        
        if self.input() == None: 
            print>>sys.stderr, "Must supply 'volume' port input to VectorCutPlane"
            return
              
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input().GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input().GetOrigin()
        ox, oy, oz = origin
        
        cellData = self.input().GetCellData()  
        pointData = self.input().GetPointData()     
        vectorsArray = pointData.GetVectors()
        
        if vectorsArray == None: 
            print>>sys.stderr, "Must supply point vector data for 'volume' port input to VectorCutPlane"
            return

        self.setRangeBounds(  list( vectorsArray.GetRange(-1) ) )
        self.nComponents = vectorsArray.GetNumberOfComponents()
        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
        
        self.plane = vtk.vtkPlane()      

        self.initialOrigin = self.input().GetOrigin()
        self.initialExtent = self.input().GetExtent()
        self.initialSpacing = self.input().GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
        centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
        self.pos = [ self.initialSpacing[i]*self.initialExtent[2*i] for i in range(3) ]
        if ( (self.initialOrigin[0] + self.pos[0]) < 0.0): self.pos[0] = self.pos[0] + 360.0

#        self.plane.SetOrigin( centroid[0], centroid[1], centroid[2]   )
#        self.plane.SetNormal( 0.0, 0.0, 1.0 )

        self.resample = vtk.vtkExtractVOI()
        self.resample.SetInput( self.input() ) 
        self.resample.SetVOI( self.initialExtent )
        lut = self.getLut()
       
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
            valueRange = self.getScalarRange()
            shiftScale.SetShift( valueRange[0] )
            shiftScale.SetScale ( (valueRange[1] - valueRange[0]) / 65535 )
            colorFloatInput = shiftScale.GetOutput() 
            colorFloatInput.Update()
            colorInput_pointData = colorFloatInput.GetPointData()     
            self.colorScalars = colorInput_pointData.GetScalars()
            self.colorScalars.SetName('color')
            lut.SetTableRange( valueRange ) 
         
        self.cutterInput = self.resample.GetOutput() 
        self.planeWidget = vtk.vtkImplicitPlaneWidget()
        self.planeWidget.SetInput( self.cutterInput  )
#        self.planeWidget.SetInput( self.input()  )
        self.planeWidget.DrawPlaneOff()
        self.planeWidget.ScaleEnabledOff()
        self.planeWidget.PlaceWidget( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] )
        self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
        self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
        self.planeWidget.AddObserver( 'InteractionEvent', self.SliceObserver )
#        print "Data bounds %s, origin = %s, spacing = %s, extent = %s, widget origin = %s " % ( str( self.dataBounds ), str( self.initialOrigin ), str( self.initialSpacing ), str( self.initialExtent ), str( self.planeWidget.GetOrigin( ) ) )
        self.cutter = vtk.vtkCutter()
        self.cutter.SetInput( self.cutterInput )
        
        self.cutter.SetGenerateCutScalars(0)
        self.glyph = vtk.vtkGlyph3DMapper() 
#        if self.colorInputModule <> None:   self.glyph.SetColorModeToColorByScalar()            
#        else:                               self.glyph.SetColorModeToColorByVector()          

#        self.glyph.SetIndexModeToVector()
        
        self.glyph.SetScaleModeToScaleByMagnitude()
        self.glyph.SetColorModeToMapScalars()     
        self.glyph.SetUseLookupTableScalarRange(1)
        self.glyph.SetOrient( 1 ) 
#        self.glyph.ClampingOn()
        self.glyph.ClampingOff()
        sliceOutputPort = self.cutter.GetOutputPort()
        self.glyph.SetInputConnection( sliceOutputPort )
        self.arrow = vtk.vtkArrowSource()
        self.arrow.SetTipResolution(3)
        self.arrow.SetShaftResolution(3)
        self.glyph.SetSourceConnection( self.arrow.GetOutputPort() )
        self.glyph.SetLookupTable( lut )
        self.glyphActor = vtk.vtkActor() 
        self.glyphActor.SetMapper( self.glyph )
        self.renderer.AddActor( self.glyphActor )
        self.planeWidget.GetPlane( self.plane )
        self.ApplyGlyphDecimationFactor()
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.set3DOutput(wmod=self.wmod) 
#        self.set2DOutput( port=sliceOutputPort, name='slice', wmod = self.wmod ) 

#        self.cutter.SetGenerateCutScalars(0)
#        self.glyph = vtk.vtkGlyph3D() 
#        if self.colorInputModule <> None:   self.glyph.SetColorModeToColorByScalar()            
#        else:                               self.glyph.SetColorModeToColorByVector()          
#
#        self.glyph.SetVectorModeToUseVector()
#        self.glyph.SetOrient( 1 ) 
#        self.glyph.ClampingOn()
#        sliceOutputPort = self.cutter.GetOutputPort()
#        self.glyph.SetInputConnection( sliceOutputPort )
#        self.arrow = vtk.vtkArrowSource()
#        self.glyph.SetSourceConnection( self.arrow.GetOutputPort() )
#        self.glyphMapper = vtk.vtkPolyDataMapper()
#        self.glyphMapper.SetInputConnection( self.glyph.GetOutputPort() ) 
#        self.glyphMapper.SetLookupTable( self.lut )
#        self.glyphActor = vtk.vtkActor() 
#        self.glyphActor.SetMapper( self.glyphMapper )
#        self.renderer.AddActor( self.glyphActor )
#        self.planeWidget.GetPlane( self.plane )
#        self.UpdateCut()
#        self.set3DOutput(wmod=self.wmod) 
#        self.set2DOutput( port=sliceOutputPort, name='slice', wmod = self.wmod ) 


    def ApplyGlyphDecimationFactor(self):
        sampleRate = [ int( round( abs( self.glyphDecimationFactor[0] ) )  ), int( round( abs( self.glyphDecimationFactor[1] ) ) )  ]
#        print "Sample rate: %s " % str( sampleRate )
        self.resample.SetSampleRate( sampleRate[0], sampleRate[0], 1 )
        
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
#        print " Cut Plane: origin = %s, normal = %s" % ( str( self.plane.GetOrigin() ), str( self.plane.GetNormal() ) ) 
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
                self.glyph.SetScaleFactor( self.glyphScale[1] )
#                self.dumpData( 'Cut Vector Values',  ptScalarsArray )
                self.glyph.Update()
#                print " UpdateCut: npoints= %d, vectors: ncomp=%d, ntup=%d " % ( np, ptScalarsArray.GetNumberOfComponents(), ptScalarsArray.GetNumberOfTuples() )
                self.render()

    def dumpData( self, label, dataArray ):
        nt = dataArray.GetNumberOfTuples()
        valArray = []
        for iT in range( 0, nt ):
            val = dataArray.GetTuple3(  iT  )
            valArray.append( "(%.3g,%.3g,%.3g)" % ( val[0], val[1], val[2] )  )
        print " _________________________ %s _________________________ " % label
        print ' '.join( valArray )      
#        for iRow in range(0,iSize[1]):
#            print str( newDataArray[ iOff[0] : iOff[0]+iSize[0], iOff[1]+iRow, 0 ] )

    def activateWidgets( self, iren ):
        self.planeWidget.SetInteractor( iren )
        self.planeWidget.SetEnabled( 1 )
        print "Initial Camera Position = %s\n --- Widget Origin = %s " % ( str( self.renderer.GetActiveCamera().GetPosition() ), str( self.planeWidget.GetOrigin() ) )
 
    def getUnscaledWorldExtent( self, extent, spacing, origin ):
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]


class PM_GlyphArrayCutPlane(PersistentVisualizationModule):
    """Takes an arbitrary slice of the input data using an implicit cut
    plane and places glyphs according to the vector field data.  The
    glyphs may be colored using either the vector magnitude or the scalar
    attributes.
    """    
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.glyphScale = 1.0 
        self.glyphRange = 1.0
        self.glyphDecimationFactor = [ 1.0, 10.0 ] 
        self.glyph = None
        self.useGlyphMapper = True 
        self.planeWidget = None    
        self.primaryInputPorts = [ 'volume' ]
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRangeInput=0, units='data' )
        self.addConfigurableLevelingFunction( 'glyphScale', 'Z', label='Glyph Size', setLevel=self.setGlyphScale, getLevel=self.getGlyphScale, layerDependent=True, windowing=False, bound=False  )
        self.addConfigurableLevelingFunction( 'glyphDensity', 'G', label='Glyph Density', setLevel=self.setGlyphDensity, getLevel=self.getGlyphDensity, layerDependent=True, windowing=False, bound=False  )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setZScale, getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )

    def setZScale( self, zscale_data, **args ):
        if self.setInputZScale( zscale_data ):
            if self.planeWidget <> None:
                self.dataBounds = list( self.input().GetBounds() )
                dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
                self.planeWidget.PlaceWidget( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] )
                centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
                self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
                self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
#                print "PlaceWidget: Data bounds = %s, data extents = %s " % ( str( self.dataBounds ), str( dataExtents ) )  
                                                
    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setScale( ctf_data, ctf_data )
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec() } )
        self.glyphMapper.SetLookupTable( colormapManager.lut )
        self.render()

    def setGlyphScale( self, ctf_data, **args ):
        self.glyphScale = abs( ctf_data[1] )
        self.glyphRange = abs( ctf_data[0] )
        self.updateScaling( True )
        
    def updateScaling( self, render = False ):
        if self.glyph <> None: 
            self.glyph.SetScaleFactor( self.glyphScale ) 
            self.glyph.SetRange( 0.0, self.glyphRange )
        else:
            self.glyphMapper.SetScaleFactor( self.glyphScale ) 
            self.glyphMapper.SetRange( 0.0, self.glyphRange )
        if render:     
            if self.glyph <> None:  self.glyph.Update()
            else:                   self.glyphMapper.Update()
            self.render()

    def getGlyphScale( self ):
        return [ self.glyphRange, self.glyphScale ]

    def setGlyphDensity( self, ctf_data, **args ):
        self.glyphDecimationFactor = ctf_data
        self.ApplyGlyphDecimationFactor()
        
    def getGlyphDensity(self):
        return self.glyphDecimationFactor
                              
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """  
        self.sliceOutput = vtk.vtkImageData()
        self.colorInputModule = self.wmod.forceGetInputFromPort( "colors", None )
        
        if self.input() == None: 
            print>>sys.stderr, "Must supply 'volume' port input to VectorCutPlane"
            return
              
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input().GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input().GetOrigin()
        ox, oy, oz = origin
        
        cellData = self.input().GetCellData()  
        pointData = self.input().GetPointData()     
        vectorsArray = pointData.GetVectors()
        
        if vectorsArray == None: 
            print>>sys.stderr, "Must supply point vector data for 'volume' port input to VectorCutPlane"
            return

        self.setRangeBounds( list( vectorsArray.GetRange(-1) ) )
        self.nComponents = vectorsArray.GetNumberOfComponents()
        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
        
        self.plane = vtk.vtkPlane()      

        self.initialOrigin = self.input().GetOrigin()
        self.initialExtent = self.input().GetExtent()
        self.initialSpacing = self.input().GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
        centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
        self.pos = [ self.initialSpacing[i]*self.initialExtent[2*i] for i in range(3) ]
        if ( (self.initialOrigin[0] + self.pos[0]) < 0.0): self.pos[0] = self.pos[0] + 360.0

#        self.plane.SetOrigin( centroid[0], centroid[1], centroid[2]   )
#        self.plane.SetNormal( 0.0, 0.0, 1.0 )

        self.resample = vtk.vtkExtractVOI()
        self.resample.SetInput( self.input() ) 
        self.resample.SetVOI( self.initialExtent )
        lut = self.getLut()
        
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
            valueRange = self.getScalarRange()
            shiftScale.SetShift( valueRange[0] )
            shiftScale.SetScale ( (valueRange[1] - valueRange[0]) / 65535 )
            colorFloatInput = shiftScale.GetOutput() 
            colorFloatInput.Update()
            colorInput_pointData = colorFloatInput.GetPointData()     
            self.colorScalars = colorInput_pointData.GetScalars()
            self.colorScalars.SetName('color')
            lut.SetTableRange( valueRange ) 
        
        scalarRange = self.getScalarRange() 
        self.glyphRange = max( abs(scalarRange[0]), abs(scalarRange[1]) )
        self.cutterInput = self.resample.GetOutput() 
        self.planeWidget = vtk.vtkImplicitPlaneWidget()
        self.planeWidget.SetInput( self.cutterInput  )
#        self.planeWidget.SetInput( self.input()  )
        self.planeWidget.DrawPlaneOff()
        self.planeWidget.ScaleEnabledOff()
        self.planeWidget.PlaceWidget( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] )
        self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
        self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
        self.planeWidget.AddObserver( 'InteractionEvent', self.SliceObserver )
#        print "Data bounds = %s, Data extents = %s, origin = %s, spacing = %s, extent = %s, widget origin = %s " % ( str( self.dataBounds ), str( dataExtents ), str( self.initialOrigin ), str( self.initialSpacing ), str( self.initialExtent ), str( self.planeWidget.GetOrigin( ) ) )
        self.cutter = vtk.vtkCutter()
        self.cutter.SetInput( self.cutterInput )        
        self.cutter.SetGenerateCutScalars(0)
        sliceOutputPort = self.cutter.GetOutputPort()
        lut.SetVectorModeToMagnitude()
        lut.SetVectorSize(2)
        lut.SetVectorComponent(0)
        
        if self.useGlyphMapper:
            self.glyphMapper = vtk.vtkGlyph3DMapper() 
#            self.glyphMapper.SetScaleModeToScaleByMagnitude()

            self.glyphMapper.SetScaleModeToNoDataScaling()   
            self.glyphMapper.SetUseLookupTableScalarRange(1)
            self.glyphMapper.SetOrient( 1 ) 
            self.glyphMapper.ClampingOff()
            self.glyphMapper.SourceIndexingOn()
            self.glyphMapper.SetInputConnection( sliceOutputPort )
            self.glyphMapper.SetLookupTable( lut )
            self.glyphMapper.ScalarVisibilityOn()            
            self.glyphMapper.SetScalarModeToUsePointFieldData()
            self.glyphMapper.SelectColorArray( vectorsArray.GetName() )

        else:
            self.glyph = vtk.vtkGlyph3D() 
            self.glyph.SetIndexModeToVector()               
            self.glyph.SetScaleModeToDataScalingOff ()
            self.glyph.SetOrient( 1 ) 
            self.glyph.ClampingOff()
            self.glyph.SetInputConnection( sliceOutputPort )

            self.glyphMapper = vtk.vtkPolyDataMapper()
            self.glyphMapper.SetInputConnection( self.glyph.GetOutputPort() )
            self.glyphMapper.SetLookupTable( lut )
            self.glyphMapper.SetColorModeToMapScalars()     
            self.glyphMapper.SetUseLookupTableScalarRange(1)    
                    
        self.createArrowSources()            
        self.updateScaling()
        
        self.glyphActor = vtk.vtkActor()         
        self.glyphActor.SetMapper( self.glyphMapper )
        
        self.renderer.AddActor( self.glyphActor )
        self.planeWidget.GetPlane( self.plane )
        self.ApplyGlyphDecimationFactor()
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.set3DOutput(wmod=self.wmod) 
#        self.set2DOutput( port=sliceOutputPort, name='slice', wmod = self.wmod ) 

    def updateModule(self, **args ):
        self.resample.SetInput( self.input() ) 
        self.cutterInput = self.resample.GetOutput() 
        self.planeWidget.SetInput( self.cutterInput  )
        self.cutter.SetInput( self.cutterInput ) 
        self.cutter.Update()
        self.glyphMapper.Modified()
        self.glyphMapper.Update()
        self.set3DOutput()

    def createArrowSources( self, scaleRange=[ 1.0, 10.0 ], n_sources=10 ):
        trans = vtk.vtkTransform()
        arrowSource = vtk.vtkArrowSource()
        arrowSource.SetTipResolution(3)
        arrowSource.SetShaftResolution(3)
        arrowSource.Update()
        arrow = arrowSource.GetOutput()
        sourcePts = arrow.GetPoints()    
        dScale = ( scaleRange[1] - scaleRange[0] ) / ( n_sources - 1 )
        for iScale in range( n_sources ):
            scale = scaleRange[0] + iScale * dScale
            trans.Identity()
            trans.Scale( scale, 1.0, 1.0 )  
            newPts = vtk.vtkPoints() 
            trans.TransformPoints( sourcePts, newPts )
            scaledArrow = vtk.vtkPolyData()
            scaledArrow.CopyStructure(arrow)
            scaledArrow.SetPoints( newPts )
            if self.useGlyphMapper: self.glyphMapper.SetSource( iScale, scaledArrow )
            else:                   self.glyph.SetSource( iScale, scaledArrow )

#        self.cutter.SetGenerateCutScalars(0)
#        self.glyph = vtk.vtkGlyph3D() 
#        if self.colorInputModule <> None:   self.glyph.SetColorModeToColorByScalar()            
#        else:                               self.glyph.SetColorModeToColorByVector()          
#
#        self.glyph.SetVectorModeToUseVector()
#        self.glyph.SetOrient( 1 ) 
#        self.glyph.ClampingOn()
#        sliceOutputPort = self.cutter.GetOutputPort()
#        self.glyph.SetInputConnection( sliceOutputPort )
#        self.arrow = vtk.vtkArrowSource()
#        self.glyph.SetSourceConnection( self.arrow.GetOutputPort() )
#        self.glyphMapper = vtk.vtkPolyDataMapper()
#        self.glyphMapper.SetInputConnection( self.glyph.GetOutputPort() ) 
#        self.glyphMapper.SetLookupTable( self.lut )
#        self.glyphActor = vtk.vtkActor() 
#        self.glyphActor.SetMapper( self.glyphMapper )
#        self.renderer.AddActor( self.glyphActor )
#        self.planeWidget.GetPlane( self.plane )
#        self.UpdateCut()
#        self.set3DOutput(wmod=self.wmod) 
#        self.set2DOutput( port=sliceOutputPort, name='slice', wmod = self.wmod ) 


    def ApplyGlyphDecimationFactor(self):
        sampleRate = [ int( round( abs( self.glyphDecimationFactor[0] ) )  ), int( round( abs( self.glyphDecimationFactor[1] ) ) )  ]
#        print "Sample rate: %s " % str( sampleRate )
        self.resample.SetSampleRate( sampleRate[0], sampleRate[0], 1 )
        
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
        self.cutter.SetCutFunction ( self.plane  )
        if self.glyph: self.glyph.Update()
        else: self.glyphMapper.Update()
        self.render()
        
        
#        self.cutterInput.Update()
#        if self.colorInputModule <> None:
#            pointData = self.cutterInput.GetPointData()
#            pointData.AddArray( self.colorScalars ) 
#            pointData.SetActiveScalars( 'color' )
#        cutterOutput = self.cutter.GetOutput()
#        cutterOutput.Update()
#        points = cutterOutput.GetPoints()
#        if points <> None:
#            np = points.GetNumberOfPoints()
#            if np > 0:
##                resampleOutput = self.resample.GetOutput()
##                ptData = resampleOutput.GetPointData()
##                print " UpdateCut, Points: %s " % '  '.join( [ str( points.GetPoint(id) ) for id in range(5) ]  )
#                pointData = cutterOutput.GetPointData()
#                ptScalarsArray = pointData.GetVectors()
##                self.glyph.SetScaleFactor( self.glyphScale[1] )
##                self.dumpData( 'Cut Vector Values',  ptScalarsArray )
#                self.glyph.Update()
##                print " UpdateCut: npoints= %d, vectors: ncomp=%d, ntup=%d " % ( np, ptScalarsArray.GetNumberOfComponents(), ptScalarsArray.GetNumberOfTuples() )
#                self.render()

    def dumpData( self, label, dataArray ):
        nt = dataArray.GetNumberOfTuples()
        valArray = []
        for iT in range( 0, nt ):
            val = dataArray.GetTuple3(  iT  )
            valArray.append( "(%.3g,%.3g,%.3g)" % ( val[0], val[1], val[2] )  )
        print " _________________________ %s _________________________ " % label
        print ' '.join( valArray )      
#        for iRow in range(0,iSize[1]):
#            print str( newDataArray[ iOff[0] : iOff[0]+iSize[0], iOff[1]+iRow, 0 ] )

    def activateWidgets( self, iren ):
        self.planeWidget.SetInteractor( iren )
        self.planeWidget.SetEnabled( 1 )
        print "Initial Camera Position = %s\n --- Widget Origin = %s " % ( str( self.renderer.GetActiveCamera().GetPosition() ), str( self.planeWidget.GetOrigin() ) )
 
    def getUnscaledWorldExtent( self, extent, spacing, origin ):
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]


class PM_StreamlineCutPlane(PersistentVisualizationModule):
    """Takes an arbitrary slice of the input data using an implicit cut
    plane and places glyphs according to the vector field data.  The
    glyphs may be colored using either the vector magnitude or the scalar
    attributes.
    """    
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.streamerScale = 10.0 
        self.streamerStepLenth = 0.05
        self.currentLevel = 0
        self.streamerSeedGridSpacing = [ 5.0, 50.0 ] 
        self.minStreamerSeedGridSpacing = [ 1.0, 1.0 ] 
        self.streamer = None
        self.planeWidget = None
        self.primaryInputPorts = [ 'volume' ]
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRangeInput=0, units='data' )
        self.addConfigurableLevelingFunction( 'streamerScale', 'Z', label='Streamer Scale', setLevel=self.setStreamerScale, getLevel=self.getStreamerScale, layerDependent=True, windowing=False, bound=False )
        self.addConfigurableLevelingFunction( 'streamerDensity', 'G', label='Streamer Density', activeBound='max', setLevel=self.setStreamerDensity, initRange=[ 1.0, 10.0, 1 ], getLevel=self.getStreamerDensity, layerDependent=True, windowing=False, bound=False )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', activeBound='max', setLevel=self.setZScale, getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )

    def setZScale( self, zscale_data, **args ):
        if self.setInputZScale( zscale_data ):
            if self.planeWidget <> None:
                self.dataBounds = list( self.input().GetBounds() )
                dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
                self.planeWidget.PlaceWidget( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] )
                centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
                self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
                self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
      
    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setScale( ctf_data, ctf_data )
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec() } )
        self.streamMapper.SetLookupTable( colormapManager.lut )
        self.render()

    def setStreamerScale( self, ctf_data, **args ):
        self.streamerScale = abs( ctf_data[1] )
        self.streamerStepLenth = abs( ctf_data[0] )
        self.updateScaling()
        
    def updateScaling( self ):
        if self.streamer <> None: 
            print "UpdateScaling: ", str( ( self.streamerStepLenth, self.streamerScale ) )
            self.streamer.SetStepLength( self.streamerStepLenth )
            self.streamer.SetMaximumPropagationTime( self.streamerScale ) 

    def getStreamerScale( self ):
        return [ self.streamerStepLenth, self.streamerScale ]

    def setStreamerDensity( self, ctf_data, **args ):
        for i in range(2):
            srVal = abs( ctf_data[i] ) 
            self.streamerSeedGridSpacing[i] = ( self.minStreamerSeedGridSpacing[i] if srVal < self.minStreamerSeedGridSpacing[i] else srVal )           
        self.UpdateCut()
        
    def getStreamerDensity(self):
        return self.streamerSeedGridSpacing
                              
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """       
        self.sliceOutput = vtk.vtkImageData()
        self.colorInputModule = self.wmod.forceGetInputFromPort( "colors", None )
        
        if self.input() == None: 
            print>>sys.stderr, "Must supply 'volume' port input to VectorCutPlane"
            return
              
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input().GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input().GetOrigin()
        ox, oy, oz = origin
        
        cellData = self.input().GetCellData()  
        pointData = self.input().GetPointData()     
        vectorsArray = pointData.GetVectors()
        
        if vectorsArray == None: 
            print>>sys.stderr, "Must supply point vector data for 'volume' port input to VectorCutPlane"
            return

        self.setRangeBounds( list( vectorsArray.GetRange(-1) ) )
        self.nComponents = vectorsArray.GetNumberOfComponents()
        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
        
        self.plane = vtk.vtkPlane()      

        self.initialOrigin = self.input().GetOrigin()
        self.initialExtent = self.input().GetExtent()
        self.initialSpacing = self.input().GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
        centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
        self.pos = [ self.initialSpacing[i]*self.initialExtent[2*i] for i in range(3) ]
        if ( (self.initialOrigin[0] + self.pos[0]) < 0.0): self.pos[0] = self.pos[0] + 360.0
        lut = self.getLut()

#        self.plane.SetOrigin( centroid[0], centroid[1], centroid[2]   )
#        self.plane.SetNormal( 0.0, 0.0, 1.0 )
        
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
            valueRange = self.getScalarRange()
            shiftScale.SetShift( valueRange[0] )
            shiftScale.SetScale ( (valueRange[1] - valueRange[0]) / 65535 )
            colorFloatInput = shiftScale.GetOutput() 
            colorFloatInput.Update()
            colorInput_pointData = colorFloatInput.GetPointData()     
            self.colorScalars = colorInput_pointData.GetScalars()
            self.colorScalars.SetName('color')
            lut.SetTableRange( valueRange ) 
         
        self.planeWidget = vtk.vtkImplicitPlaneWidget()
        self.planeWidget.SetInput( self.input()  )
        self.planeWidget.DrawPlaneOff()
        self.planeWidget.ScaleEnabledOff()
        self.planeWidgetBounds = ( self.dataBounds[0]-dataExtents[0], self.dataBounds[1]+dataExtents[0], self.dataBounds[2]-dataExtents[1], self.dataBounds[3]+dataExtents[1], self.dataBounds[4]-dataExtents[2], self.dataBounds[5]+dataExtents[2] ) 
        self.planeWidget.PlaceWidget( self.planeWidgetBounds )
        self.planeWidget.SetOrigin( centroid[0], centroid[1], centroid[2]  )
        self.planeWidget.SetNormal( ( 0.0, 0.0, 1.0 ) )
        self.planeWidget.AddObserver( 'InteractionEvent', self.SliceObserver )
        normalProperty = self.planeWidget.GetNormalProperty ()
        normalProperty.SetOpacity(0.0)
#        print "Data bounds %s, origin = %s, spacing = %s, extent = %s, widget origin = %s " % ( str( self.dataBounds ), str( self.initialOrigin ), str( self.initialSpacing ), str( self.initialExtent ), str( self.planeWidget.GetOrigin( ) ) )
        
        self.streamer = vtk.vtkStreamLine()
#        self.streamer.SetInputConnection( sliceOutputPort )
        self.streamer.SetInput( self.input() )
        self.streamer.SetIntegrationDirectionToForward ()
        self.streamer.SetEpsilon(1.0e-10)   # Increase this value if integrations go unstable (app hangs)  
        self.streamer.SpeedScalarsOff()
        self.streamer.SetIntegrationStepLength( 0.1 )
        self.streamer.OrientationScalarsOff()
        self.streamer.VorticityOff()
        
        self.streamActor = vtk.vtkActor()         
        self.streamMapper = vtk.vtkPolyDataMapper()
        self.streamMapper.SetInputConnection( self.streamer.GetOutputPort() )
        self.streamMapper.SetLookupTable( lut )
        self.streamMapper.SetColorModeToMapScalars()     
        self.streamMapper.SetUseLookupTableScalarRange(1)
        self.streamActor.SetMapper( self.streamMapper )
        
        self.renderer.AddActor( self.streamActor )
        self.planeWidget.GetPlane( self.plane )
        self.UpdateStreamerSeedGrid()
        self.updateScaling()
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.set3DOutput( wmod=self.wmod, output=self.input() ) 
 
    def updateModule(self, **args ):
        self.planeWidget.SetInput( self.input()  )        
        self.streamer.SetInput( self.input() )
        self.streamer.Modified()
        self.streamer.Update()
        self.set3DOutput()
       
    def getCurentLevel(self):
        planeOrigin = self.plane.GetOrigin()
        gridExtent = self.input().GetExtent()
        height = planeOrigin[2]
        dataBoundsMin = min(self.dataBounds[5],self.dataBounds[4])
        level = ((height-dataBoundsMin)/(self.dataBounds[5]-self.dataBounds[4]))*(gridExtent[5]-gridExtent[4])
        if level > gridExtent[5]: level = gridExtent[5]
        if level < gridExtent[4]: level = gridExtent[4]
        return level

    def UpdateStreamerSeedGrid( self ):
        sampleRate = self.streamerSeedGridSpacing
        currentLevel = self.getCurentLevel()
        sample_source = vtk.vtkImageData()        
        gridSpacing = self.input().GetSpacing()
        gridOrigin = self.input().GetOrigin()
        gridExtent = self.input().GetExtent()
        sourceSpacing = ( gridSpacing[0]*sampleRate[0], gridSpacing[1]*sampleRate[1], gridSpacing[2] )
        sourceExtent = ( int(gridExtent[0]/sampleRate[0])+1, int(gridExtent[1]/sampleRate[0])-1, int(gridExtent[2]/sampleRate[1])+1, int(gridExtent[3]/sampleRate[1])-1, currentLevel, currentLevel )
        sample_source.SetOrigin( gridOrigin[0], gridOrigin[1], gridOrigin[2] )
        sample_source.SetSpacing( sourceSpacing )
        sample_source.SetExtent( sourceExtent )
        self.streamer.SetSource( sample_source )
#        self.Render()
        print " ---- ApplyStreamerSeedGridSpacing:  Sample rate: %s, current Level: %d, sourceSpacing: %s, sourceExtent: %s " % ( str( sampleRate ), currentLevel, str( sourceSpacing ), str(sourceExtent ) )
        sys.stdout.flush()
    
    def SliceObserver(self, caller, event = None ): 
        caller.GetPlane( self.plane )
        self.UpdateCut()
        
    def UpdateCut(self):
        self.UpdateStreamerSeedGrid(  )
        
    def dumpData( self, label, dataArray ):
        nt = dataArray.GetNumberOfTuples()
        valArray = []
        for iT in range( 0, nt ):
            val = dataArray.GetTuple3(  iT  )
            valArray.append( "(%.3g,%.3g,%.3g)" % ( val[0], val[1], val[2] )  )
        print " _________________________ %s _________________________ " % label
        print ' '.join( valArray )      
#        for iRow in range(0,iSize[1]):
#            print str( newDataArray[ iOff[0] : iOff[0]+iSize[0], iOff[1]+iRow, 0 ] )

    def activateWidgets( self, iren ):
        self.planeWidget.SetInteractor( iren )
        self.planeWidget.SetEnabled( 1 )
        print "Initial Camera Position = %s\n --- Widget Origin = %s " % ( str( self.renderer.GetActiveCamera().GetPosition() ), str( self.planeWidget.GetOrigin() ) )
 
    def getUnscaledWorldExtent( self, extent, spacing, origin ):
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]

from packages.vtDV3D.WorkflowModule import WorkflowModule

class GlyphArrayCutPlane(WorkflowModule):
    
    PersistentModuleClass = PM_GlyphArrayCutPlane
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
class StreamlineCutPlane(WorkflowModule):
    
    PersistentModuleClass = PM_StreamlineCutPlane
    
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
#        self.planeWidgetX.SetInput( self.input() )
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
#        self.planeWidgetY.SetInput( self.input() )
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
#        self.planeWidgetZ.SetInput( self.input() )
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
#from enthought.mayavi.components.streamer import streamer
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
#    # The streamer component.
#    streamer = Instance(Glyph, allow_none=False, record=True)
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
