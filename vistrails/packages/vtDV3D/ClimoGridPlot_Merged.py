'''
Created on Aug 29, 2013

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
from PyQt4 import QtCore, QtGui
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from packages.serverside_data_processing.multicore_process_executable import ExecutionTarget, MultiQueueExecutable


VTK_NO_MODIFIER         = 0
VTK_SHIFT_MODIFIER      = 1
VTK_CONTROL_MODIFIER    = 2        
VTK_BACKGROUND_COLOR = ( 0.0, 0.0, 0.0 )
VTK_FOREGROUND_COLOR = ( 1.0, 1.0, 1.0 )
VTK_TITLE_SIZE = 14
VTK_NOTATION_SIZE = 14
VTK_INSTRUCTION_SIZE = 24
MIN_LINE_LEN = 50

def dump_np_array1( a, label=None ):
    print "\n-------------------------------------------------------------------------------------------------"
    if label: print label
    npts = a.shape[0]
    nrows = 20
    iSkip = npts/nrows
    for ir in range(nrows):
        iPt = iSkip*ir
        print "Pt[%d]: %f  " % ( iPt, a[ iPt ])
    print "-------------------------------------------------------------------------------------------------\n"
    for ir in range(nrows):
        iPt =  npts/2 + ir
        print "Pt[%d]: %f " % ( iPt, a[ iPt ] )
    print "-------------------------------------------------------------------------------------------------\n"

def dump_np_array3( a, label=None ):
    print "\n-------------------------------------------------------------------------------------------------"
    if label: print label
    npts = a.shape[0]/3
    nrows = 20
    iSkip = npts/nrows
    for ir in range(nrows):
        iPt = iSkip*ir
        ioff = iPt*3
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, a[ ioff ], a[ ioff+1 ], a[ ioff+2 ] )
    print "-------------------------------------------------------------------------------------------------\n"
    for ir in range(nrows):
        iPt =  npts/2 + ir
        ioff = iPt*3
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, a[ ioff ], a[ ioff+1 ], a[ ioff+2 ] )
    print "-------------------------------------------------------------------------------------------------\n"

def dump_vtk_array3( a, label=None ):
    print "\n-------------------------------------------------------------------------------------------------"
    if label: print label
    npts = a.GetNumberOfTuples()
    nrows = 20
    iSkip = npts/nrows
    for ir in range(nrows):
        iPt = iSkip*ir
        pt = a.GetTuple(iPt)
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, pt[ 0 ], pt[ 1 ], pt[ 2 ] )
    print "-------------------------------------------------------------------------------------------------\n"
    for ir in range(nrows):
        iPt =  npts/2 + ir
        pt = a.GetTuple(iPt)
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, pt[ 0 ], pt[ 1 ], pt[ 2 ] )
    print "-------------------------------------------------------------------------------------------------\n"

def dump_vtk_array1( a, label=None ):
    print "\n-------------------------------------------------------------------------------------------------"
    if label: print label
    npts = a.GetSize()
    nrows = 20
    iSkip = npts/nrows
    for ir in range(nrows):
        iPt = iSkip*ir
        v = a.GetValue(iPt)
        print "Pt[%d]: %.2f  " % ( iPt, v )
    print "-------------------------------------------------------------------------------------------------\n"
    for ir in range(nrows):
        iPt =  npts/2 + ir
        v = a.GetValue(iPt)
        print "Pt[%d]: %.2f " % ( iPt, v )
    print "-------------------------------------------------------------------------------------------------\n"
    
def dump_vtk_points( pts, label=None ):
    print "\n-------------------------------------------------------------------------------------------------"
    npts = pts.GetNumberOfPoints()
    if label: print label
    nrows = 20
    iSkip = npts/nrows
    for ir in range(nrows):
        iPt = iSkip*ir
        pt = pts.GetPoint( iPt )
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, pt[ 0 ], pt[ 1 ], pt[ 2 ] )
    print "-------------------------------------------------------------------------------------------------\n"
    for ir in range(nrows):
        iPt =  npts/2 + ir
        pt = pts.GetPoint( iPt )
        print "Pt[%d]: %.2f %.2f, %.2f " % ( iPt, pt[ 0 ], pt[ 1 ], pt[ 2 ] )
    print "-------------------------------------------------------------------------------------------------\n"

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
    
class ProcessMode:
    Default = 0
    Slicing = 1
    Thresholding = 2
    
class TextDisplayMgr:
    
    def __init__( self, renderer ):
        self.renderer = renderer
    
    def setTextPosition(self, textActor, pos, size=[400,30] ):
        vpos = [ 2, 2 ] 
        vp = self.renderer.GetSize()
        vpos = [ pos[i]*vp[i] for i in [0,1] ]
        textActor.GetPositionCoordinate().SetValue( vpos[0], vpos[1] )      
        textActor.GetPosition2Coordinate().SetValue( vpos[0] + size[0], vpos[1] + size[1] )      
  
    def getTextActor( self, id, text, pos, **args ):
        textActor = self.getProp( 'vtkTextActor', id  )
        if textActor == None:
            textActor = self.createTextActor( id, **args  )
            self.renderer.AddViewProp( textActor )
        self.setTextPosition( textActor, pos )
        text_lines = text.split('\n')
        linelen = len(text_lines[-1])
        if linelen < MIN_LINE_LEN: text += (' '*(MIN_LINE_LEN-linelen)) 
        text += '.'
        textActor.SetInput( text )
        textActor.Modified()
        return textActor

    def getProp( self, ptype, id = None ):
        try:
          props = self.renderer.GetViewProps()
          nitems = props.GetNumberOfItems()
          for iP in range(nitems):
              prop = props.GetItemAsObject(iP)
              if prop.IsA( ptype ):
                  if not id or (prop.id == id):
                      return prop
        except: 
          pass
        return None
  
    def createTextActor( self, id, **args ):
        textActor = vtk.vtkTextActor()  
        textActor.SetTextScaleMode( vtk.vtkTextActor.TEXT_SCALE_MODE_PROP )  
#        textActor.SetMaximumLineHeight( 0.4 )       
        textprop = textActor.GetTextProperty()
        textprop.SetColor( *args.get( 'color', ( VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2] ) ) )
        textprop.SetOpacity ( args.get( 'opacity', 1.0 ) )
        textprop.SetFontSize( args.get( 'size', 10 ) )
        if args.get( 'bold', False ): textprop.BoldOn()
        else: textprop.BoldOff()
        textprop.ItalicOff()
        textprop.ShadowOff()
        textprop.SetJustificationToLeft()
        textprop.SetVerticalJustificationToBottom()        
        textActor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
        textActor.GetPosition2Coordinate().SetCoordinateSystemToDisplay() 
        textActor.VisibilityOff()
        textActor.id = id
        return textActor 

class PointIngestExecutionTarget(ExecutionTarget):

    def __init__( self, proc_index, nproc, wait_for_input=False, init_args=None ):
        self.iTimeStep = 0
        self.point_data_arrays = {} 
        self.vtk_planar_points = None                                  
        self.cameraOrientation = {}
        self.topo = PlotType.Planar
        self.lon_data = None
        self.lat_data = None 
        self.z_spacing = 1.0 
        self.metadata = {}
        ExecutionTarget.__init__( self, proc_index, nproc, wait_for_input, init_args )
       
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
#         for plotType in [ PlotType.Spherical, PlotType.Planar ]:
#             position = GridLevel.getXYZPoint( self.xcenter, 0.0, 900.0 ) if PlotType.Spherical else (  self.xcenter, 0.0, 900.0 ) 
#             focal_point =  (  0.0, 0.0, 0.0 ) if PlotType.Spherical else (  self.xcenter, 0.0, 0.0 )
#             self.cameraOrientation[ plotType ] = ( position,  focal_point, (  0.0, 1.0, 0.0 )   )            
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
        np_points_data = numpy.concatenate( np_points_data_list )
        self.point_data_arrays['x'] = np_points_data[0::3].astype( numpy.float32 ) 
        self.point_data_arrays['y'] = np_points_data[1::3].astype( numpy.float32 ) 
        self.point_data_arrays['z'] = np_points_data[2::3].astype( numpy.float32 ) 
        self.results.put( np_points_data )         

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

    def initialize( self, args ): 
        ( grid_file, data_file, varname ) = args
        gf = cdms2.open( grid_file ) if grid_file else None
        df = cdms2.open( data_file )       
        self.var = df[ varname ]
        self.grid = self.var.getGrid()
        self.istart = self.proc_index
        self.istep = self.nproc
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
        self.results.put( np_var_data_block )     
        if missing_value: var_data = numpy.ma.masked_equal( np_var_data_block, missing_value, False )
        else: var_data = np_var_data_block
        self.point_data_arrays['vardata'] = var_data
        self.vrange = ( var_data.min(), var_data.max() ) 
                    
    def execute( self, args, **kwargs ): 
        ( threshold_target, rmin, rmax ) = args
        dv = self.vrange[1] - self.vrange[0]
        vmin = self.vrange[0] + rmin * dv
        vmax = self.vrange[0] + rmax * dv
        var_data = self.point_data_arrays.get( threshold_target, None)
        if id(var_data) <> id(None):
            threshold_mask = numpy.logical_and( numpy.greater( var_data, vmin ), numpy.less( var_data, vmax ) ) 
            index_array = numpy.arange( 0, len(var_data) )
            selected_index_array = index_array[ threshold_mask ]
            self.results.put( selected_index_array )       
        
#     def computeThresholdedPoints( self, **args  ):
#         topo = args.get( 'topo', self.topo )
#         self.polydata = vtk.vtkPolyData()
#         self.polydata.SetPoints( self.vtk_planar_points )                             
#         self.threshold_filter = vtk.vtkThreshold()
#         self.threshold_filter.SetInput( self.polydata )
#         self.geometry_filter = vtk.vtkGeometryFilter()
#         self.geometry_filter.SetInput( self.threshold_filter.GetOutput() )
        
#     def getProduct(self):
#         return self.geometry_filter.GetOutput()
#                           
#     def setThresholdingArray( self, aname ):
#         self.threshold_filter.SetInputArrayToProcess( 0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, aname )
# 
#     def setSliceThresholdBounds( self, slicePosition = 0.0 ):
#         if self.lev == None: return
#         sliceThickness = None
#         self.setThresholdingArray( self.sliceOrientation )
#         if    self.sliceOrientation == 'x': sliceThickness = self.sliceThickness[0]
#         elif  self.sliceOrientation == 'y': sliceThickness = self.sliceThickness[1]
#         elif  self.sliceOrientation == 'z': sliceThickness = self.z_spacing/2
#         if sliceThickness:
#             self.threshold_filter.ThresholdBetween( slicePosition-sliceThickness,  slicePosition+sliceThickness )
#             self.threshold_filter.Modified()
#             self.geometry_filter.Modified()
        
class GridTest:

    shperical_to_xyz_trans = vtk.vtkSphericalTransform()
    radian_scaling = math.pi / 180.0 
    

    def __init__( self, vtk_render_window, **args ):
        self.initial_cell_index = 0
        self.step_count = 0
        self.recolored_points = []
        self.iLevel = 0
        self.level_cache = {}
        self.vtk_spherical_points = None
        self.vtk_planar_points = None
        self.grid_levels = {}
        self.labelBuff = "NA                                    "
        self.cameraOrientation = {}
        self.iTimeStep = 0
        self.cropRegion = None
        self.slice_actor = None
        self.sliceStepSize = 1.0
        self.sliceIndex = [ 0, 0 ]
        self.sliceThickness = [ 1.0, 1.0 ]
        self.sliceOrientation = 'z'
        self.vtk_planar_points = None
        self.vtk_spherical_points = None
        self.vtk_color_data = None
        self.earth_radius = 100.0
        self.topo = PlotType.Planar
        self.lon_data = None
        self.lat_data = None
        self.lon_slice_positions = None          
        self.lat_slice_positions = None  
        self.point_data_arrays = {}  
        self.downsizeNPointsTarget = 100000 
        self.raw_point_size =  2
        self.point_size = self.raw_point_size
        self.reduced_point_sizes = { ProcessMode.Slicing:3, ProcessMode.Thresholding:3 }
        self.downsizeLevel = 0
        self.process_mode = ProcessMode.Default
        self.renderWindow = vtk_render_window
        self.renderWindowInteractor = self.renderWindow.GetInteractor()
        style = args.get( 'istyle', vtk.vtkInteractorStyleTrackballCamera() )  
        self.renderWindowInteractor.SetInteractorStyle( style )
        self.xwidth = 360.0
        self.xcenter =  self.xwidth / 2.0
        self.z_spacing = 1.0
        self.points_actors = {}
        self.core_var_data = {}
        self.np_points_data = {}
        self.core_index_arrays = {}

    def getPolydata( self, iCore ):
        actor = self.points_actors[ iCore ]
        mapper = actor.GetMapper()
        return mapper.GetInput()
        
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
            if self.points_actor.GetVisibility():
                pts = self.getPoints( **args )
                self.polydata.SetPoints( pts ) 
                return pts
        return None 

    def getPointsLayout( self ):
        return PlotType.getPointsLayout( self.grid )
            
    def computeSphericalPoints( self, **args ):
        point_layout = self.getPointsLayout()
        self.lon_data = args.get( 'lon', self.lon_data ) 
        self.lat_data = args.get( 'lat', self.lat_data ) 
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

    def computePlanarPoints( self, **args ):
        iCore = args.get( 'icore', 0 )
        icore_pts_data = self.proc_exec.get_result( iCore, True )
        self.np_points_data[iCore] = icore_pts_data
        vtk_points_data = numpy_support.numpy_to_vtk( icore_pts_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( len( icore_pts_data ) / 3 )     
        vtk_planar_points = vtk.vtkPoints()
        vtk_planar_points.SetData( vtk_points_data )
        return vtk_planar_points
#        self.grid_bounds = list( self.vtk_planar_points.GetBounds() )
#         if point_layout == PlotType.Grid: 
#             self.lon_slice_positions = self.lon_data              
#             self.lat_slice_positions = self.lat_data              
#         else:
#             self.lon_slice_positions = numpy.linspace( self.grid_bounds[0], self.grid_bounds[1], 100 )           
#             self.lat_slice_positions = numpy.linspace( self.grid_bounds[2], self.grid_bounds[3], 100 )
            
    def getNumberOfPoints(self): 
        return len( self.np_points_data ) / 3             
    
    def getPoints( self, **args ):
        topo = args.get( 'topo', self.topo )
        if topo == PlotType.Spherical:
            if not self.vtk_spherical_points:
                self.computeSphericalPoints( **args )
            return self.vtk_spherical_points
        if topo == PlotType.Planar: 
            if not self.vtk_planar_points: 
                self.computePlanarPoints( **args )
            return self.vtk_planar_points
        
    def updatePoints(self):
        self.polydata.SetPoints( self.getPoints() ) 
        
    def setVisiblity(self, visibleLevelIndex ):
        isVisible = ( visibleLevelIndex < 0 ) or ( visibleLevelIndex == self.iLevel )
        if isVisible: self.updatePoints()
        self.points_actor.SetVisibility( isVisible  )
        return isVisible
    
    def isVisible(self):
        return self.points_actor.GetVisibility()
        
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

#     def createClippedPolydata( self, **args  ):
#         self.lon_data = args.get( 'lon', self.lon_data ) 
#         self.lat_data = args.get( 'lat', self.lat_data ) 
#         topo = args.get( 'topo', self.topo )
#         self.polydata = vtk.vtkPolyData()
#         vtk_pts = self.getPoints( **args )
#         self.polydata.SetPoints( vtk_pts )                     
#         self.mapper = vtk.vtkPolyDataMapper()
#         self.createPointsActor(  self.slice_filter.GetOutput() )
# 
# 
#     def createThresholdedPolydata( self, **args  ):
#         self.lon_data = args.get( 'lon', self.lon_data ) 
#         self.lat_data = args.get( 'lat', self.lat_data ) 
#         topo = args.get( 'topo', self.topo )
#         self.polydata = vtk.vtkPolyData()
#         vtk_pts = self.getPoints( **args )
#         self.polydata.SetPoints( vtk_pts )                     
#         self.mapper = vtk.vtkPolyDataMapper()
#         self.geometry_filter.SetInput( self.threshold_filter.GetOutput() )        
#         self.createPointsActor( self.geometry_filter.GetOutput() )

    def createPolydata( self, **args  ):
        topo = args.get( 'topo', self.topo )
        polydata = vtk.vtkPolyData()
        vtk_pts = self.getPoints( **args )
        polydata.SetPoints( vtk_pts )                         
        self.createPointsActor( polydata, **args )
        
    def createPointsActor( self, polydata, **args ):
        icore = args.get( 'icore', 0 )
        lut = args.get( 'lut', None )
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInput( polydata ) 
        mapper.SetScalarModeToUsePointData()
        mapper.SetColorModeToMapScalars()
        if lut: mapper.SetLookupTable( lut )                
        actor = vtk.vtkActor()
        actor.SetMapper( mapper )
        self.points_actors[icore] = actor
        vrange = args.get('vrange',None)
        if vrange:mapper.SetScalarRange( vrange[0], vrange[1] ) 
                   
    def refreshResolution( self ):
        self.setPointSize( self.raw_point_size )
        downsizeFactor = int( math.ceil( self.getNumberOfPoints() / float( self.downsizeNPointsTarget ) ) ) 
        self.pointMask.SetOnRatio( downsizeFactor )
        self.pointMask.Modified()
        self.threshold_filter.Modified()
        self.geometry_filter.Modified()
                
    def setPointSize( self, point_size ):
        for points_actor in self.points_actors.values():
            points_actor.GetProperty().SetPointSize( point_size )
            
    def createColormap( self, lut ):
        self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        self.mapper.SetLookupTable( lut )
        
    def getLUT(self):
        return self.mapper.GetLookupTable()
        
    def getPointValue( self, iPt ):
        return self.var_data[ iPt ]

    def setVarData( self, **args ):
        iCore = args.get('icore',0)
        var_data = self.proc_exec.get_result(iCore,True)
        self.core_var_data[ iCore ] = var_data
#        vrange = ( var_data.min(), var_data.max() )
        vtk_color_data = numpy_support.numpy_to_vtk( var_data ) 
        vtk_color_data.SetName( 'vardata' ) 
        polydata = self.getPolydata( iCore )       
        polydata.GetPointData().SetScalars( vtk_color_data )
        
#         for pd_item in self.point_data_arrays.items():       
#             vtk_data = numpy_support.numpy_to_vtk( pd_item[1] )
#             vtk_data.SetName( pd_item[0] )
#             self.polydata.GetPointData().AddArray( vtk_data )  
 
    def createVertices( self, **args ): 
        iCore = args.get( 'icore', 0 )
        np_index_seq = self.proc_exec.get_result( iCore, True )
        vertices = vtk.vtkCellArray()  
        cell_sizes   = numpy.ones_like( np_index_seq )
        np_cell_data = numpy.dstack( ( cell_sizes, np_index_seq ) ).flatten()         
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( np_cell_data ) 
        vertices.SetCells( cell_sizes.size, self.vtk_cell_data )
        polydata = self.getPolydata( iCore )       
        polydata.SetVerts(vertices)
        self.core_index_arrays[ iCore ] = np_cell_data
#         if index_range[0] <> 0:
#             self.polydata.Update()
#             print "After Vertex Filter: %d, %d " % ( self.polydata.GetNumberOfPoints(), self.polydata.GetNumberOfCells() )
#             self.render()

    def createVertices_oneCell( self, geometry, **args ): 
        vertices = vtk.vtkCellArray()
        index_data = range( self.ncells )
        index_data.insert( 0, self.ncells )            
        self.np_cell_data = numpy.array( index_data, dtype=numpy.int64 )       
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( self.np_cell_data ) 
        vertices.SetCells( 1, self.vtk_cell_data )
        self.polydata.SetVerts(vertices)
        
    def getLabelActor(self):
        return self.textDisplayMgr.getTextActor( 'label', self.labelBuff, (.01, .95), size = VTK_NOTATION_SIZE, bold = True  )

    def updateTextDisplay( self, text ):
        self.labelBuff = str(text)
        self.getLabelActor().VisibilityOn()    

    def get_LUT( self, **args ):
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
    
#    def recolorPoint3(self, iPtIndex, color ):
#        if iPtIndex < self.npoints:
#            iPtId = 3*iPtIndex
#            for iC, c in enumerate( color ):
#                self.vtk_color_data.SetValue( iPtId + iC, c ) 
#            self.recolored_points.append( iPtIndex )     
#
#    def recolorPoint(self, iPtIndex, color ):
#        self.vtk_color_data.SetValue( iPtIndex, color ) 
#        self.recolored_points.append( iPtIndex )     
#
#    def clearColoredPoints( self ):
#        for iPt in self.recolored_points:
#            self.clearColoredPoint( iPt )
#        self.recolored_points = []
#
#    def clearColoredPoint3( self, iPtIndex ):
#        if iPtIndex < self.npoints:
#            iPtId = 3*iPtIndex
#            for iC in range(3):
#                self.vtk_color_data.SetValue( iPtId + iC, 0 )   
#
#    def clearColoredPoint( self, iPtIndex ):
#        self.vtk_color_data.SetValue( iPtIndex, 0 )   

    def onRightButtonPress( self, caller, event ):
        shift = caller.GetShiftKey()
        x, y = caller.GetEventPosition()
        picker = caller.GetPicker()
        picker.Pick( x, y, 0, self.renderer )
        actor = picker.GetActor()
        if actor:
            iPt = picker.GetPointId()
            if iPt >= 0:                
                dval = str( self.getPointValue( iPt ) ) 
                pick_pos = self.vtk_planar_points.GetPoint( iPt )
#                 if self.topo == PlotType.Spherical:
#                     pick_pos = glev.vtk_points_data.GetPoint( iPt )
#                 else:
#                     pick_pos = picker.GetPickPosition()                       
                text = " Point[%d] ( %.2f, %.2f ): %s " % ( iPt, pick_pos[0], pick_pos[1], dval )
                self.updateTextDisplay( text )
            
    def toggleTopo(self):
        self.recordCamera()
        self.topo = ( self.topo + 1 ) % 2
        pts =  self.setTopo( self.topo, lon=self.lon_data, lat=self.lat_data )
        if pts:
            self.resetCamera( pts )
            self.renderer.ResetCameraClippingRange()
        self.render()
        
    def render(self):
        self.renderWindow.Render()

    def toggleClipping(self):
        if self.clipper.GetEnabled():   self.clipOff()
        else:                           self.clipOn()
        
    def clipOn(self):
        self.clipper.PlaceWidget( self.cropRegion )
        self.clipper.On()
        self.executeClip()

    def clipOff(self):
        self.clipper.Off()
 
           
    def moveSlicePlane( self, distance = 0 ):
        self.setProcessMode( ProcessMode.Slicing )      
        if( distance <> 0 ): self.toggleResolution( 1 )
        if self.sliceOrientation == 'x': 
            self.sliceIndex[0] = self.sliceIndex[0] + distance
            if self.sliceIndex[0] < 0: self.sliceIndex[0] = 0
            if self.sliceIndex[0] >= len(self.lon_slice_positions): self.sliceIndex[0] = len(self.lon_slice_positions) - 1
            position = self.lon_slice_positions[ self.sliceIndex[0] ]
        if self.sliceOrientation == 'y': 
            self.sliceIndex[1] = self.sliceIndex[1] + distance
            if self.sliceIndex[1] < 0: self.sliceIndex[1] = 0
            if self.sliceIndex[1] >= len(self.lat_slice_positions): self.sliceIndex[1] = len(self.lat_slice_positions) - 1
            position = self.lat_slice_positions[ self.sliceIndex[1] ]
        if self.sliceOrientation == 'z': 
            self.sliceIndex[1] = self.sliceIndex[1] + distance
            if self.sliceIndex[1] < 0: self.sliceIndex[1] = 0
            if self.sliceIndex[1] >= len(self.lev): self.sliceIndex[1] = len(self.lev) - 1
            position = self.sliceIndex[1] * self.z_spacing
                
        self.setSliceThresholdBounds( position ) 
        if distance <> 0: self.renderWindow.Render() 
        print "Initial # points, cells: %d, %d " % ( self.polydata.GetNumberOfPoints(), self.polydata.GetNumberOfCells() )
        print "After Mask: %d, %d " % ( self.pointMask.GetOutput().GetNumberOfPoints(), self.pointMask.GetOutput().GetNumberOfCells() )
        print "After Threshold: %d, %d " % ( self.threshold_filter.GetOutput().GetNumberOfPoints(), self.threshold_filter.GetOutput().GetNumberOfCells() )
      

    def onKeyPress(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        shift = caller.GetShiftKey()
        alt = not key and keysym and keysym.startswith("Alt")
#        print " KeyPress %s %s " % ( str(key), str(keysym) ) 
        distance = None
        if keysym == "Up": 
            distance = 1 if self.inverted_levels else -1
        if keysym == "Down": 
            distance = -1 if self.inverted_levels else 1
        if distance:
            self.moveSlicePlane( distance ) 

        new_point_size = None
        slicing = self.slice_actor and self.slice_actor.GetVisibility()    
        if keysym == "Left":   
            new_point_size = (self.point_size - 1)
        if keysym == "Right":       
            new_point_size = (self.point_size + 1)
        if new_point_size and ( new_point_size > 0 ):
            self.point_size  =  new_point_size
            self.updatePointSize() 
            
        if keysym == "s":  self.toggleTopo()
        if keysym == "t":  self.stepTime()
        if keysym == "T":  self.stepTime( False )
        if keysym == "c":  self.toggleClipping()
        if keysym == "p":  self.toggleSlicerVisibility()
        if keysym == "r":  self.refreshResolution()
        if keysym == "v":  self.setVolumeRenderBounds( 0.3, 0.5 )
        if keysym == "i":  self.setPointIndexBounds( 5000, 7000 )

#         nc = self.vtk_color_data.GetNumberOfComponents()  
#         nt = self.vtk_color_data.GetNumberOfTuples()    
#         insertionPt = self.initial_cell_index + self.step_count       
#         self.step_count = self.step_count + 1       
#         edges = self.element_corners_data[:,insertionPt]
#         print "Recoloring point [%d], edges = %s " % ( insertionPt, str( edges ) )    
#         
#         self.clearColoredPoints()
#         
#         for iPt in edges: self.recolorPoint( iPt, 200 )            
#         self.recolorPoint( insertionPt, 240 )
#             
#         self.vtk_color_data.Modified()
# #        self.polydata.GetPointData().SetScalars( self.vtk_color_data )
# #        self.polydata.GetPointData().Modified()
#         self.polydata.Modified()
# #        self.polydata.Update()
#         self.renderWindow.Render()

    def print_grid_coords( self, npoints ):
        origin = [ self.lon_data[0], self.lat_data[0] ]
        for iPt in range( npoints ):
            lat = self.lat_data[iPt]
            lon = self.lon_data[iPt]
            x = ( lon - origin[0] ) * 5
            y = ( lat - origin[1] ) * 5 
            print " Point[%d]: ( %.2f, %.2f )" % ( iPt, x, y )

    def print_cell_coords( self, npoints ):
        for iPt in range( npoints ):
            corners = self.element_corners_data[:,iPt]
            print " Quad[%d]: %s" % ( iPt, str(corners) )
            
    def updateLevelVisibility(self):
        if self.setVisiblity( self.iLevel ) and ( self.iLevel >= 0 ):
            self.renderer.ResetCameraClippingRange() # ResetCamera( glev.getBounds() )
            if self.lev:
                lval = self.lev[ self.iLevel ]
                self.updateTextDisplay( "Level: %.2f, %s " % ( lval, self.lev.units ) )
        self.renderWindow.Render()
        
#        print " updateAllLevels required %.4f seconds. " % ( (t1-t0), )
        
#     def updateLevel(self):
#         if len( self.var.shape ) == 3:
#             self.var_data = self.level_cache.get( self.iLevel, None )
#             if id(self.var_data) == id(None):
#                 self.var_data = self.var[ 0, self.iLevel, 0:self.npoints ].raw_data()
#                 self.level_cache[ self.iLevel ] = self.var_data
#             self.vtk_color_data = numpy_support.numpy_to_vtk( self.var_data ) 
#             self.polydata.GetPointData().SetScalars( self.vtk_color_data )
#             self.renderWindow.Render()
#             print " Setting Level value to %.2f %s" % ( self.lev[ self.iLevel ], self.lev.units )
            
    def updatePointSize(self):
        self.setPointSize( self.point_size )
        self.renderWindow.Render()

    def stepTime( self, forward = True ):
        ntimes = len(self.time) if self.time else 1
        self.iTimeStep = self.iTimeStep + 1 if forward else self.iTimeStep - 1
        if self.iTimeStep < 0: self.iTimeStep = ntimes - 1
        if self.iTimeStep >= ntimes: self.iTimeStep = 0
        try:
            tvals = self.time.asComponentTime()
            tvalue = str( tvals[ self.iTimeStep ] )
            self.updateTextDisplay( "Time: %s " % tvalue )
        except Exception, err:
            print>>sys.stderr, "Can't understand time metadata."
        np_var_data_block = self.getDataBlock()
        var_data = np_var_data_block[:] if ( self.nLevels == 1 ) else np_var_data_block[ :, : ]    
        self.setVarData( var_data ) 
        self.renderWindow.Render()

      
    def processCoordinates( self, lat, lon ):
        self.npoints = lon.shape[0] 
        self.lat_data = lat[0:self.npoints]
        self.lon_data = lon[0:self.npoints]
        if self.lon_data.__class__.__name__ == "TransientVariable":
            self.lat_data = self.lat_data.data
            self.lon_data = self.lon_data.data       
        xmax, xmin = self.lon_data.max(), self.lon_data.min()
        self.xcenter =  ( xmax + xmin ) / 2.0       
        self.xwidth =  ( xmax - xmin ) 
#         for plotType in [ PlotType.Spherical, PlotType.Planar ]:
#             position = GridLevel.getXYZPoint( self.xcenter, 0.0, 900.0 ) if PlotType.Spherical else (  self.xcenter, 0.0, 900.0 ) 
#             focal_point =  (  0.0, 0.0, 0.0 ) if PlotType.Spherical else (  self.xcenter, 0.0, 0.0 )
#             self.cameraOrientation[ plotType ] = ( position,  focal_point, (  0.0, 1.0, 0.0 )   )            
        return lon, lat
       
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
    
    def getDataFormat( self, df ):
        source = df.attributes.get( 'source', None )
        if source and ('CAM' in source ): return 'CAM'
        title = df.attributes.get( 'TITLE', None )
        if title and ('WRF' in title): return 'WRF'
        return 'UNK'
    
    def getDataBlock( self ):
        if self.lev == None:
            if len( self.var.shape ) == 2:
                np_var_data_block = self.var[ self.iTimeStep, : ].data
            elif len( self.var.shape ) == 3:
                np_var_data_block = self.var[ self.iTimeStep, :, : ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0] * np_var_data_block.shape[1], ] )
            self.nLevels = 1
        else:
            self.nLevels = self.var.shape[1]
            if hasattr( self.lev, 'positive' ) and self.lev.positive == "down": 
                if self.lev[0] < self.lev[1]:
                    if self.iLevel == 0:
                        self.iLevel = self.nLevels - 1 
                    self.inverted_levels = True 
            if len( self.var.shape ) == 3:               
                np_var_data_block = self.var[ self.iTimeStep, :, : ].data
            elif len( self.var.shape ) == 4:
                np_var_data_block = self.var[ self.iTimeStep, :, :, : ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0], np_var_data_block.shape[1] * np_var_data_block.shape[2] ] )
            
        return np_var_data_block

    def executeClip( self, caller=None, event=None ):
        planes = vtk.vtkPlanes(); np = 6
        self.clipper.GetPlanes( planes )
        self.setClipping( planes )
        self.renderWindow.Render()
    
    def getPointsLayout(self):    
        return PlotType.getPointsLayout( self.var.getGrid() )
                            
    def plot( self, data_file, grid_file, varname, **args ): 
        color_index = args.get( 'color_index', -1 )
        self.inverted_levels = False
        self.topo = args.get( 'topo', PlotType.Spherical )
        npts_cutoff = args.get( 'max_npts', -1 )
        ncells_cutoff = args.get( 'max_ncells', -1 )
        self.iVizLevel = args.get( 'level', 0 )
        self.z_spacing = args.get( 'z_spacing', 1.5 )
        self.roi = args.get( 'roi', None )
        
        gf = cdms2.open( grid_file ) if grid_file else None
        df = cdms2.open( data_file )       
        lon, lat = self.getLatLon( df, varname, gf )
        data_format = args.get( 'data_format', self.getDataFormat( df ) )
                              
        self.var = df[ varname ]
        self.time = self.var.getTime()
        self.lev = self.var.getLevel()
        self.grid = self.var.getGrid()
        missing_value = self.var.attributes.get( 'missing_value', None )
        if self.lev == None:
            domain = self.var.getDomain()
            for axis in domain:
                if PlotType.isLevelAxis( axis[0].id.lower() ):
                    self.lev = axis[0]
                    break
                
        np_var_data_block = self.getDataBlock()
        
        point_layout = self.getPointsLayout()
        if point_layout == PlotType.Grid:
            self.sliceThickness =[ (self.lon_data[1]-self.lon_data[0])/2.0, (self.lat_data[1]-self.lat_data[0])/2.0 ]

        self.clippingPlanes = vtk.vtkPlanes()
        if missing_value: var_data = numpy.ma.masked_equal( np_var_data_block, missing_value, False )
        else: var_data = np_var_data_block
        self.createThresholdedPolydata( lon=self.lon_data, lat=self.lat_data )
        lut = self.get_LUT( invert = True, number_of_colors = 1024 )
        self.setVarData( var_data, lut )          
        self.createVertices()
        if self.cropRegion == None: 
            self.cropRegion = self.getBounds()
        self.setPointSize( self.point_size )                                                                                     
        self.createRenderer( **args )
        self.moveSlicePlane() 
        if (self.topo == PlotType.Spherical): self.CreateMap()               

    def plotPoints( self, proc_exec, data_file, grid_file, varname, **args ):
        gf = cdms2.open( grid_file ) if grid_file else None
        df = cdms2.open( data_file )       
        lon, lat = self.getLatLon( df, varname, gf )  
        self.var = df[ varname ]
        self.time = self.var.getTime()
        self.lev = self.var.getLevel()
        self.grid = self.var.getGrid()
        self.proc_exec = proc_exec
        
        if self.lev == None:
            domain = self.var.getDomain()
            for axis in domain:
                if PlotType.isLevelAxis( axis[0].id.lower() ):
                    self.lev = axis[0]
                    break
        
        lut = self.get_LUT( invert = True, number_of_colors = 1024 )
        for iCore in range(proc_exec.ncores):        
            self.createPolydata( icore=iCore, lut=lut )
            self.setVarData( icore=iCore )          
            self.createVertices( icore=iCore )
        self.setPointSize( self.point_size )                                                                                     
        self.createRenderer( **args )

    def plotProduct( self, data_file, grid_file, varname, **args ): 
        gf = cdms2.open( grid_file ) if grid_file else None
        df = cdms2.open( data_file )       
        lon, lat = self.getLatLon( df, varname, gf )  
        self.var = df[ varname ]
        self.time = self.var.getTime()
        self.lev = self.var.getLevel()
        self.grid = self.var.getGrid()
        missing_value = self.var.attributes.get( 'missing_value', None )
        if self.lev == None:
            domain = self.var.getDomain()
            for axis in domain:
                if PlotType.isLevelAxis( axis[0].id.lower() ):
                    self.lev = axis[0]
                    break                                                                             
        self.createRenderer( **args )       
        
    def setSliceColormap( self ):
        self.slice_mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
        self.slice_mapper.SetScalarModeToUsePointData()
        self.slice_mapper.SetColorModeToMapScalars()
        self.slice_mapper.SetLookupTable( self.getLUT() )    
   
#     def createProbeSlicer(self):
#         self.probe = vtk.vtkProbeFilter()
#         self.planeSource = vtk.vtkPlaneSource()
#         self.probe.SetSource( self.appendLayers.GetOutput() )
#         self.probe.SetInput( self.planeSource.GetOutput() )
#         self.slice_mapper = vtk.vtkPolyDataMapper()
#         
#         if vtk.VTK_MAJOR_VERSION <= 5:
#             self.slice_mapper.SetInput( self.probe.GetOutput() )
#         else:
#             self.slice_mapper.SetInputData( self.probe.GetOutput )
#                  
#         self.slice_actor = vtk.vtkActor()
#         self.slice_actor.SetMapper( self.slice_mapper )
#         self.renderer.AddActor( self.slice_actor )
#         self.slice_actor.SetVisibility( False )
#         self.planeSource.SetResolution( 100, len( self.lev ) )
#         self.setSlicePlaneOrientation()
#         for glev in self.grid_levels.values():
#             if glev.setVisiblity( self.iLevel ):
#                 self.setSliceColormap( glev )

#     def createSliceMapper(self):
#         self.slice_mapper = vtk.vtkPolyDataMapper()
#         self.clippingPlanes = vtk.vtkPlanes()
#         self.slice_mapper.SetClippingPlanes( self.clippingPlanes )
#         
#         if vtk.VTK_MAJOR_VERSION <= 5:
#             self.slice_mapper.SetInput( self.appendLayers.GetOutput() )
#         else:
#             self.slice_mapper.SetInputData( self.appendLayers.GetOutput() )
#                  
#         self.slice_actor = vtk.vtkActor()
#         self.slice_actor.SetMapper( self.slice_mapper )
#         self.pointPicker.AddPickList( self.slice_actor )  
#         self.renderer.AddActor( self.slice_actor )
#         self.slice_actor.SetVisibility( False )
#         self.setSliceColormap()
        
#     def setSlicePlaneOrientation( self, orientation='x' ):
#         if self.lev == None: return
#         lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
#         for glev in self.grid_levels.values():
#             if glev.vtk_planar_points:
#                 bounds = glev.getBounds( lev = lev_bounds )
#                 break
#         self.planeSource.SetOrigin( bounds[0], bounds[2], bounds[4] )
#         if orientation == 'x':  
#             self.planeSource.SetPoint1( bounds[0], bounds[2], bounds[5] )
#             self.planeSource.SetPoint2( bounds[0], bounds[3], bounds[4] )
#         if orientation == 'y':  
#             self.planeSource.SetPoint1( bounds[0], bounds[2], bounds[5] )
#             self.planeSource.SetPoint2( bounds[1], bounds[2], bounds[4] )

    def setSliceClipBounds( self, slicePosition = 0.0 ):
        if self.lev == None: return
        bounds = self.getBounds()
        mapperBounds = None
        if self.sliceOrientation == 'x':
            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
            mapperBounds = [ slicePosition-self.sliceThickness[0],  slicePosition+self.sliceThickness[0], bounds[2], bounds[3], lev_bounds[0], lev_bounds[1]  ]
        if self.sliceOrientation == 'y':
            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
            mapperBounds = [ bounds[0], bounds[1], slicePosition - self.sliceThickness[1],  slicePosition + self.sliceThickness[1], lev_bounds[0], lev_bounds[1]  ]
        if self.sliceOrientation == 'z':
            sliceThickness = self.z_spacing/2
            mapperBounds = [ bounds[0], bounds[1], bounds[2], bounds[3], slicePosition - sliceThickness,  slicePosition + sliceThickness  ]
        if mapperBounds:
            print "Setting clip planes: %s " % str( mapperBounds )
            self.clipBox.SetBounds( mapperBounds )
            self.slice_filter.Modified()
#             self.clipper.PlaceWidget( mapperBounds )
#             self.clipper.GetPlanes( self.clippingPlanes )
#             self.mapper.SetClippingPlanes( self.clippingPlanes )
            self.mapper.Modified()
            
    def setThresholdingArray( self, aname ):
        self.threshold_filter.SetInputArrayToProcess( 0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, aname )

    def setSliceThresholdBounds( self, slicePosition = 0.0 ):
        if self.lev == None: return
        sliceThickness = None
        self.setThresholdingArray( self.sliceOrientation )
        if    self.sliceOrientation == 'x': sliceThickness = self.sliceThickness[0]
        elif  self.sliceOrientation == 'y': sliceThickness = self.sliceThickness[1]
        elif  self.sliceOrientation == 'z': sliceThickness = self.z_spacing/2
        if sliceThickness:
            self.threshold_filter.ThresholdBetween( slicePosition-sliceThickness,  slicePosition+sliceThickness )
            self.threshold_filter.Modified()
            self.geometry_filter.Modified()
            self.mapper.Modified()
            
    def setProcessMode( self, mode ):
        self.process_mode = mode
        self.setPointSize( self.reduced_point_sizes[mode] )

    def setVolumeRenderBounds( self, rmin, rmax ):
        if self.lev == None: return
#        self.toggleResolution( 1 )
        self.setProcessMode( ProcessMode.Thresholding )
        self.setThresholdingArray( 'vardata' )
        dv = self.vrange[1] - self.vrange[0]
        vmin = self.vrange[0] + rmin * dv
        vmax = self.vrange[0] + rmax * dv
        self.threshold_filter.ThresholdBetween( vmin, vmax )
        self.mapper.SetScalarRange( vmin, vmax ) 
        self.threshold_filter.Modified()
        self.geometry_filter.Modified()
        self.mapper.Modified()

    def setPointIndexBounds( self, imin, imax ):
        if self.lev == None: return
#        self.toggleResolution( 1 )
        self.setThresholdingArray( 'vardata' )
        self.threshold_filter.ThresholdBetween( self.vrange[0], self.vrange[1] )
        self.createVertices( index_range=( imin, imax ) )
        self.threshold_filter.Modified()
        self.geometry_filter.Modified()
        self.mapper.Modified()
       
    def toggleSlicerVisibility( self ):
        if self.sliceOrientation == 'y':
            self.sliceOrientation = 'z'
            self.moveSlicePlane()
            self.slice_actor.SetVisibility( True  )  
        if self.sliceOrientation == 'z':
            self.sliceOrientation = 'x'
            self.moveSlicePlane()
        elif self.sliceOrientation == 'x':
            self.sliceOrientation = 'y'
            self.moveSlicePlane() 
        self.renderWindow.Render()   
     
    def CreateMap(self):        
        earth_source = vtk.vtkEarthSource()
        earth_source.SetRadius( self.earth_radius + .01 )
        earth_source.OutlineOn()
        earth_polydata = earth_source.GetOutput()
        self.earth_mapper = vtk.vtkPolyDataMapper()

        if vtk.VTK_MAJOR_VERSION <= 5:
            self.earth_mapper.SetInput(earth_polydata)
        else:
            self.earth_mapper.SetInputData(earth_polydata)

        self.earth_actor = vtk.vtkActor()
        self.earth_actor.SetMapper( self.earth_mapper )
        self.earth_actor.GetProperty().SetColor(0,0,0)
        self.renderer.AddActor( self.earth_actor )

                
    def createRenderer(self, **args ):
        background_color = args.get( 'background_color', VTK_BACKGROUND_COLOR )
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*background_color)

        self.renderWindow.AddRenderer( self.renderer )
        self.renderWindowInteractor.AddObserver( 'CharEvent', self.onKeyPress )       
        self.renderWindowInteractor.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )  
        self.textDisplayMgr = TextDisplayMgr( self.renderer )             
        self.pointPicker = vtk.vtkPointPicker()
        self.pointPicker.PickFromListOn()    
        self.renderWindowInteractor.SetPicker(self.pointPicker) 
        self.clipper = vtk.vtkBoxWidget()
        self.clipper.RotationEnabledOff()
        self.clipper.SetPlaceFactor( 1.0 ) 
        self.clipper.KeyPressActivationOff()
        self.clipper.SetInteractor( self.renderWindowInteractor )    
        self.clipper.SetHandleSize( 0.005 )
        self.clipper.SetEnabled( True )
        self.clipper.InsideOutOn()     
#        self.clipper.AddObserver( 'StartInteractionEvent', self.startClip )
#        self.clipper.AddObserver( 'EndInteractionEvent', self.endClip )
        self.clipper.AddObserver( 'InteractionEvent', self.executeClip )
        self.clipOff() 
        for points_actor in  self.points_actors.values():     
            self.renderer.AddActor( points_actor )
            self.pointPicker.AddPickList( points_actor ) 
        self.initCamera( )              
        self.renderWindow.Render()
        
    def startEventLoop(self):
        self.renderWindowInteractor.Start()

    def recordCamera( self ):
        c = self.renderer.GetActiveCamera()
        self.cameraOrientation[ self.topo ] = ( c.GetPosition(), c.GetFocalPoint(), c.GetViewUp() )

    def resetCamera( self, pts = None ):
        cdata = self.cameraOrientation.get( self.topo, None )
        if cdata:
            self.renderer.GetActiveCamera().SetPosition( *cdata[0] )
            self.renderer.GetActiveCamera().SetFocalPoint( *cdata[1] )
            self.renderer.GetActiveCamera().SetViewUp( *cdata[2] )       
        elif pts:
            self.renderer.ResetCamera( pts.GetBounds() )
        else:
            self.renderer.ResetCamera( self.getBounds() )
            
    def initCamera(self):
        self.renderer.GetActiveCamera().SetPosition( self.xcenter, 0, self.xwidth*2 ) 
        self.renderer.GetActiveCamera().SetFocalPoint( self.xcenter, 0, 0 )
        self.renderer.GetActiveCamera().SetViewUp( 0, 1, 0 )  
        self.renderer.ResetCameraClippingRange()     

             
    def getCamera(self):
        return self.renderer.GetActiveCamera()
    
    def setFocalPoint( self, fp ):
        self.renderer.GetActiveCamera().SetFocalPoint( *fp )
        
    def printCameraPos( self, label = "" ):
        cam = self.getCamera()
        cpos = cam.GetPosition()
        cfol = cam.GetFocalPoint()
        cup = cam.GetViewUp()
        camera_pos = (cpos,cfol,cup)
        print "%s: Camera => %s " % ( label, str(camera_pos) )
                     
if __name__ == '__main__':
    data_type = "CAM"
    data_dir = "/Users/tpmaxwel/data" 
    app = QtGui.QApplication(['Point Cloud Plotter'])
    widget = QVTKRenderWindowInteractor()
    print str( dir( widget ) )
    widget.Initialize()
    widget.Start()    
    
    if data_type == "WRF":
        data_file = os.path.join( data_dir, "WRF/wrfout_d01_2013-05-01_00-00-00.nc" )
        grid_file = None
        varname = "U"        
    elif data_type == "CAM":
        data_file = os.path.join( data_dir, "CAM/f1850c5_t2_ANN_climo-native.nc" )
        grid_file = os.path.join( data_dir, "CAM/ne120np4_latlon.nc" )
        varname = "U"
    elif data_type == "ECMWF":
        data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ecmwf.xml" )
        grid_file = None
        varname = "U_velocity"   
    elif data_type == "GEOS5":
        data_file = "/Developer/Data/AConaty/comp-ECMWF/ac-comp1-geos5.xml" 
        grid_file = None
        varname = "uwnd"   
    elif data_type == "MMF":
        data_file = os.path.join( data_dir, "MMF/diag_prs.20080101.nc" )
        grid_file = None
        varname = "u"

    arg_tuple_list = [ ]    
    arg_tuple_list.append( ( 'vardata', 0.4, 0.6 ) ) 
    init_args = ( grid_file, data_file, varname )
    ncores = 2
    g = GridTest( widget.GetRenderWindow() )
     
    multicore_exec = MultiQueueExecutable( PointIngestExecutionTarget, ncores=ncores )     
    multicore_exec.execute( arg_tuple_list, init_args )      

#    g.plot( data_file, grid_file, varname, topo=PlotType.Planar, roi=(0, 180, 0, 90), max_npts=-1, max_ncells=-1, data_format = data_type )
    
    g.plotPoints( multicore_exec, data_file, grid_file, varname )
#     g.createPointsActor( product, testExec.metadata )
#     g.plotProduct( data_file, grid_file, varname )

    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), multicore_exec.terminate()  ) 
    widget.show()   
    app.exec_() 

