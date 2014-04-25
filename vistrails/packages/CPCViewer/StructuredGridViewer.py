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
    
from packages.CPCViewer.DV3DPlot import DV3DPlot
import sys, vtk, cdms2, traceback, os, cdtime 
from packages.CPCViewer.ColorMapManager import *  
from packages.CPCViewer.ImagePlaneWidget import ImagePlaneWidget 
from packages.CPCViewer.Shapefile import shapeFileReader     
from packages.CPCViewer.DistributedPointCollections import kill_all_zombies
from packages.CPCViewer.DV3DPlot import  *
from packages.CPCViewer.StructuredVariableReader import StructuredDataReader
#from packages.CPCViewer.StructuredDatasetReader import StructuredFileReader
 
def bound( val, bounds ): return max( min( val, bounds[1] ), bounds[0] )
packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultOutlineMapFile = os.path.join( defaultMapDir,  'political_map.png' )

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultLogoFile = os.path.join( defaultMapDir,  'uvcdat.jpg' )
defaultMapFile = os.path.join( defaultMapDir,  'earth2k.jpg' )
defaultMapCut = -180
SLIDER_MAX_VALUE = 100
MAX_IMAGE_SIZE = 1000000

class ConfigGroup:
    Color = 0
    Rendering = 1
    Display = 2
    Utilities = 3
    BaseMap = 4
    
    @classmethod
    def getConfigGroupName( cls, groupId ):
        if groupId == cls.Color:     return "Color"
        if groupId == cls.Utilities: return "Utilities"
        if groupId == cls.Rendering: return "Rendering"
        if groupId == cls.Display:   return "Display"
        if groupId == cls.BaseMap:   return "Base Map"
        return None
    
class ConfigurableFunction( QtCore.QObject ):
    
    ConfigurableFunctions = {}    
    
    def __init__( self, name, key=None, **args ):
        QtCore.QObject.__init__(self)
        self.name = name
        self.activateByCellsOnly = args.get( 'cellsOnly', False )
        self.persist = args.get( 'persist', True )
        self.type = 'generic'
        self.matchUnits = False
        self.kwargs = args
        self.label = args.get( 'label', self.name )
        self.units = args.get( 'units', '' ).strip().lower()
        self.group = args.get( 'group', ConfigGroup.Display )  
        self.key = key
        self.functionID = -1 
        self.isLayerDependent = args.get( 'layerDependent', False )
        self.activeBound = args.get( 'activeBound', 'both' )
        self.sliderLabels = args.get( 'sliderLabels', [ 'Range Min', 'Range Max' ] )
        self.active = args.get( 'active', True )
        self.activeFunctionList = []
        self.moduleID = None
        self.altMode = False
        self._persisted = True
        self.guiEnabled = False
        self.range_bounds = None
#        self.parameterInputEnabled = True                                      # Handlers executed at:
        self.initHandler = args.get( 'init', None )         #    end of compute()
        self.openHandler = args.get( 'open', None )         #    key press
        self.startHandler = args.get( 'start', None )       #    left click
        self.updateHandler = args.get( 'update', None )     #    mouse drag or menu option choice
        self.hasState = args.get( 'hasState', True )
                        
    def clearReferrents(self):
        self.initHandler = None
        self.openHandler = None
        self.startHandler = None
        self.updateHandler = None
        self.active = False
        self.moduleID = None
        self.kwargs.clear()
        self.args = []

#     @property
#     def module(self):
#         return ModuleStore.getModule( self.moduleID ) if ( self.moduleID <> None ) else None

    def get_persisted(self):
        return self._persisted if self.persist else True
    
    def updateWindow( self ):
        pass
     
    def set_persisted(self, value):
        self._persisted = value
#        
    persisted = property(get_persisted, set_persisted) 

    def isValid(self):
        return True
    
    def hasDataUnits(self):
        return ( self.units == 'data' )
    
    def isCompatible( self, config_fn ):
        if config_fn and self.matchUnits:
            if self.units <> config_fn.units:
                return False           
        return True

    def setValue( self, new_parameter_value ):
        pass
        
    def postInstructions( self, message ):
        print "\n ----- %s -------\n" % message

    @staticmethod
    def getActiveFunctionList( active_irens = None ):
        activeFunctionList = []
        for cfgFunctionMap in ConfigurableFunction.ConfigurableFunctions.values():
            for cfgFunction in cfgFunctionMap.values():
                mod = cfgFunction.module
                if mod and (  ( active_irens == None ) or ( mod.iren in active_irens ) ):
                    activeFunctionList.append( cfgFunction )
        return activeFunctionList
    
    @staticmethod
    def clear( moduleId ):
        for configFunctionMap in ConfigurableFunction.ConfigurableFunctions.values():
            if moduleId in configFunctionMap:
                cfgFunction = configFunctionMap[moduleId]
                cfgFunction.clearReferrents()
                del configFunctionMap[ moduleId ]
                del cfgFunction
         
    def updateActiveFunctionList( self ):
        from packages.vtDV3D.PersistentModule import PersistentVisualizationModule 
        cfgFunctGlobalMap = ConfigurableFunction.ConfigurableFunctions
        cfgFunctionMap = cfgFunctGlobalMap.get( self.name, {} )
        self.activeFunctionList = []
#        valid_irens =  PersistentVisualizationModule.getValidIrens() 
#        print " ** N active_irens: %d " % len( active_irens )      
        for cfgFunction in cfgFunctionMap.values():
            if (cfgFunction <> self) and cfgFunction.module:
#                isActive = ( cfgFunction.module.iren in valid_irens )
#                if isActive and (cfgFunction.units == self.units):
                self.activeFunctionList.append( cfgFunction )
             
    def matches( self, key ):
        return self.active and ( self.key == key )
    
    def applyParameter( self, **args ):
        pass

    def init( self, ispec, **args ):
        self.moduleID = args.get( 'mid', 0 )
        if self.units == 'data': 
            self.units = ispec.units
            self.matchUnits = True             
        if ( self.initHandler != None ):
            self.initHandler( **self.kwargs ) 
        configFunctionMap = ConfigurableFunction.ConfigurableFunctions.setdefault( self.name, {} )
        configFunctionMap[self.moduleID] = self

    def fixRange(self):
        pass
            
    def expandRange( self ):
        pass
            
#    def setParameterInputEnabled( self, isEnabled ):
#        self.parameterInputEnabled = isEnabled
            
    def getHelpText( self ):
        return "<tr>   <td>%s</td>  <td>%s</td> <td>%s</td> </tr>\n" % ( self.key, self.label, self.type )

    def open( self, state, alt = False ):
        if( self.name == state ): 
            self.altMode = alt
            if ( self.openHandler != None ): 
                self.openHandler()
            
    def close(self):
        pass
            
    def activateWidget( self, iren ):
        pass
    
    def reset(self):
        return None
        
    def start( self, state, x, y ):
        if ( self.startHandler != None ) and ( self.name == state ):
            self.startHandler( x, y )

    def update( self, state, x, y, wsize ):
        if ( self.updateHandler != None ) and ( self.name == state ):
            return self.updateHandler( x, y, wsize )
        return None
    
    def getTextDisplay(self, **args ):
        return None
                
################################################################################

class ConfigurableBooleanFunction( ConfigurableFunction ):
    
    def __init__( self, name, function_args, key, **args ):
        ConfigurableFunction.__init__( self, name, function_args, key, **args )
        self.switchVal = args.get( 'initVal', False )
        self.labels = args.get( 'labels', '|'.join([self.name]*2) ).split('|')
        self.label = self.labels[ int(self.switchVal) ]
    
    
    def open( self, state, alt = False ):
        if( self.name == state ): 
            self.altMode = alt
            if ( self.openHandler != None ):
                self.switchVal = not self.switchVal
                self.label = self.labels[ int(self.switchVal) ]
                self.openHandler( self.switchVal )

################################################################################

class QtWindowLeveler( QtCore.QObject ):
    
    update_range_signal = QtCore.SIGNAL('update_range')
    
    WindowRelative = 0
    BoundsRelative = 1
    Absolute = 2
   
    def __init__( self, **args ):
        QtCore.QObject.__init__( self )
        self.OriginalWindow           = 1.0
        self.OriginalLevel            = 0.5
        self.CurrentWindow            = 1.0
        self.CurrentLevel             = 0.5
        self.sensitivity              = args.get( 'sensitivity', (1.5, 5.0) )
        self.algorithm                = self.WindowRelative if args.get( 'windowing', True ) else self.Absolute
        self.scaling = 1.0        
        self.invert = False

    def setDataRange( self, data_range ):
        if (self.algorithm == self.Absolute):
            self.setWindowLevel( data_range[0], data_range[1] )
        else:
            self.scaling = 0.5 * ( abs(data_range[0]) + abs(data_range[1]) )
            if self.scaling == 0.0: self.scaling = 1.0
            self.OriginalWindow = ( data_range[1] - data_range[0] ) / self.scaling if ( self.scaling > 0.0 ) else 1.0
            self.OriginalLevel = 1.0
          
            if( abs( self.OriginalWindow ) < 0.001 ): self.OriginalWindow = -0.001 if ( self.OriginalWindow < 0.0 ) else  0.001
            if( abs( self.OriginalLevel  ) < 0.001 ): self.OriginalLevel  = -0.001 if ( self.OriginalLevel  < 0.0 ) else  0.001
            self.setWindowLevel( self.OriginalWindow, self.OriginalLevel )
    
    def addUpdateRangeObserver( self, observer ):   
        self.connect( self, self.update_range_signal, observer )

    def windowLevel( self, X, Y, window_size ):
        result = None
        if self.algorithm == self.WindowRelative:
              window = self.InitialWindow
              level = self.InitialLevel
                
              dx = self.sensitivity[0] * ( X - self.StartWindowLevelPositionX ) / float( window_size[0] )
              dy = self.sensitivity[1] * ( self.StartWindowLevelPositionY - Y ) / float( window_size[1] )
               
              if ( abs( window ) > 0.01 ):   dx = dx * window
              else:                          dx = (dx * -0.01) if ( window < 0 ) else (dx *  0.01)
        
              if ( abs( level  ) > 0.01 ):   dy = dy * level
              else:                          dy = (dy * -0.01) if ( window < 0 ) else (dy *  0.01)
                
              if ( window < 0.0 ):           dx = -1 * dx
              if ( level < 0.0 ):            dy = -1 * dy
             
              newWindow = dx + window
              newLevel = level - dy
            
              if ( abs( newWindow ) < 0.01 ):  newWindow = -0.01 if( newWindow < 0 ) else  0.01 
              if ( abs( newLevel ) < 0.01 ):   newLevel  = -0.01 if( newLevel  < 0 ) else  0.01 
              
              if (( (newWindow < 0) and (self.CurrentWindow > 0 )) or ( (newWindow > 0) and (self.CurrentWindow < 0) )):
                  self.invert = not self.invert
            
              rmin = newLevel - 0.5*abs( newWindow )
              rmax = rmin + abs( newWindow )
              result = [ rmin*self.scaling, rmax*self.scaling, 1 if self.invert else 0 ]
              self.emit( self.update_range_signal, result )
            
              self.CurrentWindow = newWindow
              self.CurrentLevel = newLevel
        elif self.algorithm == self.BoundsRelative:
              dx =  self.sensitivity[0] * ( X - self.StartWindowLevelPositionX ) 
              dy =  self.sensitivity[1] * ( Y - self.StartWindowLevelPositionY ) 
              rmin = self.InitialRange[0] + ( dx / window_size[0] ) * self.InitialWindow
              rmax = self.InitialRange[1] + ( dy / window_size[1] ) * self.InitialWindow
              if rmin > rmax:   result =  [ rmax, rmin, 1 ]
              else:             result =  [ rmin, rmax, 0 ]
              self.CurrentWindow = result[1] - result[0]
              self.CurrentLevel =  0.5 * ( result[0] + result[1] )
        elif self.algorithm == self.Absolute:
              dx =  1.0 + self.sensitivity[0] * ( ( X - self.StartWindowLevelPositionX )  / self.StartWindowLevelPositionX ) 
              dy =  1.0 + self.sensitivity[1] * ( ( Y - self.StartWindowLevelPositionY ) / self.StartWindowLevelPositionY ) 
              self.CurrentWindow = dx*self.InitialWindow
              self.CurrentLevel =  dy*self.InitialLevel
              print str( [dx,dy,self.CurrentWindow,self.CurrentLevel] )
              result = [ self.CurrentWindow, self.CurrentLevel, 0 ]
              self.emit( self.update_range_signal, result )
 #       print " --- Set Range: ( %f, %f ),   Initial Range = ( %f, %f ), P = ( %d, %d ) dP = ( %f, %f ) " % ( result[0], result[1], self.InitialRange[0], self.InitialRange[1], X, Y, dx, dy )      
        return result
      
    def startWindowLevel( self, X, Y ):   
        self.InitialWindow = self.CurrentWindow
        self.InitialLevel = self.CurrentLevel  
        self.StartWindowLevelPositionX = float(X)
        self.StartWindowLevelPositionY = float(Y)
        rmin = self.InitialLevel - 0.5 * abs( self.CurrentWindow )
        rmax = rmin + abs( self.CurrentWindow )
        self.InitialRange = [ rmin, rmax ] if ( rmax > rmin ) else [ rmax, rmin ]
#        print " --- Initialize Range: ( %f, %f ), P = ( %d, %d ) WL = ( %f, %f ) " % ( self.InitialRange[0]*self.scaling, self.InitialRange[1]*self.scaling, X, Y, self.InitialWindow, self.InitialLevel )     

    def setWindowLevel( self, window,  level ):
        if ( (self.CurrentWindow == window) and (self.CurrentLevel == level) ): return
        
        if (( (window < 0) and (self.CurrentWindow > 0 )) or ( (window > 0) and (self.CurrentWindow < 0) )):
              self.invert = not self.invert
        
        if window < 0.01:
            pass      
        self.CurrentWindow = window
        self.CurrentLevel = level
        
        rmin = self.CurrentLevel - 0.5 * abs( self.CurrentWindow )
        rmax = rmin + abs( self.CurrentWindow )
        result = [ rmin*self.scaling, rmax*self.scaling, 1 if self.invert else 0 ]
        self.emit( self.update_range_signal, result )

        return result

    def setWindowLevelFromRange( self, range ):
        self.CurrentWindow = ( range[1] - range[0] ) / self.scaling
        self.CurrentLevel = ( range[1] + range[0] ) / ( 2 * self.scaling )
        

class WindowRefinementGenerator( QtCore.QObject ):

    def __init__( self, **args ):
        QtCore.QObject.__init__( self )
        self.initialPosition = None
        self.initialRefinement = None
        self.range = args.get( 'range', [ 0.0, 1.0 ] )
        
    def initRefinement( self, pos, initRefinement ):  
        self.initialPosition = pos
        self.initialRefinement = initRefinement
        
    def updateRefinement( self, pos, wsize ):
        newRefinement = [ 0, 0 ]
        scale = self.range[1] - self.range[0]
        for iR in [ 0, 1 ]:
            dr = ( pos[iR] - self.initialPosition[iR] ) * scale / wsize[iR]
            newRefinement[iR] = self.initialRefinement[iR] + dr
            if newRefinement[iR] < self.range[0]: newRefinement[iR] = self.range[0]
            if newRefinement[iR] > self.range[1]: newRefinement[iR] = self.range[1]
        return newRefinement

class WindowLevelingConfigurableFunction( ConfigurableFunction ):
    
    def __init__( self, name, key, **args ):
        ConfigurableFunction.__init__( self, name, key, **args  )
        self.type = 'leveling'
        self.manuallyAdjusted = False
        self.windowLeveler = QtWindowLeveler( **args )
        self.windowRefiner = WindowRefinementGenerator( range=[ 0.001, 0.999 ] )
        if( self.initHandler == None ): self.initHandler = self.initLeveling
        if( self.startHandler == None ): self.startHandler = self.startLeveling
        if( self.updateHandler == None ): self.updateHandler = self.updateLeveling
        self.setLevelDataHandler = args.get( 'setLevel', None )
        self.getLevelDataHandler = args.get( 'getLevel', None )
        self.getInitLevelDataHandler = args.get( 'getInitLevel', None )
        self.isDataValue = args.get( 'isDataValue', True )
        self.initial_range = args.get( 'initRange', None )
        self.initRefinement = args.get( 'initRefinement', [ 0.0, 1.0 ] )
        self.isValid = args.get( 'isValid', lambda: True )
        self.boundByRange = args.get( 'bound', True )
        self.adjustRangeInput = args.get( 'adjustRangeInput', -1 )
        self.widget = args.get( 'gui', None )

    def postInstructions( self, message ):
        self.module.displayInstructions( message ) # "Left-click, mouse-move, left-click in this cell." )
    
    def applyParameter( self, **args ):
        try:
            self.setLevelDataHandler( self.range, **args )
            self.persisted = False
        except Exception, err:
            print>>sys.stderr, "Error in setLevelDataHandler: ", str(err)        
    def reset(self):
        self.setLevelDataHandler( self.initial_range )
        self.persisted = False
        self.module.render() 
        return self.initial_range
    
    def fixRange(self):
        if self.adjustRangeInput >= 0:
            self.adjustRangeInput = -1
            if not self.manuallyAdjusted:
                self.manuallyAdjusted = True
                self.module.finalizeParameter( self.name )

    def expandRange( self ):
        if self.adjustRangeInput >= 0:
            ispec = self.module.getInputSpec( self.adjustRangeInput )
            if ispec and ispec.input():
                if ( self.range_bounds[0] <> ispec.seriesScalarRange[0] ) or ( self.range_bounds[1] <> ispec.seriesScalarRange[1] ):
                    self.range_bounds[0:2] = ispec.seriesScalarRange[0:2]
                    self.initial_range[:] = self.range_bounds[:]
                    if not self.manuallyAdjusted: 
                        self.range[0:2] = self.range_bounds[0:2]
                        self.initLeveling( initRange = False ) 
 
    def initLeveling( self, **args ):
        initRange = args.get( 'initRange', True )
# Dont't currently need these (But should be OK):
#        units_src = args.get('units',None)
#        input_index = args.get( 'input_index', 0 )
#        ispec = self.module.ispec( input_index )
        if self.range_bounds == None:
            self.range_bounds =   args.get( 'rangeBounds', None )
        if initRange:
            if self.initial_range == None:
                self.initial_range =  None if ( self.getLevelDataHandler == None ) else self.getLevelDataHandler()
            if self.range_bounds == None:
                self.range_bounds = self.initial_range if ( self.getLevelDataHandler == None ) else self.getLevelDataHandler()
            if self.initial_range == None: self.initial_range =  [ 0.0, 1.0, 1 ]
            if self.range_bounds == None: self.range_bounds =  self.initial_range
            self.range = list( self.initial_range  ) # if not self.module.newDataset else self.initial_range
            if len( self.range ) == 3: 
                for iR in range(2): self.range.append( self.initRefinement[iR] )
        self.windowLeveler.setDataRange( self.range )
        self.setLevelDataHandler( self.range )
        if self.widget: 
            self.widget.initLeveling( self.range )
            self.connect( self.widget, QtCore.SIGNAL('update(QString)'), self.broadcastLevelingData )

#        print "    ***** Init Leveling Parameter: %s, initial range = %s" % ( self.name, str(self.range) )
        
    def startLeveling( self, x, y ):
        if self.altMode:    self.windowRefiner.initRefinement( [ x, y ], self.range[3:5] )   
        else:               self.windowLeveler.startWindowLevel( x, y )
        self.updateActiveFunctionList()
        self.adjustRangeInput = -1
        self.emit(QtCore.SIGNAL('startLeveling()'))
        print "startLeveling: %s " % str( self.range )

    def getTextDisplay(self, **args ):
        try:
            mod = self.module
            rmin = self.range[0] # if not self.isDataValue else self.module.getDataValue( self.range[0] )
            rmax = self.range[1] # if not self.isDataValue else self.module.getDataValue( self.range[1] )
            units = mod.units if ( mod and hasattr(mod,'units') )  else None
            if units: textDisplay = " Range: %.4G, %.4G %s . " % ( rmin, rmax, units )
            else: textDisplay = " Range: %.4G, %.4G . " % ( rmin, rmax )
            return textDisplay
        except:
            return None
    
    def updateWindow( self ): 
        self.windowLeveler.setWindowLevelFromRange( self.range )
            
    def updateLeveling( self, x, y, wsize ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper     
        if self.altMode:
            refinement_range = self.windowRefiner.updateRefinement( [ x, y ], wsize )
            for iR in [ 0, 1 ]: self.range[3+iR] = refinement_range[iR]
        else:  
            leveling_range = self.windowLeveler.windowLevel( x, y, wsize )
            for iR in [ 0, 1 ]: self.range[iR] = bound( leveling_range[iR], self.range_bounds ) if self.boundByRange else leveling_range[iR]
        self.emit( QtCore.SIGNAL('updateLeveling()') )
        return self.broadcastLevelingData( active_modules = DV3DPipelineHelper.getActivePlotList() )
#        print "updateLeveling: %s " % str( self.range )

    def setImageDataRange(  self, imageRange  ):
        data_range = self.module.getDataValues( imageRange )
        self.setDataRange( data_range )

    def setDataRange(  self, data_range, isManual = False  ):
        self.range[0:2] = data_range[0:2]
        if isManual: self.manuallyAdjusted = True
#        print " setImageDataRange, imageRange=%s, dataRange=%s " % ( str(imageRange), str(data_range) )
        self.setLevelDataHandler( self.range )
        self.persisted = False

    def setScaledDataRange(  self, scaled_data_range, isManual = False  ):
        dr = (self.range_bounds[1]-self.range_bounds[0])
        self.range[0] = self.range_bounds[0] + scaled_data_range[0] * dr
        self.range[1] = self.range_bounds[0] + scaled_data_range[1] * dr
        if isManual: self.manuallyAdjusted = True
#        print " setImageDataRange, imageRange=%s, dataRange=%s " % ( str(imageRange), str(data_range) )
        self.setLevelDataHandler( self.range )
        self.persisted = False

    def getScaledDataRange(  self  ):
        dr = (self.range_bounds[1]-self.range_bounds[0])
        scaled_range = [ ( self.range[0] - self.range_bounds[0] ) / dr, ( self.range[1] - self.range_bounds[0] ) / dr ]
        return scaled_range
        
    def broadcastLevelingData(  self, range = None, **args  ):
        if range: self.range = range
#        print " ** Broadcast Leveling: altMode = %s, range = %s, refine = %s, Modules: " % ( str( self.altMode ) , str( self.range[0:2] ), str( self.range[3:5] )  )
        affected_renderers = set()
        active_module_list = args.get( 'active_modules', None )
        if (active_module_list == None) or (self.moduleID in active_module_list):
            mod = self.module
            self.setLevelDataHandler( self.range )
            mod.setParameter( self.name, range )
            self.persisted = False
            affected_renderers.add( mod.renderer )
            self.manuallyAdjusted = True
        for cfgFunction in self.activeFunctionList:
            if (active_module_list == None) or (cfgFunction.moduleID in active_module_list):
                if( cfgFunction.units == self. units ):
                    cfgFunction.setDataRange( self.range, True )
                else:
                    cfgFunction.setScaledDataRange( self.getScaledDataRange(), True )
                affected_renderers.add( cfgFunction.module.renderer )
#               print "   -> module = %x " % id(cfgFunction.module)

        for renderer in affected_renderers:
            if renderer <> None:
                rw = renderer.GetRenderWindow()
                if rw <> None: rw.Render()

        return self.range # self.wrapData( range )

class StructuredGridPlot(DV3DPlot): 
     
    global_coords = [-1, -1, -1]
    
    def __init__( self,  **args ):
        DV3DPlot.__init__( self,  **args  )
        self.configurableFunctions = {}
#         self.addUVCDATConfigGuiFunction( 'contourColormap', ColormapConfigurationDialog, 'K', label='Choose Contour Colormap', setValue=lambda data: self.setColormap(data,1) , getValue=lambda: self.getColormap(1), layerDependent=True, isValid=self.hasContours, group=ConfigGroup.Color )
        self.sliceOutputShape = args.get( 'slice_shape', [ 100, 50 ] )
        self.polygonActor = None
        self.opacity = [ 1.0, 1.0 ]
        self.iOrientation = 0
        self.updatingPlacement = False
        self.isSlicing = False
        self.planeWidgetX = None
        self.planeWidgetY = None
        self.planeWidgetZ = None
        self.opacityUpdateCount = 0
        self.generateContours = False
        self.contourLineActors = {}
        self.contourLineMapperer = None
        self.shapefilePolylineActors = {}
        self.basemapLineSpecs = {}
        self.contours = None
        self.NumContours = 10.0
        self.showOutlineMap = True
        self.pipelineBuilt = False
        self.baseMapActor = None
        self.enableBasemap = True
        self.map_opacity = [ 0.4, 0.4 ]
        self.roi = None
        self.inputSpecs = {}

        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', units='data', setLevel=self.scaleColormap, getLevel=self.getDataRangeBounds, layerDependent=True, adjustRangeInput=0, group=ConfigGroup.Color )
        self.addConfigurableLevelingFunction( 'opacity', 'O', label='Slice Plane Opacity', rangeBounds=[ 0.0, 1.0 ],  setLevel=self.setOpacity, activeBound='min',  getLevel=self.getOpacity, isDataValue=False, layerDependent=True, bound = False, group=ConfigGroup.Rendering )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ], group=ConfigGroup.Display )
        self.addConfigurableLevelingFunction( 'contourDensity', 'g', label='Contour Density', activeBound='max', setLevel=self.setContourDensity, getLevel=self.getContourDensity, layerDependent=True, windowing=False, rangeBounds=[ 3.0, 30.0, 1 ], bound=False, isValid=self.hasContours, group=ConfigGroup.Rendering )
        self.addConfigurableLevelingFunction( 'contourColorScale', 'S', label='Contour Colormap Scale', units='data', setLevel=self.scaleContourColormap, getLevel=lambda:self.getDataRangeBounds(1), layerDependent=True, adjustRangeInput=1, isValid=self.hasContours, group=ConfigGroup.Color )
        self.addConfigurableLevelingFunction( 'coastlines_Line', 'm0', label='Coastline Line', setLevel=self.setBasemapCoastlineLineSpecs, getLevel=self.getBasemapCoastlineLineSpecs, sliderLabels=[ 'Thickness', 'Density' ], layerDependent=False, rangeBounds=[ 0.0, 3.49 ], initRange=[ 1.0, 1.0, 1 ], group=ConfigGroup.BaseMap )
        self.addConfigurableLevelingFunction( 'countries_Line', 'm1', label='Countries Line', setLevel=self.setBasemapCountriesLineSpecs, getLevel=self.getBasemapCountriesLineSpecs, sliderLabels=[ 'Thickness', 'Density' ], layerDependent=False, rangeBounds=[ 0.0, 3.49 ], initRange=[ 0.0, 1.0, 0 ], group=ConfigGroup.BaseMap )
        self.addConfigurableLevelingFunction( 'states_Line', 'm2', label='States Line', setLevel=self.setBasemapStatesLineSpecs, getLevel=self.getBasemapStatesLineSpecs, sliderLabels=[ 'Thickness', 'Density' ], layerDependent=False, rangeBounds=[ 0.0, 3.49 ], initRange=[ 0.0, 1.0, 0 ], group=ConfigGroup.BaseMap )
        self.addConfigurableLevelingFunction( 'lakes_Line', 'm3', label='Lakes Line', setLevel=self.setBasemapLakesLineSpecs, getLevel=self.getBasemapLakesLineSpecs, sliderLabels=[ 'Thickness', 'Density' ], layerDependent=False, rangeBounds=[ 0.0, 3.49 ], initRange=[ 0.0, 1.0, 0 ], group=ConfigGroup.BaseMap )
        self.addConfigurableLevelingFunction( 'map_opacity', 'M', label='Base Map Opacity', rangeBounds=[ 0.0, 1.0 ],  setLevel=self.setMapOpacity, activeBound='min',  getLevel=self.getMapOpacity, isDataValue=False, layerDependent=True, group=ConfigGroup.BaseMap, bound = False )
# 
#     def activateWidgets( self, iren ):
#         if self.baseMapActor:
#             bounds = [ 0.0 ]*6
#             self.baseMapActor.GetBounds( bounds )
    def getScaleBounds(self):
        return [ 0.5, 100.0 ]

    def addConfigurableFunction(self, name, function_args, key, **args):
        self.configurableFunctions[name] = ConfigurableFunction( name, function_args, key, **args )

    def addConfigurableLevelingFunction(self, name, key, **args):
        self.configurableFunctions[name] = WindowLevelingConfigurableFunction( name, key, **args )

    def getConfigFunction( self, name ):
        return self.configurableFunctions.get(name,None)

    def removeConfigurableFunction(self, name ):        
        del self.configurableFunctions[name]

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
#         self.dataset_reader = StructuredFileReader( init_args )
#         self.dataset_reader.execute()
        self.variable_reader = StructuredDataReader( init_args )
        self.variable_reader.execute( )       
        self.execute( )
        self.start()
#        self.createConfigDialog( show, interface )

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

    def terminate( self ):
        pass

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
        
    def clearReferrents(self):
        print " **************************************** VolumeSlicer:clearReferrents, id = %d  **************************************** " % self.moduleID
        sys.stdout.flush()
        del self.planeWidgetX
        del self.planeWidgetY
        del self.planeWidgetZ
        self.planeWidgetX = None
        self.planeWidgetY = None
        self.planeWidgetZ = None
        self.latLonGrid = True
        del self.sliceOutput
        self.sliceOutput = None 
        if self.contours:
            del self.contours
            self.contours = None    
            del self.contourLineMapperer 
            self.contourLineMapperer = None
        ispec = self.getInputSpec( 0 ) 
        input0 = ispec.input() 
        print " VolumeSlicer: Input refs = %d " % input0.GetReferenceCount()
        sys.stdout.flush()

    def getDataRangeBounds(self, inputIndex=0 ):
        ispec = self.getInputSpec( inputIndex )
        return ispec.getDataRangeBounds() if ispec else None
        
    def scaleContourColormap(self, data, **args ):
        return self.scaleColormap( data, 1, **args )
        
    def hasContours(self):
        return self.generateContours
        
    def setContourDensity( self, ctf_data, **args ):
        if self.NumContours <> ctf_data[1]:
            self.NumContours = ctf_data[1]
            self.updateContourDensity()

    def getContourDensity( self ):
        return [ 3.0, self.NumContours, 1 ]
    
    def setZScale( self, zscale_data, **args ):
        self.setInputZScale( zscale_data )
        if self.planeWidgetX <> None:
            primaryInput = self.input()
            bounds = list( primaryInput.GetBounds() ) 
            if not self.planeWidgetX.MatchesBounds( bounds ):
                self.planeWidgetX.PlaceWidget( bounds )        
                self.planeWidgetY.PlaceWidget( bounds ) 
                self.render()               

    def setInputZScale( self, zscale_data, **args  ):
        ispec = self.getInputSpec(  1 )       
        if (ispec <> None) and (ispec.input() <> None):
            contourInput = ispec.input() 
            ix, iy, iz = contourInput.GetSpacing()
            sz = zscale_data[1]
            contourInput.SetSpacing( ix, iy, sz )  
            contourInput.Modified() 

    def setInteractionState(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        shift = caller.GetShiftKey()
        alt = not key and keysym.startswith("Alt")
        if alt:
            self.isAltMode = True
        else: 
#            ikey = ord(key[0]) if key else 0
            if shift: keysym = keysym.upper()
            print " ------------------------------------------ setInteractionState, key=%s, keysym=%s, shift = %s, isAltMode = %s    ------------------------------------------ " % (str(key), str(keysym), str(shift), str(self.isAltMode) )
            self.processKeyEvent( keysym, caller, event )

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

    def updateInteractionState( self, state, altMode ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper    
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
                if DV3DPipelineHelper.isLevelingConfigMode():
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
                
    def getOpacity(self):
        return self.opacity
    
    def setOpacity(self, range, **args ):
        self.opacity = range
#        printArgs( " Leveling: ", opacity=self.opacity, range=range ) 
        self.updateOpacity() 

    def updateOpacity(self, cmap_index=0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setAlphaRange( [ bound( self.opacity[i], [ 0.0, 1.0 ] ) for i in (0,1) ] )
        if (self.opacityUpdateCount % 5) == 0: self.render()
        self.opacityUpdateCount = self.opacityUpdateCount + 1  
#        self.lut.SetAlpha( self.opacity[1] )
#        self.lut.SetAlphaRange ( self.opacity[0], self.opacity[1] )
#        print "  ---> Set Opacity = %s " % str( self.opacity )
#        self.UpdateWidgetPlacement()
        
#    def UpdateWidgetPlacement(self):
#        self.updatingPlacement = True
#        self.planeWidgetX.UpdatePlacement() 
#        self.planeWidgetX.PlaceWidget()
#        self.planeWidgetY.UpdatePlacement() 
#        self.planeWidgetY.PlaceWidget()
#        self.planeWidgetZ.UpdatePlacement() 
#        self.planeWidgetZ.PlaceWidget()
#        self.updatingPlacement = False

    def enableVisualizationInteraction(self): 
#        print>>sys.stderr, "enable Visualization Interaction"
        if self.planeWidgetX <> None: self.planeWidgetX.EnableInteraction()                                                
        if self.planeWidgetY <> None:self.planeWidgetY.EnableInteraction()                                                
        if self.planeWidgetZ <> None:self.planeWidgetZ.EnableInteraction()  

    def disableVisualizationInteraction(self):
#        print>>sys.stderr, "disable Visualization Interaction" 
        if self.planeWidgetX <> None: self.planeWidgetX.DisableInteraction()                                                
        if self.planeWidgetY <> None:self.planeWidgetY.DisableInteraction()                                                
        if self.planeWidgetZ <> None:self.planeWidgetZ.DisableInteraction()  

    def updatingColormap( self, cmap_index, colormapManager ):
        if cmap_index == 0:
            if self.planeWidgetX <> None: self.planeWidgetX.SetTextureInterpolate( colormapManager.smoothColormap )
            if self.planeWidgetY <> None: self.planeWidgetY.SetTextureInterpolate( colormapManager.smoothColormap )
            if self.planeWidgetZ <> None: self.planeWidgetZ.SetTextureInterpolate( colormapManager.smoothColormap )
            self.updateModule()
                                                                        
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """     
#        contourModule = self.wmod.forceGetInputFromPort( "contours", None )
#        if self.input() == None:
#            if contourModule <> None:
#                self.input() = contourModule.getOutput() 
#            else:
#                print>>sys.stderr, "Error, must provide an input to the Volume Slicer module!"
 #       self.intersectInputExtents()
        contour_ispec = None # self.getInputSpec(  1 )       

        contourInput = contour_ispec.input() if contour_ispec <> None else None
        primaryInput = self.input()
        md = self.getInputSpec().getMetadata()
        self.latLonGrid = md.get( 'latLonGrid', True )

#        self.contourInput = None if contourModule == None else contourModule.getOutput() 
        # The 3 image plane widgets are used to probe the dataset.    
#        print " Volume Slicer buildPipeline, id = %s " % str( id(self) )
        self.sliceOutput = vtk.vtkImageData()  
        xMin, xMax, yMin, yMax, zMin, zMax = primaryInput.GetWholeExtent()       
        self.slicePosition = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        dataType = primaryInput.GetScalarTypeAsString()
        bounds = list(primaryInput.GetBounds()) 
        origin = primaryInput.GetOrigin()
        if (dataType <> 'float') and (dataType <> 'double'):
             self.setMaxScalarValue( primaryInput.GetScalarType() )
#        print "Data Type = %s, range = (%f,%f), extent = %s, origin = %s, bounds=%s, slicePosition=%s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], str(self.input().GetWholeExtent()), str(origin), str(bounds), str(self.slicePosition)  )
      
        # The shared picker enables us to use 3 planes at one time
        # and gets the picking order right
        lut = self.getLut()
        picker = None
        useVtkImagePlaneWidget = False
        textureColormapManager = self.getColormapManager( index=0 )
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005) 
                
        if self.planeWidgetZ == None:
            self.planeWidgetZ = ImagePlaneWidget( self, picker, 2 )  
            self.planeWidgetZ.SetRenderer( self.renderer )
#            self.observerTargets.add( self.planeWidgetZ )
            prop3 = self.planeWidgetZ.GetPlaneProperty()
            prop3.SetColor(0, 0, 1)
            self.planeWidgetZ.SetUserControlledLookupTable(1)
            self.planeWidgetZ.SetLookupTable( lut )
       
        self.planeWidgetZ.SetInput( primaryInput, contourInput )
        self.planeWidgetZ.SetPlaneOrientationToZAxes()
        self.planeWidgetZ.PlaceWidget( bounds )
        
        if self.planeWidgetZ.HasThirdDimension(): 
            if (self.planeWidgetX == None): 
                self.planeWidgetX = ImagePlaneWidget( self, picker, 0 )
#               self.observerTargets.add( self.planeWidgetX )
                self.planeWidgetX.SetRenderer( self.renderer )
                prop1 = self.planeWidgetX.GetPlaneProperty()
                prop1.SetColor(1, 0, 0)
                self.planeWidgetX.SetUserControlledLookupTable(1)
                self.planeWidgetX.SetLookupTable( lut )
                
            self.planeWidgetX.SetInput( primaryInput, contourInput )
            self.planeWidgetX.SetPlaneOrientationToXAxes()
            self.planeWidgetX.PlaceWidget( bounds )       
                    
            if self.planeWidgetY == None: 
                self.planeWidgetY = ImagePlaneWidget( self, picker, 1)
                self.planeWidgetY.SetRenderer( self.renderer )
                self.planeWidgetY.SetUserControlledLookupTable(1)
#                self.observerTargets.add( self.planeWidgetY )
                prop2 = self.planeWidgetY.GetPlaneProperty()
                prop2.SetColor(1, 1, 0)
                self.planeWidgetY.SetUserControlledLookupTable(1)
                self.planeWidgetY.SetLookupTable( lut )
            
            self.planeWidgetY.SetInput( primaryInput, contourInput )
            self.planeWidgetY.SetPlaneOrientationToYAxes()       
            self.planeWidgetY.PlaceWidget(  bounds  ) 

        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )
        self.updateOpacity() 
        
        if (contour_ispec <> None) and (contour_ispec.input() <> None) and (self.contours == None):
            rangeBounds = self.getRangeBounds(1)
            colormapManager = self.getColormapManager( index=1 )
            self.generateContours = True   
            self.contours = vtk.vtkContourFilter()
            self.contours.GenerateValues( self.NumContours, rangeBounds[0], rangeBounds[1] )
     
            self.contourLineMapperer = vtk.vtkPolyDataMapper()
            self.contourLineMapperer.SetInputConnection( self.contours.GetOutputPort() )
            self.contourLineMapperer.SetScalarRange( rangeBounds[0], rangeBounds[1] )
            self.contourLineMapperer.SetColorModeToMapScalars()
            self.contourLineMapperer.SetLookupTable( colormapManager.lut )
            self.contourLineMapperer.UseLookupTableScalarRangeOn()

#        self.set3DOutput() 

        # Add the times series only in regular volume slicer and not in Hovmoller Slicer
#         if self.getInputSpec().getMetadata()['plotType']=='xyz':
#             self.addConfigurableFunction('Show Time Series', None, 't' )

    def buildOutlineMap(self):
        # This function load a binary image (black and white)
        # and create a default grid for it. Then it uses re-gridding algorithms 
        # to scale in the correct domain.
        from pylab import imread
        import vtk.util.vtkImageImportFromArray as vtkUtil

        # read outline image and convert to gray scale
        try:
            data = imread(defaultOutlineMapFile)
            data = data.mean(axis=2)
    
    #        # create a variable using the data loaded in the image and an uniform grid
            dims = data.shape
            reso = [180.0/dims[0], 360.0/dims[1]]
            var = cdms2.createVariable(data)
            lat = cdms2.createUniformLatitudeAxis(90, dims[0], -reso[0])
            lon = cdms2.createUniformLongitudeAxis(-180, dims[1], reso[1])
            var.setAxis(0, lat)
            var.setAxis(1, lon)
    
            # create the final map using the ROI
            ROI = self.roi[:]
            if ROI[2] < -90.0: ROI[2] = -90.0
            if ROI[3] >  90.0: ROI[3] =  90.0
            odims = [ (ROI[3]-ROI[2])/reso[0] , (ROI[1]-ROI[0])/reso[1] ]
            ogrid = cdms2.createUniformGrid( ROI[2], odims[0], reso[0], ROI[0], odims[1], reso[1] )
            ovar = var.regrid(ogrid, regridTool='regrid2')
            
            # replace outlier numbers
            d = ovar.data
            d[d==1e+20] = d[d<>1e+20].max()
            
            img = vtkUtil.vtkImageImportFromArray()
            img.SetArray(ovar.data)
            img.Update()
            
        except Exception:
            print>>sys.stderr, "Error building Outline Map"
            traceback.print_exc()
            return None
        
        # convert to vtkImageData       
        return img.GetOutput()
    
    def updateContourDensity(self):
        if self.generateContours:
            rangeBounds = self.getRangeBounds(1)
            self.contours.GenerateValues( self.NumContours, rangeBounds[0], rangeBounds[1] )
            self.contours.Modified()
            self.render()
        
    def onSlicerLeftButtonPress( self, caller, event ):
        self.currentButton = self.LEFT_BUTTON   
        return 0

    def onSlicerRightButtonPress( self, caller, event ):
        self.currentButton = self.RIGHT_BUTTON
        return 0

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
                
    def updateModule(self, **args ):
        primaryInput = self.input()
        contour_ispec = self.getInputSpec(  1 )       
        contourInput = contour_ispec.input() if contour_ispec <> None else None
        if self.planeWidgetX <> None: self.planeWidgetX.SetInput( primaryInput, contourInput )         
        if self.planeWidgetY <> None: self.planeWidgetY.SetInput( primaryInput, contourInput )         
        if self.planeWidgetZ <> None: self.planeWidgetZ.SetInput( primaryInput, contourInput ) 
        if self.baseMapActor: self.baseMapActor.SetVisibility( int( self.enableBasemap ) )
        self.render()
#        self.set3DOutput()
           
    def TestObserver( self, caller=None, event = None ):
        print " Volume Slicer TestObserver: event = %s, " % ( event )
        
    def getAxes(self):
        pass
    
    def getLayerColor( self, type ):
        if type == 'coastline':
            return ( 0, 0, 0 )
        if type == 'countries':
            return ( 0.7, 0.2, 0.2 )
        if type == 'states':
            return ( 0.5, 0.5, 0.3 )
        if type == 'lakes':
            return ( 0, 0, 0.6 )
        return ( 0, 0, 0 )
    
    def createBasemapPolyline( self, type, **args ):
        ispec = self.getInputSpec(0)  
        md = ispec.getMetadata()
        latLonGrid = md.get( 'latLonGrid', True )
        if latLonGrid:
            line_specs = self.basemapLineSpecs.get( type, None )
            thickness = int( round( line_specs[0] ) ) if line_specs else 0
            density = int( round( line_specs[1] ) ) if line_specs else 1
            resTypes = [ "invisible", "low", "medium", "high" ]
            if (thickness > 0) and ( density > 0 ):
                rgb=self.getLayerColor( type ) 
                textFilePath = os.path.join( os.path.dirname(__file__), "data", type, "index.txt" )
                s=shapeFileReader()
                s.setColors(rgb)
                s.setWidth( thickness )
                polys=s.getPolyLines( self.roi, textFilePath, resTypes[ density ] )        
                self.renderer.AddActor(polys)
                origin = self.planeWidgetZ.GetOrigin()
                pos = polys.GetPosition()
                pos1 = [ pos[0], pos[1], origin[2] ]
                polys.SetPosition( pos1 )
                polys_list = self.shapefilePolylineActors.get( type, [ None, None, None, None, None ] ) 
                polys_list[ density ] = polys
                self.shapefilePolylineActors[ type ] = polys_list
        
    def ProcessIPWAction( self, caller, event, **args ):
        action = args.get( 'action', caller.State )
        iAxis = caller.PlaneIndex

        if event == ImagePlaneWidget.InteractionUpdateEvent:
            
            if action == ImagePlaneWidget.Cursoring:   
                if not self.isSlicing:
                    self.isSlicing = True
                ispec = self.inputSpecs[ 0 ] 
                cursor_data = caller.GetCursorData()
                image_value = cursor_data[3] 
                cpos = cursor_data[0:3]     
                dataValue = ispec.getDataValue( image_value )
                wpos = ispec.getWorldCoords( cpos )
                if self.generateContours:
                    contour_image_value = cursor_data[4]
                    if  contour_image_value:
                        contour_value = self.getDataValue( contour_image_value, 1 )
                        contour_units = self.getUnits(1)
                        textDisplay = " Position: (%s, %s, %s), Value: %.3G %s, Contour Value: %.3G %s" % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units, contour_value, contour_units )
                    else:
                        textDisplay = " Position: (%s, %s, %s), Value: %.3G %s" % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units )
#                        print " >>>>> Current Image Value: %d %d, contour value: %.3G, pos = %s " % ( image_value, contour_image_value,  contour_value, str(cpos) ) # , str(wpos) )
                else:
                    textDisplay = " Position: (%s, %s, %s), Value: %.3G %s." % ( wpos[0], wpos[1], wpos[2], dataValue, ispec.units )
#                    print " >>>>> Current Image Value: %d,  pos = %s " % ( image_value, str(cpos) ) # , str(wpos) )
                sliceIndex = caller.GetSliceIndex() 
                self.slicePosition[iAxis] = sliceIndex
                self.updateTextDisplay( textDisplay )
                
                coord = ispec.getWorldCoordsAsFloat(cpos)
                screenPos = caller.GetCurrentScreenPosition()
                self.updateLensDisplay(screenPos, coord)
                
            if action == ImagePlaneWidget.Pushing: 
                ispec = self.inputSpecs[ 0 ] 
                if not self.isSlicing:
                    self.isSlicing = True 
                sliceIndex = caller.GetSliceIndex() 
                axisName, spos = ispec.getWorldCoord( sliceIndex, iAxis, True )
                textDisplay = " %s = %s ." % ( axisName, spos )
                if iAxis == 0:
                    p1 = caller.GetPoint1()
#                    print " >++++++++++++++++++> Slicing: Set Slice[%d], index=%d, pos=%.2f, " % ( iAxis, sliceIndex, p1[0] ), textDisplay
                self.slicePosition[ iAxis ] = sliceIndex                  
                self.updateTextDisplay( textDisplay ) 

                if (iAxis == 2):              
                    origin = caller.GetOrigin()
                    for type in ( 'coastline', 'countries', 'states', 'lakes' ): 
                        line_specs = self.basemapLineSpecs.get( type, None )
                        polys_list = self.shapefilePolylineActors.get( type, None )
                        density = int( round( line_specs[1] ) ) if line_specs else 1
                        polys = polys_list[ density ] if polys_list else None
                        if polys:
                            pos = polys.GetPosition()
                            pos1 = [ pos[0], pos[1], origin[2] ]
                            polys.SetPosition( pos1 )
            
                if self.generateContours:
                    slice_data = caller.GetReslice2Output()
                    if slice_data:
                        slice_data.Update()    
                        iextent =  slice_data.GetExtent()            
                        ispacing =  slice_data.GetSpacing()            
                        self.contours.SetInput( slice_data )
                        self.contours.Modified()
                        origin = caller.GetOrigin()
                        contourLineActor = self.getContourActor( iAxis )
                        contourLineActor.SetPosition( origin[0], origin[1], origin[2] )
        #                contourLineActor.SetOrigin( origin[0], origin[1], origin[2] )
                        self.setVisibleContour( iAxis )
#                print " Generate Contours, data dims = %s, origin = %s, pos = %s, extent = %s" % ( str( slice_data.GetDimensions() ), str(slice_data.GetOrigin()), str(origin), str(slice_data.GetExtent()) )
                
            self.render()
#                print " Generate Contours, data dims = %s, pos = %s %s %s " % ( str( slice_data.GetDimensions() ), str(pos1), str(pos2), str(origin) )

    def setContourActorOrientation( self, iAxis, contourLineActor ):
        if iAxis == 1: 
            contourLineActor.SetOrientation(90,0,0)
        elif iAxis == 0: 
            contourLineActor.SetOrientation(90,0,90)   

    def updateContourActorOrientations( self ):
        for contourLineActorItem in self.contourLineActors.items():
            if contourLineActorItem[1].GetVisibility( ): 
                self.setContourActorOrientation( contourLineActorItem[0], contourLineActorItem[1] )
        self.render()
        pass

                                     
    def getContourActor( self, iAxis, **args ):
        contourLineActor = self.contourLineActors.get( iAxis, None )
        if contourLineActor == None:
            contourLineActor = vtk.vtkActor()
            contourLineActor.SetMapper(self.contourLineMapperer)
            contourLineActor.GetProperty().SetLineWidth(2)     
            self.renderer.AddActor( contourLineActor ) 
            self.contourLineActors[iAxis] = contourLineActor
            self.setContourActorOrientation( iAxis, contourLineActor )
#            print " GetContourActor %d, origin = %s, position = %s " % ( iAxis, str( contourLineActor.GetOrigin() ), str( contourLineActor.GetPosition() ) )
        return contourLineActor

            
    def setVisibleContour( self, iAxis ):
        for contourLineActorItem in self.contourLineActors.items():
            if iAxis == contourLineActorItem[0]:    contourLineActorItem[1].VisibilityOn( )
            else:                                   contourLineActorItem[1].VisibilityOff( )
       
    def getAdjustedSliceExtent( self ):
        ext = None
        if self.iOrientation == 1:      ext = [ 0, self.sliceOutputShape[1]-1,  0, self.sliceOutputShape[0]-1, 0, 0 ]  
        else:                           ext = [ 0, self.sliceOutputShape[0]-1,  0, self.sliceOutputShape[1]-1, 0, 0 ]  
#        print " Slice Extent = %s " % str( ext )
        return ext       

    def getAdjustedSliceSpacing( self, outputData ):
        padded_extent = outputData.GetWholeExtent()
        padded_shape = [ padded_extent[1]-padded_extent[0]+1, padded_extent[3]-padded_extent[2]+1, 1 ]
        padded_spacing = outputData.GetSpacing()
        scale_factor = [ padded_shape[0]/float(self.sliceOutputShape[0]), padded_shape[1]/float(self.sliceOutputShape[1]) ]
        if self.iOrientation == 1:      spacing = [ padded_spacing[1]*scale_factor[1], padded_spacing[0]*scale_factor[0], 1.0 ]
        else:                           spacing = [ padded_spacing[0]*scale_factor[0], padded_spacing[1]*scale_factor[1], 1.0 ]
#        print " Slice Spacing = %s " % str( spacing )
        return spacing
                       
    def initColorScale( self, caller, event ): 
        x, y = caller.GetEventPosition()
        self.ColorLeveler.startWindowLevel( x, y )

    def scaleColormap( self, ctf_data, cmap_index=0, **args ):
        ispec = self.inputSpecs.get( cmap_index, None )
        if ispec and ispec.input(): 
            colormapManager = self.getColormapManager( index=cmap_index )
#            if not colormapManager.matchDisplayRange( ctf_data ):
            imageRange = self.getImageValues( ctf_data[0:2], cmap_index ) 
            colormapManager.setScale( imageRange, ctf_data )
            if self.contourLineMapperer: 
                self.contourLineMapperer.Modified()
            ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } )
#            print '-'*50
#            print " Volume Slicer[%d]: Scale Colormap: ( %.4g, %.4g ) " % ( self.moduleID, ctf_data[0], ctf_data[1] )
#            print '-'*50
                
    def finalizeLeveling( self, cmap_index=0 ):
        ispec = self.inputSpecs[ cmap_index ] 
        ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
#            self.updateSliceOutput()

    def initializeConfiguration( self, cmap_index=0, **args ):
        ispec = self.inputSpecs[ cmap_index ] 
        for configFunct in self.configurableFunctions.values():
            configFunct.init( ispec, **args )
        ispec.addMetadata( { 'colormap' : self.getColormapSpec(), 'orientation' : self.iOrientation } ) 
#        self.updateSliceOutput()

    def updateColorScale( self, caller, event ):
        x, y = caller.GetEventPosition()
        wsize = self.renderer.GetSize()
        range = self.ColorLeveler.windowLevel( x, y, wsize )
        return range

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
        alt = ( keysym.lower().find('alt') == 0 )
        ctrl = caller.GetControlKey() 
        shift = caller.GetShiftKey() 
#        print " -- Key Press: %c ( %d: %s ), ctrl: %s, shift: %s, alt: %s, event = %s " % ( key, ord(key), str(keysym), bool(ctrl), bool(shift), bool(alt), str( event ) )
#        if ( key == 'x' ): 
#            self.planeWidgetX.SetPlaneOrientationToXAxes() 
#            self.planeWidgetX.SetSliceIndex( 0 ) #self.slicePosition[0] )
#            self.render()      
#        elif ( key == 'y' ):  
#            self.planeWidgetY.SetPlaneOrientationToYAxes()
#            self.planeWidgetY.SetSliceIndex( 0 ) #self.slicePosition[1] )
#            self.render()       
#        elif ( key == 'z' ):  
#            self.planeWidgetZ.SetPlaneOrientationToZAxes()
#            self.planeWidgetZ.SetSliceIndex( 0 ) #self.slicePosition[2] )
#            self.render() 


