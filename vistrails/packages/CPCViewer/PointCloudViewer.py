'''
Created on Aug 29, 2013

@author: tpmaxwel
'''

import sys, cdms2
import os.path, traceback
import vtk, time
from PyQt4 import QtCore, QtGui
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from DistributedPointCollections import vtkPartitionedPointCloud, vtkLocalPointCloud, ScalarRangeType, kill_all_zombies
from ControlPanel import CPCConfigGui, LevelingConfigParameter, POS_VECTOR_COMP, SLICE_WIDTH_HR_COMP, SLICE_WIDTH_LR_COMP
from ColorMapManager import *
from MapManager import MapManager

VTK_NO_MODIFIER         = 0
VTK_SHIFT_MODIFIER      = 1
VTK_CONTROL_MODIFIER    = 2        
VTK_TITLE_SIZE = 14
VTK_NOTATION_SIZE = 14
VTK_INSTRUCTION_SIZE = 24
MIN_LINE_LEN = 50

def getBool( val ):
    if isinstance( val, str ):
        if( val.lower()[0] == 't' ): return True
        if( val.lower()[0] == 'f' ): return False
        try:    val = int(val)
        except: pass
    return bool( val )
    
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
    LowRes = 0
    HighRes = 1
    AnyRes = 2

class ConfigMode:
    Default = 0
    Color = 1
    Points = 2
     
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

class Counter(): 
    
    def __init__( self, maxvalue = 0, minvalue = 0 ):
        self.floor = minvalue
        self.ceiling = maxvalue
        self.index = self.ceiling 
        self.active = True
        
    def reset( self, ceiling = -1 ):
        if ceiling >= 0: self.ceiling = ceiling
        self.index = self.ceiling 
        self.active = True
        
    def isActive(self):
        return self.active
        
    def setFloor(self, minvalue):
        self.floor = minvalue

    def setCeiling(self, maxvalue):
        self.ceiling = maxvalue
        
    def value(self):
        return self.index
        
    def decrement(self ):
        self.index = self.index - 1
        if self.index <= self.floor:
            self.active = False
            return True
        return False

class CPCPlot(QtCore.QObject):  
    
    sliceAxes = [ 'x', 'y', 'z' ]  

    def __init__( self, vtk_render_window, **args ):
        QtCore.QObject.__init__( self )
        self.partitioned_point_cloud = None
        self.point_cloud_overview = None
        self.renderWindow = vtk_render_window
        self.renderWindowInteractor = self.renderWindow.GetInteractor()
        style = args.get( 'istyle', vtk.vtkInteractorStyleTrackballCamera() )  
        self.renderWindowInteractor.SetInteractorStyle( style )
        self.process_mode = ProcessMode.Default
        self.config_mode = ConfigMode.Default
        self.xcenter = 100.0
        self.xwidth = 300.0
        self.ycenter = 0.0
        self.ywidth = 180.0

        self.isValid = True
        self.cameraOrientation = {}
        self.topo = PlotType.Planar
        self.sliceAxisIndex = 0
        self.zSliceWidth = 0.005
        self.sliceWidthSensitivity = [ 0.005, 0.005, 0.005 ]
        self.slicePositionSensitivity = [ 0.025, 0.025, 0.025 ]
        self.nlevels = None
#        self.colorWindowPosition = 0.5
#        self.colorWindowWidth = 1.0
#        self.windowWidthSensitivity = 0.1 
#        self.colorWindowPositionSensitivity = 0.1
        self.render_mode = ProcessMode.HighRes
        self.planeWidget = None
#        self.render_mode_point_sizes = [ 4, 10 ]
        self.colorRange = 0 
        self.thresholdCmdIndex = 0
        self.thresholdingSkipFactor = 2
        self.resolutionCounter = Counter()
        self.colormapManagers= {}
        self.stereoEnabled = 0
        self.maxStageHeight = 100.0
        self._current_subset_specs = None
        self.scalarRange = None
        self.volumeThresholdRange = None

    @property
    def current_subset_specs(self):
        return self._current_subset_specs

    @current_subset_specs.setter
    def current_subset_specs(self, value):
        if value[0] == 'Z3':
            print "Setting current_subset_specs to %s " % str( value )
        self._current_subset_specs = value
                
    def getLUT( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut
    
    def getColormapManager( self, **args ):
        cmap_index = args.get('index',0)
        name = args.get('name',None)
        invert = args.get('invert',None)
        smooth = args.get('smooth',None)
        cmap_mgr = self.colormapManagers.get( cmap_index, None )
        if cmap_mgr == None:
            lut = vtk.vtkLookupTable()
            cmap_mgr = ColorMapManager( lut ) 
            self.colormapManagers[cmap_index] = cmap_mgr
        if (invert <> None): cmap_mgr.invertColormap = invert
        if (smooth <> None): cmap_mgr.smoothColormap = smooth
        if name:   cmap_mgr.load_lut( name )
        return cmap_mgr
        
    def setColormap( self, data, **args ):
        colormapName = str(data[0])
        invertColormap = getBool( data[1] ) 
        enableStereo = getBool( data[2] )
        smoothColormap = getBool( data[3] ) if ( len( data ) > 3 ) else 1 
        cmap_index = args.get( 'index', 0 )
        cm_title = args.get( 'title', '' )
        self.updateStereo( enableStereo )
        colormapManager = self.getColormapManager( name=colormapName, invert=invertColormap, smooth=smoothColormap, index=cmap_index, units=self.getUnits(cmap_index) )
        if( colormapManager.colorBarActor == None ): 
            cmap_pos = [ 0.9, 0.2 ] if (cmap_index==0) else [ 0.02, 0.2 ]
            units = self.getUnits( cmap_index )
            self.renderer.AddActor( colormapManager.createActor( pos=cmap_pos, title=cm_title ) )
        self.render() 
        return True
        return False 
    
    def getUnits(self, var_index ):
        return ""
    

    def updateStereo( self, enableStereo ):   
        if enableStereo:
            self.renderWindow.StereoRenderOn()
            self.stereoEnabled = 1
        else:
            self.renderWindow.StereoRenderOff()
            self.stereoEnabled = 0

            
    def getColormap(self, cmap_index = 0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return [ colormapManager.colormapName, colormapManager.invertColormap, self.stereoEnabled ]
 
         
    def invalidate(self):
        self.isValid = False
        
    def toggleRenderMode( self ):     
        new_render_mode = ( self.render_mode + 1 ) % 2 
        self.setRenderMode( new_render_mode )
        self.render()
        
    def getPointCloud( self, ires = -1 ):
        if ires == -1: ires = self.render_mode
        return self.partitioned_point_cloud if ( ( ires ==  ProcessMode.HighRes ) and ( self.partitioned_point_cloud <> None ) ) else self.point_cloud_overview 

    def getPointClouds(self):
        return [ self.point_cloud_overview, self.partitioned_point_cloud ]
       
    def setRenderMode( self, render_mode, immediate = False ): 
        if (render_mode == ProcessMode.HighRes):
            if ( self.partitioned_point_cloud == None ): return 
            if not self.partitioned_point_cloud.hasActiveCollections(): return            
        self.render_mode = render_mode    
#        self.setScalarRange()   
        if render_mode ==  ProcessMode.HighRes:
            if immediate: 
                self.low_res_actor.VisibilityOff()
                if self.partitioned_point_cloud:  
                    self.resolutionCounter.reset( 0 )   
            else:
                if self.partitioned_point_cloud: 
                    psize = self.pointSize.getValue( ProcessMode.LowRes )
                    self.resolutionCounter.reset( min( psize, self.partitioned_point_cloud.nPartitions ) ) 
        else: 
            if self.partitioned_point_cloud: 
                self.partitioned_point_cloud.clear()
            self.refreshPointSize()
            self.low_res_actor.VisibilityOn()  
            
#        if self.process_mode == ProcessMode.Thresholding:   self.executeCurrentThresholdRange()
#        if self.process_mode == ProcessMode.Slicing:        self.execCurrentSlice()
        
#    def refreshResolution( self ):
#        self.setPointSize( self.raw_point_size )
#        downsizeFactor = int( math.ceil( self.getNumberOfPoints() / float( self.downsizeNPointsTarget ) ) ) 
#        self.pointMask.SetOnRatio( downsizeFactor )
#        self.pointMask.Modified()
#        self.threshold_filter.Modified()
#        self.geometry_filter.Modified()
                

    def executeCurrentThresholdRange( self ):
        self.updateThresholding( 'vardata', self.volumeThresholdRange.getRange() )    
             
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

#     def terminate(self):
#         self.partitioned_point_cloud.terminate()

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
                if self.partitioned_point_cloud and self.partitioned_point_cloud.hasActiveCollections():                
                    pick_pos, dval = self.partitioned_point_cloud.getPoint( actor, iPt ) 
                else:
                    pick_pos, dval = self.point_cloud_overview.getPoint( iPt ) 
#                 if self.topo == PlotType.Spherical:
#                     pick_pos = glev.vtk_points_data.GetPoint( iPt )
#                 else:
#                     pick_pos = picker.GetPickPosition()                                     
                if pick_pos:        text = " Point[%d] ( %.2f, %.2f ): %s " % ( iPt, pick_pos[0], pick_pos[1], dval )
                else:               text = "No Pick"
                self.updateTextDisplay( text )
            
    def toggleTopo(self):
        self.topo = ( self.topo + 1 ) % 2
        self.updateProjection()
        
    def updateProjection(self):
        self.recordCamera()
        pts =  [  self.partitioned_point_cloud.setTopo( self.topo ) if self.partitioned_point_cloud else False,
                  self.point_cloud_overview.setTopo( self.topo)    ] 
        if pts[self.render_mode]:
            self.resetCamera( pts[self.render_mode] )
            self.renderer.ResetCameraClippingRange()   
        if ( self.topo == PlotType.Spherical ):             
            self.planeWidgetOff()
            self.setFocalPoint( [0,0,0] )
        elif self.process_mode == ProcessMode.Slicing:  
            self.planeWidgetOn()
        self.mapManager.setMapVisibility( self.topo )
        self.render()
        
    def render( self, onMode = ProcessMode.AnyRes ):
        if (onMode == ProcessMode.AnyRes) or ( onMode == self.render_mode ):
            self.renderWindow.Render()

    def toggleClipping(self):
        if self.clipper.GetEnabled():   self.clipOff()
        else:                           self.clipOn()
        
    def clipOn(self):
        self.clipper.On()
        self.executeClip()

    def clipOff(self):
        self.clipper.Off()      

    def processEvent(self, eventArgs ):
        if eventArgs[0] == "KeyEvent":
            self.onKeyEvent( eventArgs[1:])
        print " -- Event: %s " % str( eventArgs )
        
#        self.emit( QtCore.SIGNAL('Close')  )
            
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
#             elif self.process_mode == ProcessMode.Slicing: 
#                 self.shiftSlice( 1, 0 )           
        if key == QtCore.Qt.Key_Down:
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( -1, 0 )  
#             elif self.process_mode == ProcessMode.Slicing: 
#                 self.shiftSlice( -1, 0 )
    
        if key == QtCore.Qt.Key_Left:   
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( 0, -1 )
#             elif self.process_mode == ProcessMode.Slicing: 
#                 self.shiftSlice( 0, -1 )
        if key == QtCore.Qt.Key_Right:       
            if self.process_mode == ProcessMode.Thresholding:
                self.shiftThresholding( 0, 1 )
#             elif self.process_mode == ProcessMode.Slicing: 
#                 self.shiftSlice( 0, 1 )
            
        if   keysym == "s":  self.toggleTopo()
        elif keysym == "t":  self.stepTime()
        elif keysym == "T":  self.stepTime( False )
        elif keysym == "c":  self.toggleClipping()
        elif keysym == "m":  self.toggleRenderMode()
        elif keysym == "p":
            if self.process_mode == ProcessMode.Slicing:
                self.sliceAxisIndex =  ( self.sliceAxisIndex + 1 ) % 3 
            self.enableSlicing()  
        elif keysym == "v":
            self.updateTextDisplay( "Mode: Thresholding", True )
            self.process_mode = ProcessMode.Thresholding 
            self.planeWidgetOff()
            self.shiftThresholding( 0, 0 )  
        elif keysym == "i":  self.setPointIndexBounds( 5000, 7000 )
        
    def enableSlicing( self ):
        self.process_mode = ProcessMode.Slicing 
        if self.render_mode ==  ProcessMode.LowRes:
            self.setRenderMode( ProcessMode.HighRes )  
        if self.topo == PlotType.Planar:                       
            self.planeWidgetOn( )
        self.updateTextDisplay( "Mode: Slicing", True )
        self.execCurrentSlice()
        
    def planeWidgetOn(self):
        self.initPlaneWidget()
        if self.sliceAxisIndex   == 0:
            self.planeWidget.SetNormal( 1.0, 0.0, 0.0 )
            self.planeWidget.NormalToXAxisOn()
        elif self.sliceAxisIndex == 1: 
            self.planeWidget.SetNormal( 0.0, 1.0, 0.0 )
            self.planeWidget.NormalToYAxisOn()
        elif self.sliceAxisIndex == 2: 
            self.planeWidget.SetNormal( 0.0, 0.0, 1.0 )
            self.planeWidget.NormalToZAxisOn()  
        self.updatePlaneWidget()          
        if not self.planeWidget.GetEnabled( ):
            self.planeWidget.SetEnabled( 1 )  
            
    def updatePlaneWidget(self): 
        o = list( self.planeWidget.GetOrigin() )
        spos = self.getCurrentSlicePosition()
        o[ self.sliceAxisIndex ] = spos
#        print " Update Plane Widget: Set Origin[%d] = %.2f " % ( self.sliceAxisIndex, spos )
        self.planeWidget.SetOrigin(o) 

    def planeWidgetOff(self):
        if self.planeWidget:
            self.planeWidget.SetEnabled( 0 )   
                
    def initPlaneWidget(self):
        if self.planeWidget == None:
            self.planeWidget = vtk.vtkImplicitPlaneWidget()
            self.planeWidget.SetInteractor( self.renderWindowInteractor )
            self.planeWidget.SetPlaceFactor( 1.5 )
            self.planeWidget.SetInput( self.point_cloud_overview.getPolydata() )
            self.planeWidget.AddObserver("StartInteractionEvent", self.processStartInteractionEvent )
            self.planeWidget.AddObserver("EndInteractionEvent", self.processEndInteractionEvent )
            self.planeWidget.AddObserver("InteractionEvent", self.processInteractionEvent )
            self.planeWidget.KeyPressActivationOff()
            self.planeWidget.OutlineTranslationOff()
            self.planeWidget.ScaleEnabledOff()
            self.planeWidget.OutsideBoundsOn() 
            self.planeWidget.OriginTranslationOff()
            self.planeWidget.SetDiagonalRatio( 0.0 )                         
            self.planeWidget.DrawPlaneOff()
            self.planeWidget.TubingOff() 
            self.planeWidget.GetNormalProperty().SetOpacity(0.0)
            self.planeWidget.SetInteractor( self.renderWindowInteractor )
            self.planeWidget.KeyPressActivationOff()
            self.widget_bounds = self.point_cloud_overview.getBounds()
            self.planeWidget.PlaceWidget( self.widget_bounds )
                
    def processCategorySelectionCommand( self, args ):
        op = args[0]
        if op == 'Subsets':
            self.enableSlicing()
        elif op == 'Color':
            self.enableColorConfig() 
        elif op == 'Points':
            self.enablePointConfig() 
                
    def enableColorConfig(self):
        self.config_mode = ConfigMode.Color

    def enablePointConfig(self):
        self.config_mode = ConfigMode.Points            

    def processAnimationCommand( self, args ):
        if args and args[0] == "ButtonClick":
            if args[1]   == "Run":
                pass
            elif args[1] == "Step":
                if self.partitioned_point_cloud: 
                    self.partitioned_point_cloud.stepTime()
                    self.point_cloud_overview.stepTime( process= not self.partitioned_point_cloud.hasActiveCollections() )
                else:
                    self.point_cloud_overview.stepTime(process=True)
                    
                self.render() 
            elif args[1] == "Stop":
                pass

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


            
    def processSlicePlaneCommand( self, args ):
#        print " processSlicePlaneCommand: %s " % str( args )
        if args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                title = args[2]
                if not (title in SLICE_WIDTH_HR_COMP):
                    self.setRenderMode( ProcessMode.LowRes, True )
#            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud:
                self.current_subset_specs = self.partitioned_point_cloud.getSubsetSpecs()
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )        
        elif args and args[0] == "EndConfig":
            self.setRenderMode( ProcessMode.HighRes )                 
            self.execCurrentSlice()
        
        elif args and args[0] == "Open":
            self.enableSlicing()
        elif args and args[0] == "UpdateTabPanel":
            axis_index = args[1]
            if axis_index == 2:
                slice_index = round( self.getSlicePosition(2) / self.zSliceWidth ) 
                self.setSlicePosition( slice_index * self.zSliceWidth, 2 )   
                self.execCurrentSlice()           
        elif args and args[0] == "Close":
            isOK = args[1]
            self.setRenderMode( ProcessMode.HighRes )
            if isOK: self.getPointCloud().setScalarRange( self.scalarRange.getScaledRange() )              
            self.render()
        elif args and args[0] == "SelectSlice":
            self.sliceAxisIndex =  args[1]
            self.enableSlicing()            
    
    def processThresholdRangeCommand( self, args = None ):
        if args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes, True )
#            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud:
                self.current_subset_specs = self.partitioned_point_cloud.getSubsetSpecs()
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
            if self.process_mode <> ProcessMode.Thresholding:
                self.enableThresholding()
        
        elif args and args[0] == "EndConfig":
            self.setRenderMode( ProcessMode.HighRes )                
#            self.partitioned_point_cloud.setScalarRange( self.scalarRange.getScaledRange() )  
            self.updateThresholding( 'vardata', self.volumeThresholdRange.getRange() ) 
        
        elif args and args[0] == "Open":
            self.enableThresholding()
        elif args and args[0] == "Close":
            isOK = args[1]
            self.setRenderMode( ProcessMode.HighRes )
            if isOK: self.updateThresholding( 'vardata', self.volumeThresholdRange.getRange() )                
            self.render()
        elif args and args[0] == "Threshold Range":
            norm_range = self.volumeThresholdRange.getRange()
            if ( self.thresholdCmdIndex % self.thresholdingSkipFactor ) == 0:
                self.updateThresholding( 'vardata', norm_range )
                    
    def enableThresholding( self, args = None ):
        self.updateTextDisplay( "Mode: Thresholding", True )
        self.thresholdCmdIndex = 0
        self.process_mode = ProcessMode.Thresholding 
        self.planeWidgetOff()
        if self.render_mode ==  ProcessMode.LowRes:
            self.setRenderMode( ProcessMode.HighRes, True )
        if self.scalarRange <> None:
            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )
        if self.volumeThresholdRange <> None:
            self.updateThresholding( 'vardata', self.volumeThresholdRange.getRange() )
                   
    def processColorScaleCommand( self, args = None ):
        if args and args[0] == "ButtonClick":
            pc =  self.getPointCloud()      
            if args[1] == "Reset":
                self.scalarRange.setRange( self.point_cloud_overview.getValueRange()  )  
                pc.setScalarRange( self.scalarRange.getScaledRange() ) 
#                self.partitioned_point_cloud.refresh(True)     
            elif args[1] == "Match Threshold Range":
                self.scalarRange.setRange( self.volumeThresholdRange.getRange()  )  
                pc.setScalarRange( self.scalarRange.getScaledRange() ) 
#                self.partitioned_point_cloud.refresh(True)     
        elif args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes )
            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud: 
                self.current_subset_specs = self.partitioned_point_cloud.getSubsetSpecs()
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
        elif args and args[0] == "EndConfig":
            if self.render_mode ==  ProcessMode.LowRes:
                self.setRenderMode( ProcessMode.HighRes ) 
                pc =  self.getPointCloud()             
                pc.setScalarRange( self.scalarRange.getScaledRange() )  
                pc.refresh(True) 
        elif args and args[0] == "UpdateTabPanel":
            pass                 
        elif args and args[0] == "Color Scale":
            norm_range = self.scalarRange.getScaledRange() 
            self.point_cloud_overview.setScalarRange( norm_range )          
        self.render()

                     
    def shiftThresholding( self, position_inc, width_inc ):
        self.volumeThresholdRange.shiftWindow(position_inc, width_inc) 
        self.updateThresholding( 'vardata', self.volumeThresholdRange.getRange() )

    def getSliceWidth(self, res, slice_index = -1  ):
        if slice_index == -1: slice_index = self.sliceAxisIndex
        if slice_index == 2: return self.zSliceWidth
        else:
            if res == ProcessMode.LowRes:  return self.sliceProperties[ SLICE_WIDTH_LR_COMP[ slice_index ] ]
            if res == ProcessMode.HighRes: return self.sliceProperties[ SLICE_WIDTH_HR_COMP[ slice_index ] ]
            
    def getSlicePosition(self, slice_index = -1 ):
        if slice_index == -1: slice_index = self.sliceAxisIndex
        return self.sliceProperties[ POS_VECTOR_COMP[ slice_index ] ]

    def setSlicePosition(self, slice_pos, slice_index = -1 ):
        if slice_index == -1: slice_index = self.sliceAxisIndex
        self.sliceProperties[ POS_VECTOR_COMP[ slice_index ] ] = slice_pos
                
    def getCurrentSlicePosition(self):
        bounds = self.point_cloud_overview.getBounds()
        sindex = 2*self.sliceAxisIndex 
        return bounds[sindex] + self.getSlicePosition() * ( bounds[sindex+1] - bounds[sindex] )
    
    def execCurrentSlice( self, **args ):
        slice_bounds = []
        for iRes in [ ProcessMode.LowRes, ProcessMode.HighRes ]:
            slice_radius = self.getSliceWidth( iRes ) # self.sliceWidth[self.sliceAxisIndex]/(iRes)     
            pmin = max( self.getSlicePosition() - slice_radius, 0.0 )
            pmin = min( pmin, 1.0 - slice_radius )
            pmax = min( self.getSlicePosition() + slice_radius, 1.0 )
            pmax = max( pmax, slice_radius )
            slice_bounds.append( (pmin,pmax) )
        print " && ExecCurrentSlice, slice properties: %s " % ( str( self.sliceProperties ) ); sys.stdout.flush()
        self.updateSlicing( self.sliceAxisIndex, slice_bounds, **args )
    
    def pushSlice( self, slice_pos ):
        self.updateTextDisplay( " Slice Position: %s " % str( slice_pos ) )
        bounds = self.point_cloud_overview.getBounds()
        sindex = 2*self.sliceAxisIndex  
        self.setSlicePosition( ( slice_pos - bounds[sindex] ) / ( bounds[sindex+1] - bounds[sindex] ) )
        self.execCurrentSlice()

#     def shiftSlice( self, position_inc, width_inc ): 
#         if position_inc <> 0:
#             self.setSlicePosition( self.getSlicePosition() + position_inc * self.slicePositionSensitivity[self.sliceAxisIndex] )
#         if width_inc <> 0:
#             if self.sliceWidth[self.sliceAxisIndex] < 2 * self.sliceWidthSensitivity[self.sliceAxisIndex]:
#                 self.sliceWidth[self.sliceAxisIndex]  *  2.0**width_inc 
#             else:
#                 self.sliceWidth[self.sliceAxisIndex] = self.sliceWidth[self.sliceAxisIndex] + width_inc * self.sliceWidthSensitivity[self.sliceAxisIndex]        
#         self.execCurrentSlice()

    def shiftResolution( self, ncollections_inc, ptsize_inc ):
        if (ncollections_inc <> 0) and ( self.partitioned_point_cloud <> None ):
            self.partitioned_point_cloud.updateNumActiveCollections( ncollections_inc )
        if ptsize_inc <> 0:
            self.updatePointSize( ptsize_inc )
        
    def updateThresholding( self, target, trange ):
        self.current_subset_specs = ( target, trange[0], trange[1] )
        self.invalidate()
        pc = self.getPointCloud()
        pc.generateSubset( spec=self.current_subset_specs )
        self.render( self.render_mode )
#        print " Update Thresholding: spec = %s, render mode = %d " % ( str( subset_spec ), self.render_mode )
        sys.stdout.flush()

    def processConfigCmd( self, args ):
#        print " processConfigCmd: %s " % str(args); sys.stdout.flush()
        if args[0] =='Color Scale':
            self.processColorScaleCommand( args[1:] )
        elif args[0] =='Animation':
            self.processAnimationCommand( args[1:] )
        elif args[0] =='Slice Planes':
            self.processSlicePlaneCommand( args[1:] )
        elif args[0] =='Threshold Range':
            self.processThresholdRangeCommand( args[1:] )
        elif args[0] =='CategorySelected':
            self.processCategorySelectionCommand( args[1:] )
        elif args[0] =='InitParm':
            self.processsInitParameter( args[1], args[2] )
        elif args[0] =='Point Size':
            self.processPointSizeCommand( args[1:] )
        elif args[0] =='Vertical Scaling':
            self.processVerticalScalingCommand( args[1:] )

    def processPointSizeCommand( self, arg = None ):
        if arg == None:
            point_size = self.pointSize.getValue( self.render_mode )
        elif arg[0] == 'UpdateTabPanel':
            render_mode = arg[1]
            self.setRenderMode( render_mode )
            if render_mode == ProcessMode.HighRes: 
                if self.partitioned_point_cloud:
                    self.partitioned_point_cloud.refresh(True)
            else:
                self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() ) 
                if self.partitioned_point_cloud:
                    self.current_subset_specs = self.partitioned_point_cloud.getSubsetSpecs()             
                    self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
            self.render()
            return
        elif arg[0] == 'Open':
            return
        elif arg[0] == 'StartConfig':
            return
        elif arg[0] == 'EndConfig':
            return
        elif arg[0] == 'Point Size':
            point_size = self.pointSize.getValue( self.render_mode )      
            pc = self.getPointCloud()
            if point_size and (point_size <> pc.getPointSize()):
                pc.setPointSize( point_size )
                self.render( self.render_mode )
            
    def processSlicePropertiesCommand( self, args ):
        op = args[1]
        if op in SLICE_WIDTH_HR_COMP:  
            self.setRenderMode( ProcessMode.HighRes )                 
            self.execCurrentSlice()
        elif op in SLICE_WIDTH_LR_COMP: 
            self.setRenderMode( ProcessMode.LowRes )                 
            self.execCurrentSlice()
        elif op in POS_VECTOR_COMP: 
            self.updatePlaneWidget()          
            self.execCurrentSlice()      

    def processsInitParameter( self, parameter_key, config_param ):
        paramKeys = parameter_key.split(':') 
        if paramKeys[0] == 'Color':
            if paramKeys[1] == 'Color Scale':
                self.scalarRange = config_param  
                self.scalarRange.setScalingBounds( self.point_cloud_overview.getValueRange()  )  
                self.connect( self.scalarRange, QtCore.SIGNAL('ValueChanged'), self.processColorScaleCommand ) 
                self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )       
            elif paramKeys[1] == 'Color Map':
                self.colorMapCfg = config_param 
                self.connect( self.colorMapCfg, QtCore.SIGNAL('ValueChanged'), self.processColorMapCommand ) 
                self.processColorMapCommand()
        elif paramKeys[0] == 'Subsets':
            if paramKeys[1] == 'Slice Planes':
                self.sliceProperties = config_param
                self.connect( self.sliceProperties, QtCore.SIGNAL('ValueChanged'), self.processSlicePropertiesCommand )  
#                self.enableSlicing()
            elif paramKeys[1] == 'Threshold Range':
                self.volumeThresholdRange = config_param                 
                self.volumeThresholdRange.setScalingBounds( self.point_cloud_overview.getValueRange()  ) 
                self.connect( self.volumeThresholdRange, QtCore.SIGNAL('ValueChanged'), self.processThresholdRangeCommand )      
#                self.enableThresholding()
        elif paramKeys[0] == 'Points':
            if paramKeys[1] == 'Point Size':
                self.pointSize = config_param   
                self.connect( self.pointSize, QtCore.SIGNAL('ValueChanged'), self.processPointSizeCommand ) 
                for ires in [ ProcessMode.LowRes, ProcessMode.HighRes ]:
                    pc = self.getPointCloud(ires)  
                    pc.setPointSize( config_param.getValue(ires) )                                 
            elif paramKeys[1] == 'Max Resolution':
                self.maxRes = config_param   
                self.connect( self.maxRes, QtCore.SIGNAL('ValueChanged'), self.processMaxResolutionCommand ) 
        elif paramKeys[0] == 'Geometry':
            if paramKeys[1] == 'Projection':
                self.projection = config_param   
                self.connect( self.projection, QtCore.SIGNAL('ValueChanged'), self.processProjectionCommand ) 
            elif paramKeys[1] == 'Vertical Scaling':
                self.vscale = config_param   
                self.connect( self.vscale, QtCore.SIGNAL('ValueChanged'), self.processVerticalScalingCommand ) 
            elif paramKeys[1] == 'Vertical Variable':
                self.vertVar = config_param   
                self.connect( self.vertVar, QtCore.SIGNAL('ValueChanged'), self.processVerticalVariableCommand )
                
    def processMaxResolutionCommand(self, args=None ):
        max_res_spec =  self.maxRes.getValue() 
        if self.partitioned_point_cloud:
            self.partitioned_point_cloud.setResolution( max_res_spec )
        if not self.partitioned_point_cloud.hasActiveCollections():
            self.render_mode = ProcessMode.LowRes
        self.render()
                
    def processVerticalScalingCommand(self, args=None ):
        if args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes ) 
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
                self.render( self.render_mode )   
        elif args and args[0] == "EndConfig":
            scaling_spec = ( self.vertVar.getValue(), self.vscale.getValue() )
            if self.partitioned_point_cloud:
                self.partitioned_point_cloud.generateZScaling( spec=scaling_spec )
            self.setRenderMode( ProcessMode.HighRes )
            self.render() 
        elif args and args[0] == "UpdateTabPanel":
            pass
        else:                     
            scaling_spec = ( self.vertVar.getValue(), self.vscale.getValue() )
            self.point_cloud_overview.generateZScaling( spec=scaling_spec )
            pcbounds = self.point_cloud_overview.getBounds()
            self.widget_bounds[4:6] = pcbounds[4:6]
            self.planeWidget.PlaceWidget( self.widget_bounds )
#            vis = self.low_res_actor.GetVisibility()
            self.render()
                        
    def processVerticalVariableCommand(self, args=None ):
        scaling_spec = ( self.vertVar['selected'], self.vscale.getValue() )
        if self.partitioned_point_cloud:
            self.partitioned_point_cloud.generateZScaling( spec=scaling_spec )
        self.point_cloud_overview.generateZScaling( spec=scaling_spec )
        self.setRenderMode( ProcessMode.HighRes )
        self.render() 
                
    def processProjectionCommand( self, args=None ):
        seleted_projection = self.projection.getValue('selected')
        projections = self.projection.getValue('choices',[])
        try:
            self.topo = projections.index( seleted_projection )
            self.updateProjection()
        except ValueError:
            print>>sys.stderr, "Can't find projection: %s " % str( seleted_projection )

    def processColorMapCommand( self, args=None ):
        colorCfg = [ self.colorMapCfg.getValue('Colormap'), self.colorMapCfg.getValue('Invert'), self.colorMapCfg.getValue('Stereo'), self.colorMapCfg.getValue('Smooth') ]
        self.setColormap( colorCfg )  

    def updateSlicing( self, sliceIndex, slice_bounds, **args ):
        self.invalidate()
        ( rmin, rmax ) = slice_bounds[ self.render_mode ]
        self.current_subset_specs = ( self.sliceAxes[sliceIndex], rmin, rmax )
        if self.render_mode ==  ProcessMode.HighRes:
            self.partitioned_point_cloud.generateSubset( spec=self.current_subset_specs, allow_processing=True )
        else:
            self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
            if self.partitioned_point_cloud:
                self.partitioned_point_cloud.generateSubset( spec=self.current_subset_specs, allow_processing=False )
        self.render( self.render_mode )

#    def updateSlicing1( self, sliceIndex, slice_bounds ):
#        self.invalidate()
#        for iRes, pc in enumerate( self.getPointClouds() ):
#            ( rmin, rmax ) = slice_bounds[iRes]
#            pc.generateSubset( ( self.sliceAxes[sliceIndex], rmin, rmax ) )
#        self.render( ProcessMode.LowRes )
                  
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
#    def setSliceClipBounds( self, sliceProperties = 0.0 ):
#        if self.lev == None: return
#        bounds = self.getBounds()
#        mapperBounds = None
#        if self.sliceOrientation == 'x':
#            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
#            mapperBounds = [ sliceProperties-self.sliceThickness[0],  sliceProperties+self.sliceThickness[0], bounds[2], bounds[3], lev_bounds[0], lev_bounds[1]  ]
#        if self.sliceOrientation == 'y':
#            lev_bounds = [ 0, len( self.lev  ) * self.z_spacing ]
#            mapperBounds = [ bounds[0], bounds[1], sliceProperties - self.sliceThickness[1],  sliceProperties + self.sliceThickness[1], lev_bounds[0], lev_bounds[1]  ]
#        if self.sliceOrientation == 'z':
#            sliceThickness = self.z_spacing/2
#            mapperBounds = [ bounds[0], bounds[1], bounds[2], bounds[3], sliceProperties - sliceThickness,  sliceProperties + sliceThickness  ]
#        if mapperBounds:
#            print "Setting clip planes: %s " % str( mapperBounds )
#            self.clipBox.SetBounds( mapperBounds )
#            self.slice_filter.Modified()
##             self.clipper.PlaceWidget( mapperBounds )
##             self.clipper.GetPlanes( self.clippingPlanes )
##             self.mapper.SetClippingPlanes( self.clippingPlanes )
#            self.mapper.Modified()

     
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
        
    def processInteractionEvent( self, obj=None, event=None ): 
        if self.process_mode == ProcessMode.Slicing:
            o = list( self.planeWidget.GetOrigin() )
            slice_pos = o[ self.sliceAxisIndex ]
            self.pushSlice( slice_pos )         
#        print " Interaction Event: %s %s " % ( str(object), str( event ) ); sys.stdout.flush()

    def processStartInteractionEvent( self, obj, event ):  
#        print " start Interaction: %s %s " % ( str(object), str( event ) ); sys.stdout.flush()
        if self.process_mode == ProcessMode.Slicing:
            self.setRenderMode( ProcessMode.LowRes )

    def processEndInteractionEvent( self, obj, event ):  
#        print " end Interaction: %s %s " % ( str(object), str( event ) ); sys.stdout.flush()
        if self.process_mode == ProcessMode.Slicing:
            self.setRenderMode( ProcessMode.HighRes )
            self.execCurrentSlice()
            self.setSlicePosition( self.getSlicePosition() )
#            self.emit(QtCore.SIGNAL("UpdateGui"), ( "SetSlicePosition", self.getSlicePosition() ) ) 
        
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
        fp = self.point_cloud_overview.getCenter() 
        self.renderer.GetActiveCamera().SetPosition( fp[0], fp[1], fp[0]*2 )
        self.renderer.GetActiveCamera().SetFocalPoint( fp[0], fp[1], 0 )
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
                
    def initCollections( self, nCollections, init_args, **args ):
        if nCollections > 1:
            self.partitioned_point_cloud = vtkPartitionedPointCloud( nCollections, init_args, **args )
            self.partitioned_point_cloud.connect( self.partitioned_point_cloud, QtCore.SIGNAL('newDataAvailable'), self.newDataAvailable )
        else:
            self.render_mode = ProcessMode.LowRes
#        self.partitioned_point_cloud.connect( self.partitioned_point_cloud, QtCore.SIGNAL('updateScaling'), self.updateScaling )        
        self.createRenderer()
        self.low_res_actor = self.point_cloud_overview.actor
        self.renderer.AddActor( self.low_res_actor )
        self.pointPicker.AddPickList( self.low_res_actor )
        
        if self.partitioned_point_cloud:
            for point_cloud in  self.partitioned_point_cloud.values():     
                self.renderer.AddActor( point_cloud.actor )
                self.pointPicker.AddPickList( point_cloud.actor )
        else:
            self.updateZRange( self.point_cloud_overview )
            
        self.mapManager = MapManager( roi = self.point_cloud_overview.getBounds() )
        self.renderer.AddActor( self.mapManager.getBaseMapActor() )
        self.renderer.AddActor( self.mapManager.getSphericalMap() )
        self.initCamera( )
        
    def reset( self, pcIndex ):
        if not self.isValid and ( self.partitioned_point_cloud <> None ):
            self.partitioned_point_cloud.clear( pcIndex )
            self.isValid = True
                    
    def updateZRange( self, pc ):
        nlev = pc.getNLevels()
        if nlev and (nlev <> self.nlevels):
            self.nlevels = nlev
            self.zSliceWidth = 1.0/(self.nlevels)
            self.sliceWidthSensitivity[2] = self.zSliceWidth
            self.slicePositionSensitivity[2] = self.zSliceWidth
            
    def decrementOverviewResolution( self ):
        if self.resolutionCounter.isActive(): # self.point_cloud_overview.isVisible():
            isBottomedOut = self.resolutionCounter.decrement()
            psize = self.resolutionCounter.value()
#            print "Decrement point size: %d, isBottomedOut: %s " % ( psize, str(isBottomedOut) ); sys.stdout.flush()
            self.point_cloud_overview.setPointSize( psize )
            if isBottomedOut: self.point_cloud_overview.hide()
            
    def refreshPointSize(self):
        self.point_cloud_overview.setPointSize( self.pointSize.getValue( ProcessMode.LowRes ) )
             
    def newDataAvailable( self, pcIndex, data_type ):
        if ( self.partitioned_point_cloud <> None ): 
            pc = self.partitioned_point_cloud.getPointCloud( pcIndex )
            pc.show()
            self.decrementOverviewResolution()
            self.partitioned_point_cloud.postDataQueueEvent()
            pc.setScalarRange( self.scalarRange.getScaledRange() )
            self.updateZRange( pc ) 
            text = " Thresholding Range[%d]: %s \n Colormap Range: %s " % ( pcIndex, str( pc.getThresholdingRange() ), str( self.scalarRange.getRange() ) )
            self.updateTextDisplay( text )
    #        print " Subproc[%d]--> new Thresholding Data Available: %s " % ( pcIndex, str( pc.getThresholdingRange() ) ); sys.stdout.flush()
    #        self.reset( ) # pcIndex )
            self.render() 
                          
    def generateSubset(self, **args ):
#        self.pointPicker.GetPickList().RemoveAllItems() 
        self.getPointCloud().generateSubset( **args  )        
        
    def terminate(self):
        if ( self.partitioned_point_cloud <> None ):
            for point_cloud in self.partitioned_point_cloud.values(): 
                point_cloud.terminate()  
          
    def setPointSize( self, point_size ) :  
        self.getPointCloud().setPointSize( point_size )    
      
    def init(self, **args ):
        init_args = args[ 'init_args' ]      
        n_overview_points = args.get( 'n_overview_points', 500000 )    
        n_subproc_points = args.get( 'n_subproc_points', 1000000 )    
        self.point_cloud_overview = vtkLocalPointCloud( 0, max_points=n_overview_points ) 
        lut = self.getLUT()
        self.point_cloud_overview.initialize( init_args, lut = lut, maxStageHeight=self.maxStageHeight  )
        nInputPoints = self.point_cloud_overview.getNumberOfInputPoints()
        nCollections = min( nInputPoints / n_subproc_points, 10  )
        print " Init PCViewer, nInputPoints = %d, n_overview_points = %d, n_subproc_points = %d, nCollections = %d, overview skip index = %s" % ( nInputPoints, n_overview_points, n_subproc_points, nCollections, self.point_cloud_overview.getSkipIndex() )
        self.initCollections( nCollections, init_args, lut = lut, maxStageHeight=self.maxStageHeight  )
 
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

    def closeEvent( self, event ):
        self.emit( QtCore.SIGNAL('Close') )
        QVTKRenderWindowInteractor.closeEvent( self, event )
    
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
    import argparse
    parser = argparse.ArgumentParser(description='DV3D Point Cloud Viewer')
    parser.add_argument( 'PATH' )
    parser.add_argument( '-d', '--data_dir', dest='data_dir', nargs='?', default="~/data", help='input data dir')
    parser.add_argument( '-t', '--data_type', dest='data_type', nargs='?', default="CAM", help='input data type')
    ns = parser.parse_args( sys.argv )
    
    kill_all_zombies()

    app = QtGui.QApplication(['Point Cloud Plotter'])
    widget = QVTKAdaptor()
    widget.Initialize()
    widget.Start()        
    point_size = 1
    n_overview_points = 500000
    height_varname = None
    data_dir = os.path.expanduser( ns.data_dir )
    height_varnames = []
    
    if ns.data_type == "WRF":
        data_file = os.path.join( data_dir, "WRF/wrfout_d01_2013-07-01_00-00-00.nc" )
        grid_file = None
        varname = "U"        
    elif ns.data_type == "CAM":
        data_file = os.path.join( data_dir, "CAM/f1850c5_t2_ANN_climo-native.nc" )
        grid_file = os.path.join( data_dir, "CAM/ne120np4_latlon.nc" )
        varname = "U"
        height_varnames = [ "Z3" ]
    elif ns.data_type == "ECMWF":
        data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ecmwf.xml" )
        grid_file = None
        varname = "U_velocity"   
    elif ns.data_type == "GEOS5":
        data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ac-comp1-geos5.xml" )
        grid_file = None
        varname = "uwnd"   
    elif ns.data_type == "MMF":
        data_file = os.path.join( data_dir, "MMF/diag_prs.20080101.nc" )
        grid_file = None
        varname = "u"
        
    g = CPCPlot( widget.GetRenderWindow() ) 
    widget.connect( widget, QtCore.SIGNAL('event'), g.processEvent )  
    g.init( init_args = ( grid_file, data_file, varname, height_varname ), n_overview_points=n_overview_points ) # , n_subproc_points=100000000 )
    
#     pointCollectionMgrThread = QPointCollectionMgrThread( g, init_args = ( grid_file, data_file, varname ), nCollections=nCollections )
#     pointCollectionMgrThread.init()
#    pointCollectionMgrThread.start()

    configDialog = CPCConfigGui()
    w = configDialog.getConfigWidget()
    w.connect( w, QtCore.SIGNAL("ConfigCmd"), g.processConfigCmd )
#    configDialog.connect( g, QtCore.SIGNAL("UpdateGui"), configDialog.externalUpdate )
    configDialog.activate()
    
    configDialog.show()
    
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
    app.connect( widget, QtCore.SIGNAL("Close"), configDialog.closeDialog ) 
    widget.show()  
    app.exec_() 
    g.terminate() 
    