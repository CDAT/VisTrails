'''
Created on Dec 17, 2010

@author: tpmaxwel
'''

import vtk, sys, time, threading, inspect, gui, traceback
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from core.modules.vistrails_module import Module, ModuleError
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.vtDV3D.InteractiveConfiguration import *
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D import ModuleStore
from db.domain import DBModule, DBAnnotation
from packages.vtDV3D import HyperwallManager
from packages.vtDV3D.vtUtilities import *
import cdms2, cdtime
ReferenceTimeUnits = "days since 1900-1-1"
MIN_LINE_LEN = 50

moduleInstances = {}

def getClassName( instance ):
    return instance.__class__.__name__ if ( instance <> None ) else "None" 

def CheckAbort(obj, event):
   if obj.GetEventPending() != 0:
       obj.SetAbortRender(1)
       
def getFloatStr( val ):
    if ( type(val) == type(' ') ): return val
    return "%.1f" % val
       
def IsListType( val ):
    valtype = type(val)
    return ( valtype ==type(list()) ) or  ( valtype ==type(tuple()) )

def ExtendClassDocumentation( klass ):
    instance = klass()
    default_doc = "" if ( klass.__doc__ == None ) else klass.__doc__ 
    klass.__doc__ = " %s\n %s " % ( default_doc, instance.getConfigurationHelpText() )

def massageText( text, target_line_len=60 ):
    text_lines = text.split('\n')
    linelen = 0
    for iLine in range(len(text_lines)):
        line = text_lines[iLine]
        linelen = len( line )
        if linelen > target_line_len: 
            line_segs = line.split('/')
            seg_len = 0
            for iSeg in range(len( line_segs )):
                seg_len += len( line_segs[iSeg] )
                if seg_len > target_line_len: break
            text_lines[iLine] = '/'.join(line_segs[0:iSeg]) + '/\n' + '/'.join( line_segs[iSeg:-1] )  
                         
    if linelen < target_line_len: text_lines[-1] += (' '*(target_line_len-linelen)) 
    rv = '\n'.join( text_lines )
    print "PROCESSED TEXT: { %s }" % rv
    return rv 
################################################################################      

class AlgorithmOutputModule( Module ):
    
    def __init__( self, **args ):
        Module.__init__(self) 
        self.algoOutput = args.get('output',None)  
        self.algoOutputPort = args.get('port',None)
        self.fieldData = args.get('fieldData',None)
        
    def getFieldData(self):
        return self.fieldData 
        
    def getOutput(self): 
        if self.algoOutput <> None: return self.algoOutput
        if self.algoOutputPort <> None: return self.algoOutputPort.GetProducer().GetOutput() 
        return None
                
    def getOutputPort(self): 
        return self.algoOutputPort 
    
    def inputToAlgorithm( self, algorithm, iPort = -1 ):
        if self.algoOutputPort <> None: 
            if iPort < 0:   algorithm.SetInputConnection( self.algoOutputPort )
            else:           algorithm.SetInputConnection( iPort, self.algoOutputPort )
        else: 
            output = self.getOutput() 
#            print " inputToAlgorithm: oid = %x " % id( output ) 
            algorithm.SetInput( output )
            algorithm.Modified()

class AlgorithmOutputModule3D( AlgorithmOutputModule ):
    
    def __init__( self, renderer, **args ):
        AlgorithmOutputModule.__init__( self, **args ) 
        self.renderer = renderer 
    
    def getRenderer(self): 
        return self.renderer

class AlgorithmOutputModule2D( AlgorithmOutputModule ):
    
    def __init__( self, view, **args ):
        AlgorithmOutputModule.__init__( self, **args ) 
        self.view = view 
    
    def getView(self): 
        return self.view

    def getRenderer(self): 
        return self.view.GetRenderer()

class InputSpecs:
    
    def __init__( self, **args ):
        self.units = ''
        self.scalarRange = None
        self.seriesScalarRange = None
        self.rangeBounds = None
        self.metadata = None
        self.input = None
        self.fieldData = None
        self.inputModule = None
        self.inputModuleList = None
        self.datasetId = None

    def initializeScalarRange( self ): 
        metadata = self.getMetadata()  
        var_md = metadata.get( 'attributes' , None )
        if var_md <> None:
            range = var_md.get( 'range', None )
            if range: 
#                print "\n ***************** ScalarRange = %s, md[%d], var_md[%d] *****************  \n" % ( str(range), id(metadata), id(var_md) )
                self.scalarRange = list( range )
                self.scalarRange.append( 1 )
                if not self.seriesScalarRange:
                    self.seriesScalarRange = list(range)
                else:
                    if self.seriesScalarRange[0] > range[0]:
                        self.seriesScalarRange[0] = range[0] 
                    if self.seriesScalarRange[1] < range[1]:
                        self.seriesScalarRange[1] = range[1] 

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
            gridSpacing = self.input.GetSpacing()
            gridOrigin = self.input.GetOrigin()
            world_coords = [ getFloatStr(gridOrigin[i] + image_coords[i]*gridSpacing[i]) for i in range(3) ]
        return world_coords

    def getWorldCoord( self, image_coord, iAxis ):
        plotType = self.metadata[ 'plotType' ]                   
        axisNames = [ 'Longitude', 'Latitude', 'Time' ] if plotType == 'zyt'  else [ 'Longitude', 'Latitude', 'Level' ]
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
                gridSpacing = self.input.GetSpacing()
                gridOrigin = self.input.GetOrigin()
                return axes[iAxis], getFloatStr( gridOrigin[iAxis] + image_coord*gridSpacing[iAxis] ) 
            return axes[iAxis], ""

    def getRangeBounds( self ):
        return self.rangeBounds  
        
    def getDataRangeBounds(self):
        if self.rangeBounds:
            range = self.getDataValues( self.rangeBounds[0:2] ) 
            if ( len( self.rangeBounds ) > 2 ): range.append( self.rangeBounds[2] ) 
            else:                               range.append( 0 )
        else: range = [ 0, 0, 0 ]
        return range
    
    def getScalarRange(self): 
        return self.scalarRange
    
    def raiseModuleError( self, msg ):
        print>>sys.stderr, msg
        raise ModuleError( self, msg )

    def getDataValue( self, image_value):
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        sval = ( float(image_value) - self.rangeBounds[0] ) / ( self.rangeBounds[1] - self.rangeBounds[0] )
        dataValue = valueRange[0] + sval * ( valueRange[1] - valueRange[0] ) 
        return dataValue
                
    def getDataValues( self, image_value_list ):
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
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        valueRange = self.scalarRange
        dv = ( valueRange[1] - valueRange[0] )
        imageValues = []
        for data_value in data_value_list:
            sval = 0.0 if ( dv == 0.0 ) else ( data_value - valueRange[0] ) / dv
            imageValue = self.rangeBounds[0] + sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
            imageValues.append( imageValue )
#        print "\n *****************  GetImageValues[%d:%x]: data_values = %s, range = %s, imageValues = %s **************** \n" % ( self.moduleID, id(self), str(data_value_list), str(self.scalarRange), str(imageValues) )
        return imageValues

    def scaleToImage( self, data_value ):
        if not self.scalarRange: 
            self.raiseModuleError( "ERROR: no variable selected in dataset input to module %s" % getClassName( self ) )
        dv = ( self.scalarRange[1] - self.scalarRange[0] )
        sval = 0.0 if ( dv == 0.0 ) else data_value / dv
        imageScaledValue =  sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
        return imageScaledValue

    def getMetadata( self, key = None ):
        if not self.metadata: self.updateMetadata()
        return self.metadata.get( key, None ) if key else self.metadata
    
    def getFieldData( self ):
        return self.fieldData  
    
    def updateMetadata( self ):
        if self.metadata == None:
            scalars = None
            if self.input <> None:
                fd = self.input.GetFieldData() 
                self.input.Update()
                self.fieldData = self.input.GetFieldData()             
            elif self.inputModule:
                self.fieldData = self.inputModule.getFieldData() 
    
            self.metadata = self.computeMetadata()
            
            if self.metadata <> None:
                self.rangeBounds = None              
                self.datasetId = self.metadata.get( 'datasetId', None )                
                tval = self.metadata.get( 'timeValue', 0.0 )
                self.timeValue = cdtime.reltime( float( tval ), ReferenceTimeUnits )               
                dtype =  self.metadata.get( 'datatype', None )
                scalars =  self.metadata.get( 'scalars', None )
                self.rangeBounds = getRangeBounds( dtype )
                title = self.metadata.get( 'title', None )
                if title:
                    targs = title.split(':')
                    if len( targs ) == 1:
                        self.titleBuffer = "\n%s" % ( title )
                    elif len( targs ) > 1:
                        self.titleBuffer = "%s\n%s" % ( targs[1], targs[0] )
                else: self.titleBuffer = ""
    #            self.persistParameterList( [ ( 'title' , [ self.titleBuffer ]  ), ] )    
                attributes = self.metadata.get( 'attributes' , None )
                if attributes:
                    self.units = attributes.get( 'units' , '' )

    def getUnits(self):
        return self.units
    
    def getLayerList(self):
        layerList = []
        pointData = self.input.GetPointData()
        for iA in range( pointData.GetNumberOfArrays() ):
            array_name = pointData.GetArrayName(iA)
            if array_name: layerList.append( array_name )
        return layerList
    
    def computeMetadata( self  ):
        if not self.fieldData: self.initializeMetadata() 
        if self.fieldData:
            return extractMetadata( self.fieldData )
        return {}
        
    def addMetadataObserver( self, caller, event ):
        fd = caller.GetOutput().GetFieldData()
        fd.ShallowCopy( self.fieldData )
        pass

    def initializeMetadata( self ):
        self.fieldData = vtk.vtkDataSetAttributes()
        mdarray = getStringDataArray( 'metadata' )
        self.fieldData.AddArray( mdarray )

    def addMetadata( self, metadata ):
        dataVector = self.fieldData.GetAbstractArray( 'metadata' ) 
        if dataVector == None:   
            print " Can't get Metadata for class %s " % getClassName( self )
        else:
            enc_mdata = encodeToString( metadata )
            dataVector.InsertNextValue( enc_mdata  )
       
class PersistentModule( QObject ):
    '''
    <H2> Interactive Configuration</H2>
    All vtDV3D Workflow Module support interactive configuration functions that 
    are used to configure parameters for colormaps, transfer functions, and other display options. 
    All configuration  functions are invoked using command keys and saved as provenance upon completion.   
    Consult the 'modules' tab of the help widget for a list of available command keys for the current cell. <P>
        There are two types of configuration functions: gui functions and leveling functions.  
        <h3> GUI Functions </h3>
        GUI functions facilitate interactive parameter configurations that require a choice from a discreet set of possible values
        ( e.g. choosing a colormap or the number of contour levels ). Typing the the gui command code pops up a gui widget.  
        All gui function command codes are lower case.
        <h3> Leveling Functions </h3>
        Leveling functions facilitate interactive configuration of continuously varying parameters  ( e.g. scaling a colormap or 
        configuring a transfer function ). Typing the leveling command code puts the cell into leveling mode.  Leveling is initiated
        when the user left-clicks in the cell while it is in leveling mode.  Mouse drag operations (while leveling) generate
        leveling configurations.  When the (left) mouse button is release the leveling configuration is saved as provenance and the
        cell returns to normal (non-leveling) mode.   
    ''' 
    markedTime = 0.0
             
    def __init__( self, mid, **args ):
        QObject.__init__(self)
        self.pipelineBuilt = False
        self.newLayerConfiguration = False
        self.activeLayer = None
        self.newDataset = False
        self.sheetName = None 
        self.cell_address = None
        self.moduleID = mid
        self.inputSpecs = {}
        self.pipeline = args.get( 'pipeline', None )
        self.taggedVersionMap = {}
        self.persistedParameters = []
        self.versionTags = {}
        self.initVersionMap()
        role = get_hyperwall_role( )
        self.isClient = ( role == 'hw_client' )
        self.isServer = ( role == 'hw_server' )
        self.timeStepName = 'timestep'
        self.wmod = None
        self.nonFunctionLayerDepParms = args.get( 'layerDepParms', [] )
        self.roi = None 
        self.configurableFunctions = {}
        self.configuring = False
        self.allowMultipleInputs = {}
        self.InteractionState = None
        self.LastInteractionState = None
        self.requiresPrimaryInput = args.get( 'requiresPrimaryInput', True )
        self.createColormap = args.get( 'createColormap', True )
        self.parmUpdating = {}
        self.ndims = args.get( 'ndims', 3 ) 
        self.primaryInputPorts = [ 'slice' ] if (self.ndims == 2) else [ 'volume' ]
        self.primaryMetaDataPort = self.primaryInputPorts[0]
        self.documentation = None
        self.parameterCache = {}
        self.timeValue = cdtime.reltime( 0.0, ReferenceTimeUnits ) 
        if self.createColormap:
            self.addUVCDATConfigGuiFunction( 'colormap', ColormapConfigurationDialog, 'c', label='Choose Colormap', setValue=self.setColormap, getValue=self.getColormap, layerDependent=True )
#        self.addConfigurableGuiFunction( self.timeStepName, AnimationConfigurationDialog, 'a', label='Animation', setValue=self.setTimeValue, getValue=self.getTimeValue )
        self.addUVCDATConfigGuiFunction( self.timeStepName, AnimationConfigurationDialog, 'a', label='Animation', setValue=self.setTimeValue, getValue=self.getTimeValue, cellsOnly=True )
        
        print "**********************************************************************"
        print "Create Module [%d] : %s (%x)" % ( self.moduleID, self.__class__.__name__, id(self) )
        print "**********************************************************************"

#        self.addConfigurableGuiFunction( 'layer', LayerConfigurationDialog, 'l', setValue=self.setLayer, getValue=self.getLayer )

#    def getSelectionStatus( self ):
#        if self.fieldData:
#            dataArray = self.fieldData.GetArray( 'selected' )  
#            if dataArray: return dataArray.GetValue(0)
#        return 0

#    def __del__(self):
#        from packages.vtDV3D.InteractiveConfiguration import IVModuleConfigurationDialog 
#        IVModuleConfigurationDialog.reset()

    def setCellLocation( self, sheetName, cell_address ):
        self.sheetName = sheetName 
        self.cell_address = cell_address
        
    def GetRenWinID(self):
        return -1
        
    def setLayer( self, layer ):
        self.activeLayer = getItem( layer )

    def getLayer( self ):
        return [ self.activeLayer, ]

    def input( self, input_index=0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.input
    
    def getUnits(self, input_index=0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getUnits()

    def inputModule( self, input_index=0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.inputModule

    def inputModuleList( self, input_index=0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.inputModuleList

    def getConfigFunctions( self, types=None ):
        cmdList = []
        for items in self.configurableFunctions.items():
            cmd = items[1]
            if types == None:
                cmdList.append( cmd ) 
            else:
                for type in types:
                    if cmd.type == type:
                        cmdList.append( cmd ) 
        return cmdList
                        

    def getDatasetId( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.datasetId  

    def getFieldData( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getFieldData()  

    def getRangeBounds( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getRangeBounds()  

    def setRangeBounds( self, rbounds, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        ispec.rangeBounds[:] = rbounds[:] 
        
    def getScalarRange( self, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.scalarRange  
            
    def getDataRangeBounds(self, input_index = 0):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getDataRangeBounds() 
    
    def invalidateWorkflowModule( self, workflowModule ):
        if (self.wmod == workflowModule): self.wmod = None
        
    def markTime( self, note ):
        new_time = time.time()
#        print " ^^^^^ Time Mark: %s, elapsed = %.4f ^^^^^ " % ( note, new_time - self.markedTime )
        self.markedTime = new_time

    def setWorkflowModule( self, workflowModule ):
        self.wmod = workflowModule

    def initiateParameterUpdate( self, parmName ):
        self.parmUpdating[parmName] = True     
     
    def addAnnotation( self, id, note ): 
        if self.isClient: return 
        import api
        controller = api.get_current_controller()
        try:
            controller.add_annotation( (id, str(note)), self.moduleID ) 
        except: pass
        
    def getOutputRecord( self, ndim  ):
        return None
    
    def setLabel( self, label ):      
        if self.isClient: return
        import api
        controller = api.get_current_controller()
        controller.add_annotation( ('__desc__', str(label)), self.moduleID ) 
        controller.current_pipeline_view.recreate_module( controller.current_pipeline, self.moduleID )
        pass

    def updateTextDisplay( self, text = None ):
        pass
    
    def setNewConfiguration(self, **args ):
        self.newLayerConfiguration = args.get( 'newLayerConfig', False )

    def clearNewConfiguration(self):
        self.newLayerConfiguration = False
        self.setResult( "executionSpecs", "" )
    
    def generateDocumentation(self):
        self.documentation = "\n <h2>Module %s</h2> \n" % getClassName( self )
        if self.__class__.__doc__ <> None: self.documentation += self.__class__.__doc__
        self.documentation += self.getConfigurationHelpText()

    def getCachedParameter(self, parameter_name ):
        layerCache = self.parameterCache.setdefault( self.getParameterId(), {} )
        return layerCache.get( parameter_name, None )
        
    def getParameter(self, parameter_name, default_value = None ):
        paramVal = self.getCachedParameter( parameter_name  )
        if (paramVal == None) and not self.isClient:
            paramVal = self.getTaggedParameterValue( parameter_name )
            if paramVal <> None: self.setParameter( parameter_name, paramVal )
        return paramVal if paramVal else default_value
                
    def setParameter(self, parameter_name, value, parameter_id = None ):
        if parameter_id == None: parameter_id = self.getParameterId()
        layerCache = self.parameterCache.setdefault( parameter_id, {} )
        layerCache[parameter_name] = value 

    def getTaggedParameterValue(self, parameter_name ):
        import api
        tag = self.getParameterId()
        ctrl = api.get_current_controller()
        pval = None
        if tag <> None: 
            try:
                tagged_version_number = self.getTaggedVersion( tag )
                if tagged_version_number >= 0:
                    tagged_pipeLine =  ctrl.vistrail.getPipeline( tagged_version_number )
                    tagged_module = tagged_pipeLine.modules[ self.moduleID ]
                    tagged_function = getFunctionFromList( parameter_name, tagged_module.functions )
                    if tagged_function:
                        parameterList = tagged_function.parameters
                        pval = [ translateToPython( parmRec ) for parmRec in parameterList ]
            except Exception, err:
                pass
#                print>>sys.stderr, " vtDV3D Exception in getTaggedParameterValue (%s):\n { %s } " % ( parameter_name, str( err ) )
        return pval
                
        
    def is_cacheable(self):
        return False
    
    def updateTextDisplay( self, text = None ):
        pass
            
    def getName(self):
        return str( getClassName( self ) )
        
    def dvCompute( self, **args ):
        self.initializeInputs( **args )     
        self.updateHyperwall()
        if self.input() or self.inputModuleList() or not self.requiresPrimaryInput:
            self.execute( **args )
            self.initializeConfiguration()
        elif self.requiresPrimaryInput:
            print>>sys.stderr, " Error, no input to module %s " % getClassName( self )
#        self.persistLayerDependentParameters()
        self.resetNavigation()
        
    def updateHyperwall(self):
        pass

    def dvUpdate(self, **args):
#        self.markTime( ' Update %s' % getClassName( self ) ) 
        self.initializeInputs( **args )     
        self.execute( **args )
 

    def getParameterDisplay( self, parmName, parmValue ):
        if parmName == self.timeStepName:
            return str( self.timeValue.tocomp() ), 1
        return None, 1
          
    def getPrimaryInput( self, **args ):
        port = args.get('port', self.primaryInputPorts[0] )
        return self.getInputValue( port, **args )
    
    def getPrimaryInputList(self, **args ):
        port = args.get('port', self.primaryInputPorts[0] )
        return self.getInputList( port, **args  )
    
    def isLayerDependentParameter( self, parmName ):
        cf = self.configurableFunctions.get( parmName, None )
        if cf: return cf.isLayerDependent
        try:
            pindex = self.nonFunctionLayerDepParms.index( parmName )
            return True
        except: return False 
       
    def getInputList( self, inputName, **args ):
        inputList = None
        portInputIsValid = not ( self.newLayerConfiguration and self.isLayerDependentParameter(inputName) )
        if portInputIsValid: 
            if self.wmod:  inputList = self.wmod.forceGetInputListFromPort( inputName )
        if inputList == None:         
            inputList = self.getParameter( inputName, None )
        return inputList
    
    def getDatasetId( self, **args ):  
        dsid = args.get( 'datasetId', None )
        if dsid:
            self.datasetId = dsid 
            self.addAnnotation( 'datasetId', self.datasetId  ) 
    
    def getInputValue1( self, inputName, default_value = None, **args ):
        import api
        if inputName == 'task':
            pass
        self.getDatasetId( **args )
        isLayerDep = self.isLayerDependentParameter( inputName )
        pval = None
        if self.wmod and ( self.isClient or not ( isLayerDep and self.newLayerConfiguration ) ):
            pval = self.wmod.forceGetInputFromPort( inputName, default_value ) 
        else:
            ctrl, tag = api.get_current_controller(), self.getParameterId()
            tagged_version_number = ctrl.current_version
            if isLayerDep:
                versions = self.getTaggedVersionList( tag )
                if versions: tagged_version_number = versions[-1] 
                else: return default_value
            try:
                tagged_pipeLine =  ctrl.vistrail.getPipeline( tagged_version_number )
                tagged_module = tagged_pipeLine.modules[ self.moduleID ]
                tagged_function = getFunctionFromList( inputName, tagged_module.functions )
                if tagged_function:
                    parameterList = tagged_function.parameters
                    pval = [ translateToPython( parmRec ) for parmRec in parameterList ]
#                    print " %s.Get-Input-Value[%s:%s] (v. %s): %s " % ( self.getName(), tag, inputName, str(tagged_version_number), str(pval) )
            except Exception, err:
                print>>sys.stderr, "vtDV3D Error getting tagged version:\n { %s }" % str(err)
        if pval == None:         
            pval = self.getParameter( inputName, default_value )
#            print ' ***** GetInputValue[%s] = %s ' % ( inputName, str(pval) )
        return pval

    def getInputValue( self, inputName, default_value = None, **args ):
        import api
        self.getDatasetId( **args )
        pval = self.getParameter( inputName, None )
        if (pval == None) and (self.wmod <> None):
            pval = self.wmod.forceGetInputFromPort( inputName, default_value )             
        if inputName == 'colormap':
            controller = api.get_current_controller()
            print ' Input colormap value, MID[%d], ctrl_version=%d, value = %s (defval=%s)'  % ( self.moduleID, controller.current_version, str(pval), str(default_value) )            
        return pval
          
    def setResult( self, outputName, value ): 
        if self.wmod <> None:       self.wmod.setResult( outputName, value )
        self.setParameter( outputName, value )    
    
    def getCDMSDataset(self):
        return ModuleStore.getCdmsDataset( self.datasetId )
           
    def setActiveScalars( self ):
        pass

    def getInputCopy(self):
        image_data = vtk.vtkImageData() 
        gridSpacing = self.input.GetSpacing()
        gridOrigin = self.input.GetOrigin()
        gridExtent = self.input.GetExtent()
        image_data.SetScalarType( self.input.GetScalarType() )  
        image_data.SetOrigin( gridOrigin[0], gridOrigin[1], gridOrigin[2] )
        image_data.SetSpacing( gridSpacing[0], gridSpacing[1], gridSpacing[2] )
        image_data.SetExtent( gridExtent[0], gridExtent[1], gridExtent[2], gridExtent[3], gridExtent[4], gridExtent[5] )
        return image_data

    def initializeInputs( self, **args ):
        isAnimation = args.get( 'animate', False )
        self.newDataset = False
        for inputIndex, inputPort in enumerate( self.primaryInputPorts ):
            ispec = InputSpecs()
            self.inputSpecs[ inputIndex ] = ispec
            if self.allowMultipleInputs.get( inputIndex, False ):
                try:
                    ispec.inputModuleList = self.getPrimaryInputList( port=inputPort, **args )
                    ispec.inputModule = ispec.inputModuleList[0]
                except Exception, err:
                    print>>sys.stderr, 'Error: Broken pipeline at input to module %s:\n (%s)' % ( getClassName(self), str(err) ) 
                    traceback.print_exc()
                    sys.exit(-1)
            else:
                inMod = self.getPrimaryInput( port=inputPort, **args )
                if inMod: ispec.inputModule = inMod
                
            if  ispec.inputModule <> None: 
                ispec.input =  ispec.inputModule.getOutput()                 
                ispec.updateMetadata()
                
                if inputIndex == 0:     
                    self.setParameter( 'metadata', ispec.metadata ) 
                    datasetId = self.getAnnotation( "datasetId" )
                    if datasetId <> ispec.datasetId:
#                        print>>sys.stderr, "\n ----------------------- Dataset changed, rebuild pipeline: %s -> %s ----------------------- \n" % ( datasetId, ispec.datasetId )
                        self.pipelineBuilt = False
                        self.newDataset = True
                        self.newLayerConfiguration = True
                        self.addAnnotation( "datasetId", ispec.datasetId )
                else:                   
                    self.setParameter( 'metadata-%d' % inputIndex, ispec.metadata )
 
                if self.roi == None:  
                    self.roi = ispec.metadata.get( 'bounds', None )  
                if isAnimation:
                    tval = args.get( 'timeValue', None )
                    if tval: self.timeValue = cdtime.reltime( float( args[ 'timeValue' ] ), ReferenceTimeUnits )
                    ispec.fieldData = ispec.inputModule.getFieldData() 
                else:
                    if inputIndex == 0: 
                        scalars = ispec.metadata.get( 'scalars', None )
                        self.initializeLayers( scalars )
                    
                ispec.initializeScalarRange()
                
                
            elif ( ispec.fieldData == None ): 
                ispec.initializeMetadata()

        if isAnimation:
            for configFunct in self.configurableFunctions.values(): configFunct.expandRange()
   
    def initializeLayers( self, scalars ):
        if self.activeLayer == None: 
            self.activeLayer =self.getAnnotation( 'activeLayer' )
        if self.input and not scalars:
            scalarsArray = self.input.GetPointData().GetScalars()
            if scalarsArray <> None:
                scalars = scalarsArray.GetName() 
            else:
                layerList = self.getLayerList()
                if len( layerList ): scalars = layerList[0] 
        if self.activeLayer <> scalars:
            self.updateLayerDependentParameters( self.activeLayer, scalars )
            self.activeLayer = scalars 
            self.addAnnotation( 'activeLayer', self.activeLayer  ) 
            self.seriesScalarRange = None

    def getDataValue( self, image_value, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getDataValue( image_value )
    
    def getInputSpec( self, input_index=0 ):
        return self.inputSpecs.get( input_index, None )
                
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

    def set2DOutput( self, **args ):
        if self.wmod:
            fieldData = self.getFieldData()
            portName = args.get( 'name', 'slice' )
            outputModule = AlgorithmOutputModule( fieldData=fieldData, **args )
            output =  outputModule.getOutput() 
            fd = output.GetFieldData() 
            fd.PassData( fieldData )                      
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % getClassName( self )

    def setOutputModule( self, outputModule, portName = 'volume', **args ): 
        if self.wmod:  
            fieldData = self.getFieldData()
            output =  outputModule.getOutput() 
            fd = output.GetFieldData()  
            fd.PassData( fieldData )                
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % getClassName( self )
         
           
    def addConfigurableMethod( self, name, method, key, **args ):
        self.configurableFunctions[name] = ConfigurableFunction( name, None, key, pmod=self, hasState=False, open=method, **args )

    def addConfigurableFunction(self, name, function_args, key, **args):
        self.configurableFunctions[name] = ConfigurableFunction( name, function_args, key, pmod=self, **args )

    def addConfigurableLevelingFunction(self, name, key, **args):
        self.configurableFunctions[name] = WindowLevelingConfigurableFunction( name, key, pmod=self, **args )
                        
    def addConfigurableGuiFunction(self, name, guiClass, key, **args):
        isActive = not HyperwallManager.getInstance().isClient
        guiCF = GuiConfigurableFunction( name, guiClass, key, pmod=self, active = isActive, start=self.startConfigurationObserver, update=self.updateConfigurationObserver, finalize=self.finalizeConfigurationObserver, **args )
        self.configurableFunctions[name] = guiCF

    def addUVCDATConfigGuiFunction(self, name, guiClass, key, **args):
        isActive = not HyperwallManager.getInstance().isClient
        guiCF = UVCDATGuiConfigFunction( name, guiClass, key, pmod=self, active = isActive, start=self.startConfigurationObserver, update=self.updateConfigurationObserver, finalize=self.finalizeConfigurationObserver, **args )
        self.configurableFunctions[name] = guiCF
        
    def getConfigFunction( self, name ):
        return self.configurableFunctions.get(name,None)

    def removeConfigurableFunction(self, name ):
        del self.configurableFunctions[name]

    def addConfigurableWidgetFunction(self, name, signature, widgetWrapper, key, **args):
        wCF = WidgetConfigurableFunction( name, signature, widgetWrapper, key, pmod=self, **args )
        self.configurableFunctions[name] = wCF
    
    def getConfigurationHelpText(self):
        lines = []
        lines.append( '\n <h3>Configuration Command Keys:</h3>\n' )
        lines.append(  '<table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">\n' )
        lines.append( '<tr> <th> Command Key </th> <th> Configuration </th> <th> Type </th> </tr>' )
        lines.append( ''.join( [ configFunct.getHelpText() for configFunct in self.configurableFunctions.values() ] ) )
        lines.append( '</table>' )
        return ''.join( lines ) 
          
    def initializeConfiguration(self):
        pass
        for configFunct in self.configurableFunctions.values():
            configFunct.init( self )
            
    def applyConfiguration(self, **args ):
        for configFunct in self.configurableFunctions.values():
            configFunct.applyParameter( **args  )
            
#    def setParameterInputsEnabled( self, isEnabled ):
#        for configFunct in self.configurableFunctions.values():
#            configFunct.setParameterInputEnabled( isEnabled )
# TBD: integrate
    def startConfigurationObserver( self, parameter_name, *args ):
        self.getLabelActor().VisibilityOn() 
        
    def getCurrentConfigFunction(self):
        return self.configurableFunctions.get( self.InteractionState, None )
                            
    def startConfiguration( self, x, y, config_types ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper   
        if (self.InteractionState <> None) and not self.configuring and DV3DPipelineHelper.isLevelingConfigMode():
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if configFunct.type in config_types:
                self.configuring = True
                configFunct.start( self.InteractionState, x, y )
                if self.ndims == 3: 
                    self.haltNavigationInteraction()
                    if (configFunct.type == 'leveling'): self.getLabelActor().VisibilityOn()
    
    def updateAnimation( self, animTimeData, textDisplay=None ):
        self.dvUpdate( timeData=animTimeData, animate=True )
        if textDisplay <> None:  self.updateTextDisplay( textDisplay )
        
    def stopAnimation( self ):
        self.resetNavigation()
               
    def updateConfigurationObserver( self, parameter_name, new_parameter_value, *args ):
        try:
            if self.getActivation( parameter_name ):
#                print " updateConfiguration[%s]: %s" % ( parameter_name, str(new_parameter_value) )
                self.setResult( parameter_name, new_parameter_value )
                configFunct = self.configurableFunctions[ parameter_name ]
                configFunct.setValue( new_parameter_value )
                textDisplay = configFunct.getTextDisplay()
                if textDisplay <> None:  
                    self.updateTextDisplay( textDisplay )
        except KeyError:
            print>>sys.stderr, " Can't find configuration function for parameter update: %s " % str( parameter_name )
                
    def updateLayerDependentParameters( self, old_layer, new_layer ):
#       print "updateLayerDependentParameters"
       self.newLayerConfiguration = True
#       for configFunct in self.configurableFunctions.values():
#            if configFunct.isLayerDependent:  
#                self.persistParameter( configFunct.name, None )     

    def refreshParameters( self, useInitialValue = False ):
        if useInitialValue:
           for configFunct in self.configurableFunctions.values():
               if configFunct.isLayerDependent:
                   pass        
        else:
            if self.wmod:    
                for configFunct in self.configurableFunctions.values():
                    value = self.wmod.forceGetInputFromPort( configFunct.name, None )
                    if value: 
                        self.setParameter( configFunct.name, value )
                        print "%s--> Refresh Parameter Value: %s = %s " % ( self.getName(), configFunct.name, str(value) )
            else: print " Missing wmod in %s.refreshParameters" % getClassName( self )
                    
#            for configFunct in self.configurableFunctions.values():
#                    
#                    self.persistParameter( configFunct.name, value ) 
#                configFunct.init( self )
                
                
                
#            function = getFunction( configFunct.name, functionList )
    def persistParameters( self ):
       parmRecList = []
       for configFunct in self.configurableFunctions.values():
            value = self.getCachedParameter( configFunct.name ) 
            if value: parmRecList.append( ( configFunct.name, value ), )                
       if parmRecList: self.persistParameterList( parmRecList ) 
       for configFunct in self.configurableFunctions.values(): configFunct.init( self ) 

    def persistLayerDependentParameters( self ):
       if self.newLayerConfiguration:
           parmRecList = []
           for configFunct in self.configurableFunctions.values():
                if configFunct.isLayerDependent: 
                    value = self.getCachedParameter( configFunct.name ) 
                    if value: parmRecList.append( ( configFunct.name, value ), )    
           if parmRecList: self.persistParameterList( parmRecList )  
           self.newLayerConfiguration = False    
                                    
    def parameterUpdating( self, parmName ):
        parm_update = self.parmUpdating [parmName] 
#        print "%s- check parameter updating: %s " % ( getClassName( self ), str(parm_update) )
        return parm_update
   
    def updateLevelingEvent( self, caller, event ):
        x, y = caller.GetEventPosition()
        wsize = caller.GetRenderWindow().GetSize()
        self.updateLeveling( x, y, wsize )
                
    def updateLeveling( self, x, y, wsize, **args ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper     
        if self.configuring:
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if configFunct.type == 'leveling':
                if DV3DPipelineHelper.isEligibleFunction( configFunct ): 
                    configData = configFunct.update( self.InteractionState, x, y, wsize )
                    if configData <> None:
    #                    print>>sys.stderr, " Update %s Leveling, data = %s " % ( configFunct.name, str( configData ) )
                        if self.wmod: self.wmod.setResult( configFunct.name, configData )
                        self.setParameter( configFunct.name, configData ) 
                        textDisplay = configFunct.getTextDisplay()
                        if textDisplay <> None:  self.updateTextDisplay( textDisplay )
                                     
    def getInteractionState( self, key ):
        for configFunct in self.configurableFunctions.values():
            if configFunct.matches( key ): return ( configFunct.name, configFunct.persisted )
        return ( None, None )    
    
#    def finalizeConfigurations( self ):
#        parameter_changes = []
#        for parameter_name in self.configurableFunctions.keys():
#            outputModule = wmod.get_output( parameter_name )
#            output = outputModule.getOutput()
#            self.persistParameter( parameter_name, output )    

    def finalizeLevelingEvent( self, caller, event ):
        return self.finalizeLeveling()  
    
    
                                    
    def finalizeLeveling( self ):
        if self.ndims == 3: self.getLabelActor().VisibilityOff()
        if self.configuring: 
            print " ~~~~~~ Finalize Leveling: ndims = %d, interactionState = %s " % ( self.ndims, self.InteractionState )
            HyperwallManager.getInstance().setInteractionState( None )
            self.finalizeConfigurationObserver( self.InteractionState )            
            if (self.ndims == 3) and self.iren: self.resetNavigation()
            self.configuring = False
            self.InteractionState = None
            return True
        return False
     
    def isLeveling( self ):
        if self.InteractionState <> None: 
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if (configFunct.type == 'leveling') or (configFunct.type == 'generic'):
                return True
        return False
    
#    def updateFunction(self, parameter_name, output ):
#        import api 
#        param_values_str = [ str(x) for x in output ] if isList(output) else str( output ) 
#        controller = api.get_current_controller()
#        module = controller.current_pipeline.modules[ self.moduleID ]
#        try:
#            controller.update_function( module, parameter_name, param_values_str, -1L, []  )
#        except IndexError, err:
#            print "Error updating parameter %s on module %s: %s" % ( parameter_name, getClassName( self ), str(err) )
#            pass 
#        return controller
        
    def getParameterId( self, parmName = None, input_index=0 ):
        parmIdList = []
        ispec = self.inputSpecs.get( input_index, None )
        if ispec and ispec.datasetId: parmIdList.append( ispec.datasetId )
        if self.activeLayer: parmIdList.append( self.activeLayer )
        if parmName: parmIdList.append( parmName )
        if parmIdList: return '.'.join( parmIdList )
        return 'all' 
    
    def tagCurrentVersion( self, tag ):
        import api
        ctrl = api.get_current_controller()  
        versionList = self.taggedVersionMap.setdefault( tag, [] )
        if (not versionList) or (versionList[-1] < ctrl.current_version):
            versionList.append( ctrl.current_version )
        self.versionTags[ ctrl.current_version ] = tag
        return ctrl.current_version

    def getTaggedVersionList( self, tag ):
        return self.taggedVersionMap.get( tag, None )
    
    def persistVersionMap( self ): 
        serializedVersionMap = encodeToString( self.taggedVersionMap ) 
        self.addAnnotation( 'taggedVersionMap', serializedVersionMap )
        
    def getAnnotation( self, key, default_value = None ):
        module = self.getRegisteredModule()
        if (module and module.has_annotation_with_key(key)): return module.get_annotation_by_key(key).value
        return default_value

    def initVersionMap( self ): 
        if (self.moduleID >= 0):
            serializedVersionMap = self.getAnnotation('taggedVersionMap')
            if serializedVersionMap: 
                try:
                    self.taggedVersionMap = decodeFromString( serializedVersionMap.strip(), {} ) 
                    for tagItem in self.taggedVersionMap.items():
                        for version in tagItem[1]:
                            self.versionTags[ version ] = tagItem[0]
                except Exception, err:
                    print "Error unpacking taggedVersionMap, serialized data: %s, err: %s" % ( serializedVersionMap, str(err) )
                    self.taggedVersionMap = {}
                
    def getTaggedVersion( self, tag ):
        versionList = self.taggedVersionMap.get( tag, None )
        return versionList[-1] if versionList else -1                     

#    def persistParameter( self, parameter_name, output, **args ):
#        if output <> None: 
#            import api
#            DV3DConfigurationWidget.savingChanges = True
#            ctrl = api.get_current_controller()
#            param_values_str = [ str(x) for x in output ] if isList(output) else str( output )  
#            v0 = ctrl.current_version
#            api.change_parameter( self.moduleID, parameter_name, param_values_str )
#            v1 = ctrl.current_version
#            tag = self.getParameterId()             
#            taggedVersion = self.tagCurrentVersion( tag )
#            new_parameter_id = args.get( 'parameter_id', tag )
#            self.setParameter( parameter_name, output, new_parameter_id )
#            print " PM: Persist Parameter %s -> %s, tag = %s, taggedVersion=%d, new_id = %s, version => ( %d -> %d ), module = %s" % ( parameter_name, str(output), tag, taggedVersion, new_parameter_id, v0, v1, getClassName( self ) )
#            DV3DConfigurationWidget.savingChanges = False

    def refreshVersion(self):
        pass

#    def change_parameters1( self, parmRecList, controller ): 
#        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper         
#        """change_parameters(
#                            parmRecList: [ ( function_name: str, param_list: list(str) ) ] 
#                            controller: VistrailController,
#                            ) -> None
#        Note: param_list is a list of strings no matter what the parameter type!
#        """
#        try:
##            controller.current_pipeline = self.pipeline # DV3DPipelineHelper.getPipeline( cell_address )
##            module = self.pipeline.modules[self.moduleID]            #    controller.update_functions( module, parmRecList )
# #    controller.update_functions( module, parmRecList )
#            cur_version = None
#            try:
#                module = controller.current_pipeline.modules[self.moduleID] 
#            except KeyError:
#                if hasattr(controller, 'uvcdat_controller'):
#                    cur_version = controller.current_version
#                    ( sheetName, cell_addr ) = DV3DPipelineHelper.getCellAddress( self.pipeline )
#                    coords = ( ord(cell_addr[0])-ord('A'), int( cell_addr[1] ) - 1 )
#                    cell = controller.uvcdat_controller.sheet_map[ sheetName ][ coords ]
#                    controller.change_selected_version( cell.current_parent_version )
#                    print " _________________________________ Changing controller version: %d -> %d based on cell [%s]%s  _________________________________ " % ( cur_version, cell.current_parent_version, sheetName, str(coords) )
#                    module = controller.current_pipeline.modules[ self.moduleID ] 
#                else:
#                    print>>sys.stderr, "Error changing parameter in module %d, parm: %s: Wrong controller version." % ( self.moduleID, str(parmRecList) )                          
#            op_list = []
#            print "Module[%d]: Persist Parameter: %s, controller: %x " % ( self.moduleID, str(parmRecList), id(controller) )
#            for parmRec in parmRecList:  op_list.extend( controller.update_function_ops( module, parmRec[0], parmRec[1] ) )
#            action = create_action( op_list ) 
#            controller.add_new_action(action)
#            controller.perform_action(action)
#            if cur_version: controller.change_selected_version(cur_version) 
#            if hasattr(controller, 'uvcdat_controller'):
#                controller.uvcdat_controller.cell_was_changed(action)
#        except Exception, err:
#            print>>sys.stderr, "Error changing parameter in module %d: parm: %s, error: %s" % ( self.moduleID, str(parmRecList), str(err) )

#    def adjustControllerVersion( self, controller ):
#        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper         
#        cur_version = None
#        if hasattr(controller, 'uvcdat_controller') and not self.moduleID in controller.current_pipeline.modules :
#            cur_version = controller.current_version
#            ( sheetName, address ) = DV3DPipelineHelper.getCellAddress( self.pipeline )
#            sheetName = sheetTabWidget.getSheetName()
#            coords = ( ord(cell_addr[0])-ord('A'), int( cell_addr[1] ) - 1 )
#            cell = controller.uvcdat_controller.sheet_map[ sheetName ][ coords ]
#            controller.change_selected_version( cell.current_parent_version )
#            print " _________________________________ Changing controller version: %d -> %d based on cell [%s]%s  _________________________________ " % ( cur_version, cell.current_parent_version, sheetName, str(coords) )
#        return cur_version
#            

    def change_parameters( self, parmRecList ):
        import api
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper  
        """change_parameters(
                            parmRecList: [ ( function_name: str, param_list: list(str) ) ] 
                            controller: VistrailController,
                            ) -> None
        Note: param_list is a list of strings no matter what the parameter type!
        """
        
        
        controller = api.get_current_controller() 
        try:
            ( sheetName, cell_address ) = DV3DPipelineHelper.getCellCoordinates( self.moduleID )
            proj_controller = controller.uvcdat_controller
            pcoords =list( proj_controller.current_cell_coords ) if proj_controller.current_cell_coords else None
            if not pcoords or ( pcoords[0] <> cell_address[0] ) or ( pcoords[1] <> cell_address[1] ):
                proj_controller.current_cell_changed(  sheetName, cell_address[0], cell_address[1]  )
            else: pcoords = None 
            cell = proj_controller.sheet_map[ sheetName ][ cell_address ]
            current_version = cell.current_parent_version 
            controller.change_selected_version( current_version )
            pipeline = controller.vistrail.getPipeline( current_version )
        except Exception, err:
            print>>sys.stderr, "Error getting current pipeline: %s " % str( err )
            pipeline = controller.current_pipeline
            proj_controller = None
            current_version = controller.current_version
            cell_address = ( None, None )
            
#        print '-'*50      
#        print 'Persist parameter: coords=%s, version=%d, controller=%x, proj_controller=%x, controller version=%d, pid=%d, modules=%s' % ( str(cell_address), current_version, id(controller), id(proj_controller), controller.current_version, pipeline.db_id, [ mid for mid in pipeline.modules ] )    
#        print '-'*50      

        try:
            module = pipeline.modules[self.moduleID] 
        except KeyError:
            print>>sys.stderr, "Error changing parameter in module %d, parm: %s: Module not in current controller pipeline." % ( self.moduleID, str(parmRecList) )  
            return
        try:
            op_list = []
            print "Module[%d]: Persist Parameter: %s, controller: %x " % ( self.moduleID, str(parmRecList), id(controller) )
            for parmRec in parmRecList:  
                op_list.extend( controller.update_function_ops( module, parmRec[0], parmRec[1] ) )
#                if parmRec[0] == 'colorScale':
#                    print 'x'
            action = create_action( op_list ) 
            controller.add_new_action(action)
            controller.perform_action(action)
            if proj_controller:
                proj_controller.cell_was_changed(action)
            if pcoords: 
                proj_controller.current_cell_changed(  sheetName, pcoords[0], pcoords[1]  )
                
        except Exception, err:
            print>>sys.stderr, "Error changing parameter in module %d: parm: %s, error: %s" % ( self.moduleID, str(parmRecList), str(err) )


               
    def persistParameterList( self, parmRecList, **args ):
        if parmRecList and not self.isClient: 
            DV3DConfigurationWidget.savingChanges = True
            strParmRecList = []
            self.getDatasetId( **args )
            for parmRec in parmRecList:
                parameter_name = parmRec[0]
                output = parmRec[1]
                param_values_str = [ str(x) for x in output ] if isList(output) else str( output )  
                strParmRecList.append( ( parameter_name, param_values_str ) )
            self.change_parameters( strParmRecList )           
            tag = self.getParameterId()
#            taggedVersion = self.tagCurrentVersion( tag )
            listParameterPersist = args.get( 'list', True )  
            for parmRec in parmRecList:
                parameter_name = parmRec[0]
                output = parmRec[1]
                self.setParameter( parameter_name, output, tag ) 
                if listParameterPersist: self.persistedParameters.append( parameter_name )
#            print " %s.Persist-Parameter-List[%s] (v. %s): %s " % ( self.getName(), tag, str(taggedVersion), str(parmRecList) )
#            self.persistVersionMap() 
#            updatePipelineConfiguration = args.get( 'update', False ) # False )                  
#            if updatePipelineConfiguration: ctrl.select_latest_version() 
            DV3DConfigurationWidget.savingChanges = False
#            self.wmod = None
                         
    def finalizeParameter(self, parameter_name, **args ):
        if ( parameter_name == None ) or ( parameter_name == 'None' ):
            return
        try:
            output = self.getParameter( parameter_name )
            assert (output <> None), "Attempt to finalize parameter that has not been cached." 
            self.persistParameterList( [ (parameter_name, output) ] )             
        except Exception, err:
            print "Error changing parameter %s for %s module: %s" % ( parameter_name, getClassName( self ), str(err) )
     
    def writeConfigurationResult( self, config_name, config_data, **args ):
        print "MODULE[%d]: Persist Config Parameter %s -> %s "  % ( self.moduleID, config_name, str(config_data) )     
        if self.wmod: self.wmod.setResult( config_name, config_data )
        self.setParameter( config_name, config_data )
        self.finalizeConfigurationObserver( config_name, **args )
           
    def finalizeConfigurationObserver( self, parameter_name, **args ):
        self.finalizeParameter( parameter_name, **args )    
        for parameter_name in self.getModuleParameters(): self.finalizeParameter( parameter_name, *args ) 
        self.endInteraction( **args ) 
        
    def endInteraction( self, **args ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper 
        notifyHelper =  args.get( 'notifyHelper', True )    
        if (self.ndims == 3) and self.iren: self.resetNavigation() 
        self.configuring = False
        if notifyHelper: DV3DPipelineHelper.endInteraction()
        self.InteractionState = None
        self.enableVisualizationInteraction()

    def setActivation( self, name, value ):
        bval = bool(value)  
        self.activation[ name ] = bval
#        print "Set activation for %s[%s] to %s "% ( self.getName(), name, bval ) 
        
    def getActivation( self, name ): 
        return self.activation.get( name, True )

    def getRegisteredModule(self):
        pipeline = self.getCurrentPipeline()
        mid = self.moduleID
        module = pipeline.modules.get( mid, None )
        return module
        
    def updateModule(self, **args ):
        pass
   
    def getCurrentPipeline(self):
        if self.pipeline <> None:
            return self.pipeline
        else:
            import api
            controller = api.get_current_controller() 
            pipeline = controller.current_pipeline
            return pipeline
    
    def getOutputModules( self, port ):
        pipeline = self.getCurrentPipeline()
        mid = self.moduleID
        modules = pipeline.get_outputPort_modules( mid, port )
        return modules
 
    def getRegisteredDescriptor( self ):       
        registry = get_module_registry()
        module = self.getRegisteredModule()
        descriptor = registry.get_descriptor_by_name( module.package, module.name, module.namespace )
        return module, descriptor        
        
    def getModuleParameters( self ):
        return []

    def setTimeValue( self, relTimeValue ):
        self.timeValue = cdtime.reltime( relTimeValue, ReferenceTimeUnits )
        self.onNewTimestep()
            
    def getTimeValue( self ):
        return self.timeValue.value

    def onNewTimestep(self):
        pass                                              

TextBlinkEventEventType =  QEvent.User + 2

class TextBlinkEvent( QEvent ):
    
    def __init__( self, type, textOn ):
         QEvent.__init__ ( self, TextBlinkEventEventType )
         self.textType = type
         self.textOn = textOn
         
class TextBlinkThread( threading.Thread ):

    def __init__( self, target, type, **args ):
        threading.Thread.__init__( self )
        self.isActive = False 
        self.daemon = True
        self.target = target
        self.timestep = args.get( 'timestep', 0.5 )
        self.nblinks = args.get( 'nblinks', -1 )
        self.textType = type
           
    def stop(self):
        self.isActive = False

    def run(self):
        self.isActive = True
        textOn = True
        blinkCount = 0
        while self.isActive:
            QApplication.postEvent( self.target, TextBlinkEvent( self.textType, textOn ) )
            delay_time = self.timestep*2 if textOn else self.timestep
            time.sleep( delay_time ) 
            textOn = not textOn 
            if textOn:
                blinkCount += 1
                if self.nblinks > 0 and blinkCount >= self.nblinks: return
       
class PersistentVisualizationModule( PersistentModule ):

    NoModifier = 0
    ShiftModifier = 1
    CtrlModifier = 2
    AltModifier = 3
    
    LEFT_BUTTON = 0
    RIGHT_BUTTON = 1
    
    renderMap = {} 
    moduleDocumentationDialog = None 

    def __init__( self, mid, **args ):
        self.currentButton = None
        PersistentModule.__init__(self, mid, **args  )
        self.modifier = self.NoModifier
        self.acceptsGenericConfigs = False
        self._max_scalar_value = None
        self.colormapManagers = {}
        self.labelBuff = "NA                          "
        self.renderer = None
        self.iren = None 
        self.gui = None
        self.titleBuffer = None
        self.instructionBuffer = " "
        self.textBlinkThread = None 
        self.activation = {}
        self.isAltMode = False
        self.stereoEnabled = 0
        self.navigationInteractorStyle = None
        self.configurationInteractorStyle = vtk.vtkInteractorStyleUser()

    def GetRenWinID(self):
        return id( self.renderer.GetRenderWindow() ) if self.renderer else -1

    def enableVisualizationInteraction(self): 
        pass
 
    def disableVisualizationInteraction(self): 
        pass
    
                      
    def setInputZScale( self, zscale_data, input_index=0, **args  ):
        ispec = self.inputSpecs[ input_index ] 
        if ispec.input <> None:
            spacing = ispec.input.GetSpacing()
            ix, iy, iz = spacing
            sz = zscale_data[1]
            if iz <> sz:
#                print " PVM >---------------> Change input zscale: %.4f -> %.4f" % ( iz, sz )
                ispec.input.SetSpacing( ix, iy, sz )  
                ispec.input.Modified() 
                return True
        return False
                    
    def getScaleBounds(self):
        return [ 0.5, 100.0 ]
        
    def getTitle(self):
        return self.titleBuffer
                                
    def TestObserver( self, caller=None, event = None ):
        pass 

    def setChartDataOutput( self, view, **args ):  
        portName = args.get( 'name', 'chart' )
        outputModule = AlgorithmOutputModule2D( view, **args )
        if self.wmod == None:
            print>>sys.stderr, "Missing wmod in setChartDataOutput for class %s" % ( getClassName( self ) )
        else:
            self.wmod.setResult( portName, outputModule )
            print "setChartDataOutput for class %s" % ( getClassName( self ) ) 
    
    def set3DOutput( self, input_index=0, **args ):  
        portName = args.get( 'name', 'volume' )
        ispec = self.inputSpecs[ input_index ] 
        fieldData = ispec.getFieldData()
        if not ( ('output' in args) or ('port' in args) ):
            if ispec.input <> None: 
                args[ 'output' ] = ispec.input
            elif ispec.inputModule <> None: 
                port = ispec.inputModule.getOutputPort()
                if port: args[ 'port' ] = port
                else:    args[ 'output' ] = ispec.inputModule.getOutput()
        if self.renderer == None: 
            self.renderer = vtk.vtkRenderer()
        outputModule = AlgorithmOutputModule3D( self.renderer, fieldData=fieldData, **args )
        output =  outputModule.getOutput() 
#        print "Setting 3D output for port %s" % ( portName ) 
        if output <> None:
            fd = output.GetFieldData() 
            fd.PassData( fieldData ) 
        if self.wmod == None:
            print>>sys.stderr, "Missing wmod in set3DOutput for class %s" % ( getClassName( self ) )
        else:
            self.wmod.setResult( portName, outputModule )
#            print "set3DOutput for class %s" % ( getClassName( self ) ) 
             
    def getDownstreamCellModules( self, selectedOnly=False ): 
        from packages.vtDV3D import ModuleStore
        import api
        controller = api.get_current_controller()
        moduleIdList = [ self.moduleID ]
        rmodList = []
        while moduleIdList:
            connectedModuleIds = getConnectedModuleIds( controller, moduleIdList.pop(), 'volume', False )
            for ( moduleId, portName ) in connectedModuleIds:
                module = ModuleStore.getModule( moduleId )
                if module: 
                    if getClassName(module) in [ "PM_MapCell3D", "PM_CloudCell3D" ]:
                        if (not selectedOnly) or module.isSelected(): rmodList.append( module )
                    else:
                        moduleIdList.append( moduleId )
        return rmodList

    def updateTextDisplay( self, text = None ):
        if (text <> None) and (self.renderer <> None): 
            self.labelBuff = str(text)
            if (self.ndims == 3):                
                self.getLabelActor().VisibilityOn()
                
    def displayInstructions( self, text ):
        if (self.renderer <> None): 
            self.instructionBuffer = str(text)
            if (self.ndims == 3):                
                actor = self.getInstructionActor()
                if actor:
                    actor.VisibilityOn()
                    self.render()
                    self.textBlinkThread = TextBlinkThread( self, 'instructions', nblinks=3 )
                    self.textBlinkThread.start()
                    return True
        return False

    def clearInstructions( self ):
        actor = self.getInstructionActor()
        if actor:
            if self.textBlinkThread:
                self.textBlinkThread.stop() 
                self.textBlinkThread = None
            actor.VisibilityOff()
            
    def toggleTextVisibility( self, textType, textOn ):
        actor = None
        if textType == 'instructions':
            actor = self.getInstructionActor()
        if actor:
            if textOn:  actor.VisibilityOn()
            else:       actor.VisibilityOff()
            self.render()

    def event(self, e): 
        if e.type() == TextBlinkEventEventType: 
            self.toggleTextVisibility( e.textType, e.textOn ) 
            return True
        return False        
            
    def UpdateCamera(self):
        pass
            
    def isBuilt(self):
        return self.pipelineBuilt

    def execute(self, **args ):
#        print "Execute Module[ %s ]: %s " % ( str(self.moduleID), str( getClassName( self ) ) )
        initConfig = False
        isAnimation = args.get( 'animate', False )
        if not self.isBuilt():
            if self.ndims == 3: self.initializeRendering()
            
            self.buildPipeline()
            
            if self.ndims == 3: self.finalizeRendering() 
            self.pipelineBuilt = True
            initConfig = True
            
        if not initConfig: self.applyConfiguration( **args  )   
        
        self.updateModule( **args ) 
        
        if not isAnimation:
#            self.displayInstructions( "Shift-right-click for config menu" )
            if initConfig: 
                self.initializeConfiguration()  
            else:   
                self.applyConfiguration()
        
    def buildPipeline(self): 
        pass 

    def getLut( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut
    
    def getColormapManager( self, **args ):
        cmap_index = args.get('index',0)
        name = args.get('name',None)
        invert = args.get('invert',None)
        cmap_mgr = self.colormapManagers.get( cmap_index, None )
        if cmap_mgr == None:
            lut = vtk.vtkLookupTable()
            cmap_mgr = ColorMapManager( lut ) 
            self.colormapManagers[cmap_index] = cmap_mgr
        if (invert <> None): cmap_mgr.invertColormap = invert
        if name:   cmap_mgr.load_lut( name )
        return cmap_mgr

        
    def setColormap( self, data, cmap_index=0 ):
        colormapName = str(data[0])
        invertColormap = int( data[1] )
        enableStereo = int( data[2] )
        ispec = self.getInputSpec( cmap_index )  
        if  (ispec <> None) and (ispec.input <> None):         
    #        self.addMetadata( { 'colormap' : self.getColormapSpec() } )
    #        print ' ~~~~~~~ SET COLORMAP:  --%s--  ' % self.colormapName
            self.updateStereo( enableStereo )
            colormapManager = self.getColormapManager( name=colormapName, invert=invertColormap, index=cmap_index, units=self.getUnits(cmap_index) )
            if self.createColormap and ( colormapManager.colorBarActor == None ): 
                cmap_pos = [ 0.9, 0.2 ] if (cmap_index==0) else [ 0.02, 0.2 ]
                units = self.getUnits( cmap_index )
                cm_title = "%s\n(%s)" % ( ispec.metadata.get('scalars',''), units ) if ispec.metadata else units 
                self.renderer.AddActor( colormapManager.createActor( pos=cmap_pos, title=cm_title ) )
            self.render() 
            return True
        return False

    def updateStereo( self, enableStereo ):   
        if self.iren:
            renwin = self.iren.GetRenderWindow()
            if enableStereo:
                renwin.StereoRenderOn()
                self.stereoEnabled = 1
            else:
                renwin.StereoRenderOff()
                self.stereoEnabled = 0

#            keycode = int('3')
#            self.iren.SetKeyEventInformation( 0, 0, keycode, 0, "3" )     
#            self.iren.InvokeEvent( vtk.vtkCommand.KeyPressEvent )
            
            
    def getColormap(self, cmap_index = 0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return [ colormapManager.colormapName, colormapManager.invertColormap, self.stereoEnabled ]

    def render( self ):
        if self.renderer:   
            rw = self.renderer.GetRenderWindow()
            if rw <> None: rw.Render()
       
    def setMaxScalarValue(self, iDType ):  
        if iDType   == vtk.VTK_UNSIGNED_CHAR:   self._max_scalar_value = 255
        elif iDType == vtk.VTK_UNSIGNED_SHORT:  self._max_scalar_value = 256*256-1
        elif iDType == vtk.VTK_SHORT:           self._max_scalar_value = 256*128-1
        else:                                   self._max_scalar_value = self.getRangeBounds()[1]  
                
    def initializeRendering(self):
        inputModule = self.getPrimaryInput()
        renderer_import = inputModule.getRenderer() if  inputModule <> None else None 
        self.renderer = vtk.vtkRenderer() if renderer_import == None else renderer_import
        self.renderer.AddObserver( 'ModifiedEvent', self.activateEvent )
        self.labelBuff = "NA                          "
#        if self.createColormap: 
#            colormapManager = self.getColormapManager( )
#            self.renderer.AddActor( colormapManager.createActor() )

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
        
    def getProp( self, ptype, id = None ):
      try:
          props = self.renderer.GetViewProps()
          nitems = props.GetNumberOfItems()
          for iP in range(nitems):
              prop = props.GetItemAsObject(iP)
              if prop.IsA( ptype ):
                  if not id or (prop.id == id):
                      return prop
      except: 
          pass
      return None
  
    def creatTitleActor( self ):
        pass
    
    def setTextPosition(self, textActor, pos, size=[400,30] ):
        vpos = [ 2, 2 ]
        if self.renderer: 
            vp = self.renderer.GetSize()
            vpos = [ pos[i]*vp[i] for i in [0,1] ]
        textActor.GetPositionCoordinate().SetValue( vpos[0], vpos[1] )      
        textActor.GetPosition2Coordinate().SetValue( vpos[0] + size[0], vpos[1] + size[1] )      
    
    def createTextActor( self, id, **args ):
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
        textActor.id = id
        return textActor
          
    def getLabelActor(self):
        return self.getTextActor( 'label', self.labelBuff, (.01, .95), size = VTK_NOTATION_SIZE, bold = True  )

    def getTitleActor(self):
        return self.getTextActor( 'title', self.titleBuffer,  (.01, .01 ), size = VTK_TITLE_SIZE, bold = True  )

    def getInstructionActor(self):
        return self.getTextActor( 'instruction', self.instructionBuffer,  (.1, .85 ), size = VTK_INSTRUCTION_SIZE, bold = True, color = ( 1.0, 0.1, 0.1 ), opacity=0.65  )

    def getTextActor( self, id, text, pos, **args ):
        textActor = self.getProp( 'vtkTextActor', id  )
        if textActor == None:
            textActor = self.createTextActor( id, **args  )
            if self.renderer: self.renderer.AddViewProp( textActor )
        self.setTextPosition( textActor, pos )
        text_lines = text.split('\n')
        linelen = len(text_lines[-1])
        if linelen < MIN_LINE_LEN: text += (' '*(MIN_LINE_LEN-linelen)) 
        text += '.'
        textActor.SetInput( text )
        textActor.Modified()
        return textActor

    def finalizeRendering(self):
        pass

    def refreshCells(self):
        spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
        spreadsheetWindow.repaint()
        
    def isConfigStyle( self, iren ):
        if not iren: return False
        return getClassName( iren.GetInteractorStyle() ) == getClassName( self.configurationInteractorStyle )
      
    def activateEvent( self, caller, event ):
        if self.renderer == None:
            print>>sys.stderr, "Error, no renderer available for activation."
        else:
            self.renwin = self.renderer.GetRenderWindow( )
            if self.renwin <> None:
                iren = self.renwin.GetInteractor() 
                if ( iren <> None ) and not self.isConfigStyle( iren ):
                    if ( iren <> self.iren ):
                        if self.iren == None: 
                            self.renwin.AddObserver("AbortCheckEvent", CheckAbort)
                        self.iren = iren
                        self.activateWidgets( self.iren )                                  
                        self.iren.AddObserver( 'CharEvent', self.setInteractionState )                   
                        self.iren.AddObserver( 'MouseMoveEvent', self.updateLevelingEvent )
#                        self.iren.AddObserver( 'LeftButtonReleaseEvent', self.finalizeLevelingEvent )
                        self.iren.AddObserver( 'AnyEvent', self.onAnyEvent )  
#                        self.iren.AddObserver( 'MouseWheelForwardEvent', self.refineLevelingEvent )     
#                        self.iren.AddObserver( 'MouseWheelBackwardEvent', self.refineLevelingEvent )     
                        self.iren.AddObserver( 'CharEvent', self.onKeyPress )
                        self.iren.AddObserver( 'KeyReleaseEvent', self.onKeyRelease )
                        self.iren.AddObserver( 'LeftButtonPressEvent', self.onLeftButtonPress )
                        self.iren.AddObserver( 'ModifiedEvent', self.onModified )
                        self.iren.AddObserver( 'RenderEvent', self.onRender )                   
                        self.iren.AddObserver( 'LeftButtonReleaseEvent', self.onLeftButtonRelease )
                        self.iren.AddObserver( 'RightButtonReleaseEvent', self.onRightButtonRelease )
                        self.iren.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )
                        for configurableFunction in self.configurableFunctions.values():
                            configurableFunction.activateWidget( iren )
                    self.updateInteractor()  
                    
    def updateInteractor(self): 
        pass
                    
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
#        if key == self.current_key:
#            t = time.time()
#            if( ( t - self.event_time ) < 0.01 ): return
#        self.event_time = time.time()
#        self.current_key = key

    def refineLevelingEvent( self, caller, event ):
        print " refineLevelingEvent: { %s } " % ( str( event ) )      

    def toggleColormapVisibility(self):
        for colormapManager in self.colormapManagers.values():
            colormapManager.toggleColormapVisibility()
            
    def processKeyEvent( self, key, caller=None, event=None ):
#        print "process Key Event, key = %s" % ( key )
        if key == 'h': 
            if  PersistentVisualizationModule.moduleDocumentationDialog == None:
                modDoc = ModuleDocumentationDialog()
                modDoc.addDocument( 'configuration', PersistentModule.__doc__ )
                PersistentVisualizationModule.moduleDocumentationDialog = modDoc
            if self.documentation == None:
                self.generateDocumentation()           
                PersistentVisualizationModule.moduleDocumentationDialog.addDocument( 'modules', self.documentation )
                PersistentVisualizationModule.moduleDocumentationDialog.addCloseObserver( self.clearDocumenation )
            PersistentVisualizationModule.moduleDocumentationDialog.show()
        elif ( self.createColormap and ( key == 'l' ) ): 
            self.toggleColormapVisibility()                         
            self.render() 
        elif (  key == 'r'  ):
            self.resetCamera()              
            if  len(self.persistedParameters):
                pname = self.persistedParameters.pop()
                configFunct = self.configurableFunctions[pname]
                param_value = configFunct.reset() 
                if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True, list=False )                
        else:
            ( state, persisted ) =  self.getInteractionState( key )
#            print " %s Set Interaction State: %s ( currently %s) " % ( str(self.__class__), state, self.InteractionState )
            if state <> None: 
                self.updateInteractionState( state, self.isAltMode  )                 
                HyperwallManager.getInstance().setInteractionState( state, self.isAltMode )
                self.isAltMode = False 
                
    def resetCamera(self):
        pass
                
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
                configFunct = ConfigurableFunction( state, None, None, pmod=self )              
                self.configurableFunctions[ state ] = configFunct
            if configFunct:
                configFunct.open( state, self.isAltMode )
                self.InteractionState = state                   
                self.LastInteractionState = self.InteractionState
                self.disableVisualizationInteraction()
        return rcf
                   
    def endInteraction( self, **args ):
        PersistentModule.endInteraction( self, **args  )
        if self.ndims == 3: self.getLabelActor().VisibilityOff()              
        
    def onLeftButtonRelease( self, caller, event ):
#        print " --- Persistent Module: LeftButtonRelease --- "
        self.currentButton = None 
#        istyle = self.iren.GetInteractorStyle()                       
#        style_name = istyle.__class__.__name__
#        print " ~~~~~~~~~ Current Interactor Style:  %s " % ( style_name )
    
    def onRightButtonRelease( self, caller, event ):
        self.currentButton = None 
               
    def onKeyRelease( self, caller, event ):
        pass

    def setModifiers(self, caller, event):
        key = caller.GetKeyCode() 
        keysym = caller.GetKeySym()
        if ( ord(key) == 0 ):
            if  ( keysym.lower().find('alt') == 0 ): 
                self.modifier = self.AltModifier
            elif  ( keysym.lower().find('shift') == 0 ): 
                self.modifier = self.ShiftModifier
            else: 
                self.modifier = self.CtrlModifier
    
    def unsetModifiers( self, caller, event ):
        self.modifier = self.NoModifier
 

            
#    def checkFunctionName( self, module, parameter_name ):
#            old_id = -1
#            function = None
#            for old_function in module.functions:
#                if old_function.name == parameter_name:
#                    old_id = old_function.real_id
#            if old_id >= 0:
#                function = module.function_idx[old_id]
#            if function <> None:
#                print>>sys.stderr, "  \n  !! Warning: Configurable Function Name Clash in %s Module: %s !! \n " % ( str(self.__class__), parameter_name )

        
#        if provType == self.ColorMapScaling: 
#            output = self.get_output( 'colorScale' )
#            controller.update_function( module, 'colorScale', output )
#        if provType == self.TransferFunctionScaling: 
#            output = self.get_output( 'functionScale' )
#            controller.update_function( module, 'functionScale', output )
#        if provType == self.OpacityScaling: 
#            output = self.get_output( 'opacityScale' )
#            controller.update_function( module, 'opacityScale', output )
                
    def activateWidgets(self, iren):
        return 0
    
    def onLeftButtonPress( self, caller, event ):
        istyle = self.iren.GetInteractorStyle()
#        print "(%s)-LBP: s = %s, nis = %s " % ( getClassName( self ), getClassName(istyle), getClassName(self.navigationInteractorStyle) )
        if not self.finalizeLeveling(): 
            shift = caller.GetShiftKey()
            self.currentButton = self.LEFT_BUTTON
            self.clearInstructions()
            self.UpdateCamera()   
            x, y = caller.GetEventPosition()      
            self.startConfiguration( x, y, [ 'leveling', 'generic' ] )  
        return 0

    def onRightButtonPress( self, caller, event ):
        shift = caller.GetShiftKey()
        self.currentButton = self.RIGHT_BUTTON
        self.clearInstructions()
        self.UpdateCamera()
        x, y = caller.GetEventPosition()
        if self.InteractionState <> None:
            self.startConfiguration( x, y,  [ 'generic' ] )
#            print " ~~~~~~~~~ RBP: Set Interactor Style: Navigation:  %s %x" % ( self.navigationInteractorStyle.__class__.__name__, id(self.iren) )          
        return 0

    def haltNavigationInteraction(self):
        if self.iren:
            istyle = self.iren.GetInteractorStyle()  
            if self.navigationInteractorStyle == None:
                self.navigationInteractorStyle = istyle    
            self.iren.SetInteractorStyle( self.configurationInteractorStyle )  
#            print "\n ---------------------- [%s] halt Navigation: nis = %s, is = %s  ----------------------  \n" % ( getClassName(self), getClassName(self.navigationInteractorStyle), getClassName(istyle)  ) 
    
    def resetNavigation(self):
        if self.iren:
            if self.navigationInteractorStyle <> None: 
                self.iren.SetInteractorStyle( self.navigationInteractorStyle )
            istyle = self.iren.GetInteractorStyle()  
#            print "\n ---------------------- [%s] reset Navigation: nis = %s, is = %s  ---------------------- \n" % ( getClassName(self), getClassName(self.navigationInteractorStyle), getClassName(istyle) )        
            self.enableVisualizationInteraction()

    def onModified( self, caller, event ):
        return 0

    def onRender( self, caller, event ):
        return 0
             
    def onKeyPress( self, caller, event ):
        return 0
 
    def getCellAddress(self):  
        cell_items = self.renderMap.items()
        rw = self.renderer.GetRenderWindow() if self.renderer else None
        if rw:
            for cell_item in cell_items:
                crw = cell_item[1].GetRenderWindow()
                if id( crw ) == id( rw ):
                    return cell_item[0]
        return None
        
    def getActiveIrens(self):
        sheetTabWidget = getSheetTabWidget()
        selected_cells = sheetTabWidget.getSelectedLocations() 
        irens = []
        for cell in selected_cells:
            cell_spec = "%s%s" % ( chr(ord('A') + cell[1] ), cell[0]+1 )
            iren = PersistentVisualizationModule.renderMap.get( cell_spec, None )
            irens.append( iren )
        return irens
   
    @staticmethod
    def getValidIrens():
        return PersistentVisualizationModule.renderMap.values()
    
    def onAnyEvent(self, caller, event ):
        if self.iren:
            istyle = self.iren.GetInteractorStyle() 
#            print "onAnyEvent: %s, iren style = %s, interactionState = %s  " % ( str( event ), istyle.__class__.__name__, self.InteractionState )

#        isKeyEvent = ( event in [ 'KeyPressEvent', 'CharEvent', 'KeyReleaseEvent' ] )
#        if isKeyEvent:
#            sheetTabWidget = getSheetTabWidget()
#            selected_cells = sheetTabWidget.getSelectedLocations() 
#            for cell in selected_cells:
#                cell_spec = "%s%s" % ( chr(ord('A') + cell[0] ), cell[1]+1 )
#                iren = PersistentVisualizationModule.renderMap.get( cell_spec, None )
#                if iren <> caller:
#                    print " >> %s Event: %s " % ( str(caller.__class__), event )
##                    renderer.SetEventInformation(int x, int y, int ctrl=0, int shift=0, char keycode=0, int repeatcount=0, const char *keysym=0)
#                    iren.SetKeyEventInformation( caller.GetControlKey(), caller.GetShiftKey(), caller.GetKeyCode(), caller.GetRepeatCount(),  caller.GetKeySym() )
#                    if   event == 'KeyPressEvent':    iren.KeyPressEvent()
#                    elif event == 'KeyReleaseEvent':  iren.KeyReleaseEvent()
#                    elif event == 'CharEvent':        iren.CharEvent()
        return 0
    
    def clearDocumenation(self):
        PersistentVisualizationModule.moduleDocumentationDialog.clearTopic( 'modules' )
        self.documentation = None


        
