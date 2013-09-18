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

class PointCollectionExecutionTarget(ExecutionTarget):

    def __init__( self, collection_index, ncollections, wait_for_input=False, init_args=None ):
        ExecutionTarget.__init__( self, proc_index, nproc, wait_for_input, init_args )
        self.point_collection = PointCollection() 
        self.point_collection.setDataSlice( collection_index, ncollections )
        
    def initialize( self ):
        self.point_collection.initialize( self.init_args )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.VARDATA, self.point_collection.getVarData() )
        data_packet[ 'vrange' ] = self.point_collection.getVarDataRange()
        self.results.put( data_packet )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.POINTS, self.point_collection.getPoints() )
        self.results.put( data_packet )

    def execute( self, args ):
        self.point_collection.execute( args )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.INDICES, self.point_collection.getPointIndices() )
        self.results.put( data_packet )

class vtkPointCloud():

    def __init__( self, data_queue  ):
        self.data_queue = data_queue
        self.vardata = None
        self.vrange = None
        self.np_index_seq = None
        self.points = None
        
    def get_results( self, block = False ):
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
    
    def updateVertices( self, **args ): 
        vertices = vtk.vtkCellArray()  
        cell_sizes   = numpy.ones_like( np_index_seq )
        np_cell_data = numpy.dstack( ( cell_sizes, self.np_index_seq ) ).flatten()         
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( np_cell_data ) 
        self.vertices.SetCells( cell_sizes.size, self.vtk_cell_data )     
        self.polydata.SetVerts(vertices)
        
    def  updateScalars( self, **args ):
        vtk_color_data = numpy_support.numpy_to_vtk( self.vardata ) 
        vtk_color_data.SetName( 'vardata' )       
        self.polydata.GetPointData().SetScalars( vtk_color_data )
        
    def initPoints( self, **args ):
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
        self.createPointsActor( polydata, **args )

    def computeSphericalPoints( self, **args ):
        point_layout = self.getPointsLayout()
        radian_scaling = math.pi / 180.0 
        theta =  ( 90.0 - self.lat_data ) * radian_scaling
        phi = self.lon_data * radian_scaling
        if point_layout == PlotType.List:
            r = numpy.empty( self.lon_data.shape, self.lon_data.dtype )      
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
        lut = args.get( 'lut', None )
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetInput( self.polydata ) 
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        if lut: self.mapper.SetLookupTable( lut )                
        self.actor = vtk.vtkActor()
        self.actor.SetMapper( mapper )
        if self.vrange: self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 

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