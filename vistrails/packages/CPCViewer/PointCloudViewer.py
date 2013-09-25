'''
Created on Aug 29, 2013

@author: tpmaxwel
'''

import sys
import os.path
import vtk, time
from PyQt4 import QtCore, QtGui
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from DistributedPointCollections import vtkPartitionedPointCloud, vtkLocalPointCloud

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
    def isLevelAxis( cls, pid ):
        if ( pid.find('level')  >= 0 ): return True
        if ( pid.find('bottom') >= 0 ) and ( pid.find('top') >= 0 ): return True
        if pid in cls.LevelAliases: return True
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
    Resolution = 3
    ColorScale = 4
    HighRes = 0
    LowRes = 1
    AnyRes = 3
 
class TextDisplayMgr:
    
    def __init__( self, renderer ):
        self.renderer = renderer
    
    def setTextPosition(self, textActor, pos, size=[400,30] ):
#        vpos = [ 2, 2 ] 
        vp = self.renderer.GetSize()
        vpos = [ pos[i]*vp[i] for i in [0,1] ]
        textActor.GetPositionCoordinate().SetValue( vpos[0], vpos[1] )      
        textActor.GetPosition2Coordinate().SetValue( vpos[0] + size[0], vpos[1] + size[1] )      
  
    def getTextActor( self, aid, text, pos, **args ):
        textActor = self.getProp( 'vtkTextActor', aid  )
        if textActor == None:
            textActor = self.createTextActor( aid, **args  )
            self.renderer.AddViewProp( textActor )
        self.setTextPosition( textActor, pos )
        text_lines = text.split('\n')
        linelen = len(text_lines[-1])
        if linelen < MIN_LINE_LEN: text += (' '*(MIN_LINE_LEN-linelen)) 
        text += '.'
        textActor.SetInput( text )
        textActor.Modified()
        return textActor

    def getProp( self, ptype, pid = None ):
        try:
            props = self.renderer.GetViewProps()
            nitems = props.GetNumberOfItems()
            for iP in range(nitems):
                prop = props.GetItemAsObject(iP)
                if prop.IsA( ptype ):
                    if not pid or (prop.id == pid):
                        return prop
        except: 
            pass
        return None
  
    def createTextActor( self, aid, **args ):
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
        textActor.id = aid
        return textActor 

        
class CPCPlot(QtCore.QObject):  
    
    sliceAxes = [ 'x', 'y', 'z' ]  

    def __init__( self, vtk_render_window, **args ):
        QtCore.QObject.__init__( self )
        self.partitioned_point_cloud = None
        self.renderWindow = vtk_render_window
        self.renderWindowInteractor = self.renderWindow.GetInteractor()
        style = args.get( 'istyle', vtk.vtkInteractorStyleTrackballCamera() )  
        self.renderWindowInteractor.SetInteractorStyle( style )
        self.process_mode = ProcessMode.Default
        self.xcenter = 100.0
        self.xwidth = 300.0
        self.windowPosition = 0.5
        self.windowPositionSensitivity = 0.05
        self.windowWidth = 0.03
        self.windowWidthSensitivity = 0.05
        self.isValid = True
        self.point_size = 1
        self.cameraOrientation = {}
        self.topo = PlotType.Planar
        self.sliceAxisIndex = 0
        self.slicePosition = [ 0.5, 0.5, 0.5 ]
        self.sliceWidth = [ 0.005, 0.005, 0.005 ]
        self.sliceWidthSensitivity = [ 0.005, 0.005, 0.005 ]
        self.slicePositionSensitivity = [ 0.025, 0.025, 0.025 ]
        self.currentScalarRange = None
        self.updatedScalarRange = None
        self.nlevels = None
        self.colorWindowPosition = 0.5
        self.colorWindowWidth = 1.0
        self.windowWidthSensitivity = 0.1 
        self.colorWindowPositionSensitivity = 0.1
        self.render_mode = ProcessMode.HighRes
       
    def invalidate(self):
        self.isValid = False
        
    def toggleRenderMode( self ):     
        new_render_mode = ( self.render_mode + 1 ) % 2 
        self.setRenderMode( new_render_mode )
        self.render()
        
    def getPointCloud(self):
        return self.partitioned_point_cloud if ( self.render_mode ==  ProcessMode.HighRes ) else self.point_cloud_overview 

    def getPointClouds(self):
        return [ self.partitioned_point_cloud, self.point_cloud_overview ]
       
    def setRenderMode( self, render_mode ): 
        self.render_mode = render_mode
        if render_mode ==  ProcessMode.HighRes:
            self.low_res_actor.VisibilityOff() 
            self.partitioned_point_cloud.show()      
        else: 
            self.partitioned_point_cloud.clear()
            self.low_res_actor.VisibilityOn()
            self.shiftThresholding( 0, 0 ) 
        self.setScalarRange( self.currentScalarRange )   
#    def refreshResolution( self ):
#        self.setPointSize( self.raw_point_size )
#        downsizeFactor = int( math.ceil( self.getNumberOfPoints() / float( self.downsizeNPointsTarget ) ) ) 
#        self.pointMask.SetOnRatio( downsizeFactor )
#        self.pointMask.Modified()
#        self.threshold_filter.Modified()
#        self.geometry_filter.Modified()
                
        
    def getLabelActor(self):
        return self.textDisplayMgr.getTextActor( 'label', self.labelBuff, (.01, .95), size = VTK_NOTATION_SIZE, bold = True  )

    def updateTextDisplay( self, text, render=False ):
        self.labelBuff = str(text)
        self.getLabelActor().VisibilityOn() 
        if render: self.render()     
    
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
        if not shift: return
        x, y = caller.GetEventPosition()
        picker = caller.GetPicker()
        picker.Pick( x, y, 0, self.renderer )
        actor = picker.GetActor()
        if actor:
            iPt = picker.GetPointId()
            if iPt >= 0:                
                pick_pos, dval = self.partitioned_point_cloud.getPoint( actor, iPt ) 
#                 if self.topo == PlotType.Spherical:
#                     pick_pos = glev.vtk_points_data.GetPoint( iPt )
#                 else:
#                     pick_pos = picker.GetPickPosition()                       
                text = " Point[%d] ( %.2f, %.2f ): %s " % ( iPt, pick_pos[0], pick_pos[1], dval )
                self.updateTextDisplay( text )
            
    def toggleTopo(self):
        self.recordCamera()
        self.topo = ( self.topo + 1 ) % 2
        pts =  [  self.partitioned_point_cloud.setTopo( self.topo ),
                  self.point_cloud_overview.setTopo( self.topo)    ] 
        if pts[self.render_mode]:
            self.resetCamera( pts[self.render_mode] )
            self.renderer.ResetCameraClippingRange()   
        self.render()
        
    def render( self, onMode = ProcessMode.AnyRes ):
        if (onMode == ProcessMode.AnyRes) or ( onMode == self.render_mode ):
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
 
           
#    def moveSlicePlane( self, distance = 0 ):
#        self.setProcessMode( ProcessMode.Slicing )      
#        if( distance <> 0 ): self.toggleResolution( 1 )
#        if self.sliceOrientation == 'x': 
#            self.sliceIndex[0] = self.sliceIndex[0] + distance
#            if self.sliceIndex[0] < 0: self.sliceIndex[0] = 0
#            if self.sliceIndex[0] >= len(self.lon_slice_positions): self.sliceIndex[0] = len(self.lon_slice_positions) - 1
#            position = self.lon_slice_positions[ self.sliceIndex[0] ]
#        if self.sliceOrientation == 'y': 
#            self.sliceIndex[1] = self.sliceIndex[1] + distance
#            if self.sliceIndex[1] < 0: self.sliceIndex[1] = 0
#            if self.sliceIndex[1] >= len(self.lat_slice_positions): self.sliceIndex[1] = len(self.lat_slice_positions) - 1
#            position = self.lat_slice_positions[ self.sliceIndex[1] ]
#        if self.sliceOrientation == 'z': 
#            self.sliceIndex[1] = self.sliceIndex[1] + distance
#            if self.sliceIndex[1] < 0: self.sliceIndex[1] = 0
#            if self.sliceIndex[1] >= len(self.lev): self.sliceIndex[1] = len(self.lev) - 1
#            position = self.sliceIndex[1] * self.z_spacing
#                
#        self.setSliceThresholdBounds( position ) 
#        if distance <> 0: self.renderWindow.Render() 
#        print "Initial # points, cells: %d, %d " % ( self.polydata.GetNumberOfPoints(), self.polydata.GetNumberOfCells() )
#        print "After Mask: %d, %d " % ( self.pointMask.GetOutput().GetNumberOfPoints(), self.pointMask.GetOutput().GetNumberOfCells() )
#        print "After Threshold: %d, %d " % ( self.threshold_filter.GetOutput().GetNumberOfPoints(), self.threshold_filter.GetOutput().GetNumberOfCells() )
      

    def processEvent(self, eventArgs ):
        if eventArgs[0] == "KeyEvent":
            self.onKeyEvent( eventArgs[1:])
            
    def onKeyEvent(self, eventArgs ):
        key = eventArgs[0]
        keysym =  eventArgs[1]
        mods = eventArgs[2]
        shift = mods & QtCore.Qt.ShiftModifier
        ctrl = mods & QtCore.Qt.ControlModifier
        alt = mods & QtCore.Qt.AltModifier
#        print " KeyPress %x '%s' %d %d %d" % ( key, keysym, shift, ctrl, alt ) 
        sys.stdout.flush()
        upArrow = QtCore.Qt.Key_Up
        if key == upArrow:
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( 1, 0 )  
            elif self.process_mode == ProcessMode.Resolution:
                self.shiftResolution( 1, 0 )  
            elif self.process_mode == ProcessMode.Slicing: 
                self.shiftSlice( 1, 0 )
            elif self.process_mode == ProcessMode.ColorScale: 
                self.shiftColorScale( 1, 0 )            
        if key == QtCore.Qt.Key_Down:
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( -1, 0 ) 
            elif self.process_mode == ProcessMode.Resolution:
                self.shiftResolution( -1, 0 )  
            elif self.process_mode == ProcessMode.Slicing: 
                self.shiftSlice( -1, 0 )
            elif self.process_mode == ProcessMode.ColorScale: 
                self.shiftColorScale( -1, 0 )            
                
#            distance = -1 if self.inverted_levels else 1
#         if distance:
#             self.moveSlicePlane( distance ) 
# 
    
        if key == QtCore.Qt.Key_Left:   
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( 0, -1 )
            elif self.process_mode == ProcessMode.Resolution: 
                self.shiftResolution( 0, -1 )
            elif self.process_mode == ProcessMode.Slicing: 
                self.shiftSlice( 0, -1 )
            elif self.process_mode == ProcessMode.ColorScale: 
                self.shiftColorScale( 0, -1 )            
        if key == QtCore.Qt.Key_Right:       
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( 0, 1 )
            elif self.process_mode == ProcessMode.Resolution: 
                self.shiftResolution( 0, 1 ) 
            elif self.process_mode == ProcessMode.Slicing: 
                self.shiftSlice( 0, 1 )
            elif self.process_mode == ProcessMode.ColorScale: 
                self.shiftColorScale( 0, 1 )            
            
        if   keysym == "s":  self.toggleTopo()
        elif keysym == "t":  self.stepTime()
        elif keysym == "T":  self.stepTime( False )
        elif keysym == "c":  self.toggleClipping()
        elif keysym == "m":  self.toggleRenderMode()
        elif keysym == "p":
            if self.process_mode == ProcessMode.Slicing:
                self.sliceAxisIndex =  ( self.sliceAxisIndex + 1 ) % 3   
            else:
                self.process_mode = ProcessMode.Slicing                          
            self.updateTextDisplay( "Mode: Slicing", True )
            self.shiftSlice( 0, 0 )
        elif keysym == "r":  
            self.process_mode = ProcessMode.Resolution
            self.updateTextDisplay( "Mode: Resolution", True ) 
        elif keysym == "C":  
            self.process_mode = ProcessMode.ColorScale
            self.updateTextDisplay( "Mode: ColorScale", True ) 
        elif keysym == "v":
            self.updateTextDisplay( "Mode: Thresholding", True )
            self.process_mode = ProcessMode.Thresholding 
            self.shiftThresholding( 0, 0 )  
        elif keysym == "i":  self.setPointIndexBounds( 5000, 7000 )
    
    def shiftSlice( self, position_inc, width_inc ): 
        if position_inc <> 0:
            self.slicePosition[self.sliceAxisIndex] = self.slicePosition[self.sliceAxisIndex] + position_inc * self.slicePositionSensitivity[self.sliceAxisIndex]
        if width_inc <> 0:
            if self.sliceWidth[self.sliceAxisIndex] < 2 * self.sliceWidthSensitivity[self.sliceAxisIndex]:
                self.sliceWidth[self.sliceAxisIndex]  *  2.0**width_inc 
            else:
                self.sliceWidth[self.sliceAxisIndex] = self.sliceWidth[self.sliceAxisIndex] + width_inc * self.sliceWidthSensitivity[self.sliceAxisIndex]
         
        slice_radius = self.sliceWidth[self.sliceAxisIndex]/2.0      
        pmin = max( self.slicePosition[self.sliceAxisIndex] - slice_radius, 0.0 )
        pmin = min( pmin, 1.0 - self.sliceWidth[self.sliceAxisIndex] )
        pmax = min( self.slicePosition[self.sliceAxisIndex] + slice_radius, 1.0 )
        pmax = max( pmax, self.sliceWidth[self.sliceAxisIndex] )
        self.updateSlicing( self.sliceAxisIndex, pmin, pmax )

    def shiftColorScale( self, position_inc, width_inc ):
        if position_inc <> 0:
            self.colorWindowPosition = self.colorWindowPosition + position_inc * self.colorWindowPositionSensitivity
        if width_inc <> 0:
            if self.colorWindowWidth < 2 * self.windowWidthSensitivity:
                self.colorWindowWidth = self.colorWindowWidth *  2.0**width_inc 
            else:
                self.colorWindowWidth = self.colorWindowWidth + width_inc * self.windowWidthSensitivity
        window_radius = self.colorWindowWidth/2.0    
        rmin = max( self.colorWindowPosition - window_radius, 0.0 )
        rmin = min( rmin, 1.0 - self.windowWidth )
        rmax = min( self.colorWindowPosition + window_radius, 1.0 )
        rmax = max( rmax, self.windowWidth )
        ds = self.currentScalarRange[1] - self.currentScalarRange[0]
        smin = self.currentScalarRange[0] + ds * rmin
        smax = self.currentScalarRange[0] + ds * rmax
        self.setScalarRange( ( smin, smax ) )
                      
    def shiftThresholding( self, position_inc, width_inc ):
        if position_inc <> 0:
            self.windowPosition = self.windowPosition + position_inc * self.windowPositionSensitivity
        if width_inc <> 0:
            if self.windowWidth < 2 * self.windowWidthSensitivity:
                self.windowWidth = self.windowWidth *  2.0**width_inc 
            else:
                self.windowWidth = self.windowWidth + width_inc * self.windowWidthSensitivity
        window_radius = self.windowWidth/2.0    
        rmin = max( self.windowPosition - window_radius, 0.0 )
        rmin = min( rmin, 1.0 - self.windowWidth )
        rmax = min( self.windowPosition + window_radius, 1.0 )
        rmax = max( rmax, self.windowWidth )
        self.updateThresholding( 'vardata', rmin, rmax )

    def shiftResolution( self, ncollections_inc, ptsize_inc ):
        if ncollections_inc <> 0:
            self.partitioned_point_cloud.updateNumActiveCollections( ncollections_inc )
        if ptsize_inc <> 0:
            self.updatePointSize( ptsize_inc )
        
    def updateThresholding( self, target, rmin, rmax ):
        subset_spec = ( target, rmin, rmax )
        self.invalidate()
        for pc in self.getPointClouds():
            pc.generateSubset( subset_spec )
        self.render( ProcessMode.LowRes )
#         print " setVolumeRenderBounds: %s " % str( subset_spec )
#         sys.stdout.flush()

    def updateSlicing( self, sliceIndex, rmin, rmax ):
        subset_spec = ( self.sliceAxes[sliceIndex], rmin, rmax )
        self.invalidate()
        for pc in self.getPointClouds():
            pc.generateSubset( subset_spec )
        self.render( ProcessMode.LowRes )
#         print " setThresholdingBounds: %s " % str( subset_spec )
#         sys.stdout.flush()
        
    
      
#    def print_grid_coords( self, npoints ):
#        origin = [ self.lon_data[0], self.lat_data[0] ]
#        for iPt in range( npoints ):
#            lat = self.lat_data[iPt]
#            lon = self.lon_data[iPt]
#            x = ( lon - origin[0] ) * 5
#            y = ( lat - origin[1] ) * 5 
#            print " Point[%d]: ( %.2f, %.2f )" % ( iPt, x, y )

#    def print_cell_coords( self, npoints ):
#        for iPt in range( npoints ):
#            corners = self.element_corners_data[:,iPt]
#            print " Quad[%d]: %s" % ( iPt, str(corners) )
#            
#    def updateLevelVisibility(self):
#        if self.setVisiblity( self.iLevel ) and ( self.iLevel >= 0 ):
#            self.renderer.ResetCameraClippingRange() # ResetCamera( glev.getBounds() )
#            if self.lev:
#                lval = self.lev[ self.iLevel ]
#                self.updateTextDisplay( "Level: %.2f, %s " % ( lval, self.lev.units ) )
#        self.renderWindow.Render()
        
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
            
    def updatePointSize( self, point_size_inc=0):
        self.point_size = self.point_size + point_size_inc
        self.setPointSize( self.point_size )
        self.renderWindow.Render()

#    def stepTime( self, forward = True ):
#        ntimes = len(self.time) if self.time else 1
#        self.iTimeStep = self.iTimeStep + 1 if forward else self.iTimeStep - 1
#        if self.iTimeStep < 0: self.iTimeStep = ntimes - 1
#        if self.iTimeStep >= ntimes: self.iTimeStep = 0
#        try:
#            tvals = self.time.asComponentTime()
#            tvalue = str( tvals[ self.iTimeStep ] )
#            self.updateTextDisplay( "Time: %s " % tvalue )
#        except Exception, err:
#            print>>sys.stderr, "Can't understand time metadata."
#        np_var_data_block = self.getDataBlock()
#        var_data = np_var_data_block[:] if ( self.nLevels == 1 ) else np_var_data_block[ :, : ]    
#        self.setVarData( var_data ) 
#        self.renderWindow.Render()

      
#                            
#    def plot( self, data_file, grid_file, varname, **args ): 
#        color_index = args.get( 'color_index', -1 )
#        self.inverted_levels = False
#        self.topo = args.get( 'topo', PlotType.Spherical )
#        npts_cutoff = args.get( 'max_npts', -1 )
#        ncells_cutoff = args.get( 'max_ncells', -1 )
#        self.iVizLevel = args.get( 'level', 0 )
#        self.z_spacing = args.get( 'z_spacing', 1.5 )
#        self.roi = args.get( 'roi', None )
#        
#        gf = cdms2.open( grid_file ) if grid_file else None
#        df = cdms2.open( data_file )       
#        lon, lat = self.getLatLon( df, varname, gf )
#        data_format = args.get( 'data_format', self.getDataFormat( df ) )
#                              
#        self.var = df[ varname ]
#        self.time = self.var.getTime()
#        self.lev = self.var.getLevel()
#        self.grid = self.var.getGrid()
#        missing_value = self.var.attributes.get( 'missing_value', None )
#        if self.lev == None:
#            domain = self.var.getDomain()
#            for axis in domain:
#                if PlotType.isLevelAxis( axis[0].id.lower() ):
#                    self.lev = axis[0]
#                    break
#                
#        np_var_data_block = self.getDataBlock()
#        
#        point_layout = self.getPointsLayout()
#        if point_layout == PlotType.Grid:
#            self.sliceThickness =[ (self.lon_data[1]-self.lon_data[0])/2.0, (self.lat_data[1]-self.lat_data[0])/2.0 ]
#
#        self.clippingPlanes = vtk.vtkPlanes()
#        if missing_value: var_data = numpy.ma.masked_equal( np_var_data_block, missing_value, False )
#        else: var_data = np_var_data_block
#        self.createThresholdedPolydata( lon=self.lon_data, lat=self.lat_data )
#        lut = self.get_LUT( invert = True, number_of_colors = 1024 )
#        self.setVarData( var_data, lut )          
#        self.createVertices()
#        if self.cropRegion == None: 
#            self.cropRegion = self.getBounds()
#        self.setPointSize( self.point_size )                                                                                     
#        self.createRenderer( **args )
#        self.moveSlicePlane() 
#        if (self.topo == PlotType.Spherical): self.CreateMap()               
#
#    def plotPoints( self, proc_exec, data_file, grid_file, varname, **args ):
#        gf = cdms2.open( grid_file ) if grid_file else None
#        df = cdms2.open( data_file )       
#        lon, lat = self.getLatLon( df, varname, gf )  
#        self.var = df[ varname ]
#        self.time = self.var.getTime()
#        self.lev = self.var.getLevel()
#        self.grid = self.var.getGrid()
#        self.proc_exec = proc_exec
#        
#        if self.lev == None:
#            domain = self.var.getDomain()
#            for axis in domain:
#                if PlotType.isLevelAxis( axis[0].id.lower() ):
#                    self.lev = axis[0]
#                    break
#        
#        lut = self.get_LUT( invert = True, number_of_colors = 1024 )
#        for iCore in range(proc_exec.ncores):        
#            self.createPolydata( icore=iCore, lut=lut )
#            self.setVarData( icore=iCore )          
#            self.createVertices( icore=iCore )
#        self.setPointSize( self.point_size )                                                                                     
#        self.createRenderer( **args )
#
#    def plotProduct( self, data_file, grid_file, varname, **args ): 
#        gf = cdms2.open( grid_file ) if grid_file else None
#        df = cdms2.open( data_file )       
#        lon, lat = self.getLatLon( df, varname, gf )  
#        self.var = df[ varname ]
#        self.time = self.var.getTime()
#        self.lev = self.var.getLevel()
#        self.grid = self.var.getGrid()
#        missing_value = self.var.attributes.get( 'missing_value', None )
#        if self.lev == None:
#            domain = self.var.getDomain()
#            for axis in domain:
#                if PlotType.isLevelAxis( axis[0].id.lower() ):
#                    self.lev = axis[0]
#                    break                                                                             
#        self.createRenderer( **args )          
#
#    def setSliceClipBounds( self, slicePosition = 0.0 ):
#        if self.lev == None: return
#        bounds = self.getBounds()
#        mapperBounds = None
#        if self.sliceOrientation == 'x':
#            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
#            mapperBounds = [ slicePosition-self.sliceThickness[0],  slicePosition+self.sliceThickness[0], bounds[2], bounds[3], lev_bounds[0], lev_bounds[1]  ]
#        if self.sliceOrientation == 'y':
#            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
#            mapperBounds = [ bounds[0], bounds[1], slicePosition - self.sliceThickness[1],  slicePosition + self.sliceThickness[1], lev_bounds[0], lev_bounds[1]  ]
#        if self.sliceOrientation == 'z':
#            sliceThickness = self.z_spacing/2
#            mapperBounds = [ bounds[0], bounds[1], bounds[2], bounds[3], slicePosition - sliceThickness,  slicePosition + sliceThickness  ]
#        if mapperBounds:
#            print "Setting clip planes: %s " % str( mapperBounds )
#            self.clipBox.SetBounds( mapperBounds )
#            self.slice_filter.Modified()
##             self.clipper.PlaceWidget( mapperBounds )
##             self.clipper.GetPlanes( self.clippingPlanes )
##             self.mapper.SetClippingPlanes( self.clippingPlanes )
#            self.mapper.Modified()
#            
#            
#    def setProcessMode( self, mode ):
#        self.process_mode = mode
#        self.setPointSize( self.reduced_point_sizes[mode] )
#       
#    def toggleSlicerVisibility( self ):
#        if self.sliceOrientation == 'y':
#            self.sliceOrientation = 'z'
#            self.moveSlicePlane()
#            self.slice_actor.SetVisibility( True  )  
#        if self.sliceOrientation == 'z':
#            self.sliceOrientation = 'x'
#            self.moveSlicePlane()
#        elif self.sliceOrientation == 'x':
#            self.sliceOrientation = 'y'
#            self.moveSlicePlane() 
#        self.renderWindow.Render()   
     
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
#        self.clipper.AddObserver( 'InteractionEvent', self.executeClip )
        self.clipOff() 

        
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
        
    def initCollections( self, nCollections, init_args ):
        self.partitioned_point_cloud = vtkPartitionedPointCloud( nCollections, init_args )
        self.partitioned_point_cloud.connect( self.partitioned_point_cloud, QtCore.SIGNAL('newDataAvailable'), self.newDataAvailable )
        self.partitioned_point_cloud.connect( self.partitioned_point_cloud, QtCore.SIGNAL('updateScaling'), self.updateScaling )        
        self.createRenderer()
        self.low_res_actor = self.point_cloud_overview.actor
        self.renderer.AddActor( self.low_res_actor )
        for point_cloud in  self.partitioned_point_cloud.values():     
            self.renderer.AddActor( point_cloud.actor )
        self.initCamera( )
        
    def updateScaling(self):
        self.applyScalarRangeUpdate()
        
    def applyScalarRangeUpdate(self):
        if self.updatedScalarRange and ( self.updatedScalarRange <> self.currentScalarRange ):
            self.setScalarRange( self.updatedScalarRange )
            self.currentScalarRange = self.updatedScalarRange
        
    def setScalarRange( self, scalar_range ):
        self.getPointCloud().setScalarRange(scalar_range )
        self.render()
        
    def reset( self, pcIndex ):
        if not self.isValid:
            self.partitioned_point_cloud.clear( pcIndex )
            self.isValid = True
            
    def updateScalarRange( self, scalar_range ):
        if self.updatedScalarRange == None:
            self.updatedScalarRange = list( scalar_range )
        else:
            self.updatedScalarRange[0] = min( self.updatedScalarRange[0], scalar_range[0] )
            self.updatedScalarRange[1] = max( self.updatedScalarRange[1], scalar_range[1] )

#        print " updateScalarRange: %s " % str( self.updatedScalarRange ); sys.stdout.flush()
        
    def updateZRange( self, pc ):
        nlev = pc.getNLevels()
        if nlev <> self.nlevels:
            self.nlevels = nlev
            self.sliceWidth[2] = 1.0/(self.nlevels)
            slice_index = round( self.slicePosition[2] / self.sliceWidth[2] ) 
            self.slicePosition[2] = slice_index * self.sliceWidth[2]
            self.sliceWidthSensitivity[2] = self.sliceWidth[2]
            self.slicePositionSensitivity[2] = self.sliceWidth[2]
               
    def newDataAvailable( self, pcIndex, data_type ): 
        pc = self.partitioned_point_cloud.getPointCloud( pcIndex )
        self.partitioned_point_cloud.postDataQueueEvent()
        sr = pc.getScalarRange() 
        if sr: self.updateScalarRange( sr )
        self.updateZRange( pc )
        if self.pointPicker.GetPickList().GetNumberOfItems() == 0: 
            self.pointPicker.AddPickList( pc.actor ) 
        text = " Thresholding Range[%d]: %s " % ( pcIndex, str( pc.getThresholdingRange() ) )
        self.updateTextDisplay( text )
#        print text; sys.stdout.flush()
        self.reset( pcIndex )
        self.render() 
                          
    def generateSubset(self, subset_spec ):
#        self.pointPicker.GetPickList().RemoveAllItems()
        if (subset_spec[0] == 'vardata'): self.updatedScalarRange = None       
        self.getPointCloud().generateSubset( subset_spec )        
        
    def terminate(self):
        for point_cloud in self.partitioned_point_cloud.values(): 
            point_cloud.terminate()  
          
    def setPointSize( self, point_size ) :  
        self.getPointCloud().setPointSize( point_size )    
      
    def init(self, **args ):
        init_args = args[ 'init_args' ]      
        nCollections = args.get( 'nCollections', 1 )    
        self.point_size = args.get( 'point_size', self.point_size )    
        self.point_cloud_overview = vtkLocalPointCloud( 0, 100 ) 
        self.point_cloud_overview.initialize( init_args )
        self.initCollections( nCollections, init_args )
        self.setPointSize( self.point_size )
        subset_spec =  ( 'vardata', 0.4, 0.6 ) 
        self.generateSubset( subset_spec )
 
    def update(self):
        pass


class QVTKAdaptor( QVTKRenderWindowInteractor ):
    
    def __init__( self, **args ):
        QVTKRenderWindowInteractor.__init__( self, **args )
        print str( dir( self ) )
    
    def keyPressEvent( self, qevent ):
        QVTKRenderWindowInteractor.keyPressEvent( self, qevent )
        self.emit( QtCore.SIGNAL('event'), ( 'KeyEvent', qevent.key(), str( qevent.text() ), qevent.modifiers() ) )
#        print " QVTKAdaptor keyPressEvent: %x [%s] " % ( qevent.key(), str( qevent.text() ) )
#        sys.stdout.flush()
    
class QPointCollectionMgrThread( QtCore.QThread ):
    
    def __init__( self, pointCollectionMgr, **args ):
        QtCore.QThread.__init__( self, parent=pointCollectionMgr )
        self.pointCollectionMgr = pointCollectionMgr
        self.delayTime = args.get( 'delayTime', 0.02 )
        self.args = args
        
    def init(self):
        self.pointCollectionMgr.init( **self.args )
         
    def run(self):
        while self.pointCollectionMgr.running:
            self.pointCollectionMgr.update()
            time.sleep( self.delayTime )
        self.exit(0)       
                             
if __name__ == '__main__':
    data_type = "CAM"
    data_dir = "/Users/tpmaxwel/data" 
    app = QtGui.QApplication(['Point Cloud Plotter'])
    widget = QVTKAdaptor()
    widget.Initialize()
    widget.Start()        
    point_size = 1
    nCollections = 16
    
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
        
    g = CPCPlot( widget.GetRenderWindow() ) 
    widget.connect( widget, QtCore.SIGNAL('event'), g.processEvent )  
    g.init( init_args = ( grid_file, data_file, varname ), nCollections=nCollections )
    
#     pointCollectionMgrThread = QPointCollectionMgrThread( g, init_args = ( grid_file, data_file, varname ), nCollections=nCollections )
#     pointCollectionMgrThread.init()
#    pointCollectionMgrThread.start()

    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
    widget.show()   
    app.exec_() 
    g.terminate()  

