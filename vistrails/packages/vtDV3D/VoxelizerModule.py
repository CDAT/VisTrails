'''
Created on Jan 24, 2011

@author: tpmaxwel
'''


import vtk, random
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from packages.vtk.base_module import vtkBaseModule
from packages.vtDV3D.ColorMapManager import ColorMapManager 
import numpy as np
# from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.vtUtilities import *

class VtkPointCloud:

    def __init__( self, desiredPointSize=0.5, maxNumPoints=1e6 ):
        self.maxNumPoints = maxNumPoints
        self.vtkPolyData = vtk.vtkPolyData()
        self.vtkTransformFilter = vtk.vtkTransformFilter()
        self.vtkTransform = vtk.vtkTransform()
        self.vtkTransformFilter.SetTransform( self.vtkTransform )
        self.vtkTransformFilter.SetInput( self.vtkPolyData )
        self.clearPoints()
        mapper = vtk.vtkPolyDataMapper()
        mapper. SetInput( self.vtkTransformFilter.GetOutput() )
        mapper.SetColorModeToDefault()
        mapper.SetScalarRange( 0.0, 1.0 )
        mapper.SetScalarVisibility(1)
        self.vtkActor = vtk.vtkActor()
        self.vtkActor.SetMapper(mapper)
        property = self.vtkActor.GetProperty()
        property.SetPointSize(desiredPointSize)

    def addPoint(self, point):
        pointId = self.vtkPoints.InsertNextPoint(point[:])
        self.vtkCells.InsertNextCell(1)
        self.vtkColor.InsertNextValue(random.random())
        self.vtkCells.InsertCellPoint(pointId)
        self.vtkCells.Modified()
        self.vtkPoints.Modified()
        self.vtkColor.Modified()
        print " addPoint[%d]: %s " % ( pointId, str(point) )

    def setPoints( self, point_data ):
        self.vtkPoints.SetData( point_data )
        ncells = point_data.GetNumberOfTuples()               
        cells = vtk.vtkIdTypeArray()
        cell_data_array = np.empty( 2*ncells, dtype=np.int64 )  
        cell_data_array[1:2*ncells:2] = range( ncells )
        cell_data_array[0:2*ncells:2] = 1
#        cell_data_array = np.array( range( ncells ), dtype=np.int64 )  
        cells.SetVoidArray( cell_data_array, 2*ncells, 1 )
        self.vtkCells.SetCells ( ncells, cells )
#        self.vtkCells.InsertNextCell( cell )
#        for iCell in range( ncells ):
#            self.vtkCells.InsertNextCell( 1 )
#            self.vtkCells.InsertCellPoint( iCell )
        cellData = self.vtkCells.GetData ()
        print " Cell Data:\n %s " % str( [ cellData.GetValue(iCell) for iCell in range(cellData.GetNumberOfTuples())]  )
        self.vtkCells.Modified()
        self.vtkPoints.Modified()
#        self.vtkDepth.Modified()

    def setScaling(self, xbounds, ybounds, zbounds ):
        t = [ -xbounds[0], -ybounds[0], -zbounds[0] ]
        s = [ 1.0/(xbounds[1]-xbounds[0]), 1.0/(ybounds[1]-ybounds[0]), 1.0/(zbounds[1]-zbounds[0]) ]
        self.vtkTransform.Identity() 
        self.vtkTransform.Translate( t[0], t[1], t[2] )
        self.vtkTransform.Scale( s[0], s[1], s[2] )
        self.vtkTransform.Modified()
        
    def clearPoints(self):
        self.vtkPoints = vtk.vtkPoints()
        self.vtkCells = vtk.vtkCellArray()
        self.vtkColor = vtk.vtkFloatArray()
        self.vtkColor.SetName('ColorArray')
        self.vtkPolyData.SetPoints(self.vtkPoints)
        self.vtkPolyData.SetVerts(self.vtkCells)
        self.vtkPolyData.GetPointData().SetScalars(self.vtkColor)
        self.vtkPolyData.GetPointData().SetActiveScalars('ColorArray')

    def dbgprint(self):
        npts = self.vtkPoints.GetNumberOfPoints ()
        pts = [ self.vtkPoints.GetPoint(iPt) for iPt in range( npts ) ]
        cellList = []
        ncells = self.vtkCells.GetNumberOfCells()
        self.vtkCells.InitTraversal() 
        for iPt in range(npts):
            cellIds = vtk.vtkIdList()
            self.vtkCells.GetNextCell( cellIds )
            nIds = cellIds.GetNumberOfIds()
            id0 = cellIds.GetId(0)
            idList = [ cellIds.GetId(iCell) for iCell in range(nIds) ]
            print " Got cell[%d]: %s " % ( iPt, idList )
            sys.stdout.flush()
            cellList.append( idList )
        print "\n POINT CLOUD SAMPLE ----------------------------------------------------------------------------------------"
        print " Points: %s " % str(pts)
        print " Cells: %s \n  --------------------------------------------------------------------------------------------------" % str(cellList)


        
class PM_Voxelizer(PersistentVisualizationModule):
    """Takes an arbitrary slice of the input data using an implicit cut
    plane and places glyphs according to the vector field data.  The
    glyphs may be colored using either the vector magnitude or the scalar
    attributes.
    """    
    def __init__( self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, **args )
        self.sampleRate = [ 5, 5, 5 ] 
        self.primaryInputPort = 'volume'
        self.addConfigurableLevelingFunction( 'sampleRate', 's', label='Point Sample Rate', setLevel=self.setSampleRate, getLevel=self.getSampleRate, layerDependent=True, bound=False )
      
    def setSampleRate( self, ctf_data ):
        self.sampleRate = ctf_data        
        self.render()

    def getSampleRate( self ):
        return self.sampleRate
                              
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """       
        
        if self.input == None: 
            print>>sys.stderr, "Must supply 'volume' port input to Voxelizer"
            return
              
        xMin, xMax, yMin, yMax, zMin, zMax = self.input.GetWholeExtent()       
        spacing = self.input.GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input.GetOrigin()
        ox, oy, oz = origin
        
        cellData = self.input.GetCellData()  
        pointData = self.input.GetPointData()     
        vectorsArray = pointData.GetVectors()
        
        if vectorsArray == None: 
            print>>sys.stderr, "Must supply point vector data for 'volume' port input to Voxelizer"
            return

        self.rangeBounds = list( vectorsArray.GetRange(-1) )
        self.nComponents = vectorsArray.GetNumberOfComponents()
#        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
#        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        self.initialOrigin = self.input.GetOrigin()
        self.initialExtent = self.input.GetExtent()
        self.initialSpacing = self.input.GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        metadata = self.getMetadata()  

        self.resample = vtk.vtkExtractVOI()
        self.resample.SetInput( self.input ) 
        self.resample.SetVOI( self.initialExtent )
        sRate = [ int( round( self.sampleRate[0] )  ), int( round( self.sampleRate[1] ) ), int( round( self.sampleRate[2] ) )  ]
        print "Sample rate: %s " % str( sRate )
        self.resample.SetSampleRate( sRate[0], sRate[1], sRate[2] )

        self.resampled_data = self.resample.GetOutput()
        self.resampled_data.Update()        
        point_data = self.resampled_data.GetPointData() 
        input_variable_data = point_data.GetVectors()
        nComp = input_variable_data.GetNumberOfComponents()
        nTup = input_variable_data.GetNumberOfTuples()
        print "-- Got input data points: nComp=%d, nTup=%d" % ( nComp, nTup ) 
        for iComp in range(nComp):
            cName = input_variable_data.GetComponentName( iComp )        
            variable_point_data = vtk.vtkFloatArray() 
        variable_point_data = input_variable_data

        self.pointCloud = VtkPointCloud(1.0)
        for iPt in range(nTup):           
            point = variable_point_data.GetTuple( iPt )
            self.pointCloud.addPoint( point )
#        self.pointCloud.setPoints( variable_point_data )
        vars = metadata['vars']
        xbounds = metadata[ 'valueRange-'+vars[0] ]
        ybounds = metadata[ 'valueRange-'+vars[1] ]
        zbounds = metadata[ 'valueRange-'+vars[2] ]
        self.pointCloud.setScaling( xbounds, ybounds, zbounds )
        self.pointCloud.dbgprint()
        self.renderer.AddActor( self.pointCloud.vtkActor )
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] ) 
        self.set3DOutput ( wmod=self.wmod, name="pointcloud" )
        
    def updateModule(self, **args ):
        self.resample.SetInput( self.input ) 
        self.resample.Modified()
        self.resampled_data.Update()
        self.set3DOutput( wmod=self.wmod, name="pointcloud" )
            
    def dumpData( self, label, dataArray ):
        nt = dataArray.GetNumberOfTuples()
        valArray = []
        for iT in range( 0, nt ):
            val = dataArray.GetTuple3(  iT  )
            valArray.append( "(%.3g,%.3g,%.3g)" % ( val[0], val[1], val[2] )  )
        print " _________________________ %s _________________________ " % label
        print ' '.join( valArray )      
 
    def getUnscaledWorldExtent( self, extent, spacing, origin ):
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]

from packages.vtDV3D.WorkflowModule import WorkflowModule

class Voxelizer(WorkflowModule):
    
    PersistentModuleClass = PM_Voxelizer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
            
