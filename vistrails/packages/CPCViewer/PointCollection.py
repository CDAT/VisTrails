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

class PlotType:
    Planar = 0
    Spherical = 1
    List = 0
    Grid = 1
    LevelAliases = [ 'isobaric' ]
    
    @classmethod
    def validCoords( cls, lat, lon ):
        return ( id(lat) <> id(None) ) and ( id(lon) <> id(None) )
    
    @classmethod
    def isLevelAxis( cls, id ):
        if ( id.find('level')  >= 0 ): return True
        if ( id.find('bottom') >= 0 ) and ( id.find('top') >= 0 ): return True
        if id in cls.LevelAliases: return True
        return False    

    @classmethod
    def getPointsLayout( cls, grid ):
        if grid <> None:
            if (grid.__class__.__name__ in ( "RectGrid", "FileRectGrid") ): 
                return cls.Grid
        return cls.List  

class PointCollection():

    def __init__( self ):
        self.iTimeStep = 0
        self.point_data = None
        self.vtk_planar_points = None                                  
        self.cameraOrientation = {}
        self.topo = PlotType.Planar
        self.lon_data = None
        self.lat_data = None 
        self.z_spacing = 1.0 
        self.metadata = {}
        self.istart = 0
        self.istep = 1
       
    def getDataBlock( self ):
        if self.lev == None:
            if len( self.var.shape ) == 2:
                np_var_data_block = self.var[ self.iTimeStep, self.istart::self.istep ].data
            elif len( self.var.shape ) == 3:
                np_var_data_block = self.var[ self.iTimeStep, :, self.istart::self.istep ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0] * np_var_data_block.shape[1], ] )
            self.nLevels = 1
        else:
            if len( self.var.shape ) == 3:               
                np_var_data_block = self.var[ self.iTimeStep, :, self.istart::self.istep ].data
            elif len( self.var.shape ) == 4:
                np_var_data_block = self.var[ self.iTimeStep, :, :, self.istart::self.istep ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0], np_var_data_block.shape[1] * np_var_data_block.shape[2] ] )

        return np_var_data_block
    
    def processCoordinates( self, lat, lon ):
        point_layout = self.getPointsLayout()
        self.lat_data = lat[self.istart::self.istep] if ( point_layout == PlotType.List ) else lat[::]
        self.lon_data = lon[self.istart::self.istep] 
        if self.lon_data.__class__.__name__ == "TransientVariable":
            self.lat_data = self.lat_data.data
            self.lon_data = self.lon_data.data        
        xmax, xmin = self.lon_data.max(), self.lon_data.min()
        self.xcenter =  ( xmax + xmin ) / 2.0       
        self.xwidth =  ( xmax - xmin ) 
        return lon, lat
    
    def getNumberOfPoints(self): 
        return len( self.np_points_data ) / 3   
              
    def computePoints( self, **args ):
        point_layout = self.getPointsLayout()
        np_points_data_list = []
        for iz in range( len( self.lev ) ):
            zvalue = iz * self.z_spacing
            if point_layout == PlotType.List:
                z_data = numpy.empty( self.lon_data.shape, self.lon_data.dtype ) 
                z_data.fill( zvalue )
                np_points_data_list.append( numpy.dstack( ( self.lon_data, self.lat_data, z_data ) ).flatten() )            
            elif point_layout == PlotType.Grid: 
                latB = self.lat_data.reshape( [ self.lat_data.shape[0], 1 ] )  
                lonB = self.lon_data.reshape( [ 1, self.lon_data.shape[0] ] )
                grid_data = numpy.array( [ (x,y,zvalue) for (x,y) in numpy.broadcast(lonB,latB) ] )
                np_points_data_list.append( grid_data.flatten() ) 
        self.np_points_data = numpy.concatenate( np_points_data_list )
        self.point_data_arrays['x'] = np_points_data[0::3].astype( numpy.float32 ) 
        self.point_data_arrays['y'] = np_points_data[1::3].astype( numpy.float32 ) 
        self.point_data_arrays['z'] = np_points_data[2::3].astype( numpy.float32 )         

    def getPointsLayout( self ):
        return PlotType.getPointsLayout( self.grid )

    def getLatLon( self, data_file, varname, grid_file = None ):
        if grid_file:
            lat = grid_file['lat']
            lon = grid_file['lon']
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )
        Var = data_file[ varname ]
        if id(Var) == id(None):
            print>>sys.stderr, "Error, can't find variable '%s' in data file." % ( varname )
            return None, None
        if hasattr( Var, "coordinates" ):
            axis_ids = Var.coordinates.strip().split(' ')
            lat = data_file( axis_ids[1], squeeze=1 )  
            lon = data_file( axis_ids[0], squeeze=1 )
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )
        elif hasattr( Var, "stagger" ):
            stagger = Var.stagger.strip()
            lat = data_file( "XLAT_%s" % stagger, squeeze=1 )  
            lon = data_file( "XLONG_%s" % stagger, squeeze=1 )
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )

        lat = Var.getLatitude()  
        lon = Var.getLongitude()
        if PlotType.validCoords( lat, lon ): 
            return  self.processCoordinates( lat.getValue(), lon.getValue() )
        
        lat = data_file( "XLAT", squeeze=1 )  
        lon = data_file( "XLONG", squeeze=1 )
        if PlotType.validCoords( lat, lon ): 
            return  self.processCoordinates( lat, lon )       
        return None, None
    
    def setDataSlice(self, istart, istep ):
        self.istart = istart
        self.istep = istep

    def initialize( self, args ): 
        ( grid_file, data_file, varname ) = args
        gf = cdms2.open( grid_file ) if grid_file else None
        df = cdms2.open( data_file )       
        self.var = df[ varname ]
        self.grid = self.var.getGrid()
        self.lon, self.lat = self.getLatLon( df, varname, gf )                              
        self.time = self.var.getTime()
        self.lev = self.var.getLevel()
        missing_value = self.var.attributes.get( 'missing_value', None )
        if self.lev == None:
            domain = self.var.getDomain()
            for axis in domain:
                if PlotType.isLevelAxis( axis[0].id.lower() ):
                    self.lev = axis[0]
                    break
                
        self.computePoints()
        np_var_data_block = self.getDataBlock().flatten()     
        if missing_value: self.var_data = numpy.ma.masked_equal( np_var_data_block, missing_value, False )
        else: self.var_data = np_var_data_block
        self.point_data_arrays['vardata'] = self.var_data
        self.vrange = ( var_data.min(), var_data.max() ) 
        
    def getPoints(self):
        return self.np_points_data

    def getPointIndices(self):
        return self.selected_index_array

    def getVarData(self):
        return self.var_data

    def getVarDataRange(self):
        return self.vrange
                    
    def execute( self, args, **kwargs ): 
        ( threshold_target, rmin, rmax ) = args
        dv = self.vrange[1] - self.vrange[0]
        vmin = self.vrange[0] + rmin * dv
        vmax = self.vrange[0] + rmax * dv
        var_data = self.point_data_arrays.get( threshold_target, None)
        if id(var_data) <> id(None):
            threshold_mask = numpy.logical_and( numpy.greater( var_data, vmin ), numpy.less( var_data, vmax ) ) 
            index_array = numpy.arange( 0, len(var_data) )
            self.selected_index_array = index_array[ threshold_mask ]      

