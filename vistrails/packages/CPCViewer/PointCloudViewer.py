'''
Created on Aug 29, 2013

@author: tpmaxwel
'''

import sys, cdms2
import os.path, traceback, threading
import vtk, time
from packages.CPCViewer.DistributedPointCollections import vtkPartitionedPointCloud, vtkLocalPointCloud, ScalarRangeType, kill_all_zombies
from packages.CPCViewer.ConfigFunctions import *
from packages.CPCViewer.ColorMapManager import *
from packages.CPCViewer.MapManager import MapManager
from packages.CPCViewer.MultiVarPointCollection import InterfaceType, PlotType
from packages.CPCViewer.DV3DPlot import DV3DPlot

VTK_NO_MODIFIER         = 0
VTK_SHIFT_MODIFIER      = 1
VTK_CONTROL_MODIFIER    = 2        
VTK_TITLE_SIZE = 14
VTK_INSTRUCTION_SIZE = 24

    
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
    
class SliderConfig:
    
    def __init__( self, label, vrange, value ): 
        self.label = label
        self.range = vrange
        self.value = value
       
       
           
class CPCPlot( DV3DPlot ):  
    

    def __init__( self, **args ):
        DV3DPlot.__init__( self, **args  )
        self.ValueChanged = SIGNAL('ValueChanged')
        self.ConfigCmd = SIGNAL('ConfigCmd')
        self.sliceAxisIndex = 0
        self.partitioned_point_cloud = None
        self.point_cloud_overview = None
        self.volumeThresholdRange = {}
        self.infovisDialog = None
        self.process_mode = ProcessMode.Default
        self.config_mode = ConfigMode.Default
        self.topo = PlotType.Planar
        self.zSliceWidth = 0.005
        self.sliceWidthSensitivity = [ 0.005, 0.005, 0.005 ]
        self.slicePositionSensitivity = [ 0.025, 0.025, 0.025 ]
        self.nlevels = None
        self.render_mode = ProcessMode.HighRes
        self.colorRange = 0 
        self.thresholdCmdIndex = 0
        self.thresholdingSkipFactor = 3
        self.deactivate_low_res_actor = False
#        self.resolutionCounter = Counter()
        self._current_subset_specs = {}
        self.scalarRange = None
        self.sphere_source = None
        self.currentSliders = {}
        self.addConfigurableSliderFunction( 'zScale', 'z', label='Vertical Scaling', sliderLabels='Vertical Scale', interactionHandler=self.processVerticalScalingCommand, range_bounds=[ 0.1, 10.0 ], initValue= 1.0  )
        self.addConfigurableSliderFunction( 'pointSize', 'P', label='Point Size', sliderLabels=['Low Resolution', 'High Resolution' ], interactionHandler=self.processPointSizeCommand, range_bounds=[ 1, 12 ], initValue=[ 5, 1 ] )
        self.addConfigurableSliderFunction( 'colorScale', 'C', label='Colormap Scale', interactionHandler=self.processColorScaleCommand )
        self.addConfigurableSliderFunction( 'thresholding', 'T', label='Thresholding Range', interactionHandler=self.processThresholdRangeCommand )
        self.addConfigurableSliderFunction( 'opacityScale', 'o', label='Opacity Scale', range_bounds=[ 0.0, 1.0 ], initValue=[ 1.0, 1.0 ], interactionHandler=self.processOpacityScalingCommand )
        
        
#        self.addConfigurableSliderFunction( 'slicing', 'C', label='Colormap Scale', interactionHandler=self.processColorScaleCommand )
#        self.addConfigurableLevelingFunction( 'map_opacity', 'M', label='Base Map Opacity', rangeBounds=[ 0.0, 1.0 ],  setLevel=self.setMapOpacity, activeBound='min',  getLevel=self.getMapOpacity, isDataValue=False, layerDependent=True, group=ConfigGroup.BaseMap, bound = False )

    def processKeyEvent( self, key, caller=None, event=None ):
        keysym = caller.GetKeySym()
        if self.onKeyEvent( [ key, keysym ] ):
            pass
        else:
            DV3DPlot.processKeyEvent( self, key, caller, event )
#         if (  key == 't'  ): self.toggleTopo()             
#         return 0

    def updateInteractionState( self, state, altMode=None ): 
        self.clearInteractions()
        config_funct = DV3DPlot.updateInteractionState( self, state, altMode )
        if ( config_funct <> None ) and (config_funct.type == 'slider'):
            config_funct.processInteractionEvent( [ "InitConfig" ] )
            for slider_index, label in enumerate( config_funct.sliderLabels ):
                self.commandeerSlider( slider_index, label, config_funct.range_bounds, config_funct.initial_value[slider_index] )
        self.render()
        
    def processTimerEvent(self, caller, event):
        DV3DPlot.processTimerEvent(self, caller, event)
        eid = caller.GetTimerEventId ()
        etype = caller.GetTimerEventType()
        if etype == vtkPartitionedPointCloud.TimerType:
            if self.partitioned_point_cloud.processTimerEvent(eid):
                if self.deactivate_low_res_actor:
                    self.low_res_actor.VisibilityOff()
                    self.deactivate_low_res_actor = True

#         if etype == 11:
#             self.printInteractionStyle('processTimerEvent')
            
    def updateSliderWidgets(self, value0, value1 ): 
        for index, value in enumerate( ( value0, value1 ) ):
            if value <> None:
                ( process_mode, interaction_state, swidget ) = self.currentSliders[index]
                srep = swidget.GetRepresentation( )   
                srep.SetValue( value )
            
    def createSliderWidget( self, index ): 
        sliderRep = vtk.vtkSliderRepresentation2D()
        loc = [ [0.01,0.48], [0.52, 0.99 ] ] 
            
        sliderRep.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
        sliderRep.GetPoint1Coordinate().SetValue( loc[index][0], 0.06, 0 )
        sliderRep.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
        sliderRep.GetPoint2Coordinate().SetValue( loc[index][1], 0.06, 0 )
        prop = sliderRep.GetSliderProperty()
        prop.SetColor( 1.0, 0.0, 0.0 )
        prop.SetOpacity( 0.5 )
        sprop = sliderRep.GetSelectedProperty()
        sprop.SetOpacity( 0.8 )           
        tprop = sliderRep.GetTubeProperty()
        tprop.SetColor( 0.5, 0.5, 0.5 )
        tprop.SetOpacity( 0.5 )
        cprop = sliderRep.GetCapProperty()
        cprop.SetColor( 0.0, 0.0, 1.0 )
        cprop.SetOpacity( 0.5 )
#        sliderRep.PlaceWidget(  bounds   )  
        sliderRep.SetSliderLength(0.05)
        sliderRep.SetSliderWidth(0.02)
        sliderRep.SetTubeWidth(0.01)
        sliderRep.SetEndCapLength(0.02)
        sliderRep.SetEndCapWidth(0.02)
        sliderRep.SetTitleHeight( 0.02 )    
        sliderWidget = vtk.vtkSliderWidget()
        sliderWidget.SetInteractor(self.renderWindowInteractor)
        sliderWidget.SetRepresentation( sliderRep )
        sliderWidget.SetAnimationModeToAnimate()
        sliderWidget.EnabledOn()
        sliderWidget.AddObserver("StartInteractionEvent", self.processStartInteractionEvent )
        sliderWidget.AddObserver("EndInteractionEvent", self.processEndInteractionEvent )
        sliderWidget.AddObserver("InteractionEvent", self.processInteractionEvent )
        sliderWidget.KeyPressActivationOff()
        return sliderWidget 
            
    def commandeerSlider(self, index, label, bounds, value ): 
        widget_item = self.currentSliders.get( index, None )
        if widget_item == None: 
            swidget = self.createSliderWidget(index) 
        else:
            ( process_mode, interaction_state, swidget ) = widget_item 
        srep = swidget.GetRepresentation( )      
        srep.SetTitleText( label )    
        srep.SetMinimumValue( bounds[ 0 ] )
        srep.SetMaximumValue( bounds[ 1 ]  )
        srep.SetValue( value )
        swidget.SetEnabled( 1 ) 
        self.currentSliders[index] = ( self.process_mode, self.InteractionState, swidget )
        
    def releaseSlider( self, index ):        
        ( process_mode, interaction_state, swidget ) = self.currentSliders.get( index, None )  
        if swidget: swidget.SetEnabled( 0 ) 
        
    def clearInteractions(self):
        if self.InteractionState <> None: 
            configFunct = self.configurableFunctions[ self.InteractionState ]
            configFunct.close()   
        self.process_mode = ProcessMode.Default
        self.config_mode = ConfigMode.Default
        self.InteractionState = None
        for ( process_mode, interaction_state, swidget ) in self.currentSliders.values():
            swidget.SetEnabled( 0 ) 
        
    @property
    def current_subset_specs(self):
        return self._current_subset_specs

    @current_subset_specs.setter
    def current_subset_specs(self, value):
        print "Setting current_subset_specs: ", str( value )
        self._current_subset_specs = value
                
        
    def toggleRenderMode( self ):     
        new_render_mode = ( self.render_mode + 1 ) % 2 
        self.setRenderMode( new_render_mode )
        self.render()
        
    def getPointCloud( self, ires = -1 ):
        if ires == -1: ires = self.render_mode
        if ( ( ires ==  ProcessMode.HighRes ) and ( self.partitioned_point_cloud <> None ) ):
            return self.partitioned_point_cloud  
        else:
            return  self.point_cloud_overview 

    def getPointClouds(self):
        return [ self.point_cloud_overview, self.partitioned_point_cloud ]
       
    def setRenderMode( self, render_mode ): 
        if (render_mode == ProcessMode.HighRes):
            if ( self.partitioned_point_cloud == None ): return 
            if not self.partitioned_point_cloud.hasActiveCollections(): return            
        self.render_mode = render_mode    
#        self.setScalarRange()   
        if render_mode ==  ProcessMode.HighRes:
            self.deactivate_low_res_actor = True
        else: 
            if self.partitioned_point_cloud: 
                self.partitioned_point_cloud.clear()
#            self.refreshPointSize()
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

    def getSphere(self):
        if self.sphere_source == None:
            self.createSphere()
        return self.sphere_source
    
    def configSphere( self, center, color ):
        sphere = self.getSphere()
        sphere.SetCenter( center )        
        self.sphere_actor.GetProperty().SetColor(color)

    def createSphere(self, center=(0,0,0), radius=0.2 ):
        self.sphere_source = vtk.vtkSphereSource()
        self.sphere_source.SetCenter(center)
        self.sphere_source.SetRadius(radius)        
        # mapper
        mapper = vtk.vtkPolyDataMapper()
        if vtk.VTK_MAJOR_VERSION <= 5:  mapper.SetInput(self.sphere_source.GetOutput())
        else:                           mapper.SetInputConnection(self.sphere_source.GetOutputPort())
        self.sphere_actor = vtk.vtkActor()
        self.sphere_actor.SetMapper(mapper)
        self.renderer.AddActor( self.sphere_actor )
         
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
                    color = self.getColormapManager().getColor( dval )
                    self.configSphere( pick_pos, color )
                else:
                    pick_pos, dval = self.point_cloud_overview.getPoint( iPt ) 
#                 if self.topo == PlotType.Spherical:
#                     pick_pos = glev.vtk_points_data.GetPoint( iPt )
#                 else:
#                     pick_pos = picker.GetPickPosition()                                     
                if pick_pos:        text = " Point[%d] ( %.2f, %.2f ): %s " % ( iPt, pick_pos[0], pick_pos[1], dval )
                else:               text = "No Pick"
                self.updateTextDisplay( text )
                
                if self.configDialog.plotting():
                    tseries = self.partitioned_point_cloud.getTimeseries( actor, iPt ) 
                    self.configDialog.pointPicked( tseries, pick_pos )       
            
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
        if ( self.topo == PlotType.Spherical ): self.setFocalPoint( [0,0,0] )
        self.enableSlicing() 
        self.mapManager.setMapVisibility( self.topo )
        self.render()
        

    def getMetadata(self):
        return self.point_cloud_overview.getMetadata()
            
    def onKeyEvent(self, eventArgs ):
        key = eventArgs[0]
        keysym =  eventArgs[1]
#         mods = eventArgs[2]
#         shift = mods & QtCore.Qt.ShiftModifier
#         ctrl = mods & QtCore.Qt.ControlModifier
#         alt = mods & QtCore.Qt.AltModifier
# #        print " KeyPress %x '%s' %d %d %d" % ( key, keysym, shift, ctrl, alt ) 
#         sys.stdout.flush()
#         upArrow = QtCore.Qt.Key_Up
#         if key == upArrow:
#             if self.process_mode == ProcessMode.Thresholding:
#                 self.shiftThresholding( 1, 0 )  
# #             elif self.process_mode == ProcessMode.Slicing: 
# #                 self.shiftSlice( 1, 0 )           
#         if key == QtCore.Qt.Key_Down:
#             if self.process_mode == ProcessMode.Thresholding:
#                 self.shiftThresholding( -1, 0 )  
# #             elif self.process_mode == ProcessMode.Slicing: 
# #                 self.shiftSlice( -1, 0 )
#     
#         if key == QtCore.Qt.Key_Left:   
#             if self.process_mode == ProcessMode.Thresholding:
#                 self.shiftThresholding( 0, -1 )
# #             elif self.process_mode == ProcessMode.Slicing: 
# #                 self.shiftSlice( 0, -1 )
#         if key == QtCore.Qt.Key_Right:       
#             if self.process_mode == ProcessMode.Thresholding:
#                 self.shiftThresholding( 0, 1 )
# #             elif self.process_mode == ProcessMode.Slicing: 
# #                 self.shiftSlice( 0, 1 )
            
        if   keysym == "s":  self.toggleTopo()
        elif keysym == "t":  self.stepTime()
        elif keysym == "A":  self.stepTime( False )
        elif keysym == "c":  self.toggleClipping()
        elif keysym == "m":  self.toggleRenderMode()
        elif keysym == "p":
            if self.process_mode == ProcessMode.Slicing:
                self.sliceAxisIndex =  ( self.sliceAxisIndex + 1 ) % 3 
            self.enableSlicing()  
        elif keysym == "v":
            self.enableThresholding()
#             self.updateTextDisplay( "Mode: Thresholding", True )
#             self.process_mode = ProcessMode.Thresholding 
#             self.planeWidgetOff()
#             self.shiftThresholding( 0, 0 )  
        elif keysym == "i":  self.setPointIndexBounds( 5000, 7000 )
        else: return False
        return True
                
    def enableSlicing( self ):
        self.clearSubsetting()
        self.clearInteractions()
        self.process_mode = ProcessMode.Slicing
        if self.render_mode ==  ProcessMode.LowRes:
            self.setRenderMode( ProcessMode.HighRes ) 
        spos = self.getCurrentSlicePosition()                    
        self.commandeerSlider( 1, "Slice Position", self.point_cloud_overview.getBounds(), spos )
        self.updateTextDisplay( "Mode: Slicing", True )
        self.execCurrentSlice()
                        
    def processCategorySelectionCommand( self, args ):
        op = args[0]
        if op == 'Subsets':
            if (self.process_mode == ProcessMode.Slicing) or ( len(self._current_subset_specs) == 0 ): 
                self.enableSlicing()
            elif self.process_mode == ProcessMode.Thresholding:  
                self.enableThresholding()
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
                thresholding = (self.process_mode == ProcessMode.Thresholding)
                if self.partitioned_point_cloud: 
                    self.partitioned_point_cloud.stepTime( update_points=thresholding )
                    self.point_cloud_overview.stepTime( process= not self.partitioned_point_cloud.hasActiveCollections(), update_points=thresholding )
                else:
                    self.point_cloud_overview.stepTime( process=True, update_points=thresholding)
                    
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

    def update_subset_specs(self, new_specs ):
        print " $$$$$$ update_subset_specs: %s " % str( new_specs )
        self.current_subset_specs.update( new_specs )

            
    def processSlicePlaneCommand( self, args ):
#        print " processSlicePlaneCommand: %s " % str( args )
        if args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                title = args[2]
                if not (title in SLICE_WIDTH_HR_COMP):
                    self.setRenderMode( ProcessMode.LowRes, True )
#            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud:
                self.update_subset_specs(  self.partitioned_point_cloud.getSubsetSpecs()  )            
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs ) 
                self.configDialog.newSubset( self.point_cloud_overview.getCellData() )       
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
            
    def processVariableCommand( self, args = None ):
        print " -------------------.>> Process Variable Command: ", str( args ) 
        self.processThresholdRangeCommand( args ) 

    @property
    def defvar(self):
        return self.point_cloud_overview.point_collection.var.id       
    
    def processThresholdRangeCommand( self, args, config_function = None ):
        if args and args[0] == "StartConfig":
            print " ---->>  processThresholdRangeCommand: StartConfig "
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes )
#            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud:
#                self.update_subset_specs(  self.partitioned_point_cloud.getSubsetSpecs()  )           
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
#                self.configDialog.newSubset( self.point_cloud_overview.getCellData() )
            if self.process_mode <> ProcessMode.Thresholding:
                self.enableThresholding()
        
        elif args and args[0] == "EndConfig":
            print " ---->>  processThresholdRangeCommand: EndConfig "
            self.setRenderMode( ProcessMode.HighRes )                
#            self.partitioned_point_cloud.setScalarRange( self.scalarRange.getScaledRange() )  
            self.updateThresholding()        
        elif args and args[0] == "InitConfig":
                self.updateTextDisplay( config_function.label )
                range = self.volumeThresholdRange[ self.defvar ].getRange()
                init_range = self.point_cloud_overview.getValueRange()
                config_function.range_bounds = init_range  
                config_function.initial_value = range
        elif args and args[0] == "Open":
            self.enableThresholding()
        elif args and args[0] == "Close":
            isOK = args[1]
            self.setRenderMode( ProcessMode.HighRes )
            if isOK: self.updateThresholding( self.defvar, self.volumeThresholdRange[self.defvar].getRange() )                
            self.render()
        elif args and args[0] == "UpdateConfig":
            print " ---->>  processThresholdRangeCommand: UpdateConfig[%d] " % self.thresholdCmdIndex
            if ( self.thresholdCmdIndex % self.thresholdingSkipFactor ) == 0:
                scaled_range = list( self.volumeThresholdRange[ self.defvar ].getRange() )
                scaled_range[ args[1] ] = args[2]
                self.volumeThresholdRange[ self.defvar ].setScaledRange(scaled_range)
                self.updateThresholding( self.defvar, scaled_range, False )
            self.thresholdCmdIndex = self.thresholdCmdIndex + 1
        elif args and args[0] == "Threshold Range":
            if ( self.thresholdCmdIndex % self.thresholdingSkipFactor ) == 0:
                target = extract_arg( args, 'name', offset=1, defval=self.defvar )
                scaled_range = self.volumeThresholdRange[ target ].getRange()
                self.updateThresholding( target, scaled_range, False )
            self.thresholdCmdIndex = self.thresholdCmdIndex + 1
                    
    def enableThresholding( self, args = None ):
        self.updateTextDisplay( "Mode: Thresholding", True )
        self.thresholdCmdIndex = 0
        self.clearSubsetting()
        self.process_mode = ProcessMode.Thresholding 
#         if self.render_mode ==  ProcessMode.LowRes:
#             self.setRenderMode( ProcessMode.HighRes )
        if self.scalarRange <> None:
            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )
        if self.defvar in self.volumeThresholdRange:
            self.updateThresholding( self.defvar, self.volumeThresholdRange[self.defvar].getRange(), False )
        self.updateInteractionState('thresholding')
                   
    def processColorScaleCommand( self, args, config_function ):
        if args and args[0] == "ButtonClick":
            pc =  self.getPointCloud()      
            if args[1] == "Reset":
                self.scalarRange.setRange( self.point_cloud_overview.getValueRange()  )  
                pc.setScalarRange( self.scalarRange.getScaledRange() ) 
#                self.partitioned_point_cloud.refresh(True)     
            elif args[1] == "Match Threshold Range":
                self.scalarRange.setRange( self.volumeThresholdRange[self.defvar].getRange()  )  
                pc.setScalarRange( self.scalarRange.getScaledRange() ) 
#                self.partitioned_point_cloud.refresh(True)     
        elif args and args[0] == "InitConfig":
                self.updateTextDisplay( config_function.label )
                init_range = self.point_cloud_overview.getValueRange()
                config_function.initial_value = init_range
                self.scalarRange.setScaledRange( config_function.initial_value )
                if config_function.range_bounds == None:
                    config_function.range_bounds = init_range  
                    self.scalarRange.setScalingBounds( config_function.range_bounds[0] )
                range = self.scalarRange.getRange()
        elif args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes )
            self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() )               
            if self.partitioned_point_cloud: 
                self.update_subset_specs(  self.partitioned_point_cloud.getSubsetSpecs()  )          
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
        elif args and args[0] == "EndConfig":
            if self.render_mode ==  ProcessMode.LowRes:
                print " Color Scale End Config "      
                self.setRenderMode( ProcessMode.HighRes ) 
                pc =  self.getPointCloud()             
                pc.setScalarRange( self.scalarRange.getScaledRange() )  
                pc.refresh(True) 
        elif args and args[0] == "UpdateTabPanel":
            pass                 
        elif args and args[0] == "Color Scale":
            norm_range = self.scalarRange.getScaledRange() 
            self.point_cloud_overview.setScalarRange( norm_range ) 
            self.setColorbarRange( norm_range ) 
        elif args and args[0] == "UpdateConfig": 
            srange = list( self.scalarRange.getScaledRange() ) 
            srange[ args[1] ] = args[2]
            self.scalarRange.setScaledRange( srange )       
            self.point_cloud_overview.setScalarRange( srange ) 
            self.setColorbarRange( srange ) 
        self.render()

                     
    def shiftThresholding( self, position_inc, width_inc ):
        self.volumeThresholdRange[self.defvar].shiftWindow(position_inc, width_inc) 
        self.updateThresholding( self.defvar, self.volumeThresholdRange[ self.defvar ].getRange() )

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
#        print " && ExecCurrentSlice, slice properties: %s " % ( str( self.sliceProperties ) ); sys.stdout.flush()
        self.updateSlicing( self.sliceAxisIndex, slice_bounds, **args )
    
    def pushSlice( self, slice_pos ):
        bounds = self.point_cloud_overview.getBounds()
#         if ( self.sliceAxisIndex  == 2 ):
#             lev = self.point_cloud_overview.point_collection.lev
#             if lev:
#                 dw = bounds[1] - widget_boundsbounds[0]
#                 iLev = int( (slice_pos-bounds[0]) / dw )
#                 self.updateTextDisplay( " Slice Position: %s " % str(  lev[ iLev ] ) )
#             else:
#                 self.updateTextDisplay( " Slice Position: %s " % str( slice_pos ) )
#         else:
        self.updateTextDisplay( " Slice Position: %s " % str( slice_pos ) )
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
            
    def clearSubsetting(self):
        self.current_subset_specs = {}
        
    def updateThresholding( self, target=None, trange=None, normalized=True ):
        if target <> None:
            subset_spec = ( target, trange[0], trange[1], normalized )
            self.current_subset_specs[target] = subset_spec
            print " $$$$$$ Update Thresholding: Generated spec = %s, render mode = %d " % ( str( subset_spec ), self.render_mode )
        else: print " Update Thresholding: render mode = %d " % ( self.render_mode )
        self.invalidate()
        pc = self.getPointCloud()
        pc.generateSubset( spec=self.current_subset_specs )
#         if (self.render_mode == ProcessMode.LowRes) and : 
#             self.configDialog.newSubset( self.point_cloud_overview.getCellData() )
        self.render( mode=self.render_mode )
        sys.stdout.flush()

    def processConfigCmd( self, args ):
        print " >>>>>>>>>> processConfigCmd: %s " % str(args); sys.stdout.flush()
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
        elif args[0] =='Opacity Scale':
            self.processOpacityScalingCommand( args[1:] )
        elif args[0] =='Opacity Graph':
            self.processOpacityGraphCommand( args[1:] )
        elif args[0] =='Vertical Scaling':
            self.processVerticalScalingCommand( args[1:] )
        elif args[0] =='ROI':
            self.processROICommand( args[1:] )
            
    def processROICommand( self, args ):
        print " process ROI Command: ", str( args )
        if args[0] == 'Submit':
            roi = args[1]
            self.partitioned_point_cloud.setROI( roi )  
            self.point_cloud_overview.setROI( roi )
            self.render()   

    def processPointSizeCommand( self, arg, config_function ):
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
                    self.update_subset_specs(  self.partitioned_point_cloud.getSubsetSpecs()  )          
                    self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
            self.render()
            return
        elif arg[0] == 'Open':
            return
        elif arg and arg[0] == "InitConfig":
                self.updateTextDisplay( config_function.label )
                config_function.initial_value = ( self.pointSize.getValue(0), self.pointSize.getValue(1) )
        elif arg[0] == 'StartConfig':
            render_mode = arg[1]
            self.setRenderMode( render_mode )
            if render_mode == ProcessMode.HighRes: 
                if self.partitioned_point_cloud:
                    self.partitioned_point_cloud.refresh(True)
            else:
                self.point_cloud_overview.setScalarRange( self.scalarRange.getScaledRange() ) 
                if self.partitioned_point_cloud:
                    self.update_subset_specs(  self.partitioned_point_cloud.getSubsetSpecs()  )          
                    self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
            self.render()
        elif arg[0] == 'EndConfig':
            self.setRenderMode( ProcessMode.HighRes )
            pc =  self.getPointCloud()             
            pc.setScalarRange( self.scalarRange.getScaledRange() )  
            pc.refresh(True) 
            self.render() 
        elif arg[0] == 'Point Size':
            point_size = self.pointSize.getValue( self.render_mode )      
            pc = self.getPointCloud()
            if point_size and (point_size <> pc.getPointSize()):
                pc.setPointSize( point_size )
                self.render( mode=self.render_mode )
        elif arg and arg[0] == "UpdateConfig": 
            resolution = arg[1]
            current_point_size = self.pointSize.getValue( resolution )  
            new_point_size = int( round( arg[2] ) )
            if (current_point_size <> new_point_size ):
                print " UpdateConfig, resolution = %s, new_point_size = %s " % ( str( resolution ), str( new_point_size ) )
                self.pointSize.setValue(resolution, new_point_size )      
                pc = self.getPointCloud(resolution)
                pc.setPointSize( new_point_size )
                self.setRenderMode( resolution )
                if resolution == ProcessMode.HighRes: 
                    if self.partitioned_point_cloud: self.partitioned_point_cloud.refresh(True)
                self.render( mode=resolution )
                            
    def processSlicePropertiesCommand( self, args ):
        op = args[1]
        if op in SLICE_WIDTH_HR_COMP:  
            self.setRenderMode( ProcessMode.HighRes )                 
            self.execCurrentSlice()
        elif op in SLICE_WIDTH_LR_COMP: 
            self.setRenderMode( ProcessMode.LowRes )                 
            self.execCurrentSlice()
        elif op in POS_VECTOR_COMP: 
            spos = self.getCurrentSlicePosition()
            self.updateSliderWidgets( None, spos )          
            self.execCurrentSlice()   
            
    def setColorbarRange( self, cbar_range, cmap_index=0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setDisplayRange( cbar_range )   

    def processsInitParameter( self, parameter_key, config_param ):
        paramKeys = parameter_key.split(':') 
        if paramKeys[0] == 'Color':
            if paramKeys[1] == 'Color Scale':
                self.scalarRange = config_param  
                self.scalarRange.setScalingBounds( self.point_cloud_overview.getValueRange()  )  
#                self.scalarRange.ValueChanged.connect( self.processColorScaleCommand ) 
                norm_range = self.scalarRange.getScaledRange() 
                self.point_cloud_overview.setScalarRange( norm_range )  
                self.setColorbarRange( norm_range )              
            elif paramKeys[1] == 'Color Map':
                self.colorMapCfg = config_param 
#                self.colorMapCfg.ValueChanged.connect( self.processColorMapCommand ) 
                self.processColorMapCommand()
            elif paramKeys[1] == 'Opacity Scale':
                self.oscale = config_param   
#                self.oscale.ValueChanged.connect(  self.processOpacityScalingCommand ) 
        elif paramKeys[0] == 'Subsets':
            if paramKeys[1] == 'Slice Planes':
                self.sliceProperties = config_param
#                self.sliceProperties.ValueChanged.connect(  self.processSlicePropertiesCommand )  
#                self.enableSlicing()
            elif paramKeys[1] == 'Threshold Range':
                self.volumeThresholdRange[self.defvar] = config_param                 
                config_param.setScalingBounds( self.point_cloud_overview.getValueRange()  ) 
#                config_param.ValueChanged.connect(  self.processThresholdRangeCommand )      
        elif paramKeys[0] == 'Analysis':
            if paramKeys[1] == 'Threshold Range':
                try:
                    vname = paramKeys[2]
                    config_param.setScalingBounds( self.point_cloud_overview.getValueRange( vname )  ) 
                    self.volumeThresholdRange[vname] = config_param                 
#                    config_param.ValueChanged.connect(  self.processThresholdRangeCommand )  
                except AttributeError:
                    pass    
#                self.enableThresholding()
        elif paramKeys[0] == 'Points':
            if paramKeys[1] == 'Point Size':
                self.pointSize = config_param 
                cats = config_param.getValue('cats') 
#                 self.pointSize.ValueChanged.connect(  self.processPointSizeCommand ) 
                for ires in [ ProcessMode.LowRes, ProcessMode.HighRes ]:
                    pt_size_data = cats[ires]
                    init_point_size = pt_size_data[4]
                    config_param.setValue(ires,init_point_size)  
                    pc = self.getPointCloud(ires)  
                    pc.setPointSize( init_point_size )                                 
            elif paramKeys[1] == 'Max Resolution':
                self.maxRes = config_param   
#                self.maxRes.ValueChanged.connect(  self.processMaxResolutionCommand ) 
        elif paramKeys[0] == 'Geometry':
            if paramKeys[1] == 'Projection':
                self.projection = config_param   
#                self.projection.ValueChanged.connect(  self.processProjectionCommand ) 
            elif paramKeys[1] == 'Vertical Scaling':
                self.vscale = config_param   
#                self.vscale.ValueChanged.connect(  self.processVerticalScalingCommand ) 
            elif paramKeys[1] == 'Vertical Variable':
                self.vertVar = config_param   
#                self.vertVar.ValueChanged.connect(  self.processVerticalVariableCommand )
        elif paramKeys[0] == 'Variables':
            self.variables[ paramKeys[1] ] = config_param
#            config_param.ValueChanged.connect(  self.processVariableCommand )
                
    def processMaxResolutionCommand(self, args=None ):
        max_res_spec =  self.maxRes.getValue() 
        if self.partitioned_point_cloud:
            self.partitioned_point_cloud.setResolution( max_res_spec )
        if not self.partitioned_point_cloud.hasActiveCollections():
            self.render_mode = ProcessMode.LowRes
        self.render()

    def processOpacityScalingCommand(self, args, config_function ):
        arange = self.oscale.getRange()
        if args[0] == "InitConfig":
            self.updateTextDisplay( config_function.label )
            config_function.initial_value = arange
        elif args[0] == "UpdateConfig": 
            srange = list( arange ) 
            srange[ args[1] ] = args[2]
            self.oscale.setRange( srange )       
        colormapManager = self.getColormapManager()
        alpha_range = colormapManager.getAlphaRange()
        if ( abs( arange[0] - alpha_range[0] ) > 0.1 ) or ( abs( arange[1] - alpha_range[0] ) > 0.1 ):
            colormapManager.setAlphaRange( arange )
            self.render()
            
    def processOpacityGraphCommand(self, args=None ):
        colormapManager = self.getColormapManager()
        colormapManager.setAlphaGraph( args[0] )
        self.render()

    def setZScale( self, zscale_data, **args ):
        pass
#        self.vscale.setValue( 'value', zscale_data[1], True )
#        self.processVerticalScalingCommand( [ "UpdateConfig" ] )

    def startConfiguration( self, x, y, config_types ):
        DV3DPlot.startConfiguration( self, x, y, config_types ) 
#         if (self.InteractionState == 'zScale') and not self.configuring:
#             self.processVerticalScalingCommand( [ "StartConfig" ] )

    def endConfiguration( self ):
        DV3DPlot.endConfiguration( self ) 
#         if (self.InteractionState == 'zScale'):
#             self.processVerticalScalingCommand( [ "EndConfig" ] )
                            
    def processVerticalScalingCommand( self, args, config_function ):
        if args and args[0] == "StartConfig":
            if self.render_mode ==  ProcessMode.HighRes:
                self.setRenderMode( ProcessMode.LowRes ) 
                self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
                self.render( mode=self.render_mode )   
        elif args and args[0] == "EndConfig":
            scaling_spec = ( self.vertVar.getValue(), self.vscale.getValue() )
            if self.partitioned_point_cloud:
                self.partitioned_point_cloud.generateZScaling( spec=scaling_spec )
            self.setRenderMode( ProcessMode.HighRes )
#            self.releaseSlider( 1 ) 
            self.render() 
        elif args and args[0] == "InitConfig":
                self.updateTextDisplay( config_function.label )                      
                config_function.initial_value = ( self.vscale.getValue(), None )
        elif args and args[0] == "UpdateConfig":           
            self.vscale.setValue( 'value', args[2], True ) 
            scaling_spec = ( self.vertVar.getValue(), args[2] )
            self.point_cloud_overview.generateZScaling( spec=scaling_spec )
            self.render()
        elif args and args[0] == "UpdateTabPanel":
            pass
        else:                     
            scaling_spec = ( self.vertVar.getValue(), args[2] )
            self.point_cloud_overview.generateZScaling( spec=scaling_spec )
#            pcbounds = self.point_cloud_overview.getBounds()
#            self.widget_bounds[4:6] = pcbounds[4:6]
#            self.planeWidget.PlaceWidget( self.widget_bounds )
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
        colorCfg = [ self.colorMapCfg.getValue('Colormap'), self.colorMapCfg.getValue('Invert'), self.colorMapCfg.getValue('Stereo'), self.colorMapCfg.getValue('Colorbar') ]
        self.setColormap( colorCfg ) 
        
    def clearSliceSpecs(self): 
        for s_axis in self.sliceAxes: 
            if s_axis in self.current_subset_specs: 
                del self.current_subset_specs[ s_axis ]

    def enableRender(self, **args ):
        onMode = args.get( 'mode', ProcessMode.AnyRes )
        return (onMode == ProcessMode.AnyRes) or ( onMode == self.render_mode )

    def updateSlicing( self, sliceIndex, slice_bounds, **args ):
        self.invalidate()
        self.clearSliceSpecs()
        ( rmin, rmax ) = slice_bounds[ self.render_mode ]
        self.current_subset_specs[ self.sliceAxes[sliceIndex] ] = ( self.sliceAxes[sliceIndex], rmin, rmax, True )
        if self.render_mode ==  ProcessMode.HighRes:
            self.partitioned_point_cloud.generateSubset( spec=self.current_subset_specs, allow_processing=True )
        else:
            self.point_cloud_overview.generateSubset( spec=self.current_subset_specs )
#            if self.partitioned_point_cloud:
#                self.partitioned_point_cloud.generateSubset( spec=self.current_subset_specs, allow_processing=False )
#        self.configDialog.newSubset( self.point_cloud_overview.getCellData() )
        self.render( mode=self.render_mode )

#    def updateSlicing1( self, sliceIndex, slice_bounds ):
#        self.invalidate()
#        for iRes, pc in enumerate( self.getPointClouds() ):
#            ( rmin, rmax ) = slice_bounds[iRes]
#            pc.generateSubset( ( self.sliceAxes[sliceIndex], rmin, rmax ) )
#        self.render( mode=ProcessMode.LowRes )
                  
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
        if vtk.VTK_MAJOR_VERSION <= 5:  self.earth_mapper.SetInput(earth_polydata)
        else:                           self.earth_mapper.SetInputData(earth_polydata)        
        self.earth_actor = vtk.vtkActor()
        self.earth_actor.SetMapper( self.earth_mapper )
        self.earth_actor.GetProperty().SetColor(0,0,0)
        self.renderer.AddActor( self.earth_actor )

 
    def processInteractionEvent( self, obj=None, event=None ):
#        print " processInteractionEvent: ( %s %d )" % ( self.InteractionState, self.process_mode )
        if ( self.InteractionState <> None ): 
            srep = obj.GetRepresentation( ) 
            config_function = self.getConfigFunction( self.InteractionState )
            config_function.processInteractionEvent( [ "UpdateConfig", self.getSliderIndex(obj), srep.GetValue() ] )                         
        else:
            if self.process_mode == ProcessMode.Slicing:
                ( process_mode, interaction_state, swidget ) = self.currentSliders[1] 
                slice_pos = swidget.GetRepresentation( ).GetValue()
                self.pushSlice( slice_pos )         

    def processStartInteractionEvent( self, obj, event ): 
        slider_index = self.checkInteractionState( obj, event ) 
#        print " processStartInteractionEvent: ( %s %d )" % ( self.InteractionState, self.process_mode )
        if ( self.InteractionState <> None ): 
            config_function = self.getConfigFunction( self.InteractionState )
            config_function.processInteractionEvent( [ "StartConfig", slider_index ] )  
        else:   
            if self.process_mode == ProcessMode.Slicing:
                self.setRenderMode( ProcessMode.LowRes )
                
    def checkInteractionState( self, obj, event ):
        for item in self.currentSliders.items():
            ( process_mode, interaction_state, swidget ) = item[1]
            if ( id( swidget ) == id( obj ) ): 
                if self.InteractionState <> interaction_state:            
                    self.processEndInteractionEvent( obj, event )
                    if self.InteractionState <> None: self.endInteraction()
                    self.InteractionState = interaction_state
                    self.process_mode = process_mode
                    print "Change Interaction State: %s %d " % ( self.InteractionState, self.process_mode )
                return item[0]
        return None
            
    def getSliderIndex(self, obj ):
        for index in self.currentSliders:
            ( process_mode, interaction_state, swidget ) = self.currentSliders[index]
            if ( id( swidget ) == id( obj ) ): return index
        return None

    def processEndInteractionEvent( self, obj, event ):  
#        print " processEndInteractionEvent: ( %s %d )" % ( self.InteractionState, self.process_mode )
        if ( self.InteractionState <> None ): 
            config_function = self.getConfigFunction( self.InteractionState )
            config_function.processInteractionEvent( [ "EndConfig" ] )  
        else:   
            if self.process_mode == ProcessMode.Slicing:
                self.setRenderMode( ProcessMode.HighRes )
                self.execCurrentSlice()
#            self.setSlicePosition( self.getSlicePosition() )
#            self.printInteractionStyle( 'processEndInteractionEvent')
#            self.renderWindow.GetInteractor().SetInteractorStyle( self.navigationInteractorStyle )
#            self.emit(QtCore.SIGNAL("UpdateGui"), ( "SetSlicePosition", self.getSlicePosition() ) ) 
               
                
    def initCollections( self, nCollections, init_args, **args ):
        if nCollections > 0:
            args[ 'interactor' ] = self.renderWindowInteractor 
            self.partitioned_point_cloud = vtkPartitionedPointCloud( nCollections, init_args, **args )
            self.partitioned_point_cloud.NewDataAvailable.connect( self.newDataAvailable )
        else:
            self.render_mode = ProcessMode.LowRes
#        self.partitioned_point_cloud.connect( self.partitioned_point_cloud, QtCore.SIGNAL('updateScaling'), self.updateScaling )        
        self.createRenderer()
        self.low_res_actor = self.point_cloud_overview.actor
        self.renderer.AddActor( self.low_res_actor )
#        self.pointPicker.AddPickList( self.low_res_actor )
        
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
            
#     def decrementOverviewResolution( self ):
#         if self.resolutionCounter.isActive(): # self.point_cloud_overview.isVisible():
#             isBottomedOut = self.resolutionCounter.decrement()
#             psize = self.resolutionCounter.value()
# #            print "Decrement point size: %d, isBottomedOut: %s " % ( psize, str(isBottomedOut) ); sys.stdout.flush()
#             self.point_cloud_overview.setPointSize( psize )
#             if isBottomedOut: self.point_cloud_overview.hide()
            
    def refreshPointSize(self):
        self.point_cloud_overview.setPointSize( self.pointSize.getValue( ProcessMode.LowRes ) )
             
    def newDataAvailable( self, pcIndex, data_type ):
        if ( self.partitioned_point_cloud <> None ): 
            pc = self.partitioned_point_cloud.getPointCloud( pcIndex )
            pc.show()
#            self.decrementOverviewResolution()
            self.partitioned_point_cloud.postDataQueueEvent()
            pc.setScalarRange( self.scalarRange.getScaledRange() )
            self.updateZRange( pc )
            trngs = pc.getThresholdingRanges() 
#            if trngs:
#                text = ' '.join( [ "%s: (%f, %f )" % (rng_val[0], rng_val[1], rng_val[2] )  for rng_val in trngs.values() ] )
#                text = " Thresholding Range[%d]: ( %.3f, %.3f )\n Colormap Range: %s " % ( pcIndex, trng[0], trng[1], str( self.scalarRange.getRange() ) )
#                self.updateTextDisplay( text )
#            print " Subproc[%d]-. new Thresholding Data Available: %s " % ( pcIndex, str( pc.getThresholdingRange() ) ); sys.stdout.flush()
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
        n_subproc_points = args.get( 'n_subproc_points', 500000 )  
        show = args.get( 'show', False )  
        n_cores = args.get( 'n_cores', 32 )    
        self.point_cloud_overview = vtkLocalPointCloud( 0, max_points=n_overview_points ) 
        lut = self.getLUT()
        self.point_cloud_overview.initialize( init_args, lut = lut, maxStageHeight=self.maxStageHeight  )
        nInputPoints = self.point_cloud_overview.getNumberOfInputPoints()
        if ( n_subproc_points > nInputPoints ): n_subproc_points = nInputPoints
        nPartitions = int( round( min( nInputPoints / n_subproc_points, 10  ) ) )
        nCollections = min( nPartitions, n_cores )
        print " Init PCViewer, nInputPoints = %d, n_overview_points = %d, n_subproc_points = %d, nCollections = %d, overview skip index = %s" % ( nInputPoints, n_overview_points, n_subproc_points, nCollections, self.point_cloud_overview.getSkipIndex() )
        self.initCollections( nCollections, init_args, lut = lut, maxStageHeight=self.maxStageHeight  )
        interface = init_args[2]
        if self.widget and show: self.widget.show()
        if self.useGui: self.createConfigDialog( show, self.processConfigCmd, interface )
        else: 
            pc = self.point_cloud_overview.getPointCollection()
            cfgInterface = ConfigurationInterface( metadata=pc.getMetadata(), defvar=pc.var.id, callback=self.processConfigCmd  )
            cfgInterface.build()
            cfgInterface.activate()
            self.processConfigCmd( [ 'CategorySelected', 'Subsets' ] )
            
        self.initializeConfiguration( mid=id(self) )  
        self.start()


    
class QPointCollectionMgrThread( threading.Thread ):
    
    def __init__( self, pointCollectionMgr, **args ):
        threading.Thread.__init__( self ) # , parent=pointCollectionMgr )
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
                             
# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser(description='DV3D Point Cloud Viewer')
#     parser.add_argument( 'PATH' )
#     parser.add_argument( '-d', '--data_dir', dest='data_dir', nargs='?', default="~/data", help='input data dir')
#     parser.add_argument( '-t', '--data_type', dest='data_type', nargs='?', default="CSU", help='input data type')
#     ns = parser.parse_args( sys.argv )
#     
#     kill_all_zombies()
# 
#     app = QtGui.QApplication(['Point Cloud Plotter'])
#     point_size = 1
#     n_overview_points = 500000
#     height_varname = None
#     data_dir = os.path.expanduser( ns.data_dir )
#     height_varnames = []
#     var_proc_op = None
#     
#     if ns.data_type == "WRF":
#         data_file = os.path.join( data_dir, "WRF/wrfout_d01_2013-07-01_00-00-00.nc" )
#         grid_file = None
#         varname = "U"        
#     elif ns.data_type == "CAM":
#         data_file = os.path.join( data_dir, "CAM/f1850c5_t2_ANN_climo-native.nc" )
#         grid_file = os.path.join( data_dir, "CAM/ne120np4_latlon.nc" )
#         varname = "U"
#         height_varnames = [ "Z3" ]
#     elif ns.data_type == "ECMWF":
#         data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ecmwf.xml" )
#         grid_file = None
#         varname = "U_velocity"   
#     elif ns.data_type == "GEOS5":
#         data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ac-comp1-geos5.xml" )
#         grid_file = None
#         varname = "uwnd"   
#     elif ns.data_type == "MMF":
#         data_file = os.path.join( data_dir, "MMF/diag_prs.20080101.nc" )
#         grid_file = None
#         varname = "u"
#     elif ns.data_type == "GEOD":
#         file_name =  "temperature_19010101_000000.nc" # "vorticity_19010102_000000.nc" # 
#         data_file = os.path.join( data_dir, "GeodesicGrid", file_name )
#         grid_file = os.path.join( data_dir, "GeodesicGrid", "grid.nc" )
#         varname = "temperature_ifc" # "vorticity" # 
#         var_proc_op = None
#     elif ns.data_type == "CSU":
#         file_name =  "psfc.nc" 
#         data_file = os.path.join( data_dir, "ColoState", file_name )
#         grid_file = os.path.join( data_dir, "ColoState", "grid.nc" )
#         varname = "pressure" 
#         var_proc_op = None
#         
#     g = CPCPlot() 
#     g.init( init_args = ( grid_file, data_file, varname, height_varname, var_proc_op ), n_overview_points=n_overview_points, n_cores=2 ) # , n_subproc_points=100000000 )
#     g.createConfigDialog()
#         
#     app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
#     app.exec_() 
#     g.terminate() 
#     
