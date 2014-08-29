'''
Created on May 9, 2014

@author: tpmaxwel
'''

import sys, vtk, cdms2, traceback, os, cdtime, cPickle 
from StringIO import StringIO
import numpy as np
import inspect
from weakref import WeakSet, WeakKeyDictionary

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

class ConfigParameter:
    
    def __init__(self, name, **args ):
        self.name = name 
        self.ValueChanged = SIGNAL( 'ValueChanged' )
        self.varname = args.get( 'varname', name ) 
        self.ptype = args.get( 'ptype', name ) 
        self.values = args
        self.valueKeyList = list( args.keys() )
        self.scaling_bounds = None
     
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


class ConfigurationHandler:
    
    def __init__(self, name, key, **args ): 
        self.parameter = ConfigParameter( name, **args ) 
        self.type = 'generic'
        self.label = args.get( 'label', self.name )
        self.units = args.get( 'units', '' ).strip().lower()
#        self.group = args.get( 'group', ConfigGroup.Display )  
        self.key = key
        
    def processConfigEvent( self, args ):
        if args[0] == "InitConfig":
            self.init( args[1:])
        elif args[0] == "StartConfig":
            self.start( args[1:])
        elif args[0] == "EndConfig":
            self.end( args[1:])
        elif args[0] == "UpdateConfig":
            self.update( args[1:])
        elif args[0] == "ClearConfig":
            self.clear( args[1:])
            
    def init( self, args ):
        pass

    def start( self, args ):
        pass

    def end( self, args ):
        pass

    def update( self, args ):
        pass

    def clear( self, args ):
        pass
    
    
class CPCConfigurationHandler:
    
    def __init__(self, name, key, **args ): 
        ConfigurationHandler.__init__(self, name, key, **args )
    
    
    
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
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
      
