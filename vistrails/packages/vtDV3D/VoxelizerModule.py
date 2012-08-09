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
import numpy as np
# from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.vtUtilities import *

class VtkPointCloud:

    def __init__( self, maxNumPoints=1e6 ):
        self.maxNumPoints = maxNumPoints
        self.vtkPolyData = vtk.vtkPolyData()
        self.clearPoints()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInput(self.vtkPolyData)
#        mapper.SetColorModeToDefault()
#        mapper.SetScalarRange(zMin, zMax)
#        mapper.SetScalarVisibility(1)
        self.vtkActor = vtk.vtkActor()
        self.vtkActor.SetMapper(mapper)

    def setPoints( self, point_data ):
        self.vtkPoints.SetData( point_data )
        ncells = point_data.GetNumberOfTuples()
        cells = vtk.vtkIdTypeArray()
        cell_data_array = np.empty( 2*ncells, dtype=np.int64 )  
        cell_data_array[1:2*ncells:2] = range( ncells )
        cell_data_array[0:2*ncells:2] = 1
        cells.SetVoidArray( cell_data_array, 2*ncells, 1 )
        print " Cell Data:\n %s " % str( [ cells.GetValue(iCell) for iCell in range(cells.GetNumberOfTuples())]  )
        self.vtkCells.SetCells ( ncells, cells )
        self.vtkCells.Modified()
        self.vtkPoints.Modified()
#        self.vtkDepth.Modified()

    def clearPoints(self):
        self.vtkPoints = vtk.vtkPoints()
        self.vtkCells = vtk.vtkCellArray()
#        self.vtkDepth = vtk.vtkDoubleArray()
#        self.vtkDepth.SetName('DepthArray')
        self.vtkPolyData.SetPoints(self.vtkPoints)
        self.vtkPolyData.SetVerts(self.vtkCells)
#        self.vtkPolyData.GetPointData().SetScalars(self.vtkDepth)
#        self.vtkPolyData.GetPointData().SetActiveScalars('DepthArray')

    def dbgprint(self):
        pts = [ self.vtkPoints.GetPoint(iPt) for iPt in range(10) ]
        cellList = []
        for iPt in range(10):
            cellIds = vtk.vtkIdList()
            self.vtkCells.GetCell( iPt, cellIds )
            cellList.append( [ cellIds.GetId(iCell) for iCell in range(cellIds.GetNumberOfIds())] )
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
        self.sampleRate = [ 10, 10, 10 ] 
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
        for iC in range(-1,3): print "Value Range %d: %s " % ( iC, str( vectorsArray.GetRange( iC ) ) )
        for iV in range(10): print "Value[%d]: %s " % ( iV, str( vectorsArray.GetTuple3( iV ) ) )
        
        self.initialOrigin = self.input.GetOrigin()
        self.initialExtent = self.input.GetExtent()
        self.initialSpacing = self.input.GetSpacing()
        self.dataBounds = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing, self.initialOrigin ) 
        dataExtents = ( (self.dataBounds[1]-self.dataBounds[0])/2.0, (self.dataBounds[3]-self.dataBounds[2])/2.0, (self.dataBounds[5]-self.dataBounds[4])/2.0 )
        centroid = ( (self.dataBounds[0]+self.dataBounds[1])/2.0, (self.dataBounds[2]+self.dataBounds[3])/2.0, (self.dataBounds[4]+self.dataBounds[5])/2.0  )
        self.pos = [ self.initialSpacing[i]*self.initialExtent[2*i] for i in range(3) ]
        if ( (self.initialOrigin[0] + self.pos[0]) < 0.0): self.pos[0] = self.pos[0] + 360.0

        self.resample = vtk.vtkExtractVOI()
        self.resample.SetInput( self.input ) 
        self.resample.SetVOI( self.initialExtent )
        sRate = [ int( round( self.sampleRate[0] )  ), int( round( self.sampleRate[1] ) ), int( round( self.sampleRate[2] ) )  ]
        print "Sample rate: %s " % str( sRate )
        self.resample.SetSampleRate( sRate[0], sRate[1], sRate[2] )

        self.resampled_data = self.resample.GetOutput()
        self.resampled_data.Update()        
        point_data = self.resampled_data.GetPointData() 
        field_data = self.resampled_data.GetFieldData()
        input_variable_data = point_data.GetVectors()
        nComp = input_variable_data.GetNumberOfComponents()
        nTup = input_variable_data.GetNumberOfTuples()
        print "-- Got input data points: nComp=%d, nTup=%d" % ( nComp, nTup ) 
#        for iComp in range(nComp):
#            cName = vtkdata.GetComponentName( iComp )        
#        variable_point_data = vtk.vtkFloatArray() 
        variable_point_data = input_variable_data

        self.pointCloud = VtkPointCloud()
        self.pointCloud.setPoints( variable_point_data )
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
        
            
