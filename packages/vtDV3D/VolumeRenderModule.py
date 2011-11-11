'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, math
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from ColorMapManager import ColorMapManager 
from InteractiveConfiguration import QtWindowLeveler 
from vtUtilities import *
from SimplePlot import GraphWidget
from PersistentModule import *

LegacyAbsValueTransferFunction = 0
LinearTransferFunction = 1 
PosValueTransferFunction = 2  
NegValueTransferFunction = 3  
AbsValueTransferFunction = 4
FullValueTransferFunction = 5 

PositiveValues = 0
NegativeValues = 1
AllValues = 2

def distance( p0, p1 ):
    dp = [ (p0[i]-p1[i]) for i in range(3) ]
    return math.sqrt( dp[0]*dp[0] + dp[1]*dp[1] + dp[2]*dp[2] )

class TransferFunction( QObject ):
    
    def __init__(self, **args ):
        self.type = args.get( 'type', FullValueTransferFunction )
        self.data = args.get( 'data', None )
        
    def  getNumberOfNodes(self):
        if self.type == AbsValueTransferFunction: return 12
        else: return 9
        
    def setType(self, tf_type ):
        self.type = tf_type
        
class TransferFunctionConfigurationDialog( QDialog ): 
     
    def __init__(self, parent=None, **args):
        QDialog.__init__( self, parent )
        self.setWindowTitle("Transfer Function Configuration")
        self.graph = GraphWidget( size=(400,300), nticks=(5,5) )
        self.functions = {} 
        self.setLayout(QVBoxLayout())
        self.currentTransferFunction = None
        self.tf_map = { "Signed Value" : FullValueTransferFunction, "Absolute Value" : AbsValueTransferFunction }
        
        tf_type_layout = QHBoxLayout()
        tf_type_label = QLabel( "Transfer Function Type:"  )
        tf_type_layout.addWidget( tf_type_label ) 

        tf_type_combo =  QComboBox ( self )
        tf_type_label.setBuddy( tf_type_combo )
        tf_type_combo.setMaximumHeight( 30 )
        tf_type_layout.addWidget( tf_type_combo )
        for tf_name in self.tf_map.keys(): 
            tf_type_combo.addItem( tf_name )     
        self.connect( tf_type_combo, SIGNAL("currentIndexChanged(QString)"), self.updateTransferFunctionType )  
        self.layout().addLayout( tf_type_layout )
                
        self.closeButton = QPushButton('Ok', self)
        self.layout().addWidget( self.graph )         
        self.layout().addWidget(self.closeButton)
        self.connect(self.closeButton, SIGNAL('clicked(bool)'), self.close)
        self.closeButton.setShortcut('Enter')
        
    def addTransferFunction( self, name, **args ):
        self.currentTransferFunction = TransferFunction( **args ) 
        self.functions[ name ]  = self.currentTransferFunction
        self.graph.buildGraph( self.currentTransferFunction.getNumberOfNodes() ) 
    
    def updateGraph( self, xbounds, ybounds, data ):
        self.graph.createGraph( xbounds, ybounds, data )
                
    def updateTransferFunctionType( self, value ):
        if self.currentTransferFunction: self.currentTransferFunction.setType( self.tf_map[ str(value) ] )
        
class PM_VolumeRenderer(PersistentVisualizationModule):
    """
        This module generates volume rendering of 3D volumetric (<i>vtkImagedata</i>) data.  Colormap scaling is controlled using 
        the <b>colorRangeScale</b> leveling function.  The volume render transfer function is configured using the <b>functionScale</b> and <b>opacityScale</b>
        leveling functions.
        <h3>  Command Keys </h3> 
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> l </td> <td> Toggle show colorbar. </td>
        </table>
    """       
    
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.max_opacity = 1.0
        self.vthresh = None
        self.filterOutliers = False
        self.refinement = [ 0.0, 0.5 ]
        self.imageRange = None
        self.otf_data = None
        self.ctf_data = None
        self.transferFunctionConfig = TransferFunctionConfigurationDialog()
        self.transferFunctionConfig.addTransferFunction( 'default' )
        self.addConfigurableLevelingFunction( 'colorScale',    'C', setLevel=self.generateCTF, getLevel=self.getDataRangeBounds, layerDependent=True, units=self.units )
        self.addConfigurableLevelingFunction( 'functionScale', 'T', setLevel=self.generateOTF, getLevel=self.getDataRangeBounds, layerDependent=True, units=self.units, initRange=[ 0.0, 1.0, 1, self.refinement[0], self.refinement[1] ], gui=self.transferFunctionConfig  )
        self.addConfigurableLevelingFunction( 'opacityScale',  'O', setLevel=self.adjustOpacity, layerDependent=True  )
    
#    def onModified( self, caller, event ):
#        self.applyFieldData( [self.volume] )            

    def onRender( self, caller, event ):
        pass
#        scale = self.volume.GetScale()
#        bounds = self.volume.GetBounds()
#        origin = self.volume.GetOrigin()
#        dims = [  int( round( ( bounds[2*i+1]-bounds[2*i] ) / scale[i] ) ) for i in range(3) ]
#        print " Volume position: %s " % str( self.volume.GetPosition() )
#        print "Volume Render Event: scale = %s, bounds = %s, origin = %s, dims = %s " % ( str2f( scale ), str2f( bounds ), str2f( origin ), str( dims )  )
                 
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """  
        extent = self.input.GetExtent()  
        self.sliceCenter = [ (extent[2*i+1]-extent[2*i])/2 for i in range(3) ]       
        spacing = self.input.GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input.GetOrigin()
        ox, oy, oz = origin
        self._range = [ self.rangeBounds[0], self.rangeBounds[1], self.rangeBounds[0], 0 ]
        dataType = self.input.GetScalarTypeAsString()
        self.setMaxScalarValue( self.input.GetScalarType() )
        self.pos = [ spacing[i]*extent[2*i] for i in range(3) ]
#        if ( (origin[0] + self.pos[0]) < 0.0): self.pos[0] = self.pos[0] + 360.0
        bounds = [ ( origin[i/2] + spacing[i/2]*extent[i] ) for i in range(6) ]
        print " @@@VolumeRenderer@@@   Data Type = %s, range = (%f,%f), max_scalar = %s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], self._max_scalar_value )
        print "Extent: %s " % str( self.input.GetWholeExtent() )
        print "Spacing: %s " % str( spacing )
        print "Origin: %s " % str( origin )
        print "Dimensions: %s " % str( self.input.GetDimensions() )
        print "Bounds: %s " % str( bounds )
        print "Input Bounds: %s " % str( self.input.GetBounds() )
        print "VolumePosition: %s " % str( self.pos )
        
#        self.inputInfo = self.inputPort.GetInformation() 
#        translation = inputInfo.Get( ResampleTranslationKey  )                                     
        
        # Create transfer mapping scalar value to color
        self.colorTransferFunction = vtk.vtkColorTransferFunction()
                
        # Create transfer mapping scalar value to opacity
        self.opacityTransferFunction = vtk.vtkPiecewiseFunction()        
                
        # The property describes how the data will look
        self.volumeProperty = vtk.vtkVolumeProperty()
        self.volumeProperty.SetColor(self.colorTransferFunction)
        self.volumeProperty.SetScalarOpacity(self.opacityTransferFunction)
        
        # The mapper knows how to render the data
        self.volumeMapper = vtk.vtkVolumeTextureMapper2D()
#        self.volumeMapper.SetScalarModeToUsePointFieldData()
#        self.inputModule.inputToAlgorithm( self.volumeMapper )
        
        # The volume holds the mapper and the property and can be used to
        # position/orient the volume
        self.volume = vtk.vtkVolume()
        self.volume.SetScale( 1.0, 1.0, 1.0 )   
#        self.volume.SetScale( spacing[0], spacing[1], spacing[2] )   
        self.volume.SetMapper(self.volumeMapper)
        self.volume.SetProperty(self.volumeProperty)
#        self.volume.AddObserver( 'AnyEvent', self.EventWatcher )
        self.input.AddObserver( 'AnyEvent', self.EventWatcher )
        
        self.volume.SetPosition( self.pos )

        self.renderer.AddVolume( self.volume )
        self.renderer.SetBackground(0.1, 0.1, 0.2) 


    def rebuildVolume( self ):
        self.volumeMapper = vtk.vtkVolumeTextureMapper2D()
        self.volume = vtk.vtkVolume()
        self.volume.SetScale( 1.0, 1.0, 1.0 )   
        self.volume.SetMapper(self.volumeMapper)
        self.volume.SetProperty(self.volumeProperty)        
        self.volume.SetPosition( self.pos )
        self.renderer.AddVolume( self.volume )

    def setActiveScalars( self ):
        pointData = self.input.GetPointData()
        if self.activeLayer:  
            pointData.SetActiveScalars( self.activeLayer )
            print " SetActiveScalars on pointData(%s): %s" % ( addr(pointData), self.activeLayer )

#    def setActiveScalars( self ):
#        if self.activeLayer <> None: 
#            print "  --->> VolumeRender Set Active Scalars: %s " % self.activeLayer
#            self.volumeMapper.SelectScalarArray(  self.activeLayer  )  
                                      
    def updateModule( self, **args  ):
        if self.inputModule:
            self.inputModule.inputToAlgorithm( self.volumeMapper )
            self.set3DOutput()

#            center = self.volume.GetCenter() 
#            matrix = self.volume.GetMatrix()
#            bounds = self.volume.GetBounds() 
#            mapper_bounds = self.volumeMapper.GetBounds()   
#            position = self.volume.GetPosition () 
#            printArgs( "Volume attrs", center=center,  matrix=matrix, bounds=bounds, mapper_bounds=mapper_bounds, position=position )   

    def UpdateCamera( self ):
#        self.volume.UseBoundsOff()     
        print " *** volume visible: %s " % ( self.volume.GetVisibility() )
        aCamera = self.renderer.GetActiveCamera()
        bounds = self.volume.GetBounds()
        p = aCamera.GetPosition()
        f = aCamera.GetFocalPoint()
        printArgs( "ResetCameraClippingRange", focal_point=f, cam_pos=p, vol_bounds=bounds )
        self.renderer.ResetCameraClippingRange() 
#        bounds = self.volume.GetBounds()
#        center = ( (bounds[0]+bounds[1])/2.0, (bounds[2]+bounds[3])/2.0, (bounds[4]+bounds[5])/2.0 ) 
#        aCamera = self.renderer.GetActiveCamera()
#        t0 = aCamera.GetThickness()
#        r0 = aCamera.GetClippingRange() 
#        aCamera.SetClippingRange( 0.1, 1000.0 )       
##        self.renderer.ResetCameraClippingRange( bounds[0], bounds[1], bounds[2], bounds[3], bounds[4], bounds[5] ) 
#        t1 = aCamera.GetThickness()
#        r1 = aCamera.GetClippingRange()     
#        d = aCamera.GetDistance()
#        f = aCamera.GetFocalPoint()
#        p = aCamera.GetPosition()
#        vol_dist = distance( p, center )
#        
#        printArgs( "ResetCameraClippingRange", focal_point=f, cam_pos=p, focal_point_dist=d, vol_dist=vol_dist, vol_bounds=bounds )
#        print " *** thickness-range>>> %s-%s ---> %s-%s " % ( str(t0), str(r0), str(t1), str(r1) ) 
        
#    def finalizeRendering(self):
#        self.SetCameraPosition() 
#        self.UpdateCamera()  
              
#    def UpdateCamera():
#      camera = self.renderer.GetActiveCamera()
#      if camera:
#        bounds = self.volume.GetBounds()
#        double spos = bounds[this->SliceOrientation * 2];
#        double cpos = cam->GetPosition()[this->SliceOrientation];
#        double range = fabs(spos - cpos);
#        double *spacing = input->GetSpacing();
#        double avg_spacing = 
#          (spacing[0] + spacing[1] + spacing[2]) / 3.0;
#        cam->SetClippingRange(
#          range - avg_spacing * 3.0, range + avg_spacing * 3.0);       
#        self.setActiveScalars()
#        if self.scalarRange == None:
#            pointData = self.input.GetPointData()
#            scalars = pointData.GetScalars()
#            self.scalarRange = scalars.GetRange()
#            self.scalarRange.append( 1 )
#        sname = "NULL" if (scalars == None) else scalars.GetName()
#        print "  --->> VolumeRender Update Module, timestep = %d, pointData%s, scalars: %s (%s) " % ( self.iTimestep, addr(pointData), sname, addr(scalars) )

#    def updateLayerEvent(self, caller, event ):
#        self.setActiveScalars(  )  
        
    def EventWatcher( self, caller, event ): 
#        print "Event %s on class %s "  % ( event, caller.__class__.__name__ ) 
#        print "  --- Volume Input Extent: %s " % str( self.input.GetWholeExtent() )
        pass          
                                                                                               
    def onKeyPress( self, caller, event ):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
#        print " -- Key Press: %c ( %d: %s ), event = %s " % ( key, ord(key), str(keysym), str( event ) )
               
    def generateCTF( self, ctf_data= None ):
        if ctf_data: self.ctf_data = ctf_data
        else: ctf_data = self.ctf_data
        if ctf_data:
            self.imageRange = self.getImageValues( ctf_data[0:2] ) 
            self.lut.SetTableRange( self.imageRange[0], self.imageRange[1] )
            self.colormapManager.setDisplayRange( ctf_data )
            self.invert = ctf_data[2]
            self.rebuildColorTransferFunction()
        
    def rebuildColorTransferFunction( self ):
        if self.imageRange <> None:
            self.colorTransferFunction.RemoveAllPoints ()
            nc = self.lut.GetNumberOfTableValues()
            dr = (self.imageRange[1] - self.imageRange[0]) 
    #        print "Generate CTF: range = ( %f %f )" % ( ctf_data[0], ctf_data[1])
            
            for i in range(nc):
                interval_position = float(i)/nc
                data_value = self.imageRange[0] + dr * interval_position
                color = self.lut.GetTableValue( (nc-i-1) if self.invert else i )
                self.colorTransferFunction.AddRGBPoint( data_value, color[0], color[1], color[2] )
    #            if i % 50 == 0:  print "   --- ctf[%d:%.2f] --  %.2e: ( %.2f %.2f %.2f ) " % ( i, table_value, data_value, color[0], color[1], color[2] )
            
          
    def PrintStats(self):
        print_docs( self.volume.mapper )
        self.print_traits()
        print "Volume: bounds=%s, scale=%s, mapper=%s" % ( str(self.volume.bounds), str(self.volume.scale), str(self.volume_mapper_type) )

 
#    def adjustOpacity1( self, opacity_data ): 
#        self.max_opacity = opacity_data[1] if opacity_data[1] < 1.0 else 1.0
#        vmin, vmax = self._range[0], self._range[1]
#        filterOutliers = opacity_data[2]
#        range_min, range_max = self.rangeBounds[0], self.rangeBounds[1]
#        vthresh = opacity_data[0]*range_max if opacity_data[0] > 0.0 else 0.0
#        
#        if (vmin >= vmax):
#            if range_max > range_min:
#                vmin =  range_min
#                vmax = range_max
#            else:
#                return None
#            
#        if (range_min >= range_max): 
#            range_min = vmin
#            range_max = vmax
#        
#        self._shift = -range_min
#        self._scale = self._max_scalar_value / ( range_max - range_min )
##        if self._rescaleInput: 
##            self._input_rescale_mapper.shift = self._shift
##            self._input_rescale_mapper.scale = self._scale
##        print "  --- UpdateVolumeScaling>> (%f %f) (%f %f) %f: mapper=%s" % ( vmin, vmax, self._shift, self._scale, self.max_opacity, str(self.volume_mapper_type) )
#
#        scaled_range = [ (vmin+self._shift)*self._scale, (vmax+self._shift)*self._scale, vthresh*self._scale ]
#        self.updateOFT( scaled_range, filterOutliers )
#        printArgs( "adjustOpacity", scaled_range=scaled_range,  opacity_data=opacity_data, otf_irange=self._range, irange_bounds=(range_min, range_max), init_range=(self._range[0], self._range[1]) )   


    def adjustOpacity( self, opacity_data ):
        maxop = abs( opacity_data[1] ) 
        self.max_opacity = maxop if maxop < 1.0 else 1.0
        range_min, range_max = self.rangeBounds[0], self.rangeBounds[1]
#        self.vthresh = opacity_data[0]*(self.seriesScalarRange[1]-self.seriesScalarRange[0])*0.02
        self.updateOFT()
#        printArgs( "adjustOpacity", irange=self._range,  max_opacity=self.max_opacity, opacity_data=opacity_data, vthresh=vthresh, ithresh=self._range[3] )   

    def generateOTF( self, otf_data=None ): 
        if otf_data: self.otf_data = otf_data
        else: otf_data = self.otf_data
        if otf_data:
            self._range = self.getImageValues( ( otf_data[0], otf_data[1], 0.0 ) )
#            self._range.append( self.scaleToImage( self.vthresh ) if self.vthresh else 0.0 )         
            if len( otf_data ) > 3: self.refinement = [ otf_data[3], otf_data[4] ]
            self.updateOFT()
#        printArgs( "generateOTF", irange=self._range,  otf_data=otf_data )   
           
#    def generateOTF1( self, otf_data ): 
#        self._range = self.getImageValues( otf_data[0:2] ) 
#        vmin, vmax, vthresh = self._range[0], self._range[1], 0.0
#        range_min, range_max = self.rangeBounds[0], self.rangeBounds[1]
#        filterOutliers = otf_data[2]
#        if (vmin >= vmax):
#            if range_max > range_min:
#                vmin =  range_min
#                vmax = range_max
#            else:
#                return None
#            
#        if (range_min >= range_max): 
#            range_min = vmin
#            range_max = vmax
#        
#        self._shift = -range_min
#        self._scale = self._max_scalar_value / ( range_max - range_min )
##        if self._rescaleInput: 
##            self._input_rescale_mapper.shift = self._shift
##            self._input_rescale_mapper.scale = self._scale
##        print "  --- UpdateVolumeScaling>> (%f %f) (%f %f) %f: mapper=%s" % ( vmin, vmax, self._shift, self._scale, self.max_opacity, str(self.volume_mapper_type) )
#
#        scaled_range = [ (vmin+self._shift)*self._scale, (vmax+self._shift)*self._scale, vthresh*self._scale ]
#        self.updateOFT( scaled_range, filterOutliers )
#        printArgs( "generateOTF", scaled_range=scaled_range,  otf_data=otf_data, vrange=(vmin, vmax), vrange_bounds=(range_min, range_max), init_range=(self._range[0], self._range[1]) )   

    def getTransferFunctionPoints( self, range, pointType ):
        zero_point = range[2] 
        scalar_bounds = [ 0, self._max_scalar_value ]
        points = []  
#        print "Generate OTF: range = ( %f %f ), zero_point = %f, refinement = ( %f %f ), max_opacity = %s" % ( range[0], range[1], zero_point, self.refinement[0], self.refinement[1], self.max_opacity )             
        if pointType == PositiveValues:
            pos_range = [ range[0], range[1] ]
            if (range[0] < zero_point ) and ( range[1] > zero_point ): pos_range[ 0 ] = zero_point
            elif ( range[0] < zero_point ) and ( range[1] < zero_point ): pos_range = [ zero_point + (zero_point-range[1]), zero_point + (zero_point-range[0]) ]
            pos_range = [ bound(pos_range[0],scalar_bounds), bound(pos_range[1],scalar_bounds) ]
            mid_point = ( pos_range[0] + pos_range[1] ) / 2.0   
            half_width =   ( pos_range[1] - pos_range[0] ) / 2.0 
            points.append( ( zero_point, 0.) )
            points.append( ( pos_range[0] - self.refinement[0] * ( pos_range[0] - zero_point ), self.max_opacity * self.refinement[0] ) )
            points.append( ( mid_point - self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            points.append( ( mid_point, self.max_opacity ) )
            points.append( ( mid_point + self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            points.append( ( pos_range[1], 0. )  )
        elif pointType == NegativeValues:
            neg_range = [ range[0], range[1] ]
            if (range[0] < zero_point ) and ( range[1] > zero_point ): neg_range[ 0 ] = zero_point
            elif ( range[0] < zero_point ) and ( range[1] < zero_point ): neg_range = [ zero_point + (zero_point-range[1]), zero_point + (zero_point-range[0]) ]
            neg_range = [ bound(neg_range[0],scalar_bounds), bound(neg_range[1],scalar_bounds) ]
            mid_point = ( neg_range[0] + neg_range[1] ) / 2.0   
            half_width = ( neg_range[1] - neg_range[0] ) / 2.0 
            points.append( ( neg_range[0], 0. )  )
            points.append( ( mid_point - self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            points.append( ( mid_point, self.max_opacity ) )
            points.append( ( mid_point + self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            points.append( ( neg_range[1] + self.refinement[0] * ( zero_point - neg_range[1] ), self.max_opacity * self.refinement[0] ) )
            points.append( ( zero_point, 0.) )
        elif pointType == AllValues:
            full_range = [ range[0], range[1] ]
            mid_point = ( full_range[0] + full_range[1] ) / 2.0   
            half_width = ( full_range[1] - full_range[0] ) / 2.0 
            points.append( ( scalar_bounds[0], 0. )  )
            if (full_range[0] > zero_point): 
                points.append( ( zero_point, 0. )  )
                points.append( ( full_range[0] - self.refinement[0] * ( full_range[0] - zero_point ), self.max_opacity * self.refinement[0] ) )
            else: 
                points.append( ( full_range[0], 0.0 ) )
                points.append( ( full_range[0], 0.0 ) )
            points.append( ( mid_point - self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            points.append( ( mid_point, self.max_opacity ) )
            points.append( ( mid_point + self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            if (zero_point > full_range[1] ):  
                points.append( ( full_range[1] + self.refinement[0] * ( zero_point - full_range[1] ), self.max_opacity * self.refinement[0] ) )
                points.append( ( zero_point, 0. )  )
            else: 
                points.append( ( full_range[1], 0.0 ) )
                points.append( ( full_range[1], 0.0 ) )
            points.append( ( scalar_bounds[1], 0.) )
        return points
          
    def updateOFT( self ):
        self.transferFunctionConfig.show()
#        print " Update Volume OTF, self._range = %s, max opacity = %s " % ( str( self._range ), str( self.max_opacity ) )
        self.opacityTransferFunction.RemoveAllPoints()  
#        dthresh = self._range[3]
        if (self.TransferFunction == PosValueTransferFunction) or (self.TransferFunction == NegValueTransferFunction):
            pointType = PositiveValues if (self.TransferFunction == PosValueTransferFunction) else NegativeValues
            points = self.getTransferFunctionPoints( self._range, pointType )
            graphData = []
            for point in points:  
                self.opacityTransferFunction.AddPoint( point[0], point[1]  )  
                graphData.append( ( self.getDataValue( point[0] ) , point[1], False )  )
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], graphData )
        elif self.TransferFunction == AbsValueTransferFunction:
            graphData = []
            points = self.getTransferFunctionPoints( self._range, NegativeValues )
            for point in points:  
                self.opacityTransferFunction.AddPoint( point[0], point[1]  ) 
                graphData.append( ( self.getDataValue( point[0] ) , point[1], False )  ) 
            points = self.getTransferFunctionPoints( self._range, PositiveValues ) 
            for point in points:  
                self.opacityTransferFunction.AddPoint( point[0], point[1]  ) 
                graphData.append( ( self.getDataValue( point[0] ) , point[1], False )  )  
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], graphData )
#            print "OTF: [ %s ] " % str( points )   
        elif self.TransferFunction == FullValueTransferFunction:
            points = self.getTransferFunctionPoints( self._range, AllValues )
            graphData = []
            for point in points:  
                self.opacityTransferFunction.AddPoint( point[0], point[1]  )  
                graphData.append( ( self.getDataValue( point[0] ) , point[1], False )  )
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], graphData )             
        elif self.TransferFunction == LegacyAbsValueTransferFunction:
            if ( zero_point < self._range[0] ):
                if self._range[0] > 0: self.opacityTransferFunction.AddPoint( 0, 0.)
                self.opacityTransferFunction.AddPoint( self._range[0], 0.)
                self.opacityTransferFunction.AddPoint( self._range[1], self.max_opacity )
                if self._range[1] < self._max_scalar_value: 
                    if self.filterOutliers:
                        self.opacityTransferFunction.AddPoint( self._range[1]+0.5, 0.0)               
                        self.opacityTransferFunction.AddPoint( self._max_scalar_value, 0.0)               
                    else:
                        self.opacityTransferFunction.AddPoint( self._max_scalar_value, self.max_opacity)               
            elif( zero_point > self._range[1] ):
                if self._range[0] > 0: 
                    if self.filterOutliers:
                        self.opacityTransferFunction.AddPoint( 0, 0.0)               
                        self.opacityTransferFunction.AddPoint( self._range[0]-0.5, 0.0)               
                    else:
                        self.opacityTransferFunction.AddPoint( 0, self.max_opacity)
                self.opacityTransferFunction.AddPoint( self._range[0], self.max_opacity )
                self.opacityTransferFunction.AddPoint( self._range[1], 0. )
                if self._range[1] < self._max_scalar_value: self.opacityTransferFunction.AddPoint( self._max_scalar_value, 0.)                              
            else:
                d0 = abs(self._range[0]-zero_point)
                d1 = abs(self._range[1]-zero_point)
                t0 = max( zero_point, self._range[0] )
                t1 = min( zero_point, self._range[1] )
                if ( d0 < d1 ):
                    min_opacity = self.max_opacity * ( d0 / d1 )
                    if self._range[0] > 0: 
                        if self.filterOutliers:
                            self.opacityTransferFunction.AddPoint( 0, 0.0)               
                            self.opacityTransferFunction.AddPoint( self._range[0]-0.5, 0.0)               
                        else:
                            self.opacityTransferFunction.AddPoint( 0, min_opacity ) 
                    self.opacityTransferFunction.AddPoint( self._range[0], min_opacity )
                    self.opacityTransferFunction.AddPoint( t0, 0.) 
                    self.opacityTransferFunction.AddPoint( t1, 0.) 
                    self.opacityTransferFunction.AddPoint( self._range[1], self.max_opacity )
                    if self._range[1] < self._max_scalar_value: 
                        if self.filterOutliers:
                            self.opacityTransferFunction.AddPoint( self._range[1]+0.5, 0.0)               
                            self.opacityTransferFunction.AddPoint( self._max_scalar_value, 0.0)               
                        else:
                            self.opacityTransferFunction.AddPoint( self._max_scalar_value, self.max_opacity)               
                else:
                    min_opacity = self.max_opacity * ( d1 / d0 )
                    if self._range[0] > 0: 
                        if self.filterOutliers:
                            self.opacityTransferFunction.AddPoint( 0, 0.0)               
                            self.opacityTransferFunction.AddPoint( self._range[0]-0.5, 0.0)               
                        else:
                            self.opacityTransferFunction.AddPoint( 0, self.max_opacity ) 
                    self.opacityTransferFunction.AddPoint( self._range[0], self.max_opacity )                    
                    self.opacityTransferFunction.AddPoint( t0, 0.) 
                    self.opacityTransferFunction.AddPoint( t1, 0.) 
                    self.opacityTransferFunction.AddPoint( self._range[1], min_opacity )
                    if self._range[1] < self._max_scalar_value:
                        if self.filterOutliers:
                            self.opacityTransferFunction.AddPoint( self._range[1]+0.5, 0.0)               
                            self.opacityTransferFunction.AddPoint( self._max_scalar_value, 0.0)               
                        else:
                            self.opacityTransferFunction.AddPoint( self._max_scalar_value, min_opacity)  
        elif self.TransferFunction == LinearTransferFunction:
            if self._range[0] > 0: 
                if self.filterOutliers:
                    self.opacityTransferFunction.AddPoint( 0, 0.0)               
                    self.opacityTransferFunction.AddPoint( self._range[0]-0.5, 0.0)               
                else:
                    self.opacityTransferFunction.AddPoint( 0, 0.)
            self.opacityTransferFunction.AddPoint( self._range[0], 0.)
            self.opacityTransferFunction.AddPoint( self._range[1], self.max_opacity )
            if self._range[1] < self._max_scalar_value: 
                if self.filterOutliers:
                    self.opacityTransferFunction.AddPoint( self._range[1]+0.5, 0.0)               
                    self.opacityTransferFunction.AddPoint( self._max_scalar_value, 0.0)               
                else:
                    self.opacityTransferFunction.AddPoint( self._max_scalar_value, self.max_opacity ) 



from WorkflowModule import WorkflowModule

class VolumeRenderer(WorkflowModule):
    
    PersistentModuleClass = PM_VolumeRenderer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
                      
if __name__ == '__main__':
 
    app = QApplication(sys.argv)
    dialog = TransferFunctionConfigurationDialog( )
    dialog.addTransferFunction( 'default' ) 
    dialog.show()
    sys.exit(app.exec_())
   
 
