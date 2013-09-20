'''
Created on Sep 18, 2013

@author: tpmaxwel
'''

import sys
import getopt
import numpy
import numpy.ma as ma
import string
import cdtime
import os.path
import pprint
import copy
import types
import re
import vtk, cdms2, time, random, math
from vtk.util import numpy_support
from packages.serverside_data_processing.multicore_process_executable import ExecutionTarget, MultiQueueExecutable
from packages.PointCloud.PointCollection import PointCollection, PlotType
from multiprocessing import Process, JoinableQueue, Queue
from PyQt4.QtCore import SIGNAL, QObject, QThread

class ExecutionDataPacket:
    POINTS = 0
    INDICES = 1
    VARDATA = 2
    
    def __init__( self, type, data_object  ):
        self.type = type
        self.data = data_object
        self.metadata = {}
        
    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, key):
        return self.metadata.get( key, None )

    def __setitem__(self, key, value):
        self.metadata[key] = value

    def __delitem__(self, key):
        del self.values[key]    

class PointCollectionExecutionTarget:

    def __init__( self, collection_index, ncollections, init_args=None ):
        self.point_collection = PointCollection() 
        self.point_collection.setDataSlice( collection_index, ncollections )
        self.collection_index = collection_index
        self.ncollections = ncollections
        self.init_args = init_args

    def __call__( self, args_queue, result_queue ):
        self.results = result_queue
        self.initialize()
        while True:
            args = list( args_queue.get( True ) )
            self.execute( args )
                
    def initialize( self ):
        self.point_collection.initialize( self.init_args )
        self.point_collection.setDataSlice( self.collection_index, self.ncollections )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.VARDATA, self.point_collection.getVarData() )
        data_packet[ 'vrange' ] = self.point_collection.getVarDataRange()
        self.results.put( data_packet )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.POINTS, self.point_collection.getPoints() )
        self.results.put( data_packet )

    def execute( self, args ):
        self.point_collection.execute( args )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.INDICES, self.point_collection.getPointIndices() )
        self.results.put( data_packet )

class vtkPointCloud(QObject):

    shperical_to_xyz_trans = vtk.vtkSphericalTransform()
    radian_scaling = math.pi / 180.0 

    def __init__( self ):
        QObject.__init__( self )
        self.vardata = None
        self.vrange = None
        self.np_index_seq = None
        self.points = None
        self.pcIndex = -1
        self.arg_queue = Queue() # JoinableQueue() 
        self.result_queue = Queue() # JoinableQueue()
        self.earth_radius = 100.0
        
    def getResults( self, block = False ):
        try:
            result = self.data_queue.get( block )
        except Exception:
            return False         
        if result.type == ExecutionDataPacket.VARDATA:
            self.vardata = result.data 
            self.vrange = result['vrange']
        elif result.type == ExecutionDataPacket.INDICES:
            self.np_index_seq = result.data 
        elif result.type == ExecutionDataPacket.POINTS:
            self.np_points_data = result.data 
        return True
    
    def generateSubset(self, subset_spec, block = False ):
        self.np_index_seq = None
        self.arg_queue.put( subset_spec,  block )
        self.updateVertices()     
        self.emit( SIGNAL('doneSubsetting'), self.pcIndex )
    
    def getData( self, dtype ):
        if dtype == ExecutionDataPacket.VARDATA:
            return self.vardata
        elif dtype == ExecutionDataPacket.INDICES:
            return self.np_index_seq 
        elif dtype == ExecutionDataPacket.POINTS:
            return self.np_points_data 
   
    def updateVertices( self, **args ): 
        vertices = vtk.vtkCellArray()  
        self.waitForData( ExecutionDataPacket.INDICES )
        cell_sizes   = numpy.ones_like( self.np_index_seq )
        np_cell_data = numpy.dstack( ( cell_sizes, self.np_index_seq ) ).flatten()         
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( np_cell_data ) 
        self.vertices.SetCells( cell_sizes.size, self.vtk_cell_data )     
        self.polydata.SetVerts(vertices)
        self.polydata.Modified()
        self.mapper.Modified()
        self.actor.Modified()
        
    def waitForData( self, dtype ):
        while( self.getData( dtype ) == None ):
            self.get_results(True)
                                             
    def updateScalars( self, **args ):
        self.waitForData( ExecutionDataPacket.VARDATA )
        vtk_color_data = numpy_support.numpy_to_vtk( self.vardata ) 
        vtk_color_data.SetName( 'vardata' )       
        self.polydata.GetPointData().SetScalars( vtk_color_data )
        
    def initPoints( self, **args ):
        self.waitForData( ExecutionDataPacket.POINTS )
        vtk_points_data = numpy_support.numpy_to_vtk( self.np_points_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( len( self.np_points_data ) / 3 )     
        self.vtk_planar_points = vtk.vtkPoints()
        self.vtk_planar_points.SetData( vtk_points_data )
        
    def createPolydata( self, **args  ):
        topo = args.get( 'topo', PlotType.Planar )
        self.polydata = vtk.vtkPolyData()
        vtk_pts = self.getPoints( topo )
        self.polydata.SetPoints( vtk_pts )                         
        self.createPointsActor( self.polydata, **args )

    def computeSphericalPoints( self, **args ):
        self.waitForData( ExecutionDataPacket.POINTS )
        point_layout = self.getPointsLayout()
        lon_data = self.np_points_data[0::3]
        lat_data = self.np_points_data[1::3]
        radian_scaling = math.pi / 180.0 
        theta =  ( 90.0 - lat_data ) * radian_scaling
        phi = lon_data * radian_scaling
        if point_layout == PlotType.List:
            r = numpy.empty( lon_data.shape, lon_data.dtype )      
            r.fill(  self.earth_radius )
            np_sp_grid_data = numpy.dstack( ( r, theta, phi ) ).flatten()
            vtk_sp_grid_data = numpy_support.numpy_to_vtk( np_sp_grid_data ) 
        elif point_layout == PlotType.Grid:
            thetaB = theta.reshape( [ theta.shape[0], 1 ] )  
            phiB = phi.reshape( [ 1, phi.shape[0] ] )
            grid_data = numpy.array( [ ( self.earth_radius, t, p ) for (t,p) in numpy.broadcast(thetaB,phiB) ] )
            sp_points_data = grid_data.flatten() 
            vtk_sp_grid_data = numpy_support.numpy_to_vtk( sp_points_data ) 
        size = vtk_sp_grid_data.GetSize()                    
        vtk_sp_grid_data.SetNumberOfComponents( 3 )
        vtk_sp_grid_data.SetNumberOfTuples( size/3 )   
        vtk_sp_grid_points = vtk.vtkPoints()
        vtk_sp_grid_points.SetData( vtk_sp_grid_data )
        self.vtk_spherical_points = vtk.vtkPoints()
        self.shperical_to_xyz_trans.TransformPoints( vtk_sp_grid_points, self.vtk_spherical_points ) 
                
    def createPointsActor( self, polydata, **args ):
        lut = args.get( 'lut', self.create_LUT() )
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetInput( self.polydata ) 
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        if lut: self.mapper.SetLookupTable( lut )                
        self.actor = vtk.vtkActor()
        self.actor.SetMapper( self.mapper )
        if self.vrange: self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
        
    def start_subprocess( self, pcIndex, nPartitions, init_args, **args ):
        self.pcIndex = pcIndex
        exec_target =  PointCollectionExecutionTarget( pcIndex, nPartitions, init_args ) 
        self.process = Process( target=exec_target, args=( self.arg_queue, self.result_queue ) )
        self.process.start()
               
    def terminate(self):
        self.process.terminate()

    def getNumberOfPoints(self): 
        return len( self.np_points_data ) / 3             
    
    def getPoints( self, topo=PlotType.Planar ):
        if topo == PlotType.Spherical:
            if not self.vtk_spherical_points:
                self.computeSphericalPoints()
            return self.vtk_spherical_points
        if topo == PlotType.Planar: 
            if not self.vtk_planar_points: 
                self.initPoints()
            return self.vtk_planar_points
        
    def updatePoints(self):
        self.polydata.SetPoints( self.getPoints() ) 

    @classmethod    
    def getXYZPoint( cls, lon, lat, r = None ):
        theta =  ( 90.0 - lat ) * cls.radian_scaling
        phi = lon * cls.radian_scaling
        spherical_coords = ( r, theta, phi )
        return cls.shperical_to_xyz_trans.TransformDoublePoint( *spherical_coords )

    def setTopo( self, topo, **args ):
        if topo <> self.topo:
            self.topo = topo
            self.clearClipping()
            if self.actor.GetVisibility():
                pts = self.getPoints( **args )
                self.polydata.SetPoints( pts ) 
                return pts
        return None 

    def getPointsLayout( self ):
        return PlotType.getPointsLayout( self.grid )
            
        
    def setVisiblity(self, visibleLevelIndex ):
        isVisible = ( visibleLevelIndex < 0 ) or ( visibleLevelIndex == self.iLevel )
        if isVisible: self.updatePoints()
        self.actor.SetVisibility( isVisible  )
        return isVisible
    
    def isVisible(self):
        return self.actor.GetVisibility()
        
    def getBounds( self, **args ):
        topo = args.get( 'topo', self.topo )
        lev = args.get( 'lev', None )
        if topo == PlotType.Spherical:
            return [ -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius ]
        else:
            b = list( self.grid_bounds )
            if lev:
                lev_bounds = ( lev[0], lev[-1] )
                b[4] = lev_bounds[0] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[1]
                b[5] = lev_bounds[1] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[0]
            elif ( b[4] == b[5] ):
                b[4] = b[4] - 100.0
                b[5] = b[5] + 100.0
            return b
                
    def setClipping( self, clippingPlanes ):
        self.mapper.SetClippingPlanes( clippingPlanes )
        
    def clearClipping( self ):
        self.mapper.RemoveAllClippingPlanes()    

    def setPointSize( self, point_size ):
        self.actor.GetProperty().SetPointSize( point_size )
        
    def getLUT(self):
        return self.mapper.GetLookupTable()
        
    def getPointValue( self, iPt ):
        return self.var_data[ iPt ]

    def create_LUT( self, **args ):
        lut = vtk.vtkLookupTable()
        type = args.get( 'type', "blue-red" )
        invert = args.get( 'invert', False )
        number_of_colors = args.get( 'number_of_colors', 256 )
        alpha_range = 1.0, 1.0
        
        if type=="blue-red":
            if invert:  hue_range = 0.0, 0.6667
            else:       hue_range = 0.6667, 0.0
            saturation_range = 1.0, 1.0
            value_range = 1.0, 1.0
         
        lut.SetHueRange( hue_range )
        lut.SetSaturationRange( saturation_range )
        lut.SetValueRange( value_range )
        lut.SetAlphaRange( alpha_range )
        lut.SetNumberOfTableValues( number_of_colors )
        lut.SetRampToSQRT()            
        lut.Modified()
        lut.ForceBuild()
        return lut   
          
class vtkPointCollection( QObject ):
    
    def __init__( self, nPartitions, init_args  ):
        QObject.__init__( self )
        self.point_clouds = {}
        self.nPartitions = nPartitions
        for pcIndex in range( nPartitions ):
            pc = vtkPointCloud()
            pc.start_subprocess(pcIndex, nPartitions, init_args )
            self.point_clouds[ pcIndex ] = pc
            self.connect( pc, SIGNAL('doneSubsetting'), self.newSubset )
            
    def getActors(self):
        return [ pc.actor for pc in self.point_clouds.values() ]
    
    def generateSubset(self, subset_spec ):
        for pc in self.point_clouds:
            pc.generateSubset( subset_spec )
            
    def newSubset(self, pcIndex ):
        self.emit( SIGNAL('newSubset'), pcIndex )
        
    def getPointCloud(self, pcIndex ):
        return self.point_clouds.get( pcIndex, None )
    
    def values(self):
        return self.point_clouds.values()
        
        
            