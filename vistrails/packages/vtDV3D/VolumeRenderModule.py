'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, math, time
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.SimplePlot import GraphWidget, NodeData 
from packages.vtDV3D.PersistentModule import *

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

def interp_zero( x0, y0, x1, y1 ):
    return y0 + (y1-y0)*(-x0/(x1-x0))

class TransferFunction( QObject ):
    
    def __init__(self, tf_type, **args ):
        self.type = tf_type
        self.data = args.get( 'data', None )
                
    def setType(self, tf_type ):
        self.type = tf_type
        
class TransferFunctionConfigurationDialog( QDialog ): 
     
    def __init__(self, parent=None, **args):
        QDialog.__init__( self, parent )
        self.setWindowTitle("Transfer Function Configuration")
        self.graph = GraphWidget( size=(400,300), nticks=(5,5) )
        self.connect( self.graph, GraphWidget.nodeMovedSignal, self.graphAdjusted )
        self.connect( self.graph, GraphWidget.moveCompletedSignal, self.doneConfig )
        self.functions = {} 
        self.setLayout(QVBoxLayout())
        self.defaultTransferFunctionType = args.get( 'default_type', AbsValueTransferFunction )
        self.tf_map = { "Signed Value" : FullValueTransferFunction, "Absolute Value" : AbsValueTransferFunction }
        self.currentTransferFunction = None
        
        tf_type_layout = QHBoxLayout()
        tf_type_label = QLabel( "Transfer Function Type:"  )
        tf_type_layout.addWidget( tf_type_label ) 

        tf_type_combo =  QComboBox ( self )
        tf_type_label.setBuddy( tf_type_combo )
        tf_type_combo.setMaximumHeight( 30 )
        tf_type_layout.addWidget( tf_type_combo )
        current_index, index = 0, 0
        for tf_name in self.tf_map.keys():
            if self.tf_map[tf_name] == self.defaultTransferFunctionType:
                current_index = index 
            tf_type_combo.addItem( tf_name )
            index = index + 1  
        tf_type_combo.setCurrentIndex( current_index )   
        self.connect( tf_type_combo, SIGNAL("currentIndexChanged(QString)"), self.updateTransferFunctionType )  
        self.layout().addLayout( tf_type_layout )
                
        self.closeButton = QPushButton('Ok', self)
        self.layout().addWidget( self.graph )         
        self.layout().addWidget(self.closeButton)
        self.connect(self.closeButton, SIGNAL('clicked(bool)'), self.close)
        self.closeButton.setShortcut('Enter')
        
    def closeEvent( self, closeEvent ):
        self.emit( SIGNAL('close()') )
        QDialog.closeEvent( self, closeEvent )  
        
    def doneConfig( self ):
        self.emit( SIGNAL('doneConfig()') )    
        
    def addTransferFunction( self, name, **args ):
        self.currentTransferFunction = TransferFunction( self.defaultTransferFunctionType, **args ) 
        self.functions[ name ]  = self.currentTransferFunction
        self.graph.buildGraph() 
        
    def initLeveling(self, range ):
        pass
    
    def graphAdjusted(self, index, value0, value1, value2 ):
        self.emit( SIGNAL('config(int,float,float,float)'), index, value0, value1, value2 )
    
    def updateGraph( self, xbounds, ybounds, data ):
        self.graph.createGraph( xbounds, ybounds, data )
                
    def updateTransferFunctionType( self, value ):
        if self.currentTransferFunction: self.currentTransferFunction.setType( self.tf_map[ str(value) ] )
        self.emit( SIGNAL('update') )
        
    def setTransferFunctionType( self, tf_type ):
        if self.currentTransferFunction:
            if tf_type in self.tf_map.values(): 
                self.currentTransferFunction.type = tf_type

    def getTransferFunctionType( self ):
        if self.currentTransferFunction: return self.currentTransferFunction.type
        return self.defaultTransferFunctionType
        
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

    NI_RANGE_POSITION = 10001
    NI_RANGE_WIDTH = 10002
    NI_SHAPE_ADJ_0 = 10003
    NI_SHAPE_ADJ_1 = 10004
    
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.max_opacity = 1.0
        self.vthresh = None
        self.filterOutliers = False
        self.refinement = [ 0.0, 0.5 ]
        self.imageRange = None
        self.otf_data = None
        self.ctf_data = None
        self.updatingOTF = False
        self.configTime = None
        self.transFunctGraphVisible = False
        self.transferFunctionConfig = None
        self.setupTransferFunctionConfigDialog()
        self.addConfigurableLevelingFunction( 'colorScale',    'C', label='Colormap Scale', setLevel=self.generateCTF, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRange=True, units=self.units )
        self.addConfigurableLevelingFunction( 'functionScale', 'T', label='Transfer Function Scale', setLevel=self.generateOTF, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRange=True, units=self.units, initRange=[ 0.0, 1.0, 1, self.refinement[0], self.refinement[1] ], gui=self.transferFunctionConfig  )
        self.addConfigurableLevelingFunction( 'opacityScale',  'O', label='Opacity', setLevel=self.adjustOpacity, layerDependent=True, adjustRange=True  )
        self.addConfigurableMethod( 'showTransFunctGraph', self.showTransFunctGraph, 'g', label='Transfer Function Graph' )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, getLevel=self.getScaleBounds )
    
#    def setZScale( self, zscale_data ):
#        if self.volume <> None:
#            sz = ( zscale_data[0] + zscale_data[1] ) / 0.5
#            self.volume.SetScale( 1.0, 1.0, sz )
#            self.volume.Modified()
#            print " VR >---------------> Set zscale: %.2f, scale: %s, spacing: %s " % ( sz, str(self.volume.GetScale()), str(self.input.GetSpacing()) )

    def getZScale( self ):
        if self.volume <> None:
            spacing = self.volume.GetScale()
            sx, sy, sz = spacing    
            return [ 1.0, sz, 1 ]

    def setupTransferFunctionConfigDialog( self ):
        if self.transferFunctionConfig == None:
            self.transferFunctionConfig = TransferFunctionConfigurationDialog()
            self.transferFunctionConfig.addTransferFunction( 'default' )
            self.connect(self.transferFunctionConfig, SIGNAL('close()'), self.clearTransferFunctionConfigDialog )
            self.connect(self.transferFunctionConfig, SIGNAL('config(int,float,float,float)'), self.configTransferFunction )
            self.connect(self.transferFunctionConfig, SIGNAL('doneConfig()'), self.persistTransferFunctionConfig )  
            self.connect(self.transferFunctionConfig, SIGNAL('update'), self.updateOTF )                      
        self.transferFunctionConfig.setVisible( self.transFunctGraphVisible )
        if self.transFunctGraphVisible: self.transferFunctionConfig.show()
    
    def configTransferFunction(self, nodeIndex, value0, value1, value2 ):
        if nodeIndex == self.NI_RANGE_POSITION:                   
            self.max_opacity = value1
            range_size = ( self.rangeBounds[1] - self.rangeBounds[0])  
            new_peak = bound( self.getImageValue( value0 ), [ self.rangeBounds[0] + 0.01*range_size, self.rangeBounds[0] + 0.99*range_size ] )
            w = ( self._range[1] - self._range[0]  ) / 2.0
            self._range[0] = new_peak - w
            self._range[1] = new_peak + w
            if self._range[0] < self.rangeBounds[0]:
                self._range[0] = self.rangeBounds[0]
                if 2.0*new_peak < range_size: 
                    self._range[1] = self.rangeBounds[0] + 2.0*new_peak
                else: 
                    self._range[1] = self.rangeBounds[1]
            if self._range[1] > self.rangeBounds[1]:
                self._range[1] = self.rangeBounds[1]              
                self._range[0] = self.rangeBounds[1] - 2.0*( self.rangeBounds[1] - new_peak )
                if self._range[0] < self.rangeBounds[0]:  self._range[0] = self.rangeBounds[0]
#            print " config RANGE_POSITION: ", nodeIndex, self.max_opacity, new_peak, str( self._range ) 
        elif nodeIndex == self.NI_RANGE_WIDTH:
            self._range[1] = self.getImageValue( value0 )
            if self._range[1] > self.rangeBounds[1]: self._range[1] = self.rangeBounds[1] 
#            print " config RANGE_WIDTH: ", nodeIndex, value0, self._range[1] 
        elif nodeIndex == self.NI_SHAPE_ADJ_0:
            self.refinement[0] = value2
#            print " config SHAPE_ADJ_0: ", nodeIndex, value2
        elif nodeIndex == self.NI_SHAPE_ADJ_1:
            self.refinement[1] = value2
#            print " config SHAPE_ADJ_1: ", nodeIndex, value2
        else: return
        
        self.updateOTF()
        self.render()

    def getDataRangeBounds(self): 
        range = PersistentVisualizationModule.getDataRangeBounds(self)
        if self.transferFunctionConfig:
            range[2] = self.transferFunctionConfig.getTransferFunctionType()
        return range
                
    def persistTransferFunctionConfig( self ):
        parmList = []
        cfs = []
        configFunct = self.configurableFunctions[ 'opacityScale' ]
        opacity_value = [ 0.0, self.max_opacity ] 
        parmList.append( ('opacityScale', opacity_value ) )
        cfs.append( configFunct )

        configFunct = self.configurableFunctions[ 'functionScale' ]
        new_values = self.getDataValues( self._range[0:2] )
        range_values = configFunct.range
        print "Update Range Values:  %s -> %s, max_opacity = %.2f " % ( str( range_values ), str( new_values ), self.max_opacity )
        for i in range( 2 ): range_values[i] = new_values[i]
        for i in range( 2 ): range_values[i+3] = self.refinement[i]
        range_values[2] = self.transferFunctionConfig.getTransferFunctionType()
        parmList.append( ('functionScale', range_values ) )
        cfs.append( configFunct )
        
        self.persistParameterList( parmList )
#        for configFunct in cfs: configFunct.initLeveling()
        
    def clearTransferFunctionConfigDialog(self):
        self.transFunctGraphVisible = False

    def showTransFunctGraph( self ): 
        self.transFunctGraphVisible = True
        self.updateOTF()
                 
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
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )

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
#        print " *** volume visible: %s " % ( self.volume.GetVisibility() )
        aCamera = self.renderer.GetActiveCamera()
        bounds = self.volume.GetBounds()
        p = aCamera.GetPosition()
        f = aCamera.GetFocalPoint()
#        printArgs( "ResetCameraClippingRange", focal_point=f, cam_pos=p, vol_bounds=bounds )
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
            
    def printOTF( self ):
        nPts = 20
        tf_range = self.opacityTransferFunction.GetRange()
        dr = ( tf_range[1] - tf_range[0] ) / nPts
        sValues = [ "%.2f" % self.opacityTransferFunction.GetValue( tf_range[0] + iP * dr ) for iP in range( nPts ) ] 
        print "OTF values: ", ' '.join(sValues)
        
    def rebuildColorTransferFunction( self ):
        if self.imageRange <> None:
            self.colorTransferFunction.RemoveAllPoints ()
            nc = self.lut.GetNumberOfTableValues()
            dr = (self.imageRange[1] - self.imageRange[0]) 
#000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000            print "Generate CTF: range = %s, invert = %s" % ( str( self.imageRange ), str(self.invert) )
            
            for i in range(nc):
                interval_position = float(i)/nc
                data_value = self.imageRange[0] + dr * interval_position
#                lut_index = (nc-i-1) if self.invert else i
                color = self.lut.GetTableValue( i )
                self.colorTransferFunction.AddRGBPoint( data_value, color[0], color[1], color[2] )
#                if i % 50 == 0:  print "   --- ctf[%d:%d:%d] --  %.2e: ( %.2f %.2f %.2f ) " % ( i, lut_index, self.invert, data_value, color[0], color[1], color[2] )
            
          
    def PrintStats(self):
        print_docs( self.volume.mapper )
        self.print_traits()
        print "Volume: bounds=%s, scale=%s, mapper=%s" % ( str(self.volume.bounds), str(self.volume.scale), str(self.volume_mapper_type) )

    def adjustOpacity( self, opacity_data ):
        maxop = abs( opacity_data[1] ) 
        self.max_opacity = maxop if maxop < 1.0 else 1.0
        range_min, range_max = self.rangeBounds[0], self.rangeBounds[1]
#        self.vthresh = opacity_data[0]*(self.seriesScalarRange[1]-self.seriesScalarRange[0])*0.02
        self.updateOTF()
#        printArgs( "adjustOpacity", irange=self._range,  max_opacity=self.max_opacity, opacity_data=opacity_data, vthresh=vthresh, ithresh=self._range[3] )   

    def generateOTF( self, otf_data=None ): 
        if otf_data: self.otf_data = otf_data
        else: otf_data = self.otf_data
        if otf_data:
            if self.transferFunctionConfig:
                self.transferFunctionConfig.setTransferFunctionType( otf_data[2] )
            self._range = self.getImageValues( ( otf_data[0], otf_data[1], 0.0 ) )
            if len( otf_data ) > 3: self.refinement = [ otf_data[3], otf_data[4] ]
            self.updateOTF()
#        printArgs( "generateOTF", irange=self._range,  otf_data=otf_data )   
           
    def  getTransferFunctionPoints( self, image_value_range, pointType ):
        zero_point = image_value_range[2] 
        scalar_bounds = [ 0, self._max_scalar_value ]
        points = []
#        print "Generate OTF: image_value_range = ( %f %f ), zero_point = %f, refinement = ( %f %f ), max_opacity = %s" % ( image_value_range[0], image_value_range[1], zero_point, self.refinement[0], self.refinement[1], self.max_opacity )             
        if pointType == PositiveValues:
            full_range = [ image_value_range[i] if image_value_range[i] >= zero_point else zero_point for i in range(2) ]
            mid_point = ( full_range[0] + full_range[1] ) / 2.0   
            half_width = ( full_range[1] - full_range[0] ) / 2.0 
            eps = (image_value_range[1]-image_value_range[0]) * .001
            self.getNewNode( points, ( zero_point, 0. ) )
            self.getNewNode( points, ( full_range[0]-eps, 0.0 ), ( zero_point+eps, self.max_opacity), self.refinement[0], color=NodeData.CYAN, index=self.NI_SHAPE_ADJ_0 )
            self.getNewNode( points, ( mid_point-eps, 0.0 ), (mid_point-half_width+eps, self.max_opacity ), self.refinement[1], color=NodeData.CYAN, index=self.NI_SHAPE_ADJ_1 )  
            self.getNewNode( points, ( mid_point, self.max_opacity ), free=True, index=self.NI_RANGE_POSITION ) 
            self.getNewNode( points, ( mid_point + self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            self.getNewNode( points, ( zero_point, 0.0 ), ( scalar_bounds[1], 0.0 ), (full_range[1]-zero_point)/(scalar_bounds[1]-zero_point), index=self.NI_RANGE_WIDTH )
            self.getNewNode( points, ( scalar_bounds[1], 0.0 ) )
        elif pointType == NegativeValues:
            eps = (image_value_range[1]-image_value_range[0]) * .001
            data_range = self.getDataValues( image_value_range )
            data_range = [ data_range[i] if data_range[i] >= 0.0 else 0.0 for i in range(2) ]
            full_range = self.getImageValues( [ -data_range[0], -data_range[1] ] )
#            full_range = [ full_range[i] if full_range[i] >= 0.0 else 0.0 for i in range(2) ]
            mid_point = ( full_range[0] + full_range[1] ) / 2.0   
            half_width = ( full_range[0] - full_range[1] ) / 2.0 
            peak_handles = [ mid_point - self.refinement[1]*half_width+eps, mid_point + self.refinement[1]*half_width-eps  ]
            ph_opacity = self.max_opacity * self.refinement[1]
            adjustment_point = full_range[0] + self.refinement[0] * ( zero_point - full_range[0] )
#            if full_range[1] > scalar_bounds[0]: self.getNewNode( points, (scalar_bounds[0], 0. ) )
#            if full_range[1] >= 0: self.getNewNode( points, ( full_range[1], 0.0 ) )
#            elif peak_handles[0] > 0: self.getNewNode( points, ( 0.0, interp_zero( full_range[1], 0.0, peak_handles[0], ph_opacity ) ) )
#            if peak_handles[0] >= 0: self.getNewNode( points, ( peak_handles[0], ph_opacity ) )            
#            elif mid_point > 0: self.getNewNode( points, ( 0.0, interp_zero( peak_handles[0], ph_opacity, mid_point, self.max_opacity ) ) )
#            if mid_point >= 0: self.getNewNode( points, ( mid_point, self.max_opacity ) ) 
#            elif peak_handles[1] > 0: self.getNewNode( points, ( 0.0, interp_zero( mid_point, self.max_opacity, peak_handles[1], ph_opacity ) ) )
#            if peak_handles[1] >= 0: self.getNewNode( points, ( peak_handles[1], ph_opacity ) )  
#            elif adjustment_point > 0: self.getNewNode( points, ( 0.0, interp_zero( peak_handles[1], ph_opacity, adjustment_point, self.refinement[0]*self.max_opacity ) ) )
#            if adjustment_point > 0: self.getNewNode( points, ( adjustment_point, self.refinement[0]*self.max_opacity )  )           
#            else: self.getNewNode( points, ( 0.0, interp_zero( adjustment_point, self.refinement[0]*self.max_opacity, zero_point, 0. ) ) )
            if full_range[1] > scalar_bounds[0]: self.getNewNode( points, (scalar_bounds[0], 0. ) )
            if peak_handles[0] > 0: self.getNewNode( points, ( full_range[1], 0.0 ) )
            if mid_point > 0: self.getNewNode( points, ( peak_handles[0], ph_opacity ) )            
            if peak_handles[1] > 0: self.getNewNode( points, ( mid_point, self.max_opacity ) ) 
            if adjustment_point > 0: self.getNewNode( points, ( peak_handles[1], ph_opacity ) )  
            if zero_point > 0: self.getNewNode( points, ( adjustment_point, self.refinement[0]*self.max_opacity )  )           
            self.getNewNode( points, ( zero_point, 0. ) )
        elif pointType == AllValues:
            full_range = [ image_value_range[0], image_value_range[1] ]
            mid_point = ( full_range[0] + full_range[1] ) / 2.0   
            half_width = ( full_range[1] - full_range[0] ) / 2.0 
            eps = (image_value_range[1]-image_value_range[0]) * .001
            self.getNewNode( points, (scalar_bounds[0], 0. ) )
            if ( full_range[0] > zero_point ): 
                self.getNewNode( points, ( zero_point, 0. ) )
                self.getNewNode( points, ( full_range[0]-eps, 0.0 ), ( zero_point+eps, self.max_opacity), self.refinement[0], color=NodeData.CYAN, index=self.NI_SHAPE_ADJ_0 )
#                points.append( ( full_range[0] - self.refinement[0] * ( full_range[0] - zero_point ), self.max_opacity * self.refinement[0] ) )
            else: 
                self.getNewNode( points, ( full_range[0], 0.0 ) )
                self.getNewNode( points, ( zero_point, 0.0 ) )
#            points.append( ( mid_point - self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) ) 
            self.getNewNode( points, ( mid_point-eps, 0.0 ), (mid_point-half_width+eps, self.max_opacity ), self.refinement[1], color=NodeData.CYAN, index=self.NI_SHAPE_ADJ_1 )  
            self.getNewNode( points, ( mid_point, self.max_opacity ), free=True, index=self.NI_RANGE_POSITION ) 
            self.getNewNode( points, ( mid_point + self.refinement[1]*half_width, self.max_opacity * self.refinement[1] ) )            
            if (zero_point > full_range[1] ):  
                self.getNewNode( points, ( full_range[1]+self.refinement[0]*(zero_point-full_range[1]), self.max_opacity*self.refinement[0] ) )
                self.getNewNode( points, ( zero_point, 0. ) )
            else: 
                self.getNewNode( points, ( zero_point, 0.0 ), ( scalar_bounds[1], 0.0 ), (full_range[1]-zero_point)/(scalar_bounds[1]-zero_point), index=self.NI_RANGE_WIDTH )
                self.getNewNode( points, ( scalar_bounds[1], 0.0 ) )
            self.getNewNode( points, ( scalar_bounds[1], 0.) )
        return points
            
    def getNewNode( self, nodeList, rootImagePoint, endImagePoint = None, s=None, **args ):
        n = NodeData( ix0=rootImagePoint[0], y0=rootImagePoint[1], **args )
        n.dx0 = self.getDataValue( rootImagePoint[0] )
        if endImagePoint:
            n.setImageVectorData( endImagePoint, s )
            n.dx1 = self.getDataValue( endImagePoint[0] )
        nodeList.append( n )
        return n
          
    def updateOTF( self  ):
        if self.updatingOTF: return   # Avoid infinite recursion
        self.updatingOTF = True
        self.setupTransferFunctionConfigDialog()
#        print " Update Volume OTF, self._range = %s, max opacity = %s " % ( str( self._range ), str( self.max_opacity ) )
        self.opacityTransferFunction.RemoveAllPoints()  
        transferFunctionType = self.transferFunctionConfig.getTransferFunctionType()
#        dthresh = self._range[3]
        if (transferFunctionType == PosValueTransferFunction) or (transferFunctionType == NegValueTransferFunction):
            pointType = PositiveValues if (self.TransferFunction == PosValueTransferFunction) else NegativeValues
            nodeDataList = self.getTransferFunctionPoints( self._range, pointType )
            for nodeData in nodeDataList: 
                pos = nodeData.getImagePosition()
                self.opacityTransferFunction.AddPoint( pos[0], pos[1] ) 
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], nodeDataList )       
        elif transferFunctionType == AbsValueTransferFunction:
            graphData = []
            nodeDataList = self.getTransferFunctionPoints( self._range, NegativeValues )
#            points = []
            for nodeData in nodeDataList:  
                pos = nodeData.getImagePosition()
                self.opacityTransferFunction.AddPoint( pos[0], pos[1] ) 
                graphData.append( nodeData  ) 
            nodeDataList = self.getTransferFunctionPoints( self._range, PositiveValues ) 
            for nodeData in nodeDataList:    
                pos = nodeData.getImagePosition()
                self.opacityTransferFunction.AddPoint( pos[0], pos[1] ) 
                graphData.append( nodeData  )  
#                points.append( str( nodeData.getDataPosition() ) )
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], graphData )
#            print "OTF: [ %s ] " % " ".join( points ) 
        elif transferFunctionType == FullValueTransferFunction:
            nodeDataList = self.getTransferFunctionPoints( self._range, AllValues )
            for nodeData in nodeDataList: 
                pos = nodeData.getImagePosition()
                self.opacityTransferFunction.AddPoint( pos[0], pos[1] ) 
            if self.otf_data: self.transferFunctionConfig.updateGraph( self.scalarRange, [ 0.0, 1.0 ], nodeDataList ) 
        self.updatingOTF = False
        
from packages.vtDV3D.WorkflowModule import WorkflowModule

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
   
 
