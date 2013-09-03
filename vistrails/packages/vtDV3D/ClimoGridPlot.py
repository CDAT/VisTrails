'''
Created on Aug 29, 2013

@author: tpmaxwel
'''

import sys
import getopt
import numpy
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
    Points = 0
    Mesh = 1
    
class GridLevel:
    
    def __init__( self, level_index, level_value ):
        self.iLevel = level_index
        self.levValue = level_value
        self.vtk_planar_points = None
        self.vtk_spherical_points = None
        self.vtk_color_data = None
        self.earth_radius = 100.0
        self.shperical_to_xyz_trans = vtk.vtkSphericalTransform()
        self.xyz_to_shperical_trans = self.shperical_to_xyz_trans.GetInverse()

    def setTopo( self, topo, lon_data, lat_data ):
        if self.actor.GetVisibility():
            self.polydata.SetPoints( self.getPoints( topo, lon_data, lat_data ) ) 
            return True
        return False 

    def computeSphericalPoints( self, lon_data, lat_data, **args ):
        radian_scaling = math.pi / 180.0 
        theta =  ( 90.0 - lat_data ) * radian_scaling
        phi = lon_data * radian_scaling
        r = numpy.empty( lon_data.shape, lon_data.dtype )      
        r.fill(  self.earth_radius )
        points_data = numpy.dstack( ( r, theta, phi ) ).flatten()
        vtk_points_data = numpy_support.numpy_to_vtk( points_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( lon_data.shape[0] )     
        vtk_raw_points = vtk.vtkPoints()
        vtk_raw_points.SetData( vtk_points_data )
        vtk_points = vtk.vtkPoints()
        self.shperical_to_xyz_trans.TransformPoints( vtk_raw_points, vtk_points )
        self.vtk_spherical_points = vtk_points

    def computePlanarPoints( self, lon_data, lat_data, **args ):
        level_spacing = args.get( 'level_spacing', 10.0 )
        self.z_data = numpy.empty( lon_data.shape, lon_data.dtype ) 
        self.zvalue =  self.iLevel * level_spacing  
        self.z_data.fill( self.zvalue )
        self.np_points_data = numpy.dstack( ( lon_data, lat_data, self.z_data ) ).flatten()     
        self.vtk_points_data = numpy_support.numpy_to_vtk( self.np_points_data )    
        self.vtk_points_data.SetNumberOfComponents( 3 )
        self.vtk_points_data.SetNumberOfTuples( len( self.np_points_data ) / 3 )     
        vtk_raw_points = vtk.vtkPoints()
        vtk_raw_points.SetData( self.vtk_points_data )
        self.vtk_planar_points = vtk_raw_points
        self.planar_bounds = self.vtk_planar_points.GetBounds()
    
    def getPoints( self, topo, lon_data, lat_data, **args ):
        if topo == PlotType.Spherical:
            if not self.vtk_spherical_points: self.computeSphericalPoints(lon_data, lat_data, **args)
            return self.vtk_spherical_points
        if topo == PlotType.Planar: 
            if not self.vtk_planar_points: self.computePlanarPoints(lon_data, lat_data, **args)
            return self.vtk_planar_points
        
    def setVisiblity(self, visibleLevelIndex ):
        isVisible = ( visibleLevelIndex < 0 ) or ( visibleLevelIndex == self.iLevel )
        self.actor.SetVisibility( isVisible  )
        return isVisible
        
    def getBounds( self, topo ):
        if topo == PlotType.Spherical:
            return [ -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius ]
        else:
            return self.planar_bounds

    def createPolydata( self, topo, lon_data, lat_data ):
        self.polydata = vtk.vtkPolyData()
 
        vtk_pts = self.getPoints( topo, lon_data, lat_data )
        self.polydata.SetPoints( vtk_pts )                     
        self.mapper = vtk.vtkPolyDataMapper()
        
        if vtk.VTK_MAJOR_VERSION <= 5:
            self.mapper.SetInput(self.polydata)
        else:
            self.mapper.SetInputData(self.polydata)
                 
        actor = vtk.vtkActor()
        actor.SetMapper( self.mapper )
        self.actor = actor
        
    def setPointSize( self, point_size ):
        self.actor.GetProperty().SetPointSize( point_size )
            
    def createColormap( self, lut ):
        self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        self.mapper.SetLookupTable( lut )
        
    def getPointValue( self, iPt ):
        return self.var_data[ iPt ]

    def setVarData( self, vardata, lut ):
        self.var_data = vardata
        self.vrange = ( self.var_data.min(), self.var_data.max() )
        self.ncells = len( self.var_data )
        if lut:
            self.vtk_color_data = numpy_support.numpy_to_vtk( self.var_data ) 
            self.createColormap( lut )
            self.polydata.GetPointData().SetScalars( self.vtk_color_data )                     

    def createVertices( self, geometry, **args ): 
        vertices = vtk.vtkCellArray()
        ncells_cutoff = args.get( 'max_cells', -1 )
            
        if geometry == PlotType.Mesh:
            quad_corners = args[ 'quads' ]
            indexing = args.get( 'indexing', 'C' )
            
            self.ncells = self.quad_corners.shape[1] if ncells_cutoff <= 0 else ncells_cutoff
            element_corners_data = quad_corners[:,0:self.ncells].raw_data().astype( numpy.int64 )
            if self.indexing == 'F': element_corners_data = element_corners_data - 1
            np_cell_size_data = numpy.empty( [ self.ncells ], numpy.int64 )
            np_cell_size_data.fill(4)
            self.np_cell_data = numpy.vstack( [ np_cell_size_data, element_corners_data ] ).flatten('F')
        else:
            np_index_seq = numpy.arange( 0, self.ncells ) # numpy.array( xrange( ncells ) )
            cell_sizes   = numpy.ones_like( np_index_seq )
            self.np_cell_data = numpy.dstack( ( cell_sizes, np_index_seq ) ).flatten() 
        
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( self.np_cell_data ) 
        vertices.SetCells( self.ncells, self.vtk_cell_data )
               
        if geometry == PlotType.Mesh:
            self.polydata.SetPolys(vertices)
        else:
            self.polydata.SetVerts(vertices)

class GridTest:
    
    def __init__(self):
        self.initial_cell_index = 0
        self.step_count = 0
        self.recolored_points = []
        self.iLevel = 0
        self.level_cache = {}
        self.vtk_spherical_points = None
        self.vtk_planar_points = None
        self.grid_levels = {}

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
                glev = self.grid_levels.get( actor, None )                  
                dval = str( glev.getPointValue( iPt ) ) if glev else "NULL"
                if self.topo == PlotType.Spherical:
                    pick_pos = [ self.lon_data[ iPt ], self.lat_data[ iPt ] ]
                else:
                    pick_pos = picker.GetPickPosition()                       
                print " Point Picked[%d] ( %.2f, %.2f ): %s " % ( iPt, pick_pos[0], pick_pos[1], dval )
            
    def ToggleTopo(self):
        self.topo = ( self.topo + 1 ) % 2
        for glev in self.grid_levels.values():
            if glev.setTopo( self.topo, self.lon_data, self.lat_data ):
                self.resetCamera()
                self.renderer.ResetCamera( glev.getBounds( self.topo ) )
        self.renderWindow.Render()

    def onKeyPress(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        shift = caller.GetShiftKey()
        alt = not key and keysym.startswith("Alt")
        print " KeyPress %s %s " % ( str(key), str(keysym) ) 
        new_level = None
        if keysym == "Up": new_level = (self.iLevel - 1) if self.inverted_levels else (self.iLevel + 1) 
        if keysym == "Down": new_level = (self.iLevel + 1) if self.inverted_levels else (self.iLevel - 1) 
        if new_level and ( new_level >= 0 ) and ( new_level < self.nLevels ):
            self.iLevel  =  new_level
            self.updateLevelVisibility() 

        new_point_size = None
        if keysym == "Left":  new_point_size = (self.point_size - 1)
        if keysym == "Right": new_point_size = (self.point_size + 1)
        if new_point_size and ( new_point_size > 0 ):
            self.point_size  =  new_point_size
            self.updatePointSize() 
            
        if keysym == "t":  self.ToggleTopo()
        if keysym == "c":  self.printCameraPos()

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
        for glev in self.grid_levels.values():
            if glev.setVisiblity( self.iLevel ) and ( self.iLevel >= 0 ):
#                self.setFocalPoint( [ self.xcenter, 0.0, glev.zvalue ] )
                self.renderer.ResetCamera( glev.getBounds( self.topo ) )
        self.renderWindow.Render()
         
    def updateLevel(self):
        if len( self.var.shape ) == 3:
            self.var_data = self.level_cache.get( self.iLevel, None )
            if id(self.var_data) == id(None):
                self.var_data = self.var[ 0, self.iLevel, 0:self.npoints ].raw_data()
                self.level_cache[ self.iLevel ] = self.var_data
            self.vtk_color_data = numpy_support.numpy_to_vtk( self.var_data ) 
            self.polydata.GetPointData().SetScalars( self.vtk_color_data )
            self.renderWindow.Render()
            print " Setting Level value to %.2f %s" % ( self.lev[ self.iLevel ], self.lev.units )
            
    def updatePointSize(self):
        self.actor.GetProperty().SetPointSize(self.point_size)
        self.renderWindow.Render()
        print " Setting Point Size: %d" % ( self.point_size )
        
          
    def plot( self, data_file, grid_file, varname, **args ): 
        color_index = args.get( 'color_index', -1 )
        self.point_size = args.get( 'point_size', 2 )
        indexing = args.get( 'indexing', 'C' )
        self.inverted_levels = False
        self.topo = args.get( 'topo', PlotType.Spherical )
        geometry = args.get( 'grid', PlotType.Points )
        npts_cutoff = args.get( 'max_npts', -1 )
        ncells_cutoff = args.get( 'max_ncells', -1 )
        self.iVizLevel = args.get( 'level', 0 )
        
        gf = cdms2.open( grid_file )
        lat = gf['lat']
        lon = gf['lon']
        quad_corners = gf['element_corners']
        df = cdms2.open( data_file )  
     
#        print " Shapes, lat: %s lon: %s corners: %s, cell data: %s  " % ( str(lat.shape), str(lon.shape), str(element_corners.shape), str( vtk_cell_data[0:20] ) )
        self.npoints = lon.shape[0] if ( npts_cutoff <= 0 ) else npts_cutoff
        self.lat_data = lat[0:self.npoints].raw_data()
        self.lon_data = lon[0:self.npoints].raw_data()
        xmax, xmin = self.lon_data.max(), self.lon_data.min()
        self.xcenter =  ( xmax + xmin ) / 2.0       
        self.xwidth =  ( xmax - xmin )        
                         
        self.var = df[ varname ]
        
        if len( self.var.shape ) == 2:
            np_var_data_block = self.var[0,0:self.npoints].raw_data()
            self.nLevels = 1
        elif len( self.var.shape ) == 3:
            self.lev = self.var.getLevel()
            self.nLevels = self.var.shape[1]
            if self.lev.positive == "down": 
                if self.iLevel == 0:
                    self.iLevel = self.nLevels - 1 
                self.inverted_levels = True                
            np_var_data_block = self.var[0,:,0:self.npoints].raw_data()

        for iLevel in range( self.nLevels ):
            glev = GridLevel( iLevel, self.lev[iLevel] )                 
            var_data = np_var_data_block[:] if ( self.nLevels == 1 ) else np_var_data_block[iLevel,:]
                                
            glev.createPolydata( self.topo, self.lon_data, self.lat_data )
            lut = self.get_LUT( invert = True, number_of_colors = 1024 )
            glev.setVarData( var_data, lut )          
#            glev.createVertices( geometry, max_cells = ncells_cutoff )  # quad_corners = gf['element_corners'], indexing = 'F', 
            glev.createVertices( geometry, quads = quad_corners, indexing = 'F' )
            glev.setVisiblity( self.iLevel )
            glev.setPointSize( self.point_size )
            self.grid_levels[ glev.actor ] = glev
                                                                     
        self.createRenderer()        
        if (self.topo == PlotType.Spherical): self.CreateMap()                       
        self.startEventLoop()

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
        background_color = args.get( 'background_color', (0,0,0) )
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*background_color)
        self.renderWindow = vtk.vtkRenderWindow()
        self.renderWindow.AddRenderer( self.renderer )
        self.renderWindowInteractor = args.get( 'istyle', vtk.vtkRenderWindowInteractor() )  
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.renderWindowInteractor.SetInteractorStyle(style)
        self.renderWindowInteractor.SetRenderWindow( self.renderWindow )
        self.renderWindowInteractor.AddObserver( 'CharEvent', self.onKeyPress )       
        self.renderWindowInteractor.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )               
        pointPicker = vtk.vtkPointPicker()
        pointPicker.PickFromListOn()    
        self.renderWindowInteractor.SetPicker(pointPicker) 
        for glev in self.grid_levels.values():           
            self.renderer.AddActor( glev.actor )
            pointPicker.AddPickList( glev.actor )               
        self.renderWindow.Render()
        
    def startEventLoop(self):
        self.renderWindowInteractor.Start()

    def resetCamera(self):
        if (self.topo == PlotType.Spherical):
            self.renderer.GetActiveCamera().SetPosition(  0.0, 0.0, 900.0 )
            self.renderer.GetActiveCamera().SetFocalPoint(  0.0, 0.0, 0.0 )
            self.renderer.GetActiveCamera().SetViewUp(  0.0, 1.0, 0.0 )       
        if (self.topo == PlotType.Planar):
            self.renderer.GetActiveCamera().SetPosition(  self.xcenter, 0.0, 900.0 ) # self.xwidth * 3 )
            self.renderer.GetActiveCamera().SetFocalPoint(  self.xcenter, 0.0, 0.0 )
            self.renderer.GetActiveCamera().SetViewUp(  0.0, 1.0, 0.0 )       
        
    def getCamera(self):
        return self.renderer.GetActiveCamera()
    
    def setFocalPoint( self, fp ):
        self.renderer.GetActiveCamera().SetFocalPoint( *fp )
        
    def printCameraPos( self ):
        cam = self.getCamera()
        cpos = cam.GetPosition()
        cfol = cam.GetFocalPoint()
        cup = cam.GetViewUp()
        camera_pos = (cpos,cfol,cup)
        print "Camera: " , str(camera_pos)

if __name__ == '__main__':
    data_dir = "/Users/tpmaxwel/data" 
    CAM_file = os.path.join( data_dir, "CAM/f1850c5_t2_ANN_climo-native.nc" )
    grid_file = os.path.join( data_dir, "CAM/ne120np4_latlon.nc" )
    varname = "U"
#    varname = "PS"

    g = GridTest()
    g.plot( CAM_file, grid_file, varname, topo=PlotType.Planar, grid=PlotType.Points, indexing='F', max_npts=-1, max_ncells=-1, level = 0 )
