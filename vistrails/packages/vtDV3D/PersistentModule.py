'''
Created on Dec 17, 2010

@author: tpmaxwel
'''

import vtk, sys, time, threading, inspect, gui
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
        self.moduleID = mid
        self.pipeline = args.get( 'pipeline', None )
        self.units = ''
        self.taggedVersionMap = {}
        self.persistedParameters = []
        self.versionTags = {}
        self.initVersionMap()
        self.datasetId = None
        self.fieldData = None
        role = get_hyperwall_role( )
        self.isClient = ( role == 'hw_client' )
        self.isServer = ( role == 'hw_server' )
        self.rangeBounds = None
        self.timeStepName = 'timestep'
        self.newDataset = False
        self.scalarRange = None
        self.seriesScalarRange = None
        self.wmod = None
        self.inputModule = None
        self.allowMultipleInputs = False
        self.newLayerConfiguration = False
        self.inputModuleList = None
        self.nonFunctionLayerDepParms = args.get( 'layerDepParms', [] )
        self.input =  None
        self.roi = None 
        self.activeLayer = None
        self.configurableFunctions = {}
        self.configuring = False
        self.InteractionState = None
        self.LastInteractionState = None
        self.requiresPrimaryInput = args.get( 'requiresPrimaryInput', True )
        self.createColormap = args.get( 'createColormap', True )
        self.parmUpdating = {}
        self.ndims = args.get( 'ndims', 3 ) 
        self.primaryInputPort = 'slice' if (self.ndims == 2) else 'volume' 
        self.primaryMetaDataPort = self.primaryInputPort
        self.documentation = None
        self.parameterCache = {}
        self.timeValue = cdtime.reltime( 0.0, ReferenceTimeUnits ) 
        if self.createColormap:
            self.addConfigurableGuiFunction( 'colormap', ColormapConfigurationDialog, 'c', label='Choose Colormap', setValue=self.setColormap, getValue=self.getColormap, layerDependent=True )
        self.addConfigurableGuiFunction( self.timeStepName, AnimationConfigurationDialog, 'a', label='Animation', setValue=self.setTimeValue, getValue=self.getTimeValue )
#        self.addConfigurableGuiFunction( 'layer', LayerConfigurationDialog, 'l', setValue=self.setLayer, getValue=self.getLayer )

#    def getSelectionStatus( self ):
#        if self.fieldData:
#            dataArray = self.fieldData.GetArray( 'selected' )  
#            if dataArray: return dataArray.GetValue(0)
#        return 0

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
                        

    def getRangeBounds(self): 
        return self.rangeBounds  
        
    def getDataRangeBounds(self): 
        range = self.getDataValues( self.rangeBounds[0:2] ) 
        if ( len( self.rangeBounds ) > 2 ): range.append( self.rangeBounds[2] ) 
        else:                               range.append( 0 )
        return range
    
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
        self.documentation = "\n <h2>Module %s</h2> \n" % ( self.__class__.__name__ )
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
        return str( self.__class__.__name__ )
        
    def dvCompute( self, **args ):
        self.updateHyperwall()
        self.initializeInputs( **args )     
        if self.input or self.inputModuleList or not self.requiresPrimaryInput:
            self.execute( **args )
            self.initializeConfiguration()
        elif self.requiresPrimaryInput:
            print>>sys.stderr, " Error, no input to module %s " % ( self.__class__.__name__ )
        self.persistLayerDependentParameters()
        
    def updateHyperwall(self):
        pass

    def dvUpdate(self, **args):
#        self.markTime( ' Update %s' % self.__class__.__name__ ) 
        self.initializeInputs( **args )     
        self.execute( **args )
 
    def getRangeBounds(self): 
        return self.rangeBounds
    
    def getScalarRange(self): 
        return self.scalarRange

    def getParameterDisplay( self, parmName, parmValue ):
        if parmName == self.timeStepName:
            return str( self.timeValue.tocomp() ), 1
        return None, 1
          
    def getPrimaryInput( self, **args ):
        return self.getInputValue( self.primaryInputPort, **args )
    
    def getPrimaryInputList(self, **args ):
        return self.getInputList( self.primaryInputPort, **args  )
    
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
    
    def getInputValue( self, inputName, default_value = None, **args ):
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
          
    def setResult( self, outputName, value ): 
        if self.wmod <> None:       self.wmod.setResult( outputName, value )
        self.setParameter( outputName, value )
                    
    def initializeLayers( self ):
        metadata = self.getMetadata()
        scalars =  metadata.get( 'scalars', None )
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
            
    def initializeScalarRange( self ): 
        metadata = self.getMetadata()  
        var_md = metadata.get( 'attributes' , None )
        if var_md <> None:
            range = var_md.get( 'range', None )
            if range: 
                self.scalarRange = list( range )
                self.scalarRange.append( 1 )
                if not self.seriesScalarRange:
                    self.seriesScalarRange = list(range)
                else:
                    if self.seriesScalarRange[0] > range[0]:
                        self.seriesScalarRange[0] = range[0] 
                    if self.seriesScalarRange[1] < range[1]:
                        self.seriesScalarRange[1] = range[1] 
#        print " --- Update scalar range = %s" % str( self.scalarRange  )

    
    def getLayerList(self):
        layerList = []
        pointData = self.input.GetPointData()
        for iA in range( pointData.GetNumberOfArrays() ):
            array_name = pointData.GetArrayName(iA)
            if array_name: layerList.append( array_name )
        return layerList
    
    def setLayer( self, layer ):
        self.activeLayer = getItem( layer )

    def getLayer( self ):
        return [ self.activeLayer, ]
    
    def updateMetadata(self):
        scalars = None
        self.metadata = None
        self.newDataset = False
        if self.input <> None:
            fd = self.input.GetFieldData() 
            self.input.Update()
            self.fieldData = self.input.GetFieldData()             
        elif self.inputModule:
            self.fieldData = self.inputModule.getFieldData() 

        self.metadata = self.getMetadata()
        
        if self.metadata <> None:
            self.rangeBounds = None 
            self.setParameter( 'metadata', self.metadata )
            self.roi = self.metadata.get( 'bounds', None )
            
            dsetId = self.metadata.get( 'datasetId', None )
            self.datasetId = self.getAnnotation( "datasetId" )
            if self.datasetId <> dsetId:
                self.pipelineBuilt = False
                self.newDataset = True
                self.newLayerConfiguration = True
                self.datasetId = dsetId
                self.addAnnotation( "datasetId", self.datasetId )
            
            tval = self.metadata.get( 'timeValue', 0.0 )
            self.timeValue = cdtime.reltime( float( tval ), ReferenceTimeUnits )               
            dtype =  self.metadata.get( 'datatype', None )
            scalars =  self.metadata.get( 'scalars', None )
            self.rangeBounds = getRangeBounds( dtype )
            title = self.metadata.get( 'title', None )
            targs = title.split(':')
            if len( targs ) == 1:
                self.titleBuffer = "\n%s" % ( title )
            elif len( targs ) > 1:
                self.titleBuffer = "%s\n%s" % ( targs[1], targs[0] )
#            self.persistParameterList( [ ( 'title' , [ self.titleBuffer ]  ), ] )

            attributes = self.metadata.get( 'attributes' , None )
            if attributes:
                self.units = attributes.get( 'units' , '' )
#                        range = var_md.get( 'range', None )
#                        if range: 
#                            self.scalarRange = list( range )
#                            self.scalarRange.append( 1 )
#            print " --- updateMetadata: scalar range = %s" % str( self.scalarRange  )
#        return scalars
    def getUnits():
        return self.units
    
    def getCDMSDataset(self):
        return ModuleStore.getCdmsDataset( self.datasetId )
           
    def setActiveScalars( self ):
        pass
#        pointData = self.input.GetPointData()
#        if self.activeLayer:  
#            pointData.SetActiveScalars( self.activeLayer )
#            print " SetActiveScalars on pointData %d: %s" % ( id(pointData), self.activeLayer )
           
                                   
#    def transferInputLayer( self, imageData ):
#        oldPointData = imageData.GetPointData() 
#        array_names = [ oldPointData.GetArrayName(iP) for iP in range( oldPointData.GetNumberOfArrays() ) ]
#        for array_name in array_names: oldPointData.RemoveArray( array_name )
#        pointData = self.input.GetPointData()
#        activeArray = None
#        if self.activeLayer <> None:  activeArray = pointData.GetArray( self.activeLayer )
#        else:                         activeArray = pointData.GetArray( 0 )
#        if activeArray <> None:       imageData.GetPointData().SetScalars( activeArray )
                               

#        if self.input <> None:
#            pointData = self.input.GetPointData() 
#            scalars = pointData.GetScalars() 
#            i0 = scalars.GetNumberOfTuples()/2
#            datavalues = [ scalars.GetTuple1(i0+100*i) for i in range(3) ]      
#            print "%s.updateMetadata: scalars= %s, i0=%d, sample values= %s" % ( self.__class__.__name__, str(id(scalars)), i0, str(datavalues) )

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
        if self.allowMultipleInputs:
            try:
                self.inputModuleList = self.getPrimaryInputList( **args )
                self.inputModule = self.inputModuleList[0]
            except Exception, err:
                raise ModuleError( self, 'Broken pipeline at input to module %s:\n (%s)' % ( self.__class__.__name__, str(err) ) )
        else:
            inMod = self.getPrimaryInput( **args )
            if inMod: self.inputModule = inMod
#            if self.inputModule == None: print " ---- No input to module %s ---- " % ( self.__class__.__name__ )
#        print " %s.initializeInputs: input Module= %s " % ( self.__class__.__name__, str( input_id ) )
        if  self.inputModule <> None: 
            self.input =  self.inputModule.getOutput() 
#            print " --- %s:initializeInputs---> # Arrays = %d " % ( self.__class__.__name__,  ( self.input.GetFieldData().GetNumberOfArrays() if self.input else -1 ) )
            
            if isAnimation:
                tval = args.get( 'timeValue', None )
                if tval: self.timeValue = cdtime.reltime( float( args[ 'timeValue' ] ), ReferenceTimeUnits )
                self.fieldData = self.inputModule.getFieldData() 
            else:
                self.updateMetadata()  
                self.initializeLayers()
                
            self.initializeScalarRange()
            
            if isAnimation:
                for configFunct in self.configurableFunctions.values(): configFunct.expandRange()

#            self.setActiveScalars()
            
        elif ( self.fieldData == None ): 
            self.initializeMetadata()
            
    def getDataValue( self, image_value):
        if not self.scalarRange: 
            raise ModuleError( self, "ERROR: no variable selected in dataset input to module %s" % str( self.__class__.__name__ ) )
        valueRange = self.scalarRange
        sval = ( image_value - self.rangeBounds[0] ) / ( self.rangeBounds[1] - self.rangeBounds[0] )
        dataValue = valueRange[0] + sval * ( valueRange[1] - valueRange[0] ) 
        return dataValue
    
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
                
    def getDataValues( self, image_value_list ):
        if not self.scalarRange: 
            raise ModuleError( self, "ERROR: no variable selected in dataset input to module %s" % str( self.__class__.__name__ ) )
        valueRange = self.scalarRange
        data_values = []
        for image_value in image_value_list:
            sval = ( image_value - self.rangeBounds[0] ) / ( self.rangeBounds[1] - self.rangeBounds[0] )
            dataValue = valueRange[0] + sval * ( valueRange[1] - valueRange[0] ) 
            data_values.append( dataValue )
        return data_values

    def getImageValue( self, data_value ):
        if not self.scalarRange: 
            raise ModuleError( self, "ERROR: no variable selected in dataset input to module %s" % str( self.__class__.__name__ ) )
        valueRange = self.scalarRange
        sval = ( data_value - valueRange[0] ) / ( valueRange[1] - valueRange[0] )
        imageValue = self.rangeBounds[0] + sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
        return imageValue

    def getImageValues( self, data_value_list ):
        if not self.scalarRange: 
            raise ModuleError( self, "ERROR: no variable selected in dataset input to module %s" % str( self.__class__.__name__ ) )
        valueRange = self.scalarRange
        imageValues = []
        for data_value in data_value_list:
            sval = ( data_value - valueRange[0] ) / ( valueRange[1] - valueRange[0] )
            imageValue = self.rangeBounds[0] + sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
            imageValues.append( imageValue )
        return imageValues

    def scaleToImage( self, data_value ):
        if not self.scalarRange: 
            raise ModuleError( self, "ERROR: no variable selected in dataset input to module %s" % str( self.__class__.__name__ ) )
        sval = data_value / ( self.scalarRange[1] - self.scalarRange[0] )
        imageScaledValue =  sval * ( self.rangeBounds[1] - self.rangeBounds[0] ) 
        return imageScaledValue

    def set2DOutput( self, **args ):
        if self.wmod:
            portName = args.get( 'name', 'slice' )
            outputModule = AlgorithmOutputModule( fieldData=self.fieldData, **args )
            output =  outputModule.getOutput() 
            fd = output.GetFieldData() 
            fd.PassData( self.fieldData )                      
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % self.__class__.__name__

    def setOutputModule( self, outputModule, portName = 'volume', **args ): 
        if self.wmod:  
            output =  outputModule.getOutput() 
            fd = output.GetFieldData()  
            fd.PassData( self.fieldData )                
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % self.__class__.__name__
        
    def getFieldData( self, id, fd=None ): 
        fdata = self.fieldData if fd==None else fd
        dataVector = fdata.GetAbstractArray( id ) 
        if dataVector == None: return None
        nd = dataVector.GetNumberOfTuples()
        return [ dataVector.GetValue(id) for id in range( nd ) ]         

    def setFieldData( self, id, data ): 
        dataVector = self.fieldData.GetAbstractArray( id ) 
        if dataVector == None: return False
        for id in range(len(data)): dataVector.SetValue( id, data[id] )         
 
    def applyFieldData( self, props ): 
        pass
#        position = self.getFieldData( 'position' ) 
#        if position <> None:  
#            for prop in props: 
#                prop.SetPosition( position )
#        scale = self.getFieldData( 'scale' ) 
#        if scale <> None: 
#            for prop in props: 
#                prop.SetScale( scale )
#        print " applyFieldData, pos = %s" % ( str(position) )

    def addMetadata( self, metadata ):
        dataVector = self.fieldData.GetAbstractArray( 'metadata' ) 
        if dataVector == None:   
            print " Can't get Metadata for class %s " % ( self.__class__.__name__ )
        else:
            enc_mdata = encodeToString( metadata )
            dataVector.InsertNextValue( enc_mdata  )

    def getMetadata( self, metadata = {}, port=None  ):
        if self.fieldData:
            md = extractMetadata( self.fieldData )
            if md: metadata.update( md )
        return metadata
        
    def addMetadataObserver( self, caller, event ):
        fd = caller.GetOutput().GetFieldData()
        fd.ShallowCopy( self.fieldData )
        pass

    def initializeMetadata( self ):
        self.fieldData = vtk.vtkDataSetAttributes()
        mdarray = getStringDataArray( 'metadata' )
        self.fieldData.AddArray( mdarray )
#        print " %s:initializeMetadata---> # FieldData Arrays = %d " % ( self.__class__.__name__, self.fieldData.GetNumberOfArrays() )
#        self.fieldData.AddArray( getFloatDataArray( 'position', [  0.0, 0.0, 0.0 ] ) )
#        self.fieldData.AddArray( getFloatDataArray( 'scale',    [  1.0, 1.0, 1.0 ] ) ) 
           
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
        for configFunct in self.configurableFunctions.values():
            configFunct.init( self )
            
    def applyConfiguration(self, **args ):
        for configFunct in self.configurableFunctions.values():
            configFunct.applyParameter( self, **args  )
            
#    def setParameterInputsEnabled( self, isEnabled ):
#        for configFunct in self.configurableFunctions.values():
#            configFunct.setParameterInputEnabled( isEnabled )
# TBD: integrate
    def startConfigurationObserver( self, parameter_name, *args ):
        self.getLabelActor().VisibilityOn() 
    
                  
    def startConfiguration( self, x, y, config_types ):
        if (self.InteractionState <> None) and not self.configuring:
            configFunct = self.configurableFunctions[ self.InteractionState ]
            if configFunct.type in config_types:
                self.configuring = True
                configFunct.start( self.InteractionState, x, y )
                if self.ndims == 3: 
                    self.iren.SetInteractorStyle( self.configurationInteractorStyle )
                    print " ~~~~~~~~~ Set Interactor Style: Configuration  ~~~~~~~~~  "
                    if (configFunct.type == 'leveling'): self.getLabelActor().VisibilityOn()
    
    def isActive( self ):
        pipeline = self.getCurentPipeline()
        return ( self.moduleID in pipeline.modules )

    def updateAnimation( self, relTimeValue, textDisplay=None ):
        self.dvUpdate( timeValue=relTimeValue, animate=True )
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
            else: print " Missing wmod in %s.refreshParameters" % self.__class__.__name__
                    
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
#        print "%s- check parameter updating: %s " % ( self.__class__.__name__, str(parm_update) )
        return parm_update
   
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
#                    print>>sys.stderr, " Update %s Leveling, data = %s " % ( configFunct.name, str( configData ) )
                    if self.wmod: self.wmod.setResult( configFunct.name, configData )
                    self.setParameter( configFunct.name, configData ) 
                    textDisplay = configFunct.getTextDisplay()
                    if textDisplay <> None:  self.updateTextDisplay( textDisplay )
                                     
    def getInteractionState( self, key ):
        for configFunct in self.configurableFunctions.values():
            if configFunct.matches( key ): return configFunct.name
        return None    
    
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
            if (self.ndims == 3) and self.iren: 
                self.iren.SetInteractorStyle( self.navigationInteractorStyle )
                print " ~~~~~~~~~ Set Interactor Style: Navigation:  %s " % ( self.navigationInteractorStyle.__class__.__name__ )
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
#            print "Error updating parameter %s on module %s: %s" % ( parameter_name, self.__class__.__name__, str(err) )
#            pass 
#        return controller
        
    def getParameterId( self, parmName = None ):
        parmIdList = []
        if not self.datasetId: self.datasetId = self.getAnnotation( 'datasetId' )
        if self.datasetId: parmIdList.append( self.datasetId )
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
#            print " PM: Persist Parameter %s -> %s, tag = %s, taggedVersion=%d, new_id = %s, version => ( %d -> %d ), module = %s" % ( parameter_name, str(output), tag, taggedVersion, new_parameter_id, v0, v1, self.__class__.__name__ )
#            DV3DConfigurationWidget.savingChanges = False

    def persistParameterList( self, parmRecList, **args ):
        if parmRecList and not self.isClient: 
            import api
            DV3DConfigurationWidget.savingChanges = True
            ctrl = api.get_current_controller()
            strParmRecList = []
            self.getDatasetId( **args )
            for parmRec in parmRecList:
                parameter_name = parmRec[0]
                output = parmRec[1]
                param_values_str = [ str(x) for x in output ] if isList(output) else str( output )  
                strParmRecList.append( ( parameter_name, param_values_str ) )
            change_parameters( self.moduleID, strParmRecList, ctrl )           
            tag = self.getParameterId()
            taggedVersion = self.tagCurrentVersion( tag )
            listParameterPersist = args.get( 'list', True )  
            for parmRec in parmRecList:
                parameter_name = parmRec[0]
                output = parmRec[1]
                self.setParameter( parameter_name, output, tag ) 
                if listParameterPersist: self.persistedParameters.append( parameter_name )
#            print " %s.Persist-Parameter-List[%s] (v. %s): %s " % ( self.getName(), tag, str(taggedVersion), str(parmRecList) )
            self.persistVersionMap() 
            updatePipelineConfiguration = args.get( 'update', False ) # False )                  
            if updatePipelineConfiguration: ctrl.select_latest_version() 
            DV3DConfigurationWidget.savingChanges = False
#            self.wmod = None
                         
    def finalizeParameter(self, parameter_name, *args ):
        try:
            output = self.getParameter( parameter_name )
            assert (output <> None), "Attempt to finalize parameter that has not been cached." 
            self.persistParameterList( [ (parameter_name, output) ] )             
        except Exception, err:
            print "Error changing parameter %s for %s module: %s" % ( parameter_name, self.__class__.__name__, str(err) )
           
    def finalizeConfigurationObserver( self, parameter_name, *args ):
        self.finalizeParameter( parameter_name, *args )    
        for parameter_name in self.getModuleParameters(): self.finalizeParameter( parameter_name, *args ) 
        self.endInteraction() 
        
    def endInteraction(self):  
        from packages.vtDV3D.PlotPipelineHelper import ConfigCommandMenuManager     
        if (self.ndims == 3) and self.iren: 
            self.iren.SetInteractorStyle( self.navigationInteractorStyle )
            print " ~~~~~~~~~ Set Interactor Style: Navigation:  %s " % ( self.navigationInteractorStyle.__class__.__name__ )
        self.configuring = False
        ConfigCommandMenuManager.endInteraction()
        self.InteractionState = None
        self.enableVisualizationInteraction()

    def setActivation( self, name, value ):
        bval = bool(value)  
        self.activation[ name ] = bval
        print "Set activation for %s[%s] to %s "% ( self.getName(), name, bval ) 
        
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
        self.colormapManager = None
        self.colormapName = 'Spectral'
        self.labelBuff = "NA                          "
        self.invertColormap = 1
        self.renderer = None
        self.iren = None 
        self.lut = None
        self.gui = None
        self.titleBuffer = None
        self.instructionBuffer = " "
        self.textBlinkThread = None 
        self.pipelineBuilt = False
        self.activation = {}
        self.isAltMode = False
        self.navigationInteractorStyle = None
        self.configurationInteractorStyle = None
        self.stereoEnabled = 0

    def enableVisualizationInteraction(self): 
        pass
 
    def disableVisualizationInteraction(self): 
        pass

    def setInputZScale( self, zscale_data, **args  ):
        if self.input <> None:
            spacing = self.input.GetSpacing()
            ix, iy, iz = spacing
            sz = zscale_data[1]
#            print " PVM >---------------> Set input zscale: %.2f" % sz
            self.input.SetSpacing( ix, iy, sz )  
            self.input.Modified() 
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
            print>>sys.stderr, "Missing wmod in setChartDataOutput for class %s" % ( self.__class__.__name__ )
        else:
            self.wmod.setResult( portName, outputModule )
            print "setChartDataOutput for class %s" % ( self.__class__.__name__ ) 
    
    def set3DOutput( self, **args ):  
        portName = args.get( 'name', 'volume' )
        if not ( ('output' in args) or ('port' in args) ):
            if self.input <> None: 
                args[ 'output' ] = self.input
            elif self.inputModule <> None: 
                port = self.inputModule.getOutputPort()
                if port: args[ 'port' ] = port
                else:    args[ 'output' ] = self.inputModule.getOutput()
        outputModule = AlgorithmOutputModule3D( self.renderer, fieldData=self.fieldData, **args )
        output =  outputModule.getOutput() 
#        print "Setting 3D output for port %s" % ( portName ) 
        if output <> None:
            fd = output.GetFieldData() 
            fd.PassData( self.fieldData ) 
        if self.wmod == None:
            print>>sys.stderr, "Missing wmod in set3DOutput for class %s" % ( self.__class__.__name__ )
        else:
            self.wmod.setResult( portName, outputModule )
#            print "set3DOutput for class %s" % ( self.__class__.__name__ ) 
             
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
                    if module.__class__.__name__ == "PM_MapCell3D":
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
        if (self.renderer <> None) and (self.textBlinkThread == None): 
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
        
    def buildColormap(self):
        if self.colormapManager <> None:
            self.colormapManager.reverse_lut = self.invertColormap
            self.colormapManager.load_lut( self.colormapName )
            if self.createColormap: self.createColorBarActor()
#            print " >>> LoadColormap:  %s " % self.colormapName
            return True
        else:
            print " >>> LoadColormap:  Colormap Manager not defined"
            return False
        
    def setColormap( self, data ):
        self.colormapName = str(data[0])
        self.invertColormap = int( data[1] )
        enableStereo = int( data[2] )
        self.addMetadata( { 'colormap' : self.getColormapSpec() } )
#        print ' ~~~~~~~ SET COLORMAP:  --%s--  ' % self.colormapName
        self.updateStereo( enableStereo )
        if self.buildColormap(): 
            self.rebuildColorTransferFunction()
            self.render() 

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
            
    def rebuildColorTransferFunction( self ):
        pass 
            
    def getColormap(self):
        reverse = 0 if ( self.colormapManager <> None ) and self.colormapManager.reverse_lut else 1
        return [ self.colormapName, reverse, self.stereoEnabled ]

    def render( self ):
        if self.renderer:   
            rw = self.renderer.GetRenderWindow()
            if rw <> None: rw.Render()
       
    def setMaxScalarValue(self, iDType ):  
        if iDType   == vtk.VTK_UNSIGNED_CHAR:   self._max_scalar_value = 255
        elif iDType == vtk.VTK_UNSIGNED_SHORT:  self._max_scalar_value = 256*256-1
        elif iDType == vtk.VTK_SHORT:           self._max_scalar_value = 256*128-1
        else:                                   self._max_scalar_value = self.rangeBounds[1]  
                
    def initializeRendering(self):
        inputModule = self.getPrimaryInput()
        renderer_import = inputModule.getRenderer() if  inputModule <> None else None 
        self.renderer = vtk.vtkRenderer() if renderer_import == None else renderer_import
        self.renderer.AddObserver( 'ModifiedEvent', self.activateEvent )
        self.labelBuff = "NA                          "
        if self.createColormap: 
            self.createColorBarActor()

    def getColormapSpec(self): 
        spec = []
        spec.append( self.colormapName )
        spec.append( str( self.invertColormap ) )
        if self.lut:
            value_range = self.lut.GetTableRange() 
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
  
    def createColorBarActor( self ):
        self.colorBarActor = self.getProp( 'vtkScalarBarActor' )
        if self.colorBarActor == None:
            self.lut = vtk.vtkLookupTable()
            self.colormapManager = ColorMapManager( self.lut ) 
            self.colorBarActor = vtk.vtkScalarBarActor()
            self.colorBarActor.SetMaximumWidthInPixels( 50 )
            self.colorBarActor.SetNumberOfLabels(9)
            labelFormat = vtk.vtkTextProperty()
            labelFormat.SetFontSize( 160 )
            labelFormat.SetColor(  VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2] ) 
            titleFormat = vtk.vtkTextProperty()
            titleFormat.SetFontSize( 160 )
            titleFormat.SetColor(  VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2]  ) 
#            titleFormat.SetVerticalJustificationToTop ()
#            titleFormat.BoldOn()
            self.colorBarActor.SetPosition( 0.9, 0.2 )    
            self.colorBarActor.SetLabelTextProperty( labelFormat )
            self.colorBarActor.SetTitleTextProperty( titleFormat )
            if self.units: self.colorBarActor.SetTitle( self.units )
            self.colorBarActor.SetLookupTable( self.colormapManager.getDisplayLookupTable() )
            self.colorBarActor.SetVisibility(0)
            self.renderer.AddActor( self.colorBarActor )
        else:
            if self.colormapManager == None:
                self.lut = self.colorBarActor.GetLookupTable()
                self.colormapManager = ColorMapManager( self.lut ) 
            else:
                self.colorBarActor.SetLookupTable( self.colormapManager.getDisplayLookupTable() )
                self.colorBarActor.Modified()
        

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
      
    def activateEvent( self, caller, event ):
        if self.renderer == None:
            print>>sys.stderr, "Error, no renderer available for activation."
        else:
            self.renwin = self.renderer.GetRenderWindow( )
            if self.renwin <> None:
                iren = self.renwin.GetInteractor() 
                if ( iren <> None ) and ( iren.GetInteractorStyle() <> self.configurationInteractorStyle ):
                    if ( iren <> self.iren ):
                        if self.iren == None: 
                            self.renwin.AddObserver("AbortCheckEvent", CheckAbort)
                            self.configurationInteractorStyle = vtk.vtkInteractorStyleUser()
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
        if ( self.iren.GetInteractorStyle() <> self.navigationInteractorStyle ): 
            istyle = self.iren.GetInteractorStyle()               
            self.navigationInteractorStyle =  istyle
            print " ~~~~~~~~~ Set Navigation Interactor Style:  %s " % ( self.navigationInteractorStyle.__class__.__name__ )
                    
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


    def processKeyEvent( self, key, caller=None, event=None ):
        print "process Key Event, key = %s" % ( key )
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
            if  self.colorBarActor.GetVisibility(): 
                  self.colorBarActor.VisibilityOff()  
            else: self.colorBarActor.VisibilityOn() 
            self.render() 
        elif (  key == 'r'  ):
            self.resetCamera()              
            if  len(self.persistedParameters):
                pname = self.persistedParameters.pop()
                configFunct = self.configurableFunctions[pname]
                param_value = configFunct.reset() 
                if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True, list=False )
            
                
#            if self.LastInteractionState <> None: 
#                configFunct = self.configurableFunctions[ self.LastInteractionState ]
#                param_value = configFunct.reset() 
#                if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True )
#                if configFunct.type == 'leveling':
#                    self.finalizeConfigurationObserver( self.InteractionState )            
#                    if self.ndims == 3: 
#                        self.iren.SetInteractorStyle( self.navigationInteractorStyle )
#                        print " ~~~~~~~~~ SetInteractorStyle: navigationInteractorStyle: ", str(self.iren.GetInteractorStyle().__class__.__name__)     
#                if self.InteractionState <> None: 
#                    configFunct.close()
#                    self.endInteraction() 
        else:
            state =  self.getInteractionState( key )
            print " %s Set Interaction State: %s ( currently %s) " % ( str(self.__class__), state, self.InteractionState )
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
                print " UpdateInteractionState, state = %s, cf = %s " % ( state, str(configFunct) )
            if not configFunct and self.acceptsGenericConfigs:
                configFunct = ConfigurableFunction( state, None, None, pmod=self )              
                self.configurableFunctions[ state ] = configFunct
            if configFunct:
                configFunct.open( state, self.isAltMode )
                configFunct.postInstructions( self )
                self.InteractionState = state                   
                self.LastInteractionState = self.InteractionState
                self.disableVisualizationInteraction()
        return rcf
                   
    def endInteraction( self ):
        PersistentModule.endInteraction( self )
        if self.ndims == 3: self.getLabelActor().VisibilityOff()              
        
    def onLeftButtonRelease( self, caller, event ):
        print " --- Persistent Module: LeftButtonRelease --- "
        self.currentButton = None 
    
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
        else:
            self.iren.SetInteractorStyle( self.navigationInteractorStyle )          
        return 0
    
    def resetNavigation(self):
        if self.iren: self.iren.SetInteractorStyle( self.navigationInteractorStyle )
        self.enableVisualizationInteraction()

    def onModified( self, caller, event ):
        return 0

    def onRender( self, caller, event ):
        return 0
             
    def onKeyPress( self, caller, event ):
        return 0
    
    def getActiveIrens(self):
        sheetTabWidget = getSheetTabWidget()
        selected_cells = sheetTabWidget.getSelectedLocations() 
        irens = []
        for cell in selected_cells:
            cell_spec = "%s%s" % ( chr(ord('A') + cell[1] ), cell[0]+1 )
            iren = PersistentVisualizationModule.renderMap.get( cell_spec, None )
            irens.append( iren )
        return irens
    
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


        
