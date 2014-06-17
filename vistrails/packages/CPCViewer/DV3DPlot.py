'''
Created on Apr 23, 2014

@author: tpmaxwell
'''
from __future__ import with_statement
from __future__ import division

_TRY_PYSIDE = True

try:
    if not _TRY_PYSIDE:
        raise ImportError()
    import PySide.QtCore as _QtCore
    QtCore = _QtCore
    import PySide.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = True
except ImportError:
    import sip
    try: sip.setapi('QString', 2)
    except: pass
    try: sip.setapi('QVariant', 2)
    except: pass
    import PyQt4.QtCore as _QtCore
    QtCore = _QtCore
    import PyQt4.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = False
    
import vtk, sys, os
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
MIN_LINE_LEN = 50
VTK_NOTATION_SIZE = 14
from packages.CPCViewer.ColorMapManager import *
from packages.CPCViewer.StructuredGridConfiguration import *
from packages.CPCViewer.StructuredVariableReader import StructuredDataReader

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

    def resizeEvent( self, event ):
        self.emit( QtCore.SIGNAL('event'), ( 'ResizeEvent', 0 ) )
        QVTKRenderWindowInteractor.resizeEvent( self, event )
 
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
       
class DV3DPlot(QtCore.QObject):  
    
    NoModifier = 0
    ShiftModifier = 1
    CtrlModifier = 2
    AltModifier = 3
    
    LEFT_BUTTON = 0
    RIGHT_BUTTON = 1


    def __init__( self,  **args ):
        QtCore.QObject.__init__( self )
        self.useGui = args.get( 'gui', True )
        self.xcenter = 100.0
        self.xwidth = 300.0
        self.ycenter = 0.0
        self.ywidth = 180.0
        self.iOrientation = 0

        self.widget = None
        self.textDisplayMgr = None
        self.enableClip = False
        self.variables = {}
        self.metadata = {}

        self.isValid = True
        self.cameraOrientation = {}
        self.labelBuff = ""
        self.configDialog = None
        self.colormapManagers= {}
        self.stereoEnabled = 0
        self.maxStageHeight = 100.0
        self.observerTargets = set()

        self.renderWindow = args.get( 'renwin', self.createRenderWindow() )
        self.renderWindowInteractor = self.renderWindow.GetInteractor()
        style = args.get( 'istyle', vtk.vtkInteractorStyleTrackballCamera() )  
        self.renderWindowInteractor.SetInteractorStyle( style )
        
        self.configuring = False
        self.configurableFunctions = {}
        self.configurationInteractorStyle = vtk.vtkInteractorStyleUser()
        self.navigationInteractorStyle = None
        self.activated = False

        self.pipelineBuilt = False
        self.baseMapActor = None
        self.enableBasemap = True
        self.map_opacity = [ 0.4, 0.4 ]
        self.roi = None
        self.isAltMode = False
        self.createColormap = True
        self.inputSpecs = {}
        self.InteractionState = None
        self.LastInteractionState = None

    def getRangeBounds( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getRangeBounds()  

    def setRangeBounds( self, rbounds, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        ispec.rangeBounds[:] = rbounds[:] 

    def setMaxScalarValue(self, iDType ):  
        if iDType   == vtk.VTK_UNSIGNED_CHAR:   self._max_scalar_value = 255
        elif iDType == vtk.VTK_UNSIGNED_SHORT:  self._max_scalar_value = 256*256-1
        elif iDType == vtk.VTK_SHORT:           self._max_scalar_value = 256*128-1
        else:                                   self._max_scalar_value = self.getRangeBounds()[1]  

    def decimateImage( self, image, decx, decy ):
        image.Update()
        dims = image.GetDimensions()
        image_size = dims[0] * dims[1]
        result = image
        if image_size > MAX_IMAGE_SIZE:
            resample = vtk.vtkImageShrink3D()
            resample.SetInput( image )
            resample.SetShrinkFactors( decx, decy, 1 )
            result = resample.GetOutput() 
            result.Update()
        return result

    def getScaleBounds(self):
        return [ 0.5, 100.0 ]

    def setInputZScale( self, zscale_data, input_index=0, **args  ):
        ispec = self.inputSpecs[ input_index ] 
        if ispec.input() <> None:
            input = ispec.input()
            ns = input.GetNumberOfScalarComponents()
            spacing = input.GetSpacing()
            ix, iy, iz = spacing
            sz = zscale_data[1]
            if iz <> sz:
#                print " PVM >---------------> Change input zscale: %.4f -> %.4f" % ( iz, sz )
                input.SetSpacing( ix, iy, sz )  
                input.Modified() 
                self.processScaleChange( spacing, ( ix, iy, sz ) )
                return True
        return False
    
    def getDataRangeBounds(self, inputIndex=0 ):
        ispec = self.getInputSpec( inputIndex )
        return ispec.getDataRangeBounds() if ispec else None

    def onSlicerLeftButtonPress( self, caller, event ):
        self.currentButton = self.LEFT_BUTTON   
        return 0

    def onSlicerRightButtonPress( self, caller, event ):
        self.currentButton = self.RIGHT_BUTTON
        return 0
        
    def getAxes(self):
        pass

    def input( self, iIndex = 0 ):
        return self.variable_reader.output( iIndex )

    def isBuilt(self):
        return self.pipelineBuilt
    
    def initializeInputs( self, **args ):
        nOutputs = self.variable_reader.nOutputs()
        for inputIndex in range( nOutputs ):
            ispec = self.variable_reader.outputSpec( inputIndex )
            self.inputSpecs[inputIndex] = ispec 
            if self.roi == None:  
                self.roi = ispec.metadata.get( 'bounds', None )  
            self.intiTime( ispec, **args )
        self.initMetadata()
        
        
    def initMetadata(self):
        spec = self.inputSpecs[0]
        attributes = spec.metadata.get( 'attributes' , None )
        if attributes:
            self.metadata['var_name'] = attributes[ 'long_name']
            self.metadata['var_units'] = attributes[ 'units']

    def intiTime(self, ispec, **args):
        t = cdtime.reltime( 0, self.variable_reader.referenceTimeUnits )
        if t.cmp( cdtime.reltime( 0, ispec.referenceTimeUnits ) ) == 1:
            self.variable_reader.referenceTimeUnits = ispec.referenceTimeUnits 
        tval = args.get( 'timeValue', None )
        if tval: self.timeValue = cdtime.reltime( float( args[ 'timeValue' ] ), ispec.referenceTimeUnits )

    def execute(self, **args ):
        initConfig = False
        isAnimation = args.get( 'animate', False )
        if not self.isBuilt(): 
            self.initializeInputs()        
            self.buildPipeline()
            self.buildBaseMap()
            self.pipelineBuilt = True
            initConfig = True
            
        if not initConfig: self.applyConfiguration( **args  )   
        
        self.updateModule( **args ) 
        
        if not isAnimation:
# #            self.displayInstructions( "Shift-right-click for config menu" )
            if initConfig: 
                self.initializeConfiguration( mid=id(self) )  
            else:   
                self.applyConfiguration()

    def updateModule( self, input_index = 0, **args  ):
        ispec = self.inputSpecs[ input_index ] 
        mapper = self.volume.GetMapper()
        mapper.SetInput( ispec.input() )
        mapper.Modified()

    def terminate( self ):
        pass
    
    def getScalarRange( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.scalarRange  

    def addConfigurableFunction(self, name, function_args, key, **args):
        self.configurableFunctions[name] = ConfigurableFunction( name, function_args, key, **args )

    def addConfigurableLevelingFunction(self, name, key, **args):
        self.configurableFunctions[name] = WindowLevelingConfigurableFunction( name, key, **args )

    def getConfigFunction( self, name ):
        return self.configurableFunctions.get(name,None)

    def removeConfigurableFunction(self, name ):        
        del self.configurableFunctions[name]

    def applyConfiguration(self, **args ):       
        for configFunct in self.configurableFunctions.values():
            configFunct.applyParameter( **args  )

    def setBasemapLineSpecs( self, shapefile_type, value ):
        self.basemapLineSpecs[shapefile_type] = value
        npixels = int( round( value[0] ) )
        density = int( round( value[1] ) )
        polys_list = self.shapefilePolylineActors.get( shapefile_type, [ None, None, None, None, None ] ) 
        try:
            selected_polys = polys_list[ density ]
            if not selected_polys:
                if npixels: 
                    self.createBasemapPolyline( shapefile_type )
            else:
                for polys in polys_list:
                    if polys:
                        polys.SetVisibility( npixels and ( id(polys) == id(selected_polys) ) )
                selected_polys.GetProperty().SetLineWidth( npixels )           
            self.render()
        except IndexError:
            print>>sys.stderr, " setBasemapLineSpecs: Density too large: %d " % density

    def setBasemapCoastlineLineSpecs( self, value, **args ):
        self.setBasemapLineSpecs('coastline', value )

    def setBasemapStatesLineSpecs( self, value, **args ):
        self.setBasemapLineSpecs('states', value )

    def setBasemapLakesLineSpecs( self, value, **args ):
        self.setBasemapLineSpecs('lakes', value )
        
    def setBasemapCountriesLineSpecs( self, value, **args ):
        self.setBasemapLineSpecs('countries', value )

    def getBasemapLineSpecs( self, shapefile_type ):
        return self.basemapLineSpecs.get( shapefile_type, None )
        
    def getBasemapCoastlineLineSpecs( self, **args ):
        return self.getBasemapLineSpecs('coastline' )
        
    def getBasemapStatesLineSpecs( self, **args ):
        return self.getBasemapLineSpecs('states' )

    def getBasemapLakesLineSpecs( self, **args ):
        return self.getBasemapLineSpecs('lakes' )

    def getBasemapCountriesLineSpecs( self, **args ):
        return self.getBasemapLineSpecs('countries' )

    def setInteractionState(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        shift = caller.GetShiftKey()
#        print " setInteractionState -- Key Press: %c ( %d: %s ), event = %s " % ( key, ord(key), str(keysym), str( event ) )
        alt = ( keysym <> None) and keysym.startswith("Alt")
        if alt:
            self.isAltMode = True
        else: 
            print " ------------------------------------------ setInteractionState, key=%s, keysym=%s, shift = %s, isAltMode = %s    ------------------------------------------ " % (str(key), str(keysym), str(shift), str(self.isAltMode) )
            self.processKeyEvent( key, caller, event )

    def processKeyEvent( self, key, caller=None, event=None ):
#        print "process Key Event, key = %s" % ( key )
        md = self.getInputSpec().getMetadata()
        if ( self.createColormap and ( key == 'l' ) ): 
            self.toggleColormapVisibility()                       
            self.render() 
        elif (  key == 'r'  ):
            self.resetCamera()              
        elif ( md and ( md.get('plotType','')=='xyz' ) and ( key == 't' )  ):
            self.showInteractiveLens = not self.showInteractiveLens 
            self.render() 
        else:
            ( state, persisted ) =  self.getInteractionState( key )
#            print " %s Set Interaction State: %s ( currently %s) " % ( str(self.__class__), state, self.InteractionState )
            if state <> None: 
                self.updateInteractionState( state, self.isAltMode  )                 
                self.isAltMode = False 

    def onLeftButtonPress( self, caller, event ):
        istyle = self.renderWindowInteractor.GetInteractorStyle()
#        print "(%s)-LBP: s = %s, nis = %s " % ( getClassName( self ), getClassName(istyle), getClassName(self.navigationInteractorStyle) )
        if not self.finalizeLeveling(): 
            shift = caller.GetShiftKey()
            self.currentButton = self.LEFT_BUTTON
 #           self.clearInstructions()
            self.UpdateCamera()   
            x, y = caller.GetEventPosition()      
            self.startConfiguration( x, y, [ 'leveling', 'generic' ] )  
        return 0

    def onRightButtonPress( self, caller, event ):
        shift = caller.GetShiftKey()
        self.currentButton = self.RIGHT_BUTTON
 #       self.clearInstructions()
        self.UpdateCamera()
        x, y = caller.GetEventPosition()
        if self.InteractionState <> None:
            self.startConfiguration( x, y,  [ 'generic' ] )
        return 0

    def onLeftButtonRelease( self, caller, event ):
        self.currentButton = None 
    
    def onRightButtonRelease( self, caller, event ):
        self.currentButton = None 

    def startConfiguration( self, x, y, config_types ): 
        if (self.InteractionState <> None) and not self.configuring:
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if configFunct.type in config_types:
                self.configuring = True
                configFunct.start( self.InteractionState, x, y )
                self.haltNavigationInteraction()
#                if (configFunct.type == 'leveling'): self.getLabelActor().VisibilityOn()

    def updateLevelingEvent( self, caller, event ):
        x, y = caller.GetEventPosition()
        wsize = caller.GetRenderWindow().GetSize()
        self.updateLeveling( x, y, wsize )
                
    def updateLeveling( self, x, y, wsize, **args ):  
        if self.configuring:
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if configFunct.type == 'leveling':
                configData = configFunct.update( self.InteractionState, x, y, wsize )
                if configData <> None:
                    self.setParameter( configFunct.name, configData ) 
                    textDisplay = configFunct.getTextDisplay()
                    if textDisplay <> None:  self.updateTextDisplay( textDisplay )
                    self.render()

    def UpdateCamera(self):
        pass
    
    def setParameter( self, name, value ):
        pass

    def haltNavigationInteraction(self):
        if self.renderWindowInteractor:
            istyle = self.renderWindowInteractor.GetInteractorStyle()  
            if self.navigationInteractorStyle == None:
                self.navigationInteractorStyle = istyle    
            self.renderWindowInteractor.SetInteractorStyle( self.configurationInteractorStyle )  
#            print "\n ---------------------- [%s] halt Navigation: nis = %s, is = %s  ----------------------  \n" % ( getClassName(self), getClassName(self.navigationInteractorStyle), getClassName(istyle)  ) 
    
    def resetNavigation(self):
        if self.renderWindowInteractor:
            if self.navigationInteractorStyle <> None: 
                self.renderWindowInteractor.SetInteractorStyle( self.navigationInteractorStyle )
            istyle = self.renderWindowInteractor.GetInteractorStyle()  
#            print "\n ---------------------- [%s] reset Navigation: nis = %s, is = %s  ---------------------- \n" % ( getClassName(self), getClassName(self.navigationInteractorStyle), getClassName(istyle) )        
            self.enableVisualizationInteraction()

    def getInteractionState( self, key ):
        for configFunct in self.configurableFunctions.values():
            if configFunct.matches( key ): return ( configFunct.name, configFunct.persisted )
        return ( None, None )    

    def updateInteractionState( self, state, altMode ): 
        rcf = None
        if state == None: 
            self.finalizeLeveling()
            self.endInteraction()   
        else:            
            if self.InteractionState <> None: 
                configFunct = self.configurableFunctions[ self.InteractionState ]
                configFunct.close()   
            configFunct = self.configurableFunctions.get( state, None )
            if configFunct and ( configFunct.type <> 'generic' ): 
                rcf = configFunct
#                print " UpdateInteractionState, state = %s, cf = %s " % ( state, str(configFunct) )
            if not configFunct and self.acceptsGenericConfigs:
                configFunct = ConfigurableFunction( state, None, None )              
                self.configurableFunctions[ state ] = configFunct
            if configFunct:
                configFunct.open( state, self.isAltMode )
                self.InteractionState = state                   
                self.LastInteractionState = self.InteractionState
                self.disableVisualizationInteraction()
            elif state == 'colorbar':
                self.toggleColormapVisibility()                        
            elif state == 'reset':
                self.resetCamera()              
                if  len(self.persistedParameters):
                    pname = self.persistedParameters.pop()
                    configFunct = self.configurableFunctions[pname]
                    param_value = configFunct.reset() 
                    if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True, list=False )                                      
        return rcf

    def getInputSpec( self, input_index=0 ):
        return self.inputSpecs.get( input_index, None )

    def getDataValue( self, image_value, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getDataValue( image_value )

    def getTimeAxis(self):
        ispec = self.getInputSpec()     
        timeAxis = ispec.getMetadata('time') if ispec else None
        return timeAxis
                    
    def getDataValues( self, image_value_list, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getDataValues( image_value_list )  
        
    def getImageValue( self, data_value, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getImageValue( data_value )  
    
    def getImageValues( self, data_value_list, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getImageValues( data_value_list )  

    def scaleToImage( self, data_value, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.scaleToImage( data_value )  

    def finalizeLeveling( self, cmap_index=0 ):
        ispec = self.inputSpecs.get( cmap_index, None )
        if ispec:
            ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
            if self.configuring: 
                self.finalizeConfigurationObserver( self.InteractionState )            
                self.resetNavigation()
                self.configuring = False
                self.InteractionState = None
                return True
        return False
#            self.updateSliceOutput()

    def finalizeConfigurationObserver( self, parameter_name, **args ):
        self.finalizeParameter( parameter_name, **args )    
#        for parameter_name in self.getModuleParameters(): self.finalizeParameter( parameter_name, *args ) 
        self.endInteraction( **args ) 

    def finalizeParameter(self, parameter_name, **args ):
        pass
    
    def endInteraction( self, **args ):  
        self.resetNavigation() 
        self.configuring = False
        self.InteractionState = None
        self.enableVisualizationInteraction()

    def initializeConfiguration( self, cmap_index=0, **args ):
        ispec = self.inputSpecs[ cmap_index ] 
        for configFunct in self.configurableFunctions.values():
            configFunct.init( ispec, **args )
        ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
#        self.updateSliceOutput()

    def getColormapSpec(self, cmap_index=0): 
        colormapManager = self.getColormapManager( index=cmap_index )
        spec = []
        spec.append( colormapManager.colormapName )
        spec.append( str( colormapManager.invertColormap ) )
        value_range = colormapManager.lut.GetTableRange() 
        spec.append( str( value_range[0] ) )
        spec.append( str( value_range[1] ) ) 
#        print " %s -- getColormapSpec: %s " % ( self.getName(), str( spec ) )
        return ','.join( spec )

    def onKeyPress( self, caller, event ):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        print " -- Key Press: %s ( %s ), event = %s " % ( key, str(keysym), str( event ) )
        if keysym == None: return
        alt = ( keysym.lower().find('alt') == 0 )
        ctrl = caller.GetControlKey() 
        shift = caller.GetShiftKey() 

    def getMapOpacity(self):
        return self.map_opacity
    
    def setMapOpacity(self, opacity_vals, **args ):
        self.map_opacity = opacity_vals
        self.updateMapOpacity() 

    def updateMapOpacity(self, cmap_index=0 ):
        if self.baseMapActor:
            self.baseMapActor.SetOpacity( self.map_opacity[0] )
            self.render()

    def showInteractiveLens(self): 
        pass

    def updateLensDisplay(self, screenPos, coord):
        pass
           
    def buildBaseMap(self):
        if self.baseMapActor <> None: self.renderer.RemoveActor( self.baseMapActor )               
        world_map =  None  
        map_border_size = 20 
            
        self.y0 = -90.0  
        self.x0 =  0.0  
        dataPosition = None
        if world_map == None:
            self.map_file = defaultMapFile
            self.map_cut = defaultMapCut
        else:
            self.map_file = world_map[0].name
            self.map_cut = world_map[1]
        
        self.world_cut =  -1 
        if  (self.roi <> None): 
            roi_size = [ self.roi[1] - self.roi[0], self.roi[3] - self.roi[2] ] 
            map_cut_size = [ roi_size[0] + 2*map_border_size, roi_size[1] + 2*map_border_size ]
            if map_cut_size[0] > 360.0: map_cut_size[0] = 360.0
            if map_cut_size[1] > 180.0: map_cut_size[1] = 180.0
        else:
            map_cut_size = [ 360, 180 ]
            
                  
        if self.world_cut == -1: 
            if  (self.roi <> None): 
                if roi_size[0] > 180:             
                    self.ComputeCornerPosition()
                    self.world_cut = self.NormalizeMapLon( self.x0 )
                else:
                    dataPosition = [ ( self.roi[1] + self.roi[0] ) / 2.0, ( self.roi[3] + self.roi[2] ) / 2.0 ]
            else:
                dataPosition = [ 180, 0 ] # [ ( self.roi[1] + self.roi[0] ) / 2.0, ( self.roi[3] + self.roi[2] ) / 2.0 ]
        else:
            self.world_cut = self.map_cut
        
        self.imageInfo = vtk.vtkImageChangeInformation()        
        image_reader = vtk.vtkJPEGReader()      
        image_reader.SetFileName(  self.map_file )
        image_reader.Update()
        baseImage = image_reader.GetOutput() 
        new_dims, scale = None, None
        if dataPosition == None:    
            baseImage = self.RollMap( baseImage ) 
            new_dims = baseImage.GetDimensions()
            scale = [ 360.0/new_dims[0], 180.0/new_dims[1], 1 ]
        else:                       
            baseImage, new_dims = self.getBoundedMap( baseImage, dataPosition, map_cut_size, map_border_size )             
            scale = [ map_cut_size[0]/new_dims[0], map_cut_size[1]/new_dims[1], 1 ]
                          
        self.baseMapActor = vtk.vtkImageActor()
        self.baseMapActor.SetOrigin( 0.0, 0.0, 0.0 )
        self.baseMapActor.SetScale( scale )
        self.baseMapActor.SetOrientation( 0.0, 0.0, 0.0 )
        self.baseMapActor.SetOpacity( self.map_opacity[0] )
        mapCorner = [ self.x0, self.y0 ]
                
        self.baseMapActor.SetPosition( mapCorner[0], mapCorner[1], 0.1 )
        if vtk.VTK_MAJOR_VERSION <= 5:  self.baseMapActor.SetInput(baseImage)
        else:                           self.baseMapActor.SetInputData(baseImage)        
        self.mapCenter = [ self.x0 + map_cut_size[0]/2.0, self.y0 + map_cut_size[1]/2.0 ]        
        self.renderer.AddActor( self.baseMapActor )


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

    def init(self, **args ):
        init_args = args[ 'init_args' ]      
        show = args.get( 'show', False )  
        n_cores = args.get( 'n_cores', 32 )    
        lut = self.getLUT()
        if self.widget and show: self.widget.show()
        self.createRenderer()
        self.initCamera()
        interface = init_args[2]
        self.variable_reader = StructuredDataReader( init_args )
        self.variable_reader.execute( )       
        self.execute( )
        self.start()
#        self.createConfigDialog( show, interface )

    def clearReferrents(self):
        self.removeObservers()
        self.renderer = None
        self.renderWindowInteractor = None

    def removeObservers( self ): 
        for target in self.observerTargets:
            target.RemoveAllObservers()
        self.observerTargets.clear()

    def createRenderWindow(self):
        if self.useGui:
            self.widget = QVTKAdaptor()
            self.widget.Initialize()
            self.widget.Start()        
            self.connect( self.widget, QtCore.SIGNAL('event'), self.processEvent )  
            self.connect( self.widget, QtCore.SIGNAL("Close"), self.closeConfigDialog  ) 
            renwin = self.widget.GetRenderWindow()
        else:
            renwin = vtk.vtkRenderWindow()
            self.renderWindowInteractor = vtk.vtkGenericRenderWindowInteractor()
            self.renderWindowInteractor.SetRenderWindow( renwin )
            
        return renwin
    
    def closeConfigDialog(self):
        pass
    
    def enableRender(self, **args ):
        return True

    def render( self, **args ):
        if self.enableRender( **args ):
            self.renderWindow.Render()

    def processEvent(self, eventArgs ):
        if eventArgs[0] == "KeyEvent":
            self.onKeyEvent( eventArgs[1:])
        if eventArgs[0] == "ResizeEvent":
            self.onResizeEvent()           
            
    def onKeyEvent(self, eventArgs ):
        pass

    def getLUT( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut

    def toggleColormapVisibility(self):
        for colormapManager in self.colormapManagers.values():
            colormapManager.toggleColormapVisibility()
        self.render()
    
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
        show_colorBar = getBool( data[3] ) if ( len( data ) > 3 ) else 0 
        cmap_index = args.get( 'index', 0 )
        metadata = self.getMetadata()
        var_name = metadata.get( 'var_name', '')
        var_units = metadata.get( 'var_units', '')
        self.updateStereo( enableStereo )
        colormapManager = self.getColormapManager( name=colormapName, invert=invertColormap, index=cmap_index, units=var_units )
        if( colormapManager.colorBarActor == None ): 
            cm_title = str.replace( "%s (%s)" % ( var_name, var_units ), " ", "\n" )
            cmap_pos = [ 0.9, 0.2 ] if (cmap_index==0) else [ 0.02, 0.2 ]
            self.renderer.AddActor( colormapManager.createActor( pos=cmap_pos, title=cm_title ) )
        colormapManager.setColorbarVisibility( show_colorBar )
        self.render() 
        return True
        return False 
    
    def getUnits(self, var_index ):
        return ""
    
    def getMetadata(self):
        return self.metadata
    

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

    def start(self):
        self.renderWindowInteractor.Start() 
         
    def invalidate(self):
        self.isValid = False

    def getLabelActor(self):
        return self.textDisplayMgr.getTextActor( 'label', self.labelBuff, (.01, .90), size = VTK_NOTATION_SIZE, bold = True  ) if self.textDisplayMgr else None

    def onResizeEvent(self):
        self.updateTextDisplay( None, True )
        
    def updateTextDisplay( self, text, render=False ):
        if text <> None:
            metadata = self.getMetadata()
            var_name = metadata.get( 'var_name', '')
            var_units = metadata.get( 'var_units', '')
            self.labelBuff = "%s (%s)\n%s" % ( var_name, var_units, str(text) )
        label_actor = self.getLabelActor()
        if label_actor: label_actor.VisibilityOn() 
        if render: self.render()     

    def getLut( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut
        
    def updatingColormap( self, cmap_index, colormapManager ):
        pass

    def addObserver( self, target, event, observer ):
        self.observerTargets.add( target ) 
        target.AddObserver( event, observer ) 

    def createRenderer(self, **args ):
        background_color = args.get( 'background_color', VTK_BACKGROUND_COLOR )
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*background_color)

        self.renderWindow.AddRenderer( self.renderer )    
        self.renderWindowInteractor.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )  
        self.textDisplayMgr = TextDisplayMgr( self.renderer )             
        self.pointPicker = vtk.vtkPointPicker()
        self.pointPicker.PickFromListOn()   
        try:        self.pointPicker.SetUseCells(True)  
        except:     print>>sys.stderr,  "Warning, vtkPointPicker patch not installed, picking will not work properly."
        self.pointPicker.InitializePickList()             
        self.renderWindowInteractor.SetPicker(self.pointPicker) 
        self.addObserver( self.renderer, 'ModifiedEvent', self.activateEvent )
        if self.enableClip:
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

    def isConfigStyle( self, iren ):
        if not iren: return False
        return getClassName( iren.GetInteractorStyle() ) == getClassName( self.configurationInteractorStyle )
    
    def onAnyEvent(self, caller, event):
        return 0
        
    def onKeyRelease(self, caller, event):
        return 0
        
    def onModified(self, caller, event):
        return 0
    
    def onRender(self, caller, event):
        return 0
    
    def updateInteractor(self): 
        return 0    
    
    def activateEvent( self, caller, event ):
        if not self.activated:
#            self.addObserver( self.renwin,"AbortCheckEvent", CheckAbort)
#            self.activateWidgets( self.renderWindowInteractor )                                  
            self.addObserver( self.renderWindowInteractor, 'CharEvent', self.setInteractionState )                   
#            self.addObserver( self.renderWindowInteractor, 'MouseMoveEvent', self.updateLevelingEvent )
#                        self.addObserver( 'LeftButtonReleaseEvent', self.finalizeLevelingEvent )
#            self.addObserver( self.renderWindowInteractor, 'AnyEvent', self.onAnyEvent )  
#                        self.addObserver( 'MouseWheelForwardEvent', self.refineLevelingEvent )     
#                        self.addObserver( 'MouseWheelBackwardEvent', self.refineLevelingEvent )     
#            self.addObserver( self.renderWindowInteractor, 'CharEvent', self.onKeyPress )
            self.addObserver( self.renderWindowInteractor, 'KeyReleaseEvent', self.onKeyRelease )
            self.addObserver( self.renderWindowInteractor, 'LeftButtonPressEvent', self.onLeftButtonPress )
            self.addObserver( self.renderWindowInteractor, 'ModifiedEvent', self.onModified )
            self.addObserver( self.renderWindowInteractor, 'RenderEvent', self.onRender )                   
            self.addObserver( self.renderWindowInteractor, 'LeftButtonReleaseEvent', self.onLeftButtonRelease )
            self.addObserver( self.renderWindowInteractor, 'RightButtonReleaseEvent', self.onRightButtonRelease )
            self.addObserver( self.renderWindowInteractor, 'RightButtonPressEvent', self.onRightButtonPress )
#             for configurableFunction in self.configurableFunctions.values():
#                 configurableFunction.activateWidget( self.renderWindowInteractor  )
            self.updateInteractor() 
            self.activated = True 
            
    def toggleClipping(self):
        if self.clipper.GetEnabled():   self.clipOff()
        else:                           self.clipOn()
        
    def clipOn(self):
        if self.enableClip:
            self.clipper.On()
            self.executeClip()

    def clipOff(self):
        if self.enableClip:
            self.clipper.Off()      
        
        
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
        self.renderer.GetActiveCamera().SetPosition( self.xcenter, self.ycenter, 400.0 )
        self.renderer.GetActiveCamera().SetFocalPoint( self.xcenter, self.ycenter, 0.0 )
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

    def update(self):
        pass

