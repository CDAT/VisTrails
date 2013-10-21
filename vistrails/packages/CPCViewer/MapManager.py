'''
Created on Oct 10, 2013

@author: tpmaxwell
'''

import sys
import os.path
import vtk, time
from PyQt4 import QtCore, QtGui
import numpy as np
import os, vtk
from PointCollection import PlotType

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultMapFile = os.path.join( defaultMapDir,  'earth2k.jpg' )
defaultMapCut = -180

def NormalizeLon( lon ): 
    while lon < 0: lon = lon + 360
    return lon % 360  
            
class MapManager( QtCore.QObject ):
    
    def __init__(self, **args ):
        super( MapManager, self ).__init__()  
        self.baseMapActor = None
        self.sphereActor = None
        self.map_opacity = args.get('opacity',0.5)
        self.map_border_size = args.get( "map_border_size", 20  ) 
        self.roi = args.get( "roi", [ 0.0, 360.0, -90.0, 90.0 ] )
        self.world_cut = args.get( "world_cut", -1 ) 
        self.enableBasemap = args.get( "enable_basemap", True )
        self.y0 = -90.0 

    def getMapOpacity(self):
        return self.map_opacity
    
    def setMapOpacity(self, opacity_vals, **args ):
        self.map_opacity = opacity_vals[0]
        self.updateMapOpacity() 
        
    def getSphericalMap( self, **args ):
        thetaResolution = args.get( "thetaRes", 64 )
        phiResolution = args.get( "phiRes", 64 )
        radius = args.get( "radius", 100 )
        lon_range = args.get( "lon_range", [ -180.0, 180.0 ] )
        lat_range = args.get( "lat_range", [ 90.0, -90.0 ] )
        if self.sphereActor == None: 
            self.sphere = vtk.vtkSphereSource()
            self.sphere.SetThetaResolution( thetaResolution )
            self.sphere.SetPhiResolution( phiResolution )
            self.sphere.SetRadius( radius )
#             self.sphere.SetStartTheta( lon_range[0] )        
#             self.sphere.SetEndTheta( lon_range[1] ) 
#             self.sphere.SetStartPhi( lat_range[0] )        
#             self.sphere.SetEndPhi( lat_range[1] )        
       
            mesh = self.sphere.GetOutput()
            
            self.sphereTexmapper = vtk.vtkTextureMapToSphere()
            self.sphereTexmapper.SetInput(mesh)
            self.sphereTexmapper.PreventSeamOff()
            
            self.sphereMapper = vtk.vtkPolyDataMapper()
            self.sphereMapper.SetInput(self.sphereTexmapper.GetOutput())
           
#             imageFlipper = vtk.vtkImageReslice()
#             imageFlipper.SetInput( self.baseImage )
#             resliceAxes = vtk.vtkMatrix4x4()
#             resliceAxes.Identity()
#             resliceAxes.SetElement( 1, 1, -1 )
#             imageFlipper.SetResliceAxesOrigin( 0, 0, 0 )              
#             imageFlipper.SetResliceAxes( resliceAxes )
                        
            imageFlipper = vtk.vtkImageFlip()
            imageFlipper.SetInput( self.baseImage )
            imageFlipper.SetFilteredAxis( 1 ) 
            
            self.sphereTexture = vtk.vtkTexture()
            self.sphereTexture.SetInput( imageFlipper.GetOutput()  )
            
            self.sphereActor = vtk.vtkActor()
            self.sphereActor.SetMapper(self.sphereMapper)
            self.sphereActor.SetTexture(self.sphereTexture)
#            self.sphereActor.GetProperty().SetOpacity( self.map_opacity )
            self.sphereActor.SetVisibility( False )  

        return self.sphereActor
  
    def updateMapOpacity(self, cmap_index=0 ):
        if self.baseMapActor:
            self.baseMapActor.SetOpacity( self.map_opacity )
#         if self.sphereActor:
#             self.sphereActor.GetProperty().SetOpacity( self.map_opacity )
        self.render()
        
    def build( self, **args ):
        if self.enableBasemap:              
            world_map =  None                 
            dataPosition = None
            if world_map == None:
                self.map_file = defaultMapFile
                self.map_cut = defaultMapCut
            else:
                self.map_file = world_map[0].name
                self.map_cut = world_map[1]
            
            roi_size = [ self.roi[1] - self.roi[0], self.roi[3] - self.roi[2] ] 
            map_cut_size = [ roi_size[0] + 2*self.map_border_size, roi_size[1] + 2*self.map_border_size ]
            if map_cut_size[0] > 360.0: map_cut_size[0] = 360.0
            if map_cut_size[1] > 180.0: map_cut_size[1] = 180.0
#            data_origin = self.input().GetOrigin() if self.input() else [ 0, 0, 0 ]
                      
            if self.world_cut == -1: 
                if  (self.roi <> None): 
                    if roi_size[0] > 180:             
                        self.ComputeCornerPosition()
                        self.world_cut = self.NormalizeMapLon( self.x0 )
                    else:
                        dataPosition = [ ( self.roi[1] + self.roi[0] ) / 2.0, ( self.roi[3] + self.roi[2] ) / 2.0 ]
                else:
                    self.world_cut = self.map_cut
            
            self.imageInfo = vtk.vtkImageChangeInformation()        
            self.image_reader = vtk.vtkJPEGReader()      
            self.image_reader.SetFileName(  self.map_file )
            self.baseImage = self.image_reader.GetOutput() 
            new_dims, scale = None, None
            if dataPosition == None:    
                self.baseImage = self.RollMap( self.baseImage ) 
                new_dims = self.baseImage.GetDimensions()
                scale = [ 360.0/new_dims[0], 180.0/new_dims[1], 1 ]
            else:                       
                self.baseImage, new_dims = self.getBoundedMap( self.baseImage, dataPosition, map_cut_size, self.map_border_size )             
                scale = [ map_cut_size[0]/new_dims[0], map_cut_size[1]/new_dims[1], 1 ]
    #        printArgs( " baseMap: ", extent=baseImage.GetExtent(), spacing=baseImage.GetSpacing(), origin=baseImage.GetOrigin() )        
                              
            self.baseMapActor = vtk.vtkImageActor()
            self.baseMapActor.SetOrigin( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetScale( scale )
            self.baseMapActor.SetOrientation( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetOpacity( self.map_opacity )
    #        self.baseMapActor.SetDisplayExtent( -1,  0,  0,  0,  0,  0 )
            print "Positioning map at location %s" % ( str( ( self.x0, self.y0) )  ) 
            mapCorner = [ self.x0, self.y0 ]
#            if ( ( self.roi[0]-map_border_size ) < 0.0 ): mapCorner[0] = mapCorner[0] - 360.0
#            print " DV3DCell, mapCorner = %s, dataPosition = %s, cell_location = %s " % ( str(mapCorner), str(dataPosition), cell_location )
                    
            self.baseMapActor.SetPosition( mapCorner[0], mapCorner[1], 0.1 )
            self.baseMapActor.SetInput( self.baseImage )
            self.mapCenter = [ self.x0 + map_cut_size[0]/2.0, self.y0 + map_cut_size[1]/2.0 ]  
            
    def getBaseMapActor(self):
        if self.baseMapActor == None: self.build()  
        return self.baseMapActor 
    
    def setMapVisibility( self, topo  ):
        if topo == PlotType.Planar:
            mapCorner = [ self.x0, self.y0 ]
            self.baseMapActor.SetOrigin( 0.0, 0.0, 0.0 )
            self.baseMapActor.SetPosition( mapCorner[0], mapCorner[1], 0.1 )
            self.baseMapActor.SetVisibility( True )  
            self.sphereActor.SetVisibility( False )  
            print "Positioning map at location %s" % ( str( ( self.x0, self.y0) )  ) 
        elif topo == PlotType.Spherical:
            self.baseMapActor.SetVisibility( False )  
            self.sphereActor.SetVisibility( True )  
            
    def ComputeCornerPosition( self ):
        if (self.roi[0] >= -180) and (self.roi[1] <= 180) and (self.roi[1] > self.roi[0]):
            self.x0 = -180
            return 180
        if (self.roi[0] >= 0) and (self.roi[1] <= 360) and (self.roi[1] > self.roi[0]):
            self.x0 = 0
            return 0
        self.x0 = int( round( self.roi[0] / 10.0 ) ) * 10
#        print "Set Corner pos: %s, roi: %s " % ( str(self.x0), str(self.roi) )
        
    def GetScaling( self, image_dims ):
        return 360.0/image_dims[0], 180.0/image_dims[1],  1

    def GetFilePath( self, cut ):
        filename = "%s_%d.jpg" % ( self.world_image, cut )
        return os.path.join( self.data_dir, filename ) 
        
    def RollMap( self, baseImage ):
        baseImage.Update()
        if self.world_cut  == self.map_cut: return baseImage
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        newCut = self.NormalizeMapLon( self.world_cut )
        delCut = newCut - self.map_cut
#        print "  %%%%%% Roll Map %%%%%%: world_cut=%.1f, map_cut=%.1f, newCut=%.1f " % ( float(self.world_cut), float(self.map_cut), float(newCut) )
        imageLen = x1 - x0 + 1
        sliceSize =  imageLen * ( delCut / 360.0 )
        sliceCoord = int( round( x0 + sliceSize) )        
        extent = list( baseExtent ) 
        
        extent[0:2] = [ x0, x0 + sliceCoord - 1 ]
        clip0 = vtk.vtkImageClip()
        clip0.SetInput( baseImage )
        clip0.SetOutputWholeExtent( extent[0], extent[1], extent[2], extent[3], extent[4], extent[5] )
        
        extent[0:2] = [ x0 + sliceCoord, x1 ]
        clip1 = vtk.vtkImageClip()
        clip1.SetInput( baseImage )
        clip1.SetOutputWholeExtent( extent[0], extent[1], extent[2], extent[3], extent[4], extent[5] )
        
        append = vtk.vtkImageAppend()
        append.SetAppendAxis( 0 )
        append.AddInput( clip1.GetOutput() )          
        append.AddInput( clip0.GetOutput() )
        
        imageInfo = vtk.vtkImageChangeInformation()
        imageInfo.SetInputConnection( append.GetOutputPort() ) 
        imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
        imageInfo.SetOutputExtentStart( 0, 0, 0 )
        imageInfo.SetOutputSpacing( baseSpacing[0], baseSpacing[1], baseSpacing[2] )
        
        result = imageInfo.GetOutput() 
        result.Update()
        return result

    def NormalizeMapLon( self, lon ): 
        while ( lon < ( self.map_cut - 0.01 ) ): lon = lon + 360
        return ( ( lon - self.map_cut ) % 360 ) + self.map_cut

    def getBoundedMap( self, baseImage, dataLocation, map_cut_size, map_border_size ):
        baseImage.Update()
        baseExtent = baseImage.GetExtent()
        baseSpacing = baseImage.GetSpacing()
        x0 = baseExtent[0]
        x1 = baseExtent[1]
        y0 = baseExtent[2]
        y1 = baseExtent[3]
        imageLen = [ x1 - x0 + 1, y1 - y0 + 1 ]
        selectionDim = [ map_cut_size[0]/2, map_cut_size[1]/2 ]
        dataXLoc = dataLocation[0]
        imageInfo = vtk.vtkImageChangeInformation()
        dataYbounds = [ dataLocation[1]-selectionDim[1], dataLocation[1]+selectionDim[1] ]
        vertExtent = [ y0, y1 ]
        bounded_dims = None
        if dataYbounds[0] > -90.0:
            yOffset = dataYbounds[0] + 90.0
            extOffset = int( round( ( yOffset / 180.0 ) * imageLen[1] ) )
            vertExtent[0] = y0 + extOffset
            self.y0 = dataYbounds[0]
        if dataYbounds[1] < 90.0:
            yOffset = 90.0 - dataYbounds[1]
            extOffset = int( round( ( yOffset / 180.0 ) * imageLen[1] ) )
            vertExtent[1] = y1 - extOffset
            
        overlapsBorder = ( self.NormalizeMapLon(dataLocation[0]-selectionDim[0]) > self.NormalizeMapLon(dataLocation[0]+selectionDim[0]) )
        if overlapsBorder:
            cut0 = self.NormalizeMapLon( dataXLoc + selectionDim[0] )
            sliceSize =  imageLen[0] * ( ( cut0 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0:2] = [ x0, x0 + sliceCoord - 1 ]
            clip0 = vtk.vtkImageClip()
            clip0.SetInput( baseImage )
            clip0.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size0 = extent[1] - extent[0] + 1
        
            self.x0 = dataLocation[0] - selectionDim[0]
            cut1 = self.NormalizeMapLon( self.x0 ) 
            sliceSize =  imageLen[0] * ( ( cut1 - self.map_cut )/ 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[0:2] = [ x0 + sliceCoord, x1 ]
            clip1 = vtk.vtkImageClip()
            clip1.SetInput( baseImage )
            clip1.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            size1 = extent[1] - extent[0] + 1
#            print "Set Corner pos: %s, cuts: %s " % ( str(self.x0), str( (cut0, cut1) ) )
        
            append = vtk.vtkImageAppend()
            append.SetAppendAxis( 0 )
            append.AddInput( clip1.GetOutput() )          
            append.AddInput( clip0.GetOutput() )
            bounded_dims = ( size0 + size1, vertExtent[1] - vertExtent[0] + 1 )
            
            imageInfo.SetInputConnection( append.GetOutputPort() ) 

        else:
                        
            self.x0 = dataXLoc - selectionDim[0]
            cut0 = self.NormalizeMapLon( self.x0 )
            sliceSize =  imageLen[0] * ( ( cut0 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )        
            extent = list( baseExtent )         
            extent[0] = x0 + sliceCoord - 1
        
            cut1 = self.NormalizeMapLon( dataXLoc + selectionDim[0] )
            sliceSize =  imageLen[0] * ( ( cut1 - self.map_cut ) / 360.0 )
            sliceCoord = int( round( x0 + sliceSize) )       
            extent[1] = x0 + sliceCoord
            clip = vtk.vtkImageClip()
            clip.SetInput( baseImage )
            clip.SetOutputWholeExtent( extent[0], extent[1], vertExtent[0], vertExtent[1], extent[4], extent[5] )
            bounded_dims = ( extent[1] - extent[0] + 1, vertExtent[1] - vertExtent[0] + 1 )
#            print "Set Corner pos: %s, dataXLoc: %s " % ( str(self.x0), str( (dataXLoc, selectionDim[0]) ) )

            imageInfo.SetInputConnection( clip.GetOutputPort() ) 
                       
        imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
        imageInfo.SetOutputExtentStart( 0, 0, 0 )
        imageInfo.SetOutputSpacing( baseSpacing[0], baseSpacing[1], baseSpacing[2] )
        
        result = imageInfo.GetOutput() 
        result.Update()
        return result, bounded_dims
    
