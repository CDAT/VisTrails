'''
Created on Aug 26, 2013

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

class GridTest:
    
    def __init__(self):
        self.initial_cell_index = 0
        self.step_count = 0
        self.recolored_points = []

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
    
    def recolorPoint3(self, iPtIndex, color ):
        if iPtIndex < self.npoints:
            iPtId = 3*iPtIndex
            for iC, c in enumerate( color ):
                self.vtk_color_data.SetValue( iPtId + iC, c ) 
            self.recolored_points.append( iPtIndex )     

    def recolorPoint(self, iPtIndex, color ):
        self.vtk_color_data.SetValue( iPtIndex, color ) 
        self.recolored_points.append( iPtIndex )     

    def clearColoredPoints( self ):
        for iPt in self.recolored_points:
            self.clearColoredPoint( iPt )
        self.recolored_points = []

    def clearColoredPoint3( self, iPtIndex ):
        if iPtIndex < self.npoints:
            iPtId = 3*iPtIndex
            for iC in range(3):
                self.vtk_color_data.SetValue( iPtId + iC, 0 )   

    def clearColoredPoint( self, iPtIndex ):
        self.vtk_color_data.SetValue( iPtIndex, 0 )   

    def onRightButtonPress( self, caller, event ):
        shift = caller.GetShiftKey()
        x, y = caller.GetEventPosition()
        picker = caller.GetPicker()
        picker.Pick( x, y, 0, self.renderer )
        iPt = picker.GetPointId()
        if iPt >= 0:
            dval = self.var_data[ iPt ]
            if self.plot_type == PlotType.Spherical:
                pick_pos = [ self.lon_data[ iPt ], self.lat_data[ iPt ] ]
            else:
                pick_pos = picker.GetPickPosition()                       
            print " Point Picked[%d] ( %.2f, %.2f ): %f " % ( iPt, pick_pos[0], pick_pos[1], dval )

    def onKeyPress(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        shift = caller.GetShiftKey()
        alt = not key and keysym.startswith("Alt")
        print " KeyPress %s %s " % ( str(key), str(keysym) )    

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
            
    def generate_mesh( self, vtk_points, ncells_cutoff=-1 ):
        quads = vtk.vtkCellArray()
        element_corners = self.gf['element_corners']
        if self.quads_list:
            ncells = len( self.quads_list  )
            quad_data_list = []
            for quad_index in self.quads_list:
                np_quad_indices = element_corners[:,quad_index].raw_data()
                quad_data_list.append( np_quad_indices )
            element_corners_data = numpy.vstack( quad_data_list ).transpose()
        else:
            ncells = element_corners.shape[1] if ncells_cutoff < 0 else ncells_cutoff
            element_corners_data = element_corners[:,0:ncells].raw_data()
            
        np_cell_size_data = numpy.array( [4]*ncells, dtype=element_corners_data.dtype )
        np_cell_data = numpy.vstack( [ np_cell_size_data, element_corners_data ] ).flatten('F').astype( numpy.int64 )
        vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( np_cell_data ) 
        quads.SetCells( ncells, vtk_cell_data )           
        mesh_polydata = vtk.vtkPolyData()
        mesh_polydata.SetPoints(vtk_points)    
        mesh_polydata.GetPointData().SetScalars( self.vtk_color_data )
        mesh_polydata.SetPolys(quads)
        mesh_mapper = vtk.vtkPolyDataMapper()
        if vtk.VTK_MAJOR_VERSION <= 5:
            mesh_mapper.SetInput(mesh_polydata)
        else:
           mesh_mapper.SetInputData(mesh_polydata)
        return mesh_mapper

    def generate_points( self, vtk_points ):
        vertices = vtk.vtkCellArray()
        ncells =  self.npoints
        np_index_seq = numpy.array( xrange( ncells ) )
        cell_sizes   = numpy.ones_like( np_index_seq )
        np_cell_data = numpy.dstack( ( cell_sizes, np_index_seq ) ).flatten() 
        vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( np_cell_data ) 
        vertices.SetCells( ncells, vtk_cell_data )           
        points_polydata = vtk.vtkPolyData()
        points_polydata.SetPoints(vtk_points)    
        points_polydata.GetPointData().SetScalars( self.vtk_color_data )
        points_polydata.SetVerts(vertices)
        points_mapper = vtk.vtkPolyDataMapper()
        if vtk.VTK_MAJOR_VERSION <= 5:
            points_mapper.SetInput(points_polydata)
        else:
           points_mapper.SetInputData(points_polydata)
        return points_mapper
               
    def plot( self, data_file, grid_file, varname, **args ): 
        use_colormap = False
        point_size = 5
        self.plot_type = PlotType.Spherical
        show_points = True
        show_mesh = False
        npts_cutoff = 30
        cells_cutoff = 8
        show_map = False
        self.quads_list = []
        
        self.gf = cdms2.open( grid_file )
        lat = self.gf['lat']
        lon = self.gf['lon']
        df = cdms2.open( data_file )
        radian_scaling = math.pi / 180.0        
    
#        print " Shapes, lat: %s lon: %s corners: %s, cell data: %s  " % ( str(lat.shape), str(lon.shape), str(element_corners.shape), str( vtk_cell_data[0:20] ) )
        self.npoints = lon.shape[0] if ( npts_cutoff <= 0 ) else npts_cutoff
        self.lat_data = lat[0:self.npoints].raw_data()
        self.lon_data = lon[0:self.npoints].raw_data()
        if self.plot_type == PlotType.Spherical:
           theta =  ( 90.0 - self.lat_data ) * radian_scaling
           phi = self.lon_data * radian_scaling
           r = numpy.ones_like( self.lat_data )
           points_data = numpy.dstack( ( r, theta, phi ) ).flatten()
        else:
           z_data = numpy.zeros_like( self.lat_data )
           points_data = numpy.dstack( ( self.lon_data, self.lat_data, z_data ) ).flatten()
           
#        self.print_grid_coords( npts_cutoff  )
#        self.print_cell_coords( npts_cutoff  )
        
        vtk_points_data = numpy_support.numpy_to_vtk( points_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( self.npoints )     
        vtk_raw_points = vtk.vtkPoints()
        vtk_raw_points.SetData( vtk_points_data )
        
        if self.plot_type == PlotType.Spherical:
            self.shperical_to_xyz_trans = vtk.vtkSphericalTransform()
            vtk_points = vtk.vtkPoints()
            self.shperical_to_xyz_trans.TransformPoints( vtk_raw_points, vtk_points )
            self.xyz_to_shperical_trans = self.shperical_to_xyz_trans.GetInverse()
        else:
            vtk_points = vtk_raw_points
                 
        var = df[ varname ]
        self.var_data = var[0,0:self.npoints].raw_data()
        ( vmin, vmax ) = ( self.var_data.min(), self.var_data.max() )
            
        if use_colormap:
            self.vtk_color_data = vtk.vtkFloatArray() 
            self.vtk_color_data.SetNumberOfTuples( self.npoints )
            self.vtk_color_data.SetNumberOfComponents( 1 )
            self.vtk_color_data = numpy_support.numpy_to_vtk( self.var_data )  
        else:
            np_color_data = numpy.array( [0]*self.npoints, dtype=numpy.uint8 )
            self.vtk_color_data = numpy_support.numpy_to_vtk( np_color_data )   
            self.vtk_color_data.SetName( "Colors" )        
                       
        mappers = []
        if show_mesh:
            mesh_mapper = self.generate_mesh( vtk_points, cells_cutoff )
            mappers.append( mesh_mapper )
            
        if show_points:
            points_mapper = self.generate_points( vtk_points )
            mappers.append( points_mapper )

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(1,1,1)
        self.renderWindow = vtk.vtkRenderWindow()
        self.renderWindow.AddRenderer( self.renderer )
        self.renderWindowInteractor = vtk.vtkRenderWindowInteractor()   
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.renderWindowInteractor.SetInteractorStyle(style)
        self.renderWindowInteractor.SetRenderWindow( self.renderWindow )
        self.renderWindowInteractor.AddObserver( 'CharEvent', self.onKeyPress )       
        self.renderWindowInteractor.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )                       

        pointPicker = vtk.vtkPointPicker()
        pointPicker.PickFromListOn()
        self.renderWindowInteractor.SetPicker(pointPicker)             
        
        lut = self.get_LUT( invert = True, number_of_colors = 1024 ) if use_colormap else None
        
        for mapper in mappers:               
            if lut:              
                mapper.SetScalarRange( vmin, vmax ) 
                mapper.SetScalarModeToUsePointData()
                mapper.SetColorModeToMapScalars()
                mapper.SetLookupTable( lut )
             
            actor = vtk.vtkActor()
            actor.SetMapper( mapper )
            actor.GetProperty().SetPointSize(point_size)        
            self.renderer.AddActor( actor )
            pointPicker.AddPickList( actor )     
        
        if (self.plot_type == PlotType.Spherical) and show_map:
            earth_source = vtk.vtkEarthSource()
            earth_source.SetRadius(1.01)
            earth_source.OutlineOn()
            earth_polydata = earth_source.GetOutput()
            earth_mapper = vtk.vtkPolyDataMapper()

            if vtk.VTK_MAJOR_VERSION <= 5:
                earth_mapper.SetInput(earth_polydata)
            else:
                earth_mapper.SetInputData(earth_polydata)

            earth_actor = vtk.vtkActor()
            earth_actor.SetMapper( earth_mapper )
            self.renderer.AddActor( earth_actor )
                  
               
        self.renderWindow.Render()
        self.renderWindowInteractor.Start()

if __name__ == '__main__':
    CAM_file = "/Users/tpmaxwel/Data/CAM/f1850c5_t2_ANN_climo-native.nc"
    grid_file = "/Users/tpmaxwel/Data/CAM/ne120np4_latlon.nc"
#    varname = "U"
    varname = "PS"

    g = GridTest()
    g.plot( CAM_file, grid_file, varname )