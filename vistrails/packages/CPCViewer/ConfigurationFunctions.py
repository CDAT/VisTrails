'''
Created on May 9, 2014

@author: tpmaxwel
'''
import sys, vtk, cdms2, traceback, os, cdtime, cPickle 
from StringIO import StringIO
import numpy as np
import inspect
from weakref import WeakSet, WeakKeyDictionary

POS_VECTOR_COMP = [ 'xpos', 'ypos', 'zpos' ]
SLICE_WIDTH_LR_COMP = [ 'xlrwidth', 'ylrwidth', 'zlrwidth' ]
SLICE_WIDTH_HR_COMP = [ 'xhrwidth', 'yhrwidth', 'zhrwidth' ]

def makeList( obj, minSize = 1 ):
    if obj == None: return None
    if isinstance( obj, tuple ): obj = list( obj ) 
    if not isinstance( obj, list ): obj = [ obj ]
    if ( len( obj ) == 1 ) and minSize > 1:
        obj = obj*minSize
#    assert len(obj) == minSize, "Wrong number of elements in list" 
    return obj

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

class ConfigManager:
    
    def __init__( self,  **args ): 
        self.ConfigCmd = SIGNAL("ConfigCmd")
        self.cfgFile = None
        self.cfgDir = None
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

    def addParameter( self, config_name, **args ):
        cparm = ConfigParameter.getParameter( config_name, **args )
        categoryName = args.get('category', None )
        varname = args.get('varname', None )
        key_tok = [] 
        if categoryName: key_tok.append( categoryName )
        key_tok.append( config_name )
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
        for config_item in self.config_params.items():
            self.ConfigCmd( ( "InitParm",  config_item[0], config_item[1] ) )

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
    
    def __init__(self, name, **args ):
        self.name = name 
        self.ValueChanged = SIGNAL( 'ValueChanged' )
        self.varname = args.get( 'varname', name ) 
        self.ptype = args.get( 'ptype', name ) 
        self.values = args
        self.valueKeyList = list( args.keys() )
        self.scaling_bounds = None

    @staticmethod
    def getParameter( config_name, **args ):
        ctype = args.get('ctype') 
        return ConfigParameter( config_name, **args )
     
    def __str__(self):
        return " ConfigParameter[%s]: %s " % ( self.name, str( self.values ) )
   
    def addValueKey( self, key ):
        if not (key in self.valueKeyList):
            self.valueKeyList.append( key ) 
                                
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


class ConfigurableFunction:
    
    CfgManager = ConfigManager() 
    ConfigurableFunctions = {}    
    
    def __init__( self, name, key=None, **args ):
        self.name = name
        self.persist = args.get( 'persist', True )
        self.value = self.CfgManager.addParameter( name, **args )
        self.type = 'generic'
        self.kwargs = args
        self.label = args.get( 'label', self.name )
        self.units = args.get( 'units', '' ).strip().lower()
        self.key = key
#        self.group = args.get( 'group', ConfigGroup.Display )  
        self.sliderLabels = makeList( args.get( 'sliderLabels', [ 'Range Min', 'Range Max' ] ) )
        self.active = args.get( 'active', True )
        self._persisted = True
        self.interactionHandler = args.get( 'interactionHandler', None )

    @classmethod
    def activate( cls ):
        cls.CfgManager.initParameters()
        
    def processInteractionEvent( self, args ):
        if self.interactionHandler:
            self.interactionHandler( args, self )
                        
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
        self.value.setValue( new_parameter_value )
        
    def postInstructions( self, message ):
        print "\n ----- %s -------\n" % message
             
    def matches( self, key ):
        return self.active and ( self.key == key )
    
    def applyParameter( self, **args ):
        pass
            
    def getHelpText( self ):
        return "<tr>   <td>%s</td>  <td>%s</td> <td>%s</td> </tr>\n" % ( self.key, self.label, self.type )
        
class ConfigurableSliderFunction( ConfigurableFunction ):

    def __init__( self, name, key=None, **args ):
        ConfigurableFunction.__init__( self, name, key, **args  )
        self.StartSlidingSignal =SIGNAL('startSliding')
        self.UpdateSlidingSignal =SIGNAL('updateSliding')
        self.type = 'slider'
        self.label = self.label
        self.initial_value = makeList( args.get( 'initValue', None ), len( self.sliderLabels ) )
        self.range_bounds = args.get( 'range_bounds', None )
        
   
