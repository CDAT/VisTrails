'''
Created on Dec 9, 2010

@author: tpmaxwel
'''
import sys, vtk, StringIO, cPickle, time, os, ConfigParser, shutil
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.vistrail.vistrail import VersionAlreadyTagged
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from db.domain import DBModule, DBAnnotation
from core.db.action import create_action
from core.debug import DebugPrint
from PyQt4 import QtCore, QtGui
import numpy.core.umath as umath
# from vtk.util.vtkConstants import *
import numpy as np
packagePath = os.path.dirname( __file__ ) 
resourcePath = os.path.join( packagePath,  'resources')

VTK_CURSOR_ACTION       = 0
VTK_SLICE_MOTION_ACTION = 1
VTK_WINDOW_LEVEL_ACTION = 2

VTK_NO_MODIFIER         = 0
VTK_SHIFT_MODIFIER      = 1
VTK_CONTROL_MODIFIER    = 2        
VTK_BACKGROUND_COLOR = ( 1.0, 1.0, 1.0 )
VTK_FOREGROUND_COLOR = ( 0.0, 0.0, 0.0 )
VTK_TITLE_SIZE = 14
VTK_NOTATION_SIZE = 14
VTK_INSTRUCTION_SIZE = 24

# Some constants used throughout code

VTK_LARGE_FLOAT = 1.0e+38
VTK_LARGE_INTEGER = 2147483647 # 2^31 - 1

# These types are returned by GetDataType to indicate pixel type.
VTK_VOID            = 0
VTK_BIT             = 1
VTK_CHAR            = 2
VTK_SIGNED_CHAR     =15
VTK_UNSIGNED_CHAR   = 3
VTK_SHORT           = 4
VTK_UNSIGNED_SHORT  = 5
VTK_INT             = 6
VTK_UNSIGNED_INT    = 7
VTK_LONG            = 8
VTK_UNSIGNED_LONG   = 9
VTK_FLOAT           =10
VTK_DOUBLE          =11
VTK_ID_TYPE         =12

hyperwall_role = None 
currentTime = 0
# dvLogFile =  open( os.path.expanduser( '~/.vistrails/dv3d_log.txt' ), 'w' )
dvDbgIO = DebugPrint()
dvDbgIO.set_stream( sys.stderr )

EnableMemoryLogging = True

class MemoryLogger:
    def __init__( self, enabled = True ):
        self.logfile = None
        self.enabled = enabled
        
    def close(self):
        if self.logfile <> None: 
            self.logfile.close( )
            self.logfile = None
        
    def log( self, label ):
        import shlex, subprocess, gc
        if self.enabled:
            gc.collect()
            args = ['ps', 'u', '-p', str(os.getpid())]
            psout = subprocess.check_output( args ).split('\n')
            ps_vals = psout[1].split()
            try:
                mem_usage_MB = float( ps_vals[5] ) / 1024.0
                mem_usage_GB = mem_usage_MB / 1024.0
            except ValueError, err:
                print>>sys.stderr, "Error parsing psout: ", str(err)
                print>>sys.stderr, str(psout)
                return
                    
            if self.logfile == None:
                self.logfile = open( "/tmp/dv3d-memory_usage.log", 'w' )
            self.logfile.write(" %10.2f (%6.3f): %s\n" % ( mem_usage_MB, mem_usage_GB, label ) )
            self.logfile.flush()
        
memoryLogger = MemoryLogger( EnableMemoryLogging )        
        
def displayMessage( msg ):
    msgBox = QtGui.QMessageBox()
    msgBox.setText( msg )
    msgBox.exec_()
    
def get_coords_from_cell_address( row, col):
    try:
        col = ord(col)-ord('A')
        row = int(row)-1
        return ( col, row )
    except:
        raise Exception('ColumnRowAddress format error: %s ' % str( [ row, col ] ) )

#def dvLog( obj, msg ):
#    dvLogFile.write( '\n%s: %s' % ( obj.__class__.__name__, msg ) )
#    dvLogFile.flush( )

def bound( val, bounds ): return max( min( val, bounds[1] ), bounds[0] )

def str2f( data ): return "[ %s ]" % ( ", ".join( [ '%.2f' % value for value in data ] ) )

def flt2str( fval ): 
    aval = abs( fval )
    if ( fval == 0.0 ): return "0.0"
    if ( aval >= 1000000 ) or ( aval < 0.001 ): return ( "%.2e" % fval )
    if ( aval >= 1000 ): return ( "%.0f" % fval )
    if ( aval >= 100 ): return ( "%.1f" % fval )
    if ( aval >= 1 ): return ( "%.2f" % fval )
    if ( aval < 0.01 ): return ( "%.4f" % fval )
    return ( "%.3f" % fval )

def pt2str( pt ): return "( %.2f, %.2f )" % ( pt.x(), pt.y() ) 

def printTime( label ):
    global currentTime
    t = time.time()
    dt = t - currentTime 
    currentTime = t
    print " >--> DT: %6.3f:  %s " % ( dt, label )
    
def runTimedCommand( self, run_cmd, timeout  ):
    p = subprocess.Popen( run_cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr )
    

def callbackWrapper( func, wrapped_arg ):
    def callMe( *args ):
        return func( wrapped_arg, *args )
    return callMe

def getConfiguration( defaults ):
    from gui.application import get_vistrails_application
    app = get_vistrails_application()
    appConfig = app.temp_configuration if app else None
    dotVistrails = appConfig.dotVistrails if appConfig else os.path.expanduser("~/.vistrails/")
    datasetConfigFile = os.path.expanduser( os.path.join( dotVistrails, 'dv3d.cfg' )  )
    if not os.path.isfile( datasetConfigFile ):
        defaultConfigFile = os.path.join( resourcePath, 'dv3d.cfg' ) 
        assert os.path.isfile( defaultConfigFile ), "Error, default dv3d Config File does not exist at %s!" % defaultConfigFile
        shutil.copy( defaultConfigFile, appConfig.dotVistrails )            
    datasetConfig = ConfigParser.ConfigParser( defaults )
    datasetConfig.read( datasetConfigFile )  
    return datasetConfig, appConfig

def set_hyperwall_role( hw_role ):
    global hyperwall_role
    hyperwall_role = hw_role 

def get_hyperwall_role( ):
    global hyperwall_role
    return hyperwall_role
                                         
def delete_module( module,pipeline ):
    """delete_module(module: Module, pipeline: Pipeline) -> None
    deletes the module from the current pipeline in the proper way, taking
    care to also delete all connections. This is done to make sure that the
    modified pipelines we send to the clients are not broken"""
    graph = pipeline.graph
    connect_ids = [x[1] for x in graph.edges_to(module.id)]
    connect_ids += [x[1] for x in graph.edges_from(module.id)]
    action_list = []
    for c_id in connect_ids:
        action_list.append(('delete',pipeline.connections[c_id]))
    action_list.append(('delete',pipeline.modules[module.id]))
    
    action = create_action(action_list)
    pipeline.perform_action(action)
        
    
def isList( val ):
    valtype = type(val)
    return ( valtype ==type(list()) ) or  ( valtype ==type(tuple()) )

def isStr( val ):
    return ( type(val) == type(' ') ) 

def str2bool( value ):
    if ( type(value) == bool ): return value
    return value.strip().lower()[0] == 't'

def serializeStrMap( strMap ): 
    return ';'.join( [ '#'.join(dsitems) for dsitems in strMap.items() ] )
              
def deserializeStrMap( serialized_strMap ): 
    stringMap = {}
    for dsrec in serialized_strMap.split(';'):
        dsitems = dsrec.split('#')
        if len( dsitems ) == 2: stringMap[ dsitems[0] ] = dsitems[1]
    return stringMap

def printArgs( label, **args ):
    print " ------- %s --------- " % label
    for key in args:
        print " ** %s = %s " % ( key, str(args[key]) )

def encodeToString( obj ):
    rv = None
    try:
        buffer = StringIO.StringIO()
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
        buffer = StringIO.StringIO( string_value )
        pickler = cPickle.Unpickler( buffer )
        obj = pickler.load()
        buffer.close()
    except Exception, err:
        print>>sys.stderr, "Error unpickling string %s: %s" % ( string_value, str(err) )
    return obj

def addr( obj ): 
    return '0' if (obj == None) else obj.GetAddressAsString( obj.__class__.__name__ )

def getNewVtkDataArray( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return vtk.vtkUnsignedShortArray() 
    if scalar_dtype == np.ubyte:
        return vtk.vtkUnsignedCharArray() 
    if scalar_dtype == np.float:
        return vtk.vtkFloatArray() 
    return None

def getDatatypeString( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return 'UShort' 
    if scalar_dtype == np.ubyte:
        return 'UByte' 
    if scalar_dtype == np.float:
        return 'Float' 
    return None

def printSample3D( label, dataArray, size=10, offset=10 ):
    print " --- --- %s: Shape = %s, Vals: " % ( label, list( dataArray.shape ) )
    for iy in range( 0, size ):
        val = []
        for ix in range( 0, size ):
            val.append( str( dataArray[ offset + ix, offset + iy, offset ] ) )
        print ' '.join( val )
        
def getMaxScalarValue( scalar_dtype ):
    if scalar_dtype == np.ushort:
        return 65535.0
    if scalar_dtype == np.ubyte:
        return 255.0 
    if scalar_dtype == np.float:
        f = np.finfo(float) 
        return f.max
    return None

def getRangeBounds( type_str ):
    if type_str == 'UShort':
        return [ 0, 65535, 1 ]
    if type_str == 'UByte':
        return [ 0, 255, 1 ] 
    if type_str == 'Float':
        f = np.finfo(float) 
        return [ -f.max, f.max, 1 ]
    return None

        
def extractMetadata( fieldData ):
    mdList = []
    inputVarList = []
    varlist = fieldData.GetAbstractArray( 'varlist' ) 
    if varlist == None:  
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

def getFloatDataArray( name, values = [] ): 
    array = vtk.vtkFloatArray()
    array.SetName( name )
    for value in values:
        array.InsertNextValue( value )
    return array

def getIntDataArray( name, values = [] ): 
    array = vtk.vtkIntArray()
    array.SetName( name )
    for value in values:
        array.InsertNextValue( value )
    return array

def newList( size, init_value ):
    return [ init_value for i in range(size) ]
       
def getStringDataArray( name, values = [] ):
    array = vtk.vtkStringArray()
    array.SetName( name )
    for value in values:
        array.InsertNextValue( value )
    return array

def getItem( output, index = 0 ):  
    return output[ index ] if isList(output) else output  
                   
def wrapVTKModule( classname, instance ): 
    registry = get_module_registry()
    result = registry.get_descriptor_by_name( 'edu.utah.sci.vistrails.vtk', classname).module()
    result.vtkInstance = instance
    return result

def addAnnotation( module, **args ):  # args: id, key, value
    annotation = DBAnnotation( **args )
    module.db_add_annotation(annotation)

def getMetadata( module, **args ):
    id = args.get( 'id', None )
    if id <> None: return module.db_get_annotation_by_id( id )
    key = args.get( 'key', None )
    if key <> None: return module.db_get_annotation_by_key( key )
    return None

def getWorkflowModule( mid, forceGet = True, controller = None  ):    
    if controller == None: 
        import api
        controller = api.get_current_controller()
    vistrails_interpreter = getDefaultInterpreter()
    object_map = vistrails_interpreter.find_persistent_entities( controller.current_pipeline )[0]
    module_instance = object_map.get( mid, None )
    if (module_instance == None) and forceGet:
        current_version = controller.current_version
        min_version = current_version - 3 if current_version > 3 else 0
        for version in range( current_version-1, min_version, -1 ):
            pipeline =  controller.vistrail.getPipeline( version )
            object_map = vistrails_interpreter.find_persistent_entities( pipeline )[0]
            module_instance = object_map.get( mid, None )
            if module_instance <> None: return module_instance
    return module_instance

def NormalizeLon( lon ): 
    while lon < 0: lon = lon + 360
    return lon % 360  

def SameGrid( grid0, grid1 ):
    return (grid0 == grid1)
#    return (grid0.getOrder() == grid1.getOrder()) and (grid0.getType() == grid1.getType()) and (grid0.shape == grid1.shape)

def getWorkflowObjectMap( controller = None  ):    
    if controller == None: 
        import api
        controller = api.get_current_controller()
    vistrails_interpreter = getDefaultInterpreter()
    return vistrails_interpreter.find_persistent_entities( controller.current_pipeline )[0]

def getFunctionList( mid, controller = None ):
    if controller == None: 
        import api
        controller = api.get_current_controller()
    module = controller.current_pipeline.modules[ mid ]
    return module.functions if module.functions else []

def getFunctionFromList( function_name, functionList ):
    for function in functionList:
        if (function.name == function_name): #  and (function.vtType == 'function'):
            return function
    return None

def getFunction( mid, function_name, controller = None ):
    functionList = getFunctionFromList( mid, controller )
    return getFunction( function_name, functionList ) if functionList else None

def translateToPython( parmRec ):
    if parmRec.type == 'Float':    return float( parmRec.strValue ) if parmRec.strValue else 0.0
    if parmRec.type == 'Integer':  return int( parmRec.strValue ) if parmRec.strValue else 0
    return parmRec.strValue
        
def getTaggedVersionNumber( tag, controller = None ):
    tagged_version_number = -1
    if tag <> None: 
        if controller == None: 
            import api
            controller = api.get_current_controller()
        if controller.vistrail.hasTag( tag ):
            tagged_version_number = controller.vistrail.get_version_number( tag )
    return tagged_version_number


def tagCurrentVersion( tag ):
    if tag: 
        import api
        ctrl = api.get_current_controller()
        vistrail = ctrl.vistrail
        tagged_version_number = -1
        if tag <> None: 
            if vistrail.hasTag( tag ):
                tagged_version_number = vistrail.get_version_number( tag )
                vistrail.changeTag( None, tagged_version_number )
            try:
                vistrail.addTag( tag, ctrl.current_version )
                print "  --- Tagging version %d as %s" % ( ctrl.current_version, tag )
            except VersionAlreadyTagged, err:
                curr_tag = vistrail.get_tag( ctrl.current_version ) 
                print>>sys.stderr, " !! Version %d already tagged as %s, applying tag %s, prev tagged version: %d" % ( ctrl.current_version, tag, curr_tag, tagged_version_number )
    return ctrl.current_version

def printPersistentModuleMap( label, controller = None ):   
    if controller == None: 
        import api
        controller = api.get_current_controller()
    vistrails_interpreter = getDefaultInterpreter()
    object_map = vistrails_interpreter.find_persistent_entities( controller.current_pipeline )[0]
#    print " %s --- PersistentModuleMap: %s " % ( label, str( object_map ) )

def getObjectMap( controller ):    
    vistrails_interpreter = getDefaultInterpreter()
    object_maps = vistrails_interpreter.find_persistent_entities( controller.current_pipeline )
    return object_maps[0] if object_maps else None

def getDownstreamModules( mid ):  
    import api
    controller = api.get_current_controller()
    pipeline = controller.current_pipeline
    current_module = pipeline.modules[ mid ]
    test_modules = [ current_module ]
    downstream_modules = [ ]
    while len( test_modules ):
        test_mod = test_modules.pop()
        output_port_specs = test_mod.output_port_specs
        for output_port in output_port_specs:            
            out_modules = pipeline.get_outputPort_modules( test_mod.id, output_port.name )
            downstream_modules.extend( out_modules )
            test_modules.extend( out_modules )
    return downstream_modules
            
def getDesignatedConnections( controller,  mid, portName, isDestinationPort = True ):
    portType = "destination" if isDestinationPort else "source" 
    connections = controller.current_pipeline.connections
    desig_connections = []
    for connection in connections.values():
        for port in connection.ports:
            if port.type==portType and port.name==portName and port.moduleId == mid:
                desig_connections.append( connection )
    return desig_connections

def isCellModule( module ):
    return  module.name in [ "MapCell3D", "ChartCell", "SlicePlotCell", "CloudCell3D" ]

def getSheetTabWidget( sheet_index = -1 ):
    from packages.spreadsheet.spreadsheet_controller import spreadsheetController
    spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
    if sheet_index == -1: sheet_index = spreadsheetWindow.get_current_tab_controller().currentIndex () 
    return spreadsheetWindow.get_current_tab_controller().tabWidgets[ sheet_index ]

def adjustSheetDimensions(row, col ):
    sheetTabWidget = getSheetTabWidget()
    ( rc, cc ) = sheetTabWidget.getDimension()
    rowChanged, colChanged = False, False
    if row >= rc: 
        rc = row + 1
        rowChanged = True
    if col >= cc: 
        cc = col + 1
        colChanged = True
    if rowChanged or colChanged:    sheetTabWidget.setDimension( rc, cc )
    if rowChanged:                  sheetTabWidget.rowSpinBoxChanged()            
    if colChanged:                  sheetTabWidget.colSpinBoxChanged()

def getConnectedModuleIds( controller,  mid, portName, isDestinationPort = True ):
    connections = getDesignatedConnections( controller,  mid, portName, isDestinationPort )
    connectedModuleIds = []
    if connections:
        for connection in connections:
            oppositePortType = "source" if isDestinationPort else "destination"
            for port in connection.ports:
                if port.type==oppositePortType:
                    connectedModuleIds.append( ( port.moduleId, port.name ) )
    return connectedModuleIds

def getFunctionParmStrValues( module, functionName, defValue = None ):
    if module and functionName:
        for function in module.functions:
            if function.name == functionName:
                values = []
                for parameter in function.parameters:
                    values.append( parameter.strValue )
                return values
    return defValue

def getModuleClass( mid ):
    import api
    registry = get_module_registry()
    controller = api.get_current_controller() 
    reg_module = controller.current_pipeline.modules[ mid ]
    descriptor = registry.get_descriptor_by_name( reg_module.package, reg_module.name, reg_module.namespace )
    return descriptor.module

def updateScene():
    import api
    controller = api.get_current_controller()
    controller.current_pipeline_view.setupScene(controller.current_pipeline)  

def getSigString( klass ):
    registry = get_module_registry()
    descriptor = registry.get_descriptor( klass )
    return "( %s )" % descriptor.sigstring

def isLevelAxis( axis ):
    if axis.isLevel(): return True
    if ( axis.id == 'isobaric' ): 
        axis.designateLevel(1)
        return True
    return False

def getVariableSelectionLabel( varName, ndims ):
    if ndims == 2:  return '%s (slice)' % varName 
    if ndims == 3:  return '%s (volume)' % varName 
    return ''

def getVarNDim( vardata ):
    dims = [ 0, 0, 0 ]
    for dval in vardata.domain:
        axis = dval[0] 
        if axis.isLongitude(): 
            dims[0] = 1
        elif axis.isLatitude(): 
            dims[1] = 1
        elif isLevelAxis( axis ): 
            dims[2] = 1
    return dims[0] + dims[1] + dims[2]
           
#def getAttachedCells( module, port, cells = [] ):
#     import api
#     registry = get_module_registry()
#     controller = api.get_current_controller() 
#     this_mid = module.moduleInfo['moduleId'] 
#     output_mids = controller.current_pipeline.get_outputPort_modules( this_mid, port )
#     for mid in output_mids:
#         reg_module = controller.current_pipeline.modules[ mid ]
#         descriptor = registry.get_descriptor_by_name( reg_module.package, reg_module.name, reg_module.namespace )
#         module = descriptor.module
#         mclass = module.__class__
#         modclass = Module
#         if issubclass( mclass, SpreadsheetCell ):
#             cells.append( module )
#         elif issubclass( mclass, Module ): 
#             getAttachedCells( module, port, cells )

def executeWorkflow():
    import api
    controller = api.get_current_controller()        
    controller.execute_current_workflow()
   
  
class vtkImageExportToArray:
    """
    vtkImageExportToArray: a NumPy front-end to vtkImageExport
    
    Load a python array into a vtk image.
     
    Convert a vtk image into a NumPy array
    
    Methods:
    
      SetInput(input) -- connect to VTK image pipeline
      GetArray()      -- execute pipeline and return a Numeric array
      
    Convert VTK_UNSIGNED_SHORT to python Int:
    (this might be necessary because Python doesn't support unsigned short,
    the default is to cast unsigned short to signed short).
    
      SetConvertUnsignedShortToInt(yesno)
      ConvertUnsignedShortToIntOn()
      ConvertUnsignedShortToIntOff()
    
    From vtkImageExport:
    
      GetDataExtent()
      GetDataSpacing()
      GetDataOrigin()
    """
    def __init__(self):
        self.__export = vtk.vtkImageExport()
        self.__ConvertUnsignedShortToInt = 1

    # type dictionary: note that python doesn't support
    # unsigned integers!

    __typeDict = { VTK_CHAR:            np.int8,
                   VTK_UNSIGNED_CHAR:   np.uint8,
                   VTK_SHORT:           np.int16,
                   VTK_UNSIGNED_SHORT:  np.int16,
                   VTK_INT:             np.int32,
                   VTK_FLOAT:           np.float32,
                   VTK_DOUBLE:          np.float64 }

    __sizeDict = { VTK_CHAR:1,
                   VTK_UNSIGNED_CHAR:1,
                   VTK_SHORT:2,
                   VTK_UNSIGNED_SHORT:2,
                   VTK_INT:4,
                   VTK_FLOAT:4,
                   VTK_DOUBLE:8 }

    # convert unsigned shorts to ints, to avoid sign problems
    def SetConvertUnsignedShortToInt(self,yesno):
        self.__ConvertUnsignedShortToInt = yesno

    def GetConvertUnsignedShortToInt(self):
        return self.__ConvertUnsignedShortToInt
    
    def ConvertUnsignedShortToIntOn(self):
        self.__ConvertUnsignedShortToInt = 1

    def ConvertUnsignedShortToIntOff(self):
        self.__ConvertUnsignedShortToInt = 0

    # set the input
    def SetInput(self,input):
        return self.__export.SetInput(input)

    def GetInput(self):
        return self.__export.GetInput()

    def GetArray(self):
        input = self.__export.GetInput()
        type = input.GetScalarType()
        extent = input.GetWholeExtent()
        numComponents = input.GetNumberOfScalarComponents()
        dim = (extent[5]-extent[4]+1,
               extent[3]-extent[2]+1,
               extent[1]-extent[0]+1)
        if (numComponents > 1):
            dim = dim + (numComponents,)
        size = dim[0]*dim[1]*dim[2]*numComponents*self.__sizeDict[type]

        imString = np.zeros( (size,), np.uint8 ).tostring()
        self.__export.Export(imString)

        imArray = np.fromstring(imString,self.__typeDict[type])
        imArray = np.reshape(imArray,dim)

        # convert unsigned short to int to avoid sign issues
        if (type == VTK_UNSIGNED_SHORT and self.__ConvertUnsignedShortToInt):
            imArray = umath.bitwise_and( imArray.astype( np.int32 ), 0xffff )
#            imArray = imArray.astype( np.int32 ) & 0xffff 

        # just to remind myself of the dangers of memory management
        del imString

        return imArray
        
    def GetDataExtent(self):
        return self.__export.GetInput().GetWholeExtent()
    
    def GetDataSpacing(self):
        return self.__export.GetInput().GetSpacing()
    
    def GetDataOrigin(self):
        return self.__export.GetInput().GetOrigin()
    

class vtkImageImportFromArray:
    """
    vtkImageImportFromArray: a NumPy front-end to vtkImageImport
    
    Load a python array into a vtk image.
    
    Methods:
    
      GetOutput() -- connect to VTK image pipeline
      SetArray()  -- set the array to load in
      
    Convert python 'Int' to VTK_UNSIGNED_SHORT:
    (python doesn't support unsigned short, so this might be necessary)
    
      SetConvertIntToUnsignedShort(yesno)
      ConvertIntToUnsignedShortOn()
      ConvertIntToUnsignedShortOff()
    
    Methods from vtkImageImport: 
    (if you don't set these, sensible defaults will be used)
    
      SetDataExtent()
      SetDataSpacing()
      SetDataOrigin()
    """
    def __init__(self):
        self.__import = vtk.vtkImageImport()
        self.__ConvertIntToUnsignedShort = 0
        self.__Array = None

    # type dictionary: note that python doesn't support
    # unsigned integers properly!
    __typeDict = {'c':VTK_UNSIGNED_CHAR,
                  'b':VTK_UNSIGNED_CHAR,
                  '1':VTK_CHAR,
                  's':VTK_SHORT,
                  'i':VTK_INT,
                  'l':VTK_LONG,
                  'f':VTK_FLOAT,
                  'd':VTK_DOUBLE,
                  'F':VTK_FLOAT,
                  'D':VTK_DOUBLE }

    # convert 'Int32' to 'unsigned short'
    def SetConvertIntToUnsignedShort(self,yesno):
        self.__ConvertIntToUnsignedShort = yesno

    def GetConvertIntToUnsignedShort(self):
        return self.__ConvertIntToUnsignedShort
    
    def ConvertIntToUnsignedShortOn(self):
        self.__ConvertIntToUnsignedShort = 1

    def ConvertIntToUnsignedShortOff(self):
        self.__ConvertIntToUnsignedShort = 0

    # get the output
    def GetOutput(self):
        return self.__import.GetOutput()

    # import an array
    def SetArray(self,imArray):
        self.__Array = imArray
        imString = imArray.tostring()
        numComponents = 1
        dim = imArray.shape

        if (len(dim) == 4):
            numComponents = dim[3]
            dim = (dim[0],dim[1],dim[2])
            
        type = self.__typeDict[imArray.typecode()]

        if (imArray.typecode() == 'F' or imArray.typecode == 'D'):
            numComponents = numComponents * 2

        if (self.__ConvertIntToUnsignedShort and imArray.typecode() == 'i'):
            imString = imArray.astype(Numeric.Int16).tostring()
            type = VTK_UNSIGNED_SHORT
        else:
            imString = imArray.tostring()
            
        self.__import.CopyImportVoidPointer(imString,len(imString))
        self.__import.SetDataScalarType(type)
        self.__import.SetNumberOfScalarComponents(numComponents)
        extent = self.__import.GetDataExtent()
        self.__import.SetDataExtent(extent[0],extent[0]+dim[2]-1,
                                    extent[2],extent[2]+dim[1]-1,
                                    extent[4],extent[4]+dim[0]-1)

    def GetArray(self):
        return self.__Array
        
    # a whole bunch of methods copied from vtkImageImport

    def SetDataExtent(self,extent):
        self.__import.SetDataExtent(extent)

    def GetDataExtent(self):
        return self.__import.GetDataExtent()
    
    def SetDataSpacing(self,spacing):
        self.__import.SetDataSpacing(spacing)

    def GetDataSpacing(self):
        return self.__import.GetDataSpacing()
    
    def SetDataOrigin(self,origin):
        self.__import.SetDataOrigin(origin)

    def GetDataOrigin(self):
        return self.__import.GetDataOrigin()

#
#class Timer(QtCore.QTimer):
#    """Simple subclass of QTimer that allows the user to have a function called
#    periodically.  
#
#    Any exceptions raised in the callable are caught.  If
#    `StopIteration` is raised the timer stops.  If other exceptions are
#    encountered the timer is stopped and the exception re-raised.
#    """
#    
#    def __init__(self, millisecs, callable, *args, **kw_args):
#        """ Initialize instance to invoke the given `callable` with given
#        arguments and keyword args after every `millisecs` (milliseconds).
#        """
#        QtCore.QTimer.__init__(self)
#
#        self.callable = callable
#        self.args = args
#        self.kw_args = kw_args
#
#        self.connect(self, QtCore.SIGNAL('timeout()'), self.Notify)
#
#        self._is_active = True
#        self.start(millisecs)
#
#    def Notify(self):
#        """ Call the given callable.  Exceptions raised in the callable are
#        caught.  If `StopIteration` is raised the timer stops.  If other
#        exceptions are encountered the timer is stopped and the exception
#        re-raised.  Note that the name of this method is part of the API
#        because some code expects this to be a wx.Timer sub-class.
#        """
#        try:
#            self.callable(*self.args, **self.kw_args)
#        except StopIteration:
#            self.stop()
#        except:
#            self.stop()
#            raise
#
#    def Start(self, millisecs=None):
#        """ Emulate wx.Timer.
#        """
#        self._is_active = True
#
#        if millisecs is None:
#            self.start()
#        else:
#            self.start(millisecs)
#
#    def Stop(self):
#        """ Emulate wx.Timer.
#        """
#        self._is_active = False
#        self.stop()
#
#    def IsRunning(self):
#        """ Emulate wx.Timer.
#        """
#        return self._is_active

