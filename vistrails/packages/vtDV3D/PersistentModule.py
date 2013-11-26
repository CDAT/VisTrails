'''
Created on Dec 17, 2010

@author: tpmaxwel
'''

import vtk, sys, time, threading, inspect, gui, traceback
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry, MissingPort
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.vtDV3D.InteractiveConfiguration import *
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D import ModuleStore
from db.domain import DBModule, DBAnnotation
from packages.vtDV3D import HyperwallManager
from packages.vtDV3D.vtUtilities import *
import cdms2, cdtime
DefaultReferenceTimeUnits = "days since 1900-1-1"
MIN_LINE_LEN = 50
ecount = 0


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

def intersectExtents( e1, e2 ):
    int_ext = []
    intersectionRequired = False
    if e1 and e2:
        for ie in range(0,3):
            ie0, ie1 = 2*ie, 2*ie+1
            if (e1[ ie0 ] <> e2[ ie0 ]) or (e1[ ie1 ] <> e2[ ie1 ]):
                intersectionRequired = True
            int_ext.append( max( e1[ ie0 ], e2[ ie0 ] )  )
            int_ext.append( min( e1[ ie1 ], e2[ ie1 ] )  )                    
    return int_ext if intersectionRequired else None
    
def intersectExtentList( extList ):
    intExtent = None
    intersectionRequired = False
    for e in extList:
        newIntExtent = intersectExtents( e, intExtent )
        if newIntExtent <> None: 
            intersectionRequired = True 
            intExtent = newIntExtent
        else: intExtent = e
    return intExtent if intersectionRequired else None
    
    
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
        self.referenceTimeUnits = None
        self.metadata = None
        self._input = None
        self.fieldData = None
        self.inputModule = None
        self.inputModuleList = None
        self.datasetId = None
        self.clipper = None
        self.dtype = None
        
    def isFloat(self):
        return self.dtype == "Float"

    def setInputModule( self, module ): 
        self.inputModuleList = module
        self.inputModule = self.inputModuleList[ 0 ]

    def selectInputArray( self, raw_input, plotIndex ):
        self.updateMetadata( plotIndex )
        old_point_data = raw_input.GetPointData()  
        nArrays = old_point_data.GetNumberOfArrays() 
        if nArrays == 1: return raw_input  
        image_data = vtk.vtkImageData()
        image_data.ShallowCopy( raw_input )
        new_point_data = image_data.GetPointData()        
        array_index = plotIndex if plotIndex < nArrays else 0
        inputVarList = self.metadata.get( 'inputVarList', [] )
        if array_index < len( inputVarList ):
            aname = inputVarList[ array_index ] 
            new_point_data.SetActiveScalars( aname )
#            print "Selecting scalars array %s for input %d" % ( aname, array_index )
        else:
            print>>sys.stderr, "Error, can't find scalars array for input %d" % array_index
#        print "Selecting %s (array-%d) for plot index %d" % ( aname, array_index, plotIndex)
        return image_data
 
    def initializeInput( self, inputIndex, moduleID ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper 
        if self.inputModule:
            raw_input = self.inputModule.getOutput() 
            plotIndex = DV3DPipelineHelper.getPlotIndex( moduleID, inputIndex ) 
#            print "InitializeInput for module %d, inputIndex=%d, plotIndex=%d" % ( moduleID, inputIndex, plotIndex)     
            if raw_input:
                self._input =  self.selectInputArray( raw_input, plotIndex )                             
            self.updateMetadata( plotIndex )
#            print "Computed metadata for input %d to module %d (plotIndex = %d): %s " % ( inputIndex, moduleID, plotIndex, str(self.metadata) )
            return True
        return False
        
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
    
    def getScalarRange(self): 
        return self.scalarRange
    
    def raiseModuleError( self, msg ):
        print>>sys.stderr, msg
        raise ModuleError( self, msg )

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
            diagnosticWriter.log( self, ' Uninitialized field data being accessed in ispec[%x]  ' % id(self)  ) 
            self.initializeMetadata()
        return self.fieldData  
    
    def updateMetadata( self, plotIndex ):
        if self.metadata == None:
            scalars = None
            if self.input() <> None:
                fd = self.input().GetFieldData() 
                self.input().Update()
                self.fieldData = self.input().GetFieldData()         
            elif self.inputModule:
                self.fieldData = self.inputModule.getFieldData() 
             
#            arr_names = [] 
#            na = self.fieldData.GetNumberOfArrays()
#            for iF in range( na ):
#                arr_names.append( self.fieldData.GetArrayName(iF) )
#            print " updateMetadata: getFieldData, arrays = ", str( arr_names ) ; sys.stdout.flush()
            
            if self.fieldData == None:
                diagnosticWriter.log( self, ' NULL field data in updateMetadata: ispec[%x]  ' % id(self)  ) 
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
    
    def computeMetadata( self, plotIndex ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper
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
        self.referenceTimeUnits = DefaultReferenceTimeUnits
        self.debug = False
        self.pipelineBuilt = False
        self.update_proj_controller = True
        self.newLayerConfiguration = False
        self.activeLayer = None
        self.newDataset = False
        self.moduleID = mid
        self.timeIndex = 0 
        self.inputSpecs = {}
        self.taggedVersionMap = {}
        self.persistedParameters = []
        self.versionTags = {}
        self.cell_location = None
        self.isInSelectedCell = False
#        self.initVersionMap()
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
        self.documentation = None
        self.parameterCache = {}
        self.timeValue = cdtime.reltime( 0.0, self.referenceTimeUnits ) 
        self.required_dtype = {}
        if self.createColormap:
            self.addUVCDATConfigGuiFunction( 'colormap', ColormapConfigurationDialog, 'c', label='Choose Colormap', setValue=self.setColormap, getValue=self.getColormap, layerDependent=True, group=ConfigGroup.Color )
#        self.addConfigurableGuiFunction( self.timeStepName, AnimationConfigurationDialog, 'a', label='Animation', setValue=self.setTimeValue, getValue=self.getTimeValue )
        self.addUVCDATConfigGuiFunction( self.timeStepName, AnimationConfigurationDialog, 'a', label='Animation', setValue=self.setTimeValue, getValue=self.getTimeValue, persist=False, cellsOnly=True, group=ConfigGroup.Display )
        
#        print "**********************************************************************"
#        print "Create Module [%d] : %s (%x)" % ( self.moduleID, self.__class__.__name__, id(self) )
#        print "**********************************************************************"

#        self.addConfigurableGuiFunction( 'layer', LayerConfigurationDialog, 'l', setValue=self.setLayer, getValue=self.getLayer )

#    def getSelectionStatus( self ):
#        if self.fieldData:
#            dataArray = self.fieldData.GetArray( 'selected' )  
#            if dataArray: return dataArray.GetValue(0)
#        return 0



    def setCellLocation( self, cell_location ):
        self.cell_location = cell_location       
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller()        
        self.connect( tabController, QtCore.SIGNAL("current_cell_changed"), self.current_cell_changed )
        
        
    def clearCellSelection(self):
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller() 
        for w in tabController.tabWidgets:       
            w.clearSelection()

    def current_cell_changed(self, sheetName, row, col):
        if ( sheetName == self.cell_location[1] ):
            cell_addr = "%s%d" % ( chr(ord('A') + col ), row+1 )
            self.isInSelectedCell = ( cell_addr == self.cell_location[-1] )

    def getCellLocation( self ):
        return self.cell_location

    def onCurrentPage(self):
        import api
        try:
            prj_controller = api.get_current_project_controller()
            return ( self.cell_location[0] == prj_controller.name ) and ( self.cell_location[1] == prj_controller.current_sheetName )
        except:
            return True
        
    def clearReferrents(self):
        
        for f in self.configurableFunctions.values(): 
            f.clearReferrents()
        self.configurableFunctions.clear()
        self.updateConfigurationObserver = None
        self.startConfigurationObserver = None
        self.finalizeConfigurationObserver = None

    def getVolumeBounds( self, **args ):  
        extent = args.get( "extent", self.input().GetExtent() )
        spacing = args.get( "spacing", self.input().GetSpacing() )
        origin = args.get( "origin", self.input().GetOrigin() )
        bounds = [ ( origin[i/2] + spacing[i/2]*extent[i] ) for i in range(6) ]
        return bounds
                
    def setLayer( self, layer ):
        self.activeLayer = getItem( layer )

    def getLayer( self ):
        return [ self.activeLayer, ]

    def ispec( self, input_index=0 ):
        try:
            return self.inputSpecs[ input_index ]
        except:
            return None 

    def input( self, input_index=0 ):
        try:
            ispec = self.inputSpecs[ input_index ]
        except:
            return None 
        return ispec.input()

    def intersectInputExtents( self ):
        ext_list = []
        if len( self.inputSpecs.keys() ) > 1:
            for ispec in self.inputSpecs.values():
                ext_list.append( ispec.input().GetExtent() )
        ie = intersectExtentList( ext_list )
        if ie:
            for ( ispecIndex, ispec ) in self.inputSpecs.items():
                ispec.clipInput( ie )
                self.reInitInput( ispecIndex )
            
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
             
    def getOutputRecord( self, ndim  ):
        return None
    
    def setLabel( self, label ):      
        if self.isClient: return
        controller = self.get_current_controller()
        controller.add_annotation( ('__desc__', str(label)), self.moduleID ) 
        controller.current_pipeline_view.recreate_module( controller.current_pipeline, self.moduleID )
        pass
    
    def get_current_controller(self):
        try:
            import api
            return api.get_current_controller()
        except:
            return self.wmod.moduleInfo.get( 'controller', None ) if self.wmod else None 

    def get_current_project_controller(self):
        try:
            import api
            return api.get_current_project_controller()
        except:
            return None

    def updateTextDisplay( self, text = None, **args ):
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
#        if parameter_name == 'colorScale':
#            print 'x'
        if parameter_id == None: parameter_id = self.getParameterId()
        layerCache = self.parameterCache.setdefault( parameter_id, {} )
        layerCache[parameter_name] = value 

    def getTaggedParameterValue(self, parameter_name ):
        tag = self.getParameterId()
        ctrl = self.get_current_controller()
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
    
    def updateTextDisplay( self, text = None, **args ):
        pass
            
    def getName(self):
        return str( getClassName( self ) )
        
    def dvCompute( self, **args ):
#        print "  ***** Updating %s Module, id = %d ***** " % ( self.__class__.__name__, self.moduleID )
        self.initializeInputs( **args )     
        self.updateHyperwall()
        if self.input() or self.inputModuleList() or self.inputModule() or not self.requiresPrimaryInput:
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
        port = args.get('port', self.getPrimaryInputPorts()[0] )
        return self.getInputValue( port, **args )
    
    def getPrimaryInputList(self, **args ):
        port = args.get('port', self.getPrimaryInputPorts()[0] )
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
#            self.addAnnotation( 'datasetId', self.datasetId  ) 
    
    def getInputValue1( self, inputName, default_value = None, **args ):
        if inputName == 'task':
            pass
        self.getDatasetId( **args )
        isLayerDep = self.isLayerDependentParameter( inputName )
        pval = None
        if self.wmod and ( self.isClient or not ( isLayerDep and self.newLayerConfiguration ) ):
            pval = self.wmod.forceGetInputFromPort( inputName, default_value ) 
        else:
            ctrl, tag = self.get_current_controller(), self.getParameterId()
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
        self.getDatasetId( **args )
        pval = self.getParameter( inputName, None )
#        if inputName == 'levelRangeScale':
#            controller = self.get_current_controller()
#            print ' Input levelRangeScale value, MID[%d], ctrl_version=%d, parameter value = %s, (defval=%s)'  % ( self.moduleID, controller.current_version, str(pval), str(default_value) )            
        if (pval == None) and (self.wmod <> None):
            pval = self.wmod.forceGetInputFromPort( inputName, default_value )             
#        if inputName == 'levelRangeScale':
#            print ' Actual Input value = %s'  % str(pval)           
        return pval

    def getInputValues( self, inputName, **args ):
        self.getDatasetId( **args )
        pval = self.getParameter( inputName, None )
        if (pval == None) and (self.wmod <> None):
            if 'forceGetInputListFromPort' in dir(self.wmod):
                pval = self.wmod.forceGetInputListFromPort( inputName )    
            else:
                pval = self.wmod.forceGetInputsFromPort( inputName, [] )             
        return pval
          
    def setResult( self, outputName, value ): 
        if self.wmod <> None:       self.wmod.setResult( outputName, value )
        self.setParameter( outputName, value )    
    
    def getCDMSDataset(self):
        return ModuleStore.getCdmsDataset( self.datasetId )
           
#    def setActiveScalars( self ):
#        pass

    def getInputCopy(self):
        image_data = vtk.vtkImageData() 
        gridSpacing = self.input().GetSpacing()
        gridOrigin = self.input().GetOrigin()
        gridExtent = self.input().GetExtent()
        image_data.SetScalarType( self.input().GetScalarType() )  
        image_data.SetOrigin( gridOrigin[0], gridOrigin[1], gridOrigin[2] )
        image_data.SetSpacing( gridSpacing[0], gridSpacing[1], gridSpacing[2] )
        image_data.SetExtent( gridExtent[0], gridExtent[1], gridExtent[2], gridExtent[3], gridExtent[4], gridExtent[5] )
        return image_data
    
    def reInitInput( self, inputIndex ):
        ispec = self.inputSpecs[ inputIndex ] 
        if  ispec.initializeInput( inputIndex, self.moduleID ):            
            if inputIndex == 0:     self.setParameter( 'metadata', ispec.metadata ) 
            else:                   self.setParameter( 'metadata-%d' % inputIndex, ispec.metadata )
            self.roi = ispec.metadata.get( 'bounds', None )
            
    def getPrimaryInputPorts(self):
        return self.primaryInputPorts
    
    def intiTime(self, ispec, **args):
        t = cdtime.reltime( 0, self.referenceTimeUnits)
        if t.cmp( cdtime.reltime( 0, ispec.referenceTimeUnits ) ) == 1:
            self.referenceTimeUnits = ispec.referenceTimeUnits 
        tval = args.get( 'timeValue', None )
        if tval: self.timeValue = cdtime.reltime( float( args[ 'timeValue' ] ), ispec.referenceTimeUnits )

    def initializeInputs( self, **args ):
        
        isAnimation = args.get( 'animate', False )
        restarting = args.get( 'restarting', False )
        self.newDataset = False
        inputPorts = self.getPrimaryInputPorts()
        for inputIndex, inputPort in enumerate( inputPorts ):
            ispec = InputSpecs()
            self.inputSpecs[ inputIndex ] = ispec
#            inputList = self.getPrimaryInputList( port=inputPort, **args )
            if self.allowMultipleInputs.get( inputIndex, False ):
                try:
                    ispec.setInputModule(  self.getPrimaryInputList( port=inputPort, **args ) )
                except Exception, err:
                    print>>sys.stderr, 'Error: Broken pipeline at input to module %s:\n (%s)' % ( getClassName(self), str(err) ) 
                    self.getPrimaryInputList( port=inputPort, **args )
                    traceback.print_exc()
                    sys.exit(-1)
            else:
                inMod = self.getPrimaryInput( port=inputPort, **args )
                if inMod: ispec.inputModule = inMod
                
            if  ispec.initializeInput( inputIndex, self.moduleID ):
                self.intiTime( ispec, **args )
                
                if inputIndex == 0:     
                    self.setParameter( 'metadata', ispec.metadata ) 
#                    datasetId = self.getAnnotation( "datasetId" )
                else:                   
                    self.setParameter( 'metadata-%d' % inputIndex, ispec.metadata )

                if not isAnimation:
#                        print>>sys.stderr, "\n ----------------------- Dataset changed, rebuild pipeline: %s -> %s ----------------------- \n" % ( datasetId, ispec.datasetId )
                    self.pipelineBuilt = False
                    self.newDataset = True
                    self.newLayerConfiguration = True
#                        self.addAnnotation( "datasetId", ispec.datasetId )
 
                if self.roi == None:  
                    self.roi = ispec.metadata.get( 'bounds', None )  
                if isAnimation:
                    ispec.fieldData = ispec.inputModule.getFieldData() 
                                    
            elif ( ispec.fieldData == None ): 
                ispec.initializeMetadata()

        if isAnimation:
            for configFunct in self.configurableFunctions.values(): 
                if restarting:  configFunct.fixRange()
                else:           configFunct.expandRange()
   
#    def initializeLayers( self, scalars ):
#        if self.activeLayer == None: 
#            self.activeLayer =self.getAnnotation( 'activeLayer' )
#        if self.input and not scalars:
#            scalarsArray = self.input().GetPointData().GetScalars()
#            if scalarsArray <> None:
#                scalars = scalarsArray.GetName() 
#            else:
#                layerList = self.getLayerList()
#                if len( layerList ): scalars = layerList[0] 
#        if self.activeLayer <> scalars:
#            self.updateLayerDependentParameters( self.activeLayer, scalars )
#            self.activeLayer = scalars 
##            self.addAnnotation( 'activeLayer', self.activeLayer  ) 
#            self.seriesScalarRange = None

    def getDataValue( self, image_value, input_index = 0 ):
        ispec = self.inputSpecs[ input_index ] 
        return ispec.getDataValue( image_value )

    def getTimeAxis(self):
        ispec = self.getInputSpec()     
        timeAxis = ispec.getMetadata('time') if ispec else None
        return timeAxis
    
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
            if fieldData:
                fd = output.GetFieldData() 
                fd.PassData( fieldData ) 
            else:                     
                diagnosticWriter.log( self, ' set2DOutput, NULL field data ' )    
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % getClassName( self )

    def setOutputModule( self, outputModule, portName = 'volume', **args ): 
        if self.wmod:  
            fieldData = self.getFieldData()
            output =  outputModule.getOutput() 
            if fieldData:
                fd = output.GetFieldData()
                fd.PassData( fieldData )                
            else:                     
                diagnosticWriter.log( self, ' setOutputModule, NULL field data ' )    
            self.wmod.setResult( portName, outputModule ) 
        else: print " Missing wmod in %s.set2DOutput" % getClassName( self )
         
           
    def addConfigurableMethod( self, name, method, key, **args ):
        self.configurableFunctions[name] = ConfigurableFunction( name, args.get('signature',None), key, hasState=False, open=method, **args )

    def addConfigurableBooleanFunction( self, name, method, key, **args ):
        self.configurableFunctions[name] = ConfigurableBooleanFunction( name, args.get('signature',None), key, hasState=False, open=method, **args )

    def addConfigurableFunction(self, name, function_args, key, **args):
        self.configurableFunctions[name] = ConfigurableFunction( name, function_args, key, **args )

    def addConfigurableLevelingFunction(self, name, key, **args):
        self.configurableFunctions[name] = WindowLevelingConfigurableFunction( name, key, **args )
                        
    def addConfigurableGuiFunction(self, name, guiClass, key, **args):
        isActive = not HyperwallManager.getInstance().isClient
        guiCF = GuiConfigurableFunction( name, guiClass, key, active = isActive, start=self.startConfigurationObserver, update=self.updateConfigurationObserver, finalize=self.finalizeConfigurationObserver, **args )
        self.configurableFunctions[name] = guiCF

    def addUVCDATConfigGuiFunction(self, name, guiClass, key, **args):
        isActive = not HyperwallManager.getInstance().isClient
        guiCF = UVCDATGuiConfigFunction( name, guiClass, key, active = isActive, start=self.startConfigurationObserver, update=self.updateConfigurationObserver, finalize=self.finalizeConfigurationObserver, **args )
        self.configurableFunctions[name] = guiCF
        
    def getConfigFunction( self, name ):
        return self.configurableFunctions.get(name,None)

    def removeConfigurableFunction(self, name ):
        
        del self.configurableFunctions[name]

    def addConfigurableWidgetFunction(self, name, signature, widgetWrapper, key, **args):
        wCF = WidgetConfigurableFunction( name, signature, widgetWrapper, key, **args )
        self.configurableFunctions[name] = wCF
    
    def getConfigurationHelpText(self):
        lines = []
        lines.append( '\n <h3>Configuration Command Keys:</h3>\n' )
        lines.append(  '<table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">\n' )
        lines.append( '<tr> <th> Command Key </th> <th> Configuration </th> <th> Type </th> </tr>' )
        lines.append( ''.join( [ configFunct.getHelpText() for configFunct in self.configurableFunctions.values() ] ) )
        lines.append( '</table>' )
        return ''.join( lines ) 
          
    def initializeConfiguration(self, **args):
        
        for configFunct in self.configurableFunctions.values():
            configFunct.init( self, **args )
            
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
    
    def updateAnimation( self, animTimeData, textDisplay=None, restartingAnimation=False ):     
        self.dvUpdate( timeData=animTimeData, animate=True, restarting=restartingAnimation )
        if textDisplay <> None:  self.updateTextDisplay( textDisplay, worker_thread=True )
#        QtCore.QCoreApplication.processEvents()
        
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
        if self.ndims == 3:
            self.getLabelActor().VisibilityOff()
            actor = self.getLensActor()
            if actor: actor.VisibilityOff()

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
            
    def getParameterId( self, parmName = None, input_index=0 ):
        parmIdList = []
        ispec = self.inputSpecs.get( input_index, None )
        if ispec and ispec.datasetId: parmIdList.append( ispec.datasetId )
        if self.activeLayer: parmIdList.append( self.activeLayer )
        if parmName: parmIdList.append( parmName )
        if parmIdList: return '.'.join( parmIdList )
        return 'all' 
    
    def tagCurrentVersion( self, tag ):
        ctrl = self.get_current_controller()  
        versionList = self.taggedVersionMap.setdefault( tag, [] )
        if (not versionList) or (versionList[-1] < ctrl.current_version):
            versionList.append( ctrl.current_version )
        self.versionTags[ ctrl.current_version ] = tag
        return ctrl.current_version

    def getTaggedVersionList( self, tag ):
        return self.taggedVersionMap.get( tag, None )
                    
    def getTaggedVersion( self, tag ):
        versionList = self.taggedVersionMap.get( tag, None )
        return versionList[-1] if versionList else -1                     


    def refreshVersion(self):
        pass

    def getCurrentPipeline( self ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper  
        try:
            ( sheetName, cell_address ) = DV3DPipelineHelper.getCellCoordinates( self.moduleID )
            proj_controller = self.get_current_project_controller()
            if proj_controller == None:
                controller = self.get_current_controller()
                return controller.current_pipeline if controller else None
            controller =  proj_controller.vt_controller 
            if self.update_proj_controller:
                pcoords =list( proj_controller.current_cell_coords ) if proj_controller.current_cell_coords else None
                if not pcoords or ( pcoords[0] <> cell_address[0] ) or ( pcoords[1] <> cell_address[1] ):
                    proj_controller.current_cell_changed(  sheetName, cell_address[0], cell_address[1]  )
                else: pcoords = None 
            cell = proj_controller.sheet_map[ sheetName ][ cell_address ]
            current_version = cell.current_parent_version 
            controller.change_selected_version( current_version )
            return controller.vistrail.getPipeline( current_version )
        except Exception, err:
            print>>sys.stderr, "Error getting current pipeline: %s " % str( err )
            traceback.print_exc()
            return controller.current_pipeline       

    def change_parameters( self, parmRecList ):
        import api
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper  
        """change_parameters(
                            parmRecList: [ ( function_name: str, param_list: list(str) ) ] 
                            controller: VistrailController,
                            ) -> None
        Note: param_list is a list of strings no matter what the parameter type!
        """
        
        
        config_list = []
        try:
            ( sheetName, cell_address ) = DV3DPipelineHelper.getCellCoordinates( self.moduleID )
            proj_controller = self.get_current_project_controller()
            if proj_controller == None:
                controller = self.get_current_controller()
            else:
                if ( sheetName <> proj_controller.current_sheetName ): return
                controller =  proj_controller.vt_controller 
                if self.update_proj_controller:
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
            
        try:
            module = pipeline.modules[self.moduleID] 
        except KeyError:
            print>>sys.stderr, "Error changing parameter in module %d (%s), parm: %s: Module not in current controller pipeline." % ( self.moduleID, self.__class__.__name__, str(parmRecList) )  
            return
        try:
            op_list = []
#            print "Module[%d]: Persist Parameter: %s, controller: %x " % ( self.moduleID, str(parmRecList), id(controller) )
            for parmRec in parmRecList: 
                try:
                    op_list.extend( controller.update_function_ops( module, parmRec[0], parmRec[1] ) )
                    config_fn = self.getConfigFunction( parmRec[0] )
                    if config_fn: 
                        config_list.append( config_fn )
                    else: 
                        pass
                except MissingPort:
                    print>>sys.stderr, "Missing input port %s in controller, parmRecList = %s " % ( parmRec[0], str( parmRecList ) )
                    
#                    print>>sys.stderr, "Unrecognized config function %s in module %d (%s)" % ( parmRec[0], self.moduleID, self.__class__.__name__ )
            action = create_action( op_list ) 
            controller.add_new_action(action)
            controller.perform_action(action)
            controller.select_latest_version()
          
            for config_fn in config_list:
                config_fn.persisted = True
                
            if self.update_proj_controller and proj_controller:
                proj_controller.cell_was_changed(action)
                if pcoords:  proj_controller.current_cell_changed(  sheetName, pcoords[0], pcoords[1]  )
            sys.stdout.flush()
                
        except Exception, err:
            print>>sys.stderr, "Error changing parameter in module %d (%s): parm: %s, error: %s" % ( self.moduleID, self.__class__.__name__, str(parmRecList), str(err) )
            traceback.print_exc()
               
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
#        print "MODULE[%d]: Persist Config Parameter %s -> %s "  % ( self.moduleID, config_name, str(config_data) )     
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

    def setTimeValue( self, iTimeIndex ):
        self.timeIndex = iTimeIndex
        try:
            relTimeValue = self.timeRange[ 2 ] + iTimeIndex* self.timeRange[ 3 ]
            self.timeValue = cdtime.reltime( relTimeValue, self.referenceTimeUnits )
        except:
            pass
        self.onNewTimestep()
            
    def getTimeValue( self ):
        return self.timeIndex

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
        self.observerTags = []
        self.observerTargets = set()
        self.stereoEnabled = 0
        self.showInteractiveLens = False
        self.navigationInteractorStyle = None
        self.configurationInteractorStyle = vtk.vtkInteractorStyleUser()

    def enableVisualizationInteraction(self): 
        pass
 
    def disableVisualizationInteraction(self): 
        pass
                      
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
                    
    def getScaleBounds(self):
        return [ 0.5, 100.0 ]
    
    def processScaleChange( self, old_spacing, new_spacing ):
        pass
        
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
        if ispec.fieldData == None: ispec.updateMetadata(0)
        fieldData = ispec.getFieldData()
        na = fieldData.GetNumberOfArrays()
        if not ( ('output' in args) or ('port' in args) ):
            if ispec.input() <> None: 
                args[ 'output' ] = ispec.input()
            elif ispec.inputModule <> None: 
                port = ispec.inputModule.getOutputPort()
                if port: args[ 'port' ] = port
                else:    args[ 'output' ] = ispec.inputModule.getOutput()
        outputModule = AlgorithmOutputModule3D( self.renderer, fieldData=fieldData, **args )
        output =  outputModule.getOutput() 
#        print "Setting 3D output for port %s" % ( portName ) 
        if output <> None:
            fd = output.GetFieldData() 
            if fieldData:
                fd = output.GetFieldData()
                fd.PassData( fieldData )                
            else:                     
                diagnosticWriter.log( self, ' set3DOutput, NULL field data ' ) 
                   
        if self.wmod == None:
            print>>sys.stderr, "Missing wmod in set3DOutput for class %s" % ( getClassName( self ) )
        else:
            self.wmod.setResult( portName, outputModule )
#            print "set3DOutput for class %s" % ( getClassName( self ) ) 
             
    def getDownstreamCellModules( self, selectedOnly=False ): 
        from packages.vtDV3D import ModuleStore
        controller = self.get_current_controller()
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

    def updateTextDisplay( self, text = None, **args ):
        worker_thread = args.get("worker_thread", False )
        if (text <> None) and (self.renderer <> None): 
            if (self.ndims == 3):                
                if worker_thread:
                    app = QCoreApplication.instance()
                    gui_event = DV3DGuiEvent( "label_text_update", text=text )
                    app.postEvent( self, gui_event )
                else:
                    self.labelBuff = str(text)
                    self.getLabelActor().VisibilityOn()    
                
    def updateLensDisplay(self, screenPos, coord):
        if (screenPos <> None) and (self.renderer <> None) and self.showInteractiveLens: 
            actor = self.getLensActor( screenPos, coord )
            if actor: actor.VisibilityOn()
    
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
#        memoryLogger.log(" start %s:execute" % self.__class__.__name__ )
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
#        memoryLogger.log("finished %s:execute" % self.__class__.__name__ )

        
    def buildPipeline(self): 
        pass 

    def getLut( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut
    
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

        
    def setColormap( self, data, cmap_index=0 ):
        colormapName = str(data[0])
        invertColormap = int( data[1] )
        enableStereo = int( data[2] )
        smoothColormap = int( data[3] ) if ( len( data ) > 3 ) else 1 
        ispec = self.getInputSpec( cmap_index )  
        if  (ispec <> None) and (ispec.input() <> None):         
    #        self.addMetadata( { 'colormap' : self.getColormapSpec() } )
    #        print ' ~~~~~~~ SET COLORMAP:  --%s--  ' % self.colormapName
            self.updateStereo( enableStereo )
            colormapManager = self.getColormapManager( name=colormapName, invert=invertColormap, smooth=smoothColormap, index=cmap_index, units=self.getUnits(cmap_index) )
            if self.createColormap and ( colormapManager.colorBarActor == None ): 
                cmap_pos = [ 0.9, 0.2 ] if (cmap_index==0) else [ 0.02, 0.2 ]
                units = self.getUnits( cmap_index )
                cm_title = "%s\n(%s)" % ( ispec.metadata.get('scalars',''), units ) if ispec.metadata else units 
                self.renderer.AddActor( colormapManager.createActor( pos=cmap_pos, title=cm_title ) )
            self.updatingColormap( cmap_index, colormapManager )
            self.render() 
            return True
        return False
    
    def updatingColormap( self, cmap_index, colormapManager ):
        pass

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
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper  
        inputModule = self.getPrimaryInput()
        renderer_import = inputModule.getRenderer() if  inputModule <> None else None 
        if renderer_import == None:             
            self.renderer = DV3DPipelineHelper.getRenderer( mid=self.moduleID )
            if self.renderer == None:
                self.renderer = vtk.vtkRenderer()
                DV3DPipelineHelper.setRenderer( self.renderer, mid=self.moduleID )            
        else: 
            self.renderer = renderer_import
        self.addObserver( self.renderer, 'ModifiedEvent', self.activateEvent )
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
          
    def createData(self, coord):
        from paraview.vtk.dataset_adapter import numpyTovtkDataArray
#        ds = self.getCDMSDataset()
#        (guiName, varName, varId ) = 
#        current_var = None
#        haveVar = False
#        for isIndex in range( len( self.inputSpecs ) ):
#            if not haveVar:
#                ispec = self.inputSpecs[ isIndex ] 
#                ds= ModuleStore.getCdmsDataset( ispec.datasetId )
#                tvars = ds.transientVariables.values()
#                for tvar in tvars:
#                    if (tvar.id == varId):
#                        current_var = tvar
#                        haveVar = True
#                        break

        try:
            
            current_var = ModuleStore.getActiveVariable()              
            newvar = current_var(lat=coord[1], lon=coord[0], lev=coord[2], squeeze=1)
            
            fieldData = vtk.vtkFieldData()
            fieldData.AllocateArrays(2)
            fieldData.AddArray(numpyTovtkDataArray(newvar.getTime()[:], name='x'))
            fieldData.AddArray(numpyTovtkDataArray(newvar.filled(), name='y'))
    
            dataobject = vtk.vtkDataObject()
            dataobject.SetFieldData(fieldData)
            return ( current_var, dataobject )
        
        except Exception, err:
            print>>sys.stderr, "Error getting current variable data: ", str(err)
        
        return None

    def createLensActor(self, id_, pos):
        lensActor = vtk.vtkXYPlotActor();
        lensActor.SetTitle("Time vs. VAR")
        lensActor.SetXTitle("Time")
        lensActor.SetYTitle("VAR")
        lensActor.SetBorder(1)
        lensActor.PlotPointsOn()

##        ds = self.getCDMSDataset()
#        ispec = self.inputSpecs[ 0 ] 
#        ds= ModuleStore.getCdmsDataset( ispec.datasetId )
#        
#        if ds <> None:
#            if len(ds.transientVariables)>0:
#                if len(ds.transientVariables)>1: print 'Warning: this module has several transient Variables, plotting the first one.'
#                var = ds.transientVariables.values()[0]
#                if hasattr(var, 'long_name'):
#                    lensActor.SetTitle("Time vs. %s (%s)" % (var.long_name, var.id))
#                else:
#                    lensActor.SetTitle("Time vs.%s" % var.id)
#                lensActor.SetYTitle(var.id)
#                lensActor.SetYRange(var.min(), var.max())

        prop = lensActor.GetProperty()
        prop.SetColor( VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2] )
        prop.SetLineWidth(2)
        prop.SetPointSize(4)
    
        lensActor.VisibilityOff()
        lensActor.id = id_

        return lensActor
    
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
    
    def getLensActor(self, pos=None, coord=None):
        id_ = 'lens'        
        lensActor = self.getProp( 'vtkXYPlotActor', id_)
        if lensActor == None:
            lensActor = self.createLensActor(id_, pos)
            if self.renderer: 
                self.renderer.AddViewProp( lensActor )
                
        if (coord<>None):
            dataElements = self.createData(coord)
            if dataElements <> None: 
                ( var, dataObjectInput ) = dataElements 
                if hasattr(var, 'long_name'):
                    lensActor.SetTitle("Time vs. %s (%s)" % (var.long_name, var.id))
                else:
                    lensActor.SetTitle("Time vs.%s" % var.id)
                lensActor.SetYTitle(var.id)
                lensActor.SetYRange(var.min(), var.max())
                
                lensActor.GetDataObjectInputList().RemoveAllItems()
                lensActor.AddDataObjectInput( dataObjectInput )
                lensActor.SetXValuesToValue()
                lensActor.SetDataObjectXComponent(0, 0)
                lensActor.SetDataObjectYComponent(0, 1)
      
        # update position      
        if pos<>None:
            coord = lensActor.GetPositionCoordinate()
            coord.SetCoordinateSystemToDisplay()
            coord.SetValue( pos[0], pos[1])
      
        return lensActor


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
            self.renwin = self.renderer.GetRenderWindow()
            if self.renwin <> None:
                iren = self.renwin.GetInteractor() 
                if ( iren <> None ) and not self.isConfigStyle( iren ):
                    if ( iren <> self.iren ):
                        if self.iren == None: 
                            self.addObserver( self.renwin,"AbortCheckEvent", CheckAbort)
                        self.iren = iren
                        self.activateWidgets( self.iren )                                  
                        self.addObserver( self.iren, 'CharEvent', self.setInteractionState )                   
                        self.addObserver( self.iren, 'MouseMoveEvent', self.updateLevelingEvent )
#                        self.addObserver( 'LeftButtonReleaseEvent', self.finalizeLevelingEvent )
                        self.addObserver( self.iren, 'AnyEvent', self.onAnyEvent )  
#                        self.addObserver( 'MouseWheelForwardEvent', self.refineLevelingEvent )     
#                        self.addObserver( 'MouseWheelBackwardEvent', self.refineLevelingEvent )     
                        self.addObserver( self.iren, 'CharEvent', self.onKeyPress )
                        self.addObserver( self.iren, 'KeyReleaseEvent', self.onKeyRelease )
                        self.addObserver( self.iren, 'LeftButtonPressEvent', self.onLeftButtonPress )
                        self.addObserver( self.iren, 'ModifiedEvent', self.onModified )
                        self.addObserver( self.iren, 'RenderEvent', self.onRender )                   
                        self.addObserver( self.iren, 'LeftButtonReleaseEvent', self.onLeftButtonRelease )
                        self.addObserver( self.iren, 'RightButtonReleaseEvent', self.onRightButtonRelease )
                        self.addObserver( self.iren, 'RightButtonPressEvent', self.onRightButtonPress )
                        for configurableFunction in self.configurableFunctions.values():
                            configurableFunction.activateWidget( iren )
                    self.updateInteractor()  
    
    def addObserver( self, target, event, observer ):
        self.observerTargets.add( target ) 
        target.AddObserver( event, observer ) 

    def clearReferrents(self):
        PersistentModule.clearReferrents(self)
        self.removeObservers()
        self.renderer = None
        self.iren = None
        self.gui = None

    def removeObservers( self ): 
        for target in self.observerTargets:
            target.RemoveAllObservers()
        self.observerTargets.clear()
                                               
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
        self.render()
            
    def processKeyEvent( self, key, caller=None, event=None ):
#        print "process Key Event, key = %s" % ( key )
        md = self.getInputSpec().getMetadata()
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
            HyperwallManager.getInstance().setInteractionState( 'colorbar', False )                        
            self.render() 
        elif (  key == 'r'  ):
            self.resetCamera()              
            if  len(self.persistedParameters):
                pname = self.persistedParameters.pop()
                configFunct = self.configurableFunctions[pname]
                param_value = configFunct.reset() 
                if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True, list=False )                
        elif ( md and ( md.get('plotType','')=='xyz' ) and ( key == 't' )  ):
            self.showInteractiveLens = not self.showInteractiveLens 
            self.render() 
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
                HyperwallManager.getInstance().setInteractionState( state, False )                        
            elif state == 'reset':
                self.resetCamera()              
                if  len(self.persistedParameters):
                    pname = self.persistedParameters.pop()
                    configFunct = self.configurableFunctions[pname]
                    param_value = configFunct.reset() 
                    if param_value: self.persistParameterList( [ (configFunct.name, param_value), ], update=True, list=False )                
                HyperwallManager.getInstance().setInteractionState( state, False )                        
        return rcf

    def invokeKeyEvent( self, keysym ):
        ascii_key = QString(keysym).toLatin1()[0]
        self.iren.SetKeyEventInformation( 0, 0, ascii_key, 0, keysym )
        self.iren.KeyPressEvent()
                   
    def endInteraction( self, **args ):
        PersistentModule.endInteraction( self, **args  )
        if self.ndims == 3: 
            self.getLabelActor().VisibilityOff()              
            actor  = self.getLensActor()
            if actor: actor.VisibilityOff()

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
    
    def getSheetAddress(self):
        sheet_addr = "Project 1:Sheet 1"
        try:
            from api import get_current_project_controller
            prj_controller = get_current_project_controller() 
            sheet_addr = "%s:%s" % ( prj_controller.name, prj_controller.current_sheetName )            
        except: pass
        return sheet_addr
         
    def getActiveRens(self):
        rens = []
        sheetTabWidget = getSheetTabWidget()
        if sheetTabWidget:
            sheet_addr = getSheetAddress(self)
            selected_cells = sheetTabWidget.getSelectedLocations() 
            for cell in selected_cells:
                cell_spec = "%s:%s%s" % ( sheet_addr, chr(ord('A') + cell[1] ), cell[0]+1 )
                winid = PersistentVisualizationModule.renderMap.get( cell_spec, None )
                if winid: rens.append( winid )
        return rens
       
    def onAnyEvent(self, caller, event ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper 
        global ecount       
#        rw = DV3DPipelineHelper.getRenderWindow( 'A1' ) 
#         shift = caller.GetShiftKey()
#         alt = caller.GetAltKey()
#         ctrl = caller.GetControlKey()

#        print " onAnyEvent: %s %s " % ( str((shift,alt,ctrl)), str(event) )
#        if self.cell_location:
#            addr = self.cell_location[-1]
#            if event == "ModifiedEvent" and addr == "A2":
#                print "Cell %s, E[%d]: %s" % ( str(addr), ecount, str( event ) )
#                ecount = ecount + 1

#        if self.iren:
#            istyle = self.iren.GetInteractorStyle() 
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


        
