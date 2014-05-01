'''
Created on Apr 29, 2014

@author: tpmaxwel
'''

import sys, vtk, cdms2, traceback, os, cdtime, cPickle 
from StringIO import StringIO
import numpy as np
import inspect
from weakref import WeakSet, WeakKeyDictionary

class SIGNAL(object):
    
    def __init__( self, name = None ):
        self._functions = WeakSet()
        self._methods = WeakKeyDictionary()
        self._name = name

    def __call__(self, *args, **kargs):
        # Call handler functions
        for func in self._functions:
            func(*args, **kargs)

        # Call handler methods
        for obj, funcs in self._methods.items():
            for func in funcs:
                func(obj, *args, **kargs)

    def connect(self, slot):
        if inspect.ismethod(slot):
            if slot.__self__ not in self._methods:
                self._methods[slot.__self__] = set()

            self._methods[slot.__self__].add(slot.__func__)

        else:
            self._functions.add(slot)

    def disconnect(self, slot):
        if inspect.ismethod(slot):
            if slot.__self__ in self._methods:
                self._methods[slot.__self__].remove(slot.__func__)
        else:
            if slot in self._functions:
                self._functions.remove(slot)

    def clear(self):
        self._functions.clear()
        self._methods.clear()

POS_VECTOR_COMP = [ 'xpos', 'ypos', 'zpos' ]
SLICE_WIDTH_LR_COMP = [ 'xlrwidth', 'ylrwidth', 'zlrwidth' ]
SLICE_WIDTH_HR_COMP = [ 'xhrwidth', 'yhrwidth', 'zhrwidth' ]

def extract_arg( args, argname, **kwargs ):
    target = kwargs.get( 'defval', None )
    offset = kwargs.get( 'offset', 0 )
    for iArg in range( offset, len(args) ):
        if args[iArg] == argname:
            target = args[iArg+1]
    return target

def deserialize_value( sval ):
    if isinstance( sval, float ): 
        return sval
    try:
        return int(sval)
    except ValueError:
        try:
            return float(sval)
        except ValueError:
            return sval

def get_value_decl( val ):
    if isinstance( val, bool ): return "bool"
    if isinstance( val, int ): return "int"
    if isinstance( val, float ): return "float"
    return "str"

class ConfigurationInterface:
    
    ConfigCmd = SIGNAL("ConfigCmd")
    GuiCmd = SIGNAL("GuiCmd")

    def __init__(self, **args ):    
        self.metadata = args.get( 'metadata', {} )
        defvar = args.get( 'defvar', {} )
        self.cfgManager = ConfigManager( defvar=defvar ) 
        callback = args.get( 'callback', None )
        if callback: self.cfgManager.ConfigCmd.connect( callback )       
        
    def newSubset( self, indices ):
        for ctrl in self.tagged_controls:
            ctrl.newSubset( indices )
        
    def activate(self):
        self.cfgManager.initParameters()
#        self.configContainer.selectCategory( self.iSubsetCatIndex )
                           
    def build( self, **args ):
        init_roi = args.get( 'roi', ( 0, -90, 360, 90 ) )
        defvar = self.cfgManager.getMetadata( 'defvar' )
        self.iColorCatIndex = self.addCategory( 'Color' )
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=1, Stereo=0, Colorbar=0  )             
        self.iSubsetCatIndex = self.addCategory( 'Subsets' )
        cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
        var_rec = self.metadata[ defvar ]
        vrange = var_rec[2]
        thresh_cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Threshold Range", rmin=vrange[0], rmax=vrange[1], ctype = 'Leveling', varname=defvar )        
        roi_cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "ROI", roi=init_roi  )
        op_cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Opacity Scale", rmin=0.0, rmax=1.0, ctype = 'Range'  )               
        self.iPointsCatIndex = self.addCategory( 'Points' )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
        self.GeometryCatIndex = self.addCategory( 'Geometry' )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
        vertical_vars = args.get( 'vertical_vars', [] )
        vertical_vars.insert( 0, "Levels" )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = vertical_vars, init_index=0  )
        self.AnalysisCatIndex = self.addCategory( 'Analysis' )
        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "Animation" )
        
    def saveConfig(self):
        self.cfgManager.saveConfig()
        
    def addCategory(self, cat_name ):
        return self.cfgManager.addCategory( cat_name )

class ConfigManager:
    ConfigCmd = SIGNAL("ConfigCmd")
    
    def __init__( self, controller=None, **args ): 
        self.cfgFile = None
        self.cfgDir = None
        self.controller = controller
        self.config_params = {}
        self.iCatIndex = 0
        self.cats = {}
        self.metadata = args
        
    def getMetadata(self, key=None ):
        return self.metadata.get( key, None ) if key else self.metadata

    def addParam(self, key ,cparm ):
        self.config_params[ key ] = cparm
#        print "Add param[%s]" % key
                     
    def saveConfig( self ):
        try:
            f = open( self.cfgFile, 'w' )
            for config_item in self.config_params.items():
                cfg_str = " %s = %s " % ( config_item[0], config_item[1].serialize() )
                f.write( cfg_str )
            f.close()
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile

    def addParameter( self, iCatIndex, config_name, **args ):
        categoryName = self.controller.getCategoryName( iCatIndex ) if self.controller else self.cats[ iCatIndex ]
        cparm = ConfigParameter.getParameter( config_name, **args )
        varname = args.get('varname', None )
        key_tok = [ categoryName, config_name ]
        if varname: key_tok.append( varname )
        self.addParam( ':'.join( key_tok ), cparm )
        return cparm

    def readConfig( self ):
        try:
            f = open( self.cfgFile, 'r' )
            while( True ):
                config_str = f.readline()
                if not config_str: break
                cfg_tok = config_str.split('=')
                parm = self.config_params.get( cfg_tok[0].strip(), None )
                if parm: parm.initialize( cfg_tok[1] )
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile                       
        
    def initParameters(self):
        if not self.cfgDir:
            self.cfgDir = os.path.join( os.path.expanduser( "~" ), ".cpc" )
            if not os.path.exists(self.cfgDir): 
                os.mkdir(  self.cfgDir )
        if not self.cfgFile:
            self.cfgFile = os.path.join( self.cfgDir, "cpcConfig.txt" )
        else:
            self.readConfig()            
        emitter = self.controller if self.controller else self
        for config_item in self.config_params.items():
            emitter.ConfigCmd( ( "InitParm",  config_item[0], config_item[1] ) )

    def getParameterPersistenceList(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            cfg_spec = cfg_item[1].pack()
            plist.append( ( key, cfg_spec[1] ) )
        return plist

    def initialize( self, parm_name, parm_values ):
        if not ( isinstance(parm_values,list) or isinstance(parm_values,tuple) ):
            parm_values = [ parm_values ]
        cfg_parm = self.config_params.get( parm_name, None )
        if cfg_parm: cfg_parm.unpack( parm_values )

    def getPersistentParameterSpecs(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            values_decl = cfg_item[1].values_decl()
            plist.append( ( key, values_decl ) )
        return plist
    
    def addCategory(self, cat_name ):
        self.iCatIndex = self.iCatIndex + 1
        self.cats[ self.iCatIndex ] = cat_name
        return self.iCatIndex
       
class ConfigParameter:
    
    ValueChanged = SIGNAL( 'ValueChanged' )
    
    @staticmethod
    def getParameter( config_name, **args ):
        if args.get('ctype') == 'Leveling':
            return LevelingConfigParameter( config_name, **args )
        if args.get('ctype') == 'Range':
            return RangeConfigParameter( config_name, **args )
        else:
            return ConfigParameter( config_name, **args )

    def __init__(self, name, **args ):
        self.name = name 
        self.varname = args.get( 'varname', name ) 
        self.ptype = args.get( 'ptype', name ) 
        self.values = args
        self.valueKeyList = list( args.keys() )
     
    def __str__(self):
        return " ConfigParameter[%s]: %s " % ( self.name, str( self.values ) )
   
    def addValueKey( self, key ):
        if not (key in self.valueKeyList):
            self.valueKeyList.append( key ) 
    
    def values_decl(self):
        decl = []
        for key in self.valueKeyList:
            val = self.values.get( key, None )
            if ( val <> None ): decl.append( get_value_decl( val )  ) 
        return decl
                            
    def pack( self ):
        try:
            return ( self.ptype, [ str( self.values[key] ) for key in self.valueKeyList ] )
        except KeyError:
            print "Error packing parameter %s%s. Values = %s " % ( self.name, str(self.valueKeyList), str(self.values))

    def unpack( self, value_strs ):
        if len( value_strs ) <> len( self.values.keys() ): 
            print>>sys.stderr, " Error: parameter structure mismatch in %s ( %d vs %d )" % ( self.name,  len( value_strs ), len( self.values.keys() ) ); sys.stderr.flush()
        for ( key, str_val ) in zip( self.valueKeyList, value_strs ):
            self.values[key] = deserialize_value( str_val ) 
#        print " && Unpack parameter %s: %s " % ( self.name, str( self.values ) ); sys.stdout.flush()
            
    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values.get( key, None )

    def __setitem__(self, key, value ):
        self.values[key] = value 
        self.addValueKey( key )

    def __call__(self, **args ):
        self.values.update( args )
        args1 = [ self.ptype ]
        for item in args.items():
            args1.extend( list(item) )
            self.addValueKey( item[0] )
        args1.append( self.name )
        self.ValueChanged( args1 )
         
    def getName(self):
        return self.name

    def getVarName(self):
        return self.varname

    def getParameterType(self):
        return self.ptype
    
    def initialize( self, config_str ):
        self.values = eval( config_str )
        self.sort()

    def serialize( self ):
        return str( self.values )

    def getValue( self, key='value', default_value=None ):
        return self.values.get( key, default_value )

    def setValue( self, key, val, update=False  ):
        self.values[ key ] = val
        self.addValueKey( key )
        if update: 
            args1 = [  self.ptype, key, val, self.name]
            self.ValueChanged( args1 )

    def incrementValue( self, index, inc ):
        self.values[ index ] = self.values[ index ] + inc
        
class LevelingConfigParameter( ConfigParameter ):
    
    def __init__(self, name, **args ):
        ConfigParameter.__init__( self, name, **args ) 
        self.wposSensitivity = args.get( 'pos_s', 0.05 )
        self.wsizeSensitivity = args.get( 'width_s', 0.05 )
        self.normalized = True
        self.range_bounds = [ 0.0, 1.0 ]     
        if 'rmin' in args: 
            if (self.rmin <> 0) or (self.rmax <> 1):
                self.normalized = False 
                self.range_bounds = [ self['rmin'], self['rmax'] ]              
            self.computeWindow()
        else:               
            self.computeRange()
        self.scaling_bounds = None
        
    def setScaledRange( self, srange ):
        self.normalized = False 
        self.range_bounds = [ srange[0], srange[1] ]  
        self['rmin'] =  srange[0]           
        self['rmax'] =  srange[1]
        self.computeWindow()           
        
    @property
    def rmin(self):
        return self['rmin']

    @rmin.setter
    def rmin(self, value):
        self['rmin'] = value
        self.computeWindow()
        
    @property
    def rmax(self):
        return self['rmax']

    @rmax.setter
    def rmax(self, value):
        self['rmax'] = value
        self.computeWindow()

    @property
    def wpos(self):
        return self['wpos']

    @wpos.setter
    def wpos(self, value):
        self['wpos'] = value
        self.computeRange()  
        
    @property
    def wsize(self):
        return self['wsize']

    @wsize.setter
    def wsize(self, value):
        self['wsize'] = value
        self.computeRange()  
        
    def setScalingBounds( self, sbounds ):
        self.scaling_bounds = sbounds

    def shiftWindow( self, position_inc, width_inc ):
        if position_inc <> 0:
            self.wpos = self.wpos + position_inc * self.wposSensitivity
        if width_inc <> 0:
            if self.wsize < 2 * self.wsizeSensitivity:
                self.wsize = self.wsize *  2.0**width_inc 
            else:
                self.wsize = self.wsize + width_inc * self.wsizeSensitivity 
        self.computeRange() 
                     
    def computeRange(self):
        window_radius = self.wsize/2.0    
        rmin = self.wpos - window_radius # max( self.wpos - window_radius, 0.0 )
        rmax = self.wpos + window_radius # min( self.wpos + window_radius, 1.0 )
        self( rmin = rmin, rmax = rmax, name=self.varname ) # min( rmin, 1.0 - self.wsize ), rmax =  max( rmax, self.wsize ) )

    def computeWindow(self):
        wpos = ( self.rmax + self.rmin ) / 2.0
        wwidth = ( self.rmax - self.rmin ) 
        self( wpos = wpos, wsize = wwidth, name=self.varname ) # min( max( wpos, 0.0 ), 1.0 ), wsize = max( min( wwidth, 1.0 ), 0.0 ) )
        
    def getScaledRange(self):
        if self.scaling_bounds:
            ds = self.scaling_bounds[1] - self.scaling_bounds[0]
            return ( self.scaling_bounds[0] + self.rmin * ds, self.scaling_bounds[0] + self.rmax * ds )
        else:
            return self.getRange()

    
    def setWindowSensitivity(self, pos_s, width_s):
        self.wposSensitivity = pos_s
        self.wsizeSensitivity = width_s

    def setRange(self, range ):
        self.rmin = range[0] # min( max( range[0], 0.0 ), 1.0 )
        self.rmax = range[1] # max( min( range[1], 1.0 ), 0.0 )
        
    def setWindow( self, wpos, wwidth ):
        self.wpos =   wpos # min( max( wpos, 0.0 ), 1.0 )
        self.wsize =  wwidth #     max( min( wwidth, 1.0 ), 0.0 )      
        self.ValueChanged( ( self.ptype, 'rmin', self.rmin, 'rmax', self.rmax, 'name', self.varname ) )

    def getWindow(self):
        return ( self.wpos, self.wsize )

    def getRange( self ):
        return ( self.rmin, self.rmax )

    def getNormalizedRange( self ):
        if self.normalized:
            return ( self.rmin, self.rmax )
        else:
            rb = ( self.range_bounds[1] - self.range_bounds[0] )
            return [ ( self.rmin - self.range_bounds[0] ) / rb, ( self.rmax - self.range_bounds[0] ) / rb ]
            
            
            
class RangeConfigParameter( ConfigParameter ):
    
    def __init__(self, name, **args ):
        ConfigParameter.__init__( self, name, **args ) 
        self.scaling_bounds = None
        
    @property
    def rmin(self):
        return self['rmin']

    @rmin.setter
    def rmin(self, value):
        self['rmin'] = value
        
    @property
    def rmax(self):
        return self['rmax']

    @rmax.setter
    def rmax(self, value):
        self['rmax'] = value
        
    def setScalingBounds( self, sbounds ):
        self.scaling_bounds = sbounds
        
    def getScaledRange(self):
        if self.scaling_bounds:
            ds = self.scaling_bounds[1] - self.scaling_bounds[0]
            return ( self.scaling_bounds[0] + self.rmin * ds, self.scaling_bounds[0] + self.rmax * ds )
        else:
            return self.getRange()

    def setRange(self, range ):
        self.rmin = range[0] # min( max( range[0], 0.0 ), 1.0 )
        self.rmax = range[1] # max( min( range[1], 1.0 ), 0.0 )
        
    def getRange( self ):
        return ( self.rmin, self.rmax )

def CheckAbort(obj, event):
    if obj.GetEventPending() != 0:
        obj.SetAbortRender(1)

def getClassName( instance ):
    return instance.__class__.__name__ if ( instance <> None ) else "None" 

class PlotType:
    Planar = 0
    Spherical = 1
    List = 0
    Grid = 1
    LevelAliases = [ 'isobaric', "layers", "interfaces" ]
    
    @classmethod
    def validCoords( cls, lat, lon ):
        return ( id(lat) <> id(None) ) and ( id(lon) <> id(None) )
    
    @classmethod
    def isLevelAxis( cls, pid ):
        lname = pid.lower()
        if ( lname.find('lev')  >= 0 ): return True
        if ( lname.find('bottom') >= 0 ) and ( lname.find('top') >= 0 ): return True
        if pid in cls.LevelAliases: return True
        if lname in cls.LevelAliases: return True
        return False    

    @classmethod
    def getPointsLayout( cls, grid ):
        if grid <> None:
            if (grid.__class__.__name__ in ( "RectGrid", "FileRectGrid") ): 
                return cls.Grid
        return cls.List  


def getBool( val ):
    if isinstance( val, str ):
        if( val.lower()[0] == 't' ): return True
        if( val.lower()[0] == 'f' ): return False
        try:    val = int(val)
        except: pass
    return bool( val )
    
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
    
class ConfigurableFunction:
    
    ConfigurableFunctions = {}    
    
    def __init__( self, name, key=None, **args ):
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

class QtWindowLeveler:
    
    UpdateRangeSignal = SIGNAL('updateRange')
    
    WindowRelative = 0
    BoundsRelative = 1
    Absolute = 2
   
    def __init__( self, **args ):
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
        self.UpdateRangeSignal.connect( observer )

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
              self.UpdateRangeSignal( result )
            
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
              self.UpdateRangeSignal( result )
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
        self.UpdateRangeSignal( result )

        return result

    def setWindowLevelFromRange( self, range ):
        self.CurrentWindow = ( range[1] - range[0] ) / self.scaling
        self.CurrentLevel = ( range[1] + range[0] ) / ( 2 * self.scaling )
        
class WindowRefinementGenerator():

    def __init__( self, **args ):
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
    StartLevelingSignal =SIGNAL('startLeveling')
    UpdateLevelingSignal =SIGNAL('updateLeveling')
    
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
            self.widget.UpdateSignal.connect( self.broadcastLevelingData ) # self.connect( self.widget, QSIGNAL('update(QString)'), self.broadcastLevelingData )

#        print "    ***** Init Leveling Parameter: %s, initial range = %s" % ( self.name, str(self.range) )
        
    def startLeveling( self, x, y ):
#        if self.altMode:    self.windowRefiner.initRefinement( [ x, y ], self.range[3:5] )   
#        else:               
        self.windowLeveler.startWindowLevel( x, y )
        self.updateActiveFunctionList()
        self.adjustRangeInput = -1
        self.StartLevelingSignal()
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
        if self.altMode:
            refinement_range = self.windowRefiner.updateRefinement( [ x, y ], wsize )
            for iR in [ 0, 1 ]: self.range[3+iR] = refinement_range[iR]
        else:  
            leveling_range = self.windowLeveler.windowLevel( x, y, wsize )
            for iR in [ 0, 1 ]: self.range[iR] = bound( leveling_range[iR], self.range_bounds ) if self.boundByRange else leveling_range[iR]
        self.UpdateLevelingSignal()
        rv = self.broadcastLevelingData( )
        return rv
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
        active_module_list = args.get( 'active_modules', None )
        if (active_module_list == None) or (self.moduleID in active_module_list):
            self.setLevelDataHandler( self.range )
            self.persisted = False
            self.manuallyAdjusted = True
        for cfgFunction in self.activeFunctionList:
            if (active_module_list == None) or (cfgFunction.moduleID in active_module_list):
                if( cfgFunction.units == self.units ):
                    cfgFunction.setDataRange( self.range, True )
                else:
                    cfgFunction.setScaledDataRange( self.getScaledDataRange(), True )
        return self.range 
    
    

def getStringDataArray( name, values = [] ):
    array = vtk.vtkStringArray()
    array.SetName( name )
    for value in values:
        array.InsertNextValue( value )
    return array

def getMaxScalarValue( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return 65535.0
    if scalar_dtype == np.ubyte:
        return 255.0 
    if scalar_dtype == np.float32:
        f = np.finfo(np.float32) 
        return f.max
    if scalar_dtype == np.float64:
        f = np.finfo(np.float64) 
        return f.max
    return None

class CDMSDataType:
    Volume = 1
    Slice = 2
    Vector = 3
    Hoffmuller = 4
    ChartData = 5
    VariableSpace = 6
    Points = 7
    
    @classmethod
    def getName( cls, type ):
        if type == cls.Volume: return "volume"
        if type == cls.Points: return "points"
        if type == cls.Vector: return "vector"
        
def getItem( output, index = 0 ): 
    if not ( isinstance(output,list) or isinstance(output,tuple) ): return  output
    return output[ index ] 

def encodeToString( obj ):
    rv = None
    try:
        buffer = StringIO()
        pickler = cPickle.Pickler( buffer )
        pickler.dump( obj )
        rv = buffer.getvalue()
        buffer.close()
    except Exception, err:
        print>>sys.stderr, "Error pickling object %s: %s" % ( str(obj), str(err) )
    return rv

def decodeFromString( string_value, default_value=None ):
    obj = default_value
    try:
        buffer = StringIO( string_value )
        pickler = cPickle.Unpickler( buffer )
        obj = pickler.load()
        buffer.close()
    except Exception, err:
        print>>sys.stderr, "Error unpickling string %s: %s" % ( string_value, str(err) )
    return obj

def addr( obj ): 
    return '0' if (obj == None) else obj.GetAddressAsString( obj.__class__.__name__ )

def getRangeBounds( type_str ):
    if type_str == 'UShort':
        return [ 0, 65535, 1 ]
    if type_str == 'UByte':
        return [ 0, 255, 1 ] 
    if type_str == 'Float':
        f = np.finfo(float) 
        return [ -f.max, f.max, 1 ]
    return None

def getNewVtkDataArray( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return vtk.vtkUnsignedShortArray() 
    if scalar_dtype == np.ubyte:
        return vtk.vtkUnsignedCharArray() 
    if scalar_dtype == np.float32:
        return vtk.vtkFloatArray() 
    if scalar_dtype == np.float64:
        return vtk.vtkDoubleArray() 
    return None

def getDatatypeString( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return 'UShort' 
    if scalar_dtype == np.ubyte:
        return 'UByte' 
    if scalar_dtype == np.float32:
        return 'Float' 
    if scalar_dtype == np.float64:
        return 'Double' 
    return None

class OutputRecManager: 
    
    sep = ';#:|!'   
            
    def __init__( self, serializedData = None ): 
        self.outputRecs = {}
        if serializedData <> None:
            self.deserialize( serializedData )
            
    def deleteOutput( self, dsid, outputName ):
        orecMap =  self.outputRecs.get( dsid, None )
        if orecMap: del orecMap[outputName] 

    def addOutputRec( self, dsid, orec ): 
        orecMap =  self.outputRecs.setdefault( dsid, {} )
        orecMap[ orec.name ] = orec

    def getOutputRec( self, dsid, outputName ):
        orecMap =  self.outputRecs.get( dsid, None )
        return orecMap[ outputName ] if orecMap else None

    def getOutputRecNames( self, dsid  ): 
        orecMap =  self.outputRecs.get( dsid, None )
        return orecMap.keys() if orecMap else []

    def getOutputRecs( self, dsid ):
        orecMap =  self.outputRecs.get( dsid, None )
        return orecMap.values() if orecMap else []
    
class OutputRec:
    
    def __init__(self, name, **args ): 
        self.name = name
        self.varComboList = args.get( "varComboList", [] )
        self.levelsCombo = args.get( "levelsCombo", None )
        self.level = args.get( "level", None )
        self.varTable = args.get( "varTable", None )
        self.varList = args.get( "varList", None )
        self.varSelections = args.get( "varSelections", [] )
        self.type = args.get( "type", None )
        self.ndim = args.get( "ndim", 3 )
        self.updateSelections() 

    def getVarList(self):
        vlist = []
        for vrec in self.varList:
            vlist.append( str( getItem( vrec ) ) )
        return vlist
    
    def getSelectedVariableList(self):
        return [ str( varCombo.currentText() ) for varCombo in self.varComboList ]

    def getSelectedLevel(self):
        return str( self.levelsCombo.currentText() ) if self.levelsCombo else None
    
    def updateSelections(self):
        self.varSelections = []
        for varCombo in self.varComboList:
            varSelection = str( varCombo.currentText() ) 
            self.varSelections.append( [ varSelection, "" ] )

       
def getFloatStr( val ):
    if ( type(val) == type(' ') ): return val
    return "%.1f" % val

def extractMetadata( fieldData ):
    mdList = []
    inputVarList = []
    varlist = fieldData.GetAbstractArray( 'varlist' ) 
    if varlist == None:   # module.getFieldData() 
        print>>sys.stderr, " Can't get Metadata!" 
    else: 
        nvar = varlist.GetNumberOfValues()
        for vid in range(nvar):
            varName = str( varlist.GetValue(vid) )
            inputVarList.append( varName )
            dataVector = fieldData.GetAbstractArray( 'metadata:%s' % varName ) 
            if dataVector == None:  
                print>>sys.stderr, " Can't get Metadata for var %s!" % varName 
            else: 
                metadata = {}
                nval = dataVector.GetNumberOfValues()
                for id in range(nval):
                    enc_mdata = str( dataVector.GetValue(id) )
                    md = decodeFromString( enc_mdata )
                    metadata.update( md )
                mdList.append( metadata )
        for md in mdList: md['inputVarList'] = inputVarList
    return mdList 
            
def freeImageData( image_data ):
#     from packages.vtDV3D.vtUtilities import memoryLogger
#     memoryLogger.log("start freeImageData")
    pointData = image_data.GetPointData()
    for aIndex in range( pointData.GetNumberOfArrays() ):
 #       array = pointData.GetArray( aIndex )
        pointData.RemoveArray( aIndex )
#        if array:
#            name = pointData.GetArrayName(aIndex)            
#            print "---- freeImageData-> Removing array %s: %s" % ( name, array.__class__.__name__ )  
    fieldData = image_data.GetFieldData()
    for aIndex in range( fieldData.GetNumberOfArrays() ): 
        aname = fieldData.GetArrayName(aIndex)
        array = fieldData.GetArray( aname )
        if array:
            array.Initialize()
            fieldData.RemoveArray( aname )
    image_data.ReleaseData()
#    memoryLogger.log("finished freeImageData")
    
class DataCache():
    
    def __init__(self):
        self.data = {}
        self.cells = set()

class CachedImageData():
    
    def __init__(self, image_data, cell_coords ):
        self.data = image_data
        self.cells = set()
        self.cells.add( cell_coords )

def getRoiSize( roi ):
    if roi == None: return 0
    return abs((roi[2]-roi[0])*(roi[3]-roi[1]))

def getTitle( dsid, name, attributes, showUnits=False ):
       long_name = attributes.get( 'long_name', attributes.get( 'standard_name', name ) )
       if not showUnits: return "%s:%s" % ( dsid, long_name )
       units = attributes.get( 'units', 'unitless' )
       return  "%s:%s (%s)" % ( dsid, long_name, units )
   
def isDesignated( axis ):
    return ( axis.isLatitude() or axis.isLongitude() or axis.isLevel() or axis.isTime() )

def matchesAxisType( axis, axis_attr, axis_aliases ):
    matches = False
    aname = axis.id.lower()
    axis_attribute = axis.attributes.get('axis',None)
    if axis_attribute and ( axis_attribute.lower() in axis_attr ):
        matches = True
    else:
        for axis_alias in axis_aliases:
            if ( aname.find( axis_alias ) >= 0): 
                matches = True
                break
    return matches

class AxisType:
    NONE = 0
    Time = 1
    Longitude = 2
    Latitude = 3
    Level = 4
    lev_aliases = [ 'bottom', 'top', 'zdim' ]
    lev_axis_attr = [ 'z' ]
    lat_aliases = [ 'north', 'south', 'ydim' ]
    lat_axis_attr = [ 'y' ]
    lon_aliases = [ 'east', 'west', 'xdim' ]
    lon_axis_attr = [ 'x' ]

def getAxisType( axis ):
    if axis.isLevel() or matchesAxisType( axis, AxisType.lev_axis_attr, AxisType.lev_aliases ):
        return AxisType.Level      
    elif axis.isLatitude() or matchesAxisType( axis, AxisType.lat_axis_attr, AxisType.lat_aliases ):
        return AxisType.Latitude                   
    elif axis.isLongitude() or matchesAxisType( axis, AxisType.lon_axis_attr, AxisType.lon_aliases ):
        return AxisType.Longitude     
    elif axis.isTime():
        return AxisType.Time
    else: return  AxisType.NONE    

def designateAxisType( self, axis ):
    if not isDesignated( axis ):
        if matchesAxisType( axis, AxisType.lev_axis_attr, AxisType.lev_aliases ):
            axis.designateLevel() 
            return AxisType.Level         
        elif matchesAxisType( axis, AxisType.lat_axis_attr, AxisType.lat_aliases ):
            axis.designateLatitude() 
            return AxisType.Latitude                    
        elif matchesAxisType( axis, AxisType.lon_axis_attr, AxisType.lon_aliases ):
            axis.designateLongitude()
            return AxisType.Longitude    
    return getAxisType( axis )


class InputSpecs:
    
    def __init__( self, **args ):
        self.units = ''
        self.scalarRange = None
        self.seriesScalarRange = None
        self.rangeBounds = None
        self.referenceTimeUnits = None
        self.metadata = None
        self._input = None
        self.fieldData = None
        self.datasetId = None
        self.clipper = None
        self.dtype = None
        
    def isFloat(self):
        return self.dtype == "Float"

#     def selectInputArray( self, raw_input, plotIndex ):
#         self.updateMetadata( plotIndex )
#         old_point_data = raw_input.GetPointData()  
#         nArrays = old_point_data.GetNumberOfArrays() 
#         if nArrays == 1: return raw_input  
#         image_data = vtk.vtkImageData()
#         image_data.ShallowCopy( raw_input )
#         new_point_data = image_data.GetPointData()        
#         array_index = plotIndex if plotIndex < nArrays else 0
#         inputVarList = self.metadata.get( 'inputVarList', [] )
#         if array_index < len( inputVarList ):
#             aname = inputVarList[ array_index ] 
#             new_point_data.SetActiveScalars( aname )
# #            print "Selecting scalars array %s for input %d" % ( aname, array_index )
#         else:
#             print>>sys.stderr, "Error, can't find scalars array for input %d" % array_index
# #        print "Selecting %s (array-%d) for plot index %d" % ( aname, array_index, plotIndex)
#         return image_data
 
    def initializeInput( self, imageData, fieldData, plotIndex=0 ): 
        self._input =  imageData 
        self.fieldData = fieldData                          
        self.updateMetadata( plotIndex )
        
    def input( self ):
        if self.clipper:
            input = self.clipper.GetOutput()
            input.Update()
            return input
        return self._input
        
    def clipInput( self, extent ):
        self.clipper = vtk.vtkImageClip()
        self.clipper.AddInput( self._input )
        self.clipper.SetOutputWholeExtent( extent )

    def getWorldCoords( self, image_coords ):
        plotType = self.metadata[ 'plotType' ]                   
        world_coords = None
        try:
            if plotType == 'zyt':
                lat = self.metadata[ 'lat' ]
                lon = self.metadata[ 'lon' ]
                timeAxis = self.metadata[ 'time' ]
                tval = timeAxis[ image_coords[2] ]
                relTimeValue = cdtime.reltime( float( tval ), timeAxis.units ) 
                timeValue = str( relTimeValue.tocomp() )          
                world_coords = [ getFloatStr(lon[ image_coords[0] ]), getFloatStr(lat[ image_coords[1] ]), timeValue ]   
            else:         
                lat = self.metadata[ 'lat' ]
                lon = self.metadata[ 'lon' ]
                lev = self.metadata[ 'lev' ]
                world_coords = [ getFloatStr(lon[ image_coords[0] ]), getFloatStr(lat[ image_coords[1] ]), getFloatStr(lev[ image_coords[2] ]) ]   
        except:
            gridSpacing = self.input().GetSpacing()
            gridOrigin = self.input().GetOrigin()
            world_coords = [ getFloatStr(gridOrigin[i] + image_coords[i]*gridSpacing[i]) for i in range(3) ]
        return world_coords

    def getWorldCoordsAsFloat( self, image_coords ):
        plotType = self.metadata[ 'plotType' ]                   
        world_coords = None
        try:
            if plotType == 'zyt':
                lat = self.metadata[ 'lat' ]
                lon = self.metadata[ 'lon' ]
                timeAxis = self.metadata[ 'time' ]
                tval = timeAxis[ image_coords[2] ]
                relTimeValue = cdtime.reltime( float( tval ), timeAxis.units ) 
                timeValue = str( relTimeValue.tocomp() )          
                world_coords = [ lon[ image_coords[0] ], lat[ image_coords[1] ], timeValue ]   
            else:         
                lat = self.metadata[ 'lat' ]
                lon = self.metadata[ 'lon' ]
                lev = self.metadata[ 'lev' ]
                world_coords = [ lon[ image_coords[0] ], lat[ image_coords[1] ], lev[ image_coords[2] ] ]   
        except:
            gridSpacing = self.input().GetSpacing()
            gridOrigin = self.input().GetOrigin()
            world_coords = [ gridOrigin[i] + image_coords[i]*gridSpacing[i] for i in range(3) ]
        return world_coords
    
    def getWorldCoord( self, image_coord, iAxis, latLonGrid  ):
        plotType = self.metadata[ 'plotType' ] 
        if plotType == 'zyt':                  
            axisNames = [ 'Longitude', 'Latitude', 'Time' ] if latLonGrid else [ 'X', 'Y', 'Time' ]
        else:
            axisNames =  [ 'Longitude', 'Latitude', 'Level' ] if latLonGrid else [ 'X', 'Y', 'Level' ]
        try:
            axes = [ 'lon', 'lat', 'time' ] if plotType == 'zyt'  else [ 'lon', 'lat', 'lev' ]
            world_coord = self.metadata[ axes[iAxis] ][ image_coord ]
            if ( plotType == 'zyt') and  ( iAxis == 2 ):
                timeAxis = self.metadata[ 'time' ]     
                timeValue = cdtime.reltime( float( world_coord ), timeAxis.units ) 
                world_coord = str( timeValue.tocomp() )          
            return axisNames[iAxis], getFloatStr( world_coord )
        except:
            if (plotType == 'zyx') or (iAxis < 2):
                gridSpacing = self.input().GetSpacing()
                gridOrigin = self.input().GetOrigin()
                return axes[iAxis], getFloatStr( gridOrigin[iAxis] + image_coord*gridSpacing[iAxis] ) 
            return axes[iAxis], ""

    def getRangeBounds( self ):
        if self.dtype == "Float": 
            return self.scalarRange
        return self.rangeBounds  
        
    def getDataRangeBounds(self):
        if self.dtype == "Float":
            return self.scalarRange
        if self.rangeBounds:
            srange = self.getDataValues( self.rangeBounds[0:2] ) 
            if ( len( self.rangeBounds ) > 2 ): srange.append( self.rangeBounds[2] ) 
            else:                               srange.append( 0 )
        else: srange = [ 0, 0, 0 ]
        return srange
        
    def raiseModuleError( self, msg ):
        print>>sys.stderr, msg
        raise Exception( msg )

    def getDataValue( self, image_value):
        if self.isFloat(): return image_value
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        sval = ( float(image_value) - self.rangeBounds[0] ) / ( self.rangeBounds[1] - self.rangeBounds[0] )
        dataValue = valueRange[0] + sval * ( valueRange[1] - valueRange[0] ) 
#        print " GetDataValue(%.3G): valueRange = %s " % ( sval, str( valueRange ) )
        return dataValue
                
    def getDataValues( self, image_value_list ):
        if self.isFloat(): return image_value_list
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        dr = ( self.rangeBounds[1] - self.rangeBounds[0] )
        data_values = []
        for image_value in image_value_list:
            sval = 0.0 if ( dr == 0.0 ) else ( image_value - self.rangeBounds[0] ) / dr
            dataValue = valueRange[0] + sval * ( valueRange[1] - valueRange[0] ) 
            data_values.append( dataValue )
        return data_values

    def getImageValue( self, data_value ):
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        dv = ( valueRange[1] - valueRange[0] )
        sval = 0.0 if ( dv == 0.0 ) else ( data_value - valueRange[0] ) / dv 
        imageValue = self.rangeBounds[0] + sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
        return imageValue

    def getImageValues( self, data_value_list ):
        if self.isFloat(): return data_value_list
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        dv = ( valueRange[1] - valueRange[0] )
        imageValues = []
        for data_value in data_value_list:
            sval = 0.0 if ( dv == 0.0 ) else ( data_value - valueRange[0] ) / dv
            imageValue = self.rangeBounds[0] + sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
            imageValues.append( imageValue )
#        print "\n *****************  GetImageValues: data_values = %s, range = %s, imageValues = %s **************** \n" % ( str(data_value_list), str(self.scalarRange), str(imageValues) )
        return imageValues

    def scaleToImage( self, data_value ):
        if self.isFloat(): return data_value
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        dv = ( self.scalarRange[1] - self.scalarRange[0] )
        sval = 0.0 if ( dv == 0.0 ) else data_value / dv
        imageScaledValue =  sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
        return imageScaledValue

    def getMetadata( self, key = None ):
        return self.metadata.get( key, None ) if ( key and self.metadata )  else self.metadata
  
    def getFieldData( self ):
        if self.fieldData == None:
            print>>sys.stderr, ' Uninitialized field data being accessed in ispec[%x]  ' % id(self)  
            self.initializeMetadata()
        return self.fieldData  
    
    def updateMetadata( self, plotIndex ):
        if self.metadata == None:
            scalars = None
             
#            arr_names = [] 
#            na = self.fieldData.GetNumberOfArrays()
#            for iF in range( na ):
#                arr_names.append( self.fieldData.GetArrayName(iF) )
#            print " updateMetadata: getFieldData, arrays = ", str( arr_names ) ; sys.stdout.flush()
            
            if self.fieldData == None:
                print>>sys.stderr,  ' NULL field data in updateMetadata: ispec[%x]  ' % id(self)  
                self.initializeMetadata() 
    
            self.metadata = self.computeMetadata( plotIndex )
            
            if self.metadata <> None:
                self.rangeBounds = None              
                self.datasetId = self.metadata.get( 'datasetId', None )                
                tval = self.metadata.get( 'timeValue', 0.0 )
                self.referenceTimeUnits = self.metadata.get( 'timeUnits', None )
                self.timeValue = cdtime.reltime( float( tval ), self.referenceTimeUnits )               
                self.dtype =  self.metadata.get( 'datatype', None )
                scalars =  self.metadata.get( 'scalars', None )
                self.rangeBounds = getRangeBounds( self.dtype )
                title = self.metadata.get( 'title', None )
                if title:
                    targs = title.split(':')
                    if len( targs ) == 1:
                        self.titleBuffer = "\n%s" % ( title )
                    elif len( targs ) > 1:
                        self.titleBuffer = "%s\n%s" % ( targs[1], targs[0] )
                else: self.titleBuffer = "" 
                attributes = self.metadata.get( 'attributes' , None )
                if attributes:
                    self.units = attributes.get( 'units' , '' )
                    srange = attributes.get( 'range', None )
                    if srange: 
        #                print "\n ***************** ScalarRange = %s, md[%d], var_md[%d] *****************  \n" % ( str(range), id(metadata), id(var_md) )
                        self.scalarRange = list( srange )
                        self.scalarRange.append( 1 )
                        if not self.seriesScalarRange:
                            self.seriesScalarRange = list(srange)
                        else:
                            if self.seriesScalarRange[0] > srange[0]:
                                self.seriesScalarRange[0] = srange[0] 
                            if self.seriesScalarRange[1] < srange[1]:
                                self.seriesScalarRange[1] = srange[1] 

    def getUnits(self):
        return self.units
    
    def getLayerList(self):
        layerList = []
        pointData = self.input().GetPointData()
        for iA in range( pointData.GetNumberOfArrays() ):
            array_name = pointData.GetArrayName(iA)
            if array_name: layerList.append( array_name )
        return layerList
    
    def computeMetadata( self, plotIndex=0 ):
        if not self.fieldData: self.initializeMetadata() 
        if self.fieldData:
            mdList = extractMetadata( self.fieldData )
            if plotIndex < len(mdList):
                return mdList[ plotIndex ]
            else:
                try: return mdList[ 0 ]
                except: pass               
        print>>sys.stderr, "[%s]: Error, Metadata for input %d not found in ispec[%x]  "  % ( self.__class__.__name__,  plotIndex, id(self) )
        return {}
        
    def addMetadataObserver( self, caller, event ):
        fd = caller.GetOutput().GetFieldData()
        fd.ShallowCopy( self.fieldData )
        pass

    def initializeMetadata( self ):
        try:
            self.fieldData = vtk.vtkDataSetAttributes()
            mdarray = getStringDataArray( 'metadata' )
            self.fieldData.AddArray( mdarray )
#            diagnosticWriter.log( self, ' initialize field data in ispec[%x]  ' % id(self) )  
        except Exception, err:
            print>>sys.stderr, "Error initializing metadata"

    def addMetadata( self, metadata ):
        dataVector = self.fieldData.GetAbstractArray( 'metadata' ) 
        if dataVector == None:
            cname = getClassName( self ) 
            if cname <> "InputSpecs": print " Can't get Metadata for class %s " % cname
        else:
            enc_mdata = encodeToString( metadata )
            dataVector.InsertNextValue( enc_mdata  )

