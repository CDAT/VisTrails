'''
Created on Nov 21, 2011

@author: tpmaxwel
'''
import vtk, sys, os, copy, time, traceback
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from packages.vtDV3D.InteractiveConfiguration import *
from core.modules.vistrails_module import Module, ModuleError
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from packages.uvcdat_cdms.init import CDMSVariable, CDMSVariableOperation 
from packages.vtDV3D.WorkflowModule import WorkflowModule 
from packages.vtDV3D import ModuleStore
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import *
from packages.vtDV3D import identifier
from packages.uvcdat.init import Variable, VariableSource
import cdms2, cdtime, cdutil, MV2 
PortDataVersion = 0

def freeImageData( image_data ):
    from packages.vtDV3D.vtUtilities import memoryLogger
    memoryLogger.log("start freeImageData")
    pointData = image_data.GetPointData()
    for aIndex in range( pointData.GetNumberOfArrays() ):
        array = pointData.GetArray( aIndex )
        if array:
            name = pointData.GetArrayName(aIndex)
#             s0 = array.GetSize()
#             r0 = array.GetReferenceCount()
            array.Initialize()
            array.Squeeze()
#             s1 = array.GetSize()
            pointData.RemoveArray( aIndex )
#             r1 = array.GetReferenceCount()
            print "---- freeImageData-> Removing array %s: %s" % ( name, array.__class__.__name__ )  
    fieldData = image_data.GetFieldData()
    for aIndex in range( fieldData.GetNumberOfArrays() ): 
        aname = fieldData.GetArrayName(aIndex)
        array = fieldData.GetArray( aname )
        if array:
#             print "---- freeImageData-> Removing field data: %s" % aname
            array.Initialize()
            array.Squeeze()
            fieldData.RemoveArray( aname )
    image_data.ReleaseData()
    memoryLogger.log("finished freeImageData")
    
def get_value_from_function(module, fun):
    for i in xrange(module.getNumFunctions()):
        if fun == module.functions[i].name:
            return module.functions[i].params[0].value()
    return None

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = 'gov.nasa.nccs.vtdv3d'
    reg = get_module_registry()
    out_specs = []
    for port_spec in port_specs:
        if len(port_spec) == 2:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier)))
        elif len(port_spec) == 3:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier),
                              port_spec[2])) 
    return out_specs

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

                   
class PM_CDMSDataReader( PersistentVisualizationModule ):
    
    dataCache = {}
    imageDataCache = {}

    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['portData'], **args)
        self.datasetId = None
        self.fileSpecs = None
        self.varSpecs = None
        self.gridSpecs = None
        self.currentTime = 0
        self.currentLevel = None
        self.timeIndex = 0
        self.timeValue = None
        self.useTimeIndex = False
        self.timeAxis = None
#        memoryLogger.log("Init CDMSDataReader")
        if self.outputType == CDMSDataType.Hoffmuller:
            self.addUVCDATConfigGuiFunction( 'chooseLevel', LevelConfigurationDialog, 'L', label='Choose Level' ) 
            
    def getTimeAxis(self):
        return self.timeAxis
       
    def getCachedImageData( self, data_id, cell_coords ):
        image_data = self.imageDataCache.get( data_id, None )
        if image_data: 
            image_data.cells.add( cell_coords )
            return image_data.data
        return None

    def setCachedImageData( self, data_id, cell_coords, image_data ):
        self.imageDataCache[data_id] = CachedImageData( image_data, cell_coords )

    @classmethod
    def clearCache( cls, cell_coords ):
        for dataCacheItems in cls.dataCache.items():
            dataCacheKey = dataCacheItems[0]
            dataCacheObj = dataCacheItems[1]
            if cell_coords in dataCacheObj.cells:
                dataCacheObj.cells.remove( cell_coords )
                if len( dataCacheObj.cells ) == 0:
                    varDataMap = dataCacheObj.data.get('varData', None )
                    if varDataMap: varDataMap[ 'newDataArray'] = None 
                    dataCacheObj.data['varData'] = None
                    del cls.dataCache[ dataCacheKey ]
#                    print "Removing Cached data: ", str( dataCacheKey )
        for imageDataItem in cls.imageDataCache.items():
            imageDataCacheKey = imageDataItem[0]
            imageDataCacheObj = imageDataItem[1]
            if cell_coords in imageDataCacheObj.cells:
                imageDataCacheObj.cells.remove( cell_coords )
                if len( imageDataCacheObj.cells ) == 0:
                    freeImageData( imageDataCacheObj.data )
                    imageDataCacheObj.data = None
                    print "Removing Cached image data: ", str( imageDataCacheKey )
        
    def getCachedData( self, varDataId, cell_coords ):
        dataCacheObj = self.dataCache.setdefault( varDataId, DataCache() )
        data = dataCacheObj.data.get( 'varData', None )
        if data: dataCacheObj.cells.add( cell_coords )
        return data

    def setCachedData(self, varDataId, cell_coords, varDataMap ):
        dataCacheObj = self.dataCache.setdefault( varDataId, DataCache() )
        dataCacheObj.data[ 'varData' ] = varDataMap
        dataCacheObj.cells.add( cell_coords )
                
    def getParameterDisplay( self, parmName, parmValue ):
        if parmName == 'timestep':
#            timestep = self.getTimeIndex( int( parmValue[0] ) )
            timestep = int( parmValue[0] )
            try:    return str( self.timeLabels[ timestep ] ), 10
            except: pass
        return None, 1

    def addCDMSVariable( self, cdms_var, index ):
        dsetId = "Computed"
        var = None
        varname = None
        if issubclass( cdms_var.__class__, CDMSVariableOperation ):
            varname = cdms_var.outvar.name
            var =  cdms_var.outvar.var
        else:
            varname = cdms_var.name
            var = cdms_var.var
            if cdms_var.file : dsetId = cdms_var.file
        self.cdmsDataset.addTransientVariable( varname, var )
        self.cdmsDataset.setVariableRecord( "VariableName%d" % index, '*'.join( [ dsetId, varname ] ) )
        return var, dsetId
    
    def designateAxes(self,var):
        lev_aliases = [ 'bottom', 'top', 'zdim' ]
        lev_axis_attr = [ 'z' ]
        lat_aliases = [ 'north', 'south', 'ydim' ]
        lat_axis_attr = [ 'y' ]
        lon_aliases = [ 'east', 'west', 'xdim' ]
        lon_axis_attr = [ 'x' ]
        for axis in var.getAxisList():
            if not isDesignated( axis ):
                if matchesAxisType( axis, lev_axis_attr, lev_aliases ):
                    axis.designateLevel()
                    print " --> Designating axis %s as a Level axis " % axis.id            
                elif matchesAxisType( axis, lat_axis_attr, lat_aliases ):
                    axis.designateLatitude()
                    print " --> Designating axis %s as a Latitude axis " % axis.id                     
                elif matchesAxisType( axis, lon_axis_attr, lon_aliases ):
                    axis.designateLongitude()
                    print " --> Designating axis %s as a Longitude axis " % axis.id 

    def setupTimeAxis( self, var, **args ):
        self.nTimesteps = 1
        self.timeRange = [ 0, self.nTimesteps, 0.0, 0.0 ]
        self.timeAxis = var.getTime()
        if self.timeAxis:
            self.nTimesteps = len( self.timeAxis ) if self.timeAxis else 1
            try:
                comp_time_values = self.timeAxis.asComponentTime()
                t0 = comp_time_values[0].torel(self.referenceTimeUnits).value
                if (t0 < 0):
                    self.referenceTimeUnits = self.timeAxis.units
                    t0 = comp_time_values[0].torel(self.referenceTimeUnits).value
                dt = 0.0
                if self.nTimesteps > 1:
                    t1 = comp_time_values[-1].torel(self.referenceTimeUnits).value
                    dt = (t1-t0)/(self.nTimesteps-1)
                    self.timeRange = [ 0, self.nTimesteps, t0, dt ]
            except:
                values = self.timeAxis.getValue()
                t0 = values[0] if len(values) > 0 else 0
                t1 = values[-1] if len(values) > 1 else t0
                dt = ( values[1] - values[0] )/( len(values) - 1 ) if len(values) > 1 else 0
                self.timeRange = [ 0, self.nTimesteps, t0, dt ]
        self.setParameter( "timeRange" , self.timeRange )
        self.cdmsDataset.timeRange = self.timeRange
        self.cdmsDataset.referenceTimeUnits = self.referenceTimeUnits
        self.timeLabels = self.cdmsDataset.getTimeValues()
        timeData = args.get( 'timeData', [ self.cdmsDataset.timeRange[2], 0, False ] )
        if timeData:
            self.timeValue = cdtime.reltime( float(timeData[0]), self.referenceTimeUnits )
            self.timeIndex = timeData[1]
            self.useTimeIndex = timeData[2]
        else:
            self.timeValue = cdtime.reltime( t0, self.referenceTimeUnits )
            self.timeIndex = 0
            self.useTimeIndex = False
#            print "Set Time [mid = %d]: %s, NTS: %d, Range: %s, Index: %d (use: %s)" % ( self.moduleID, str(self.timeValue), self.nTimesteps, str(self.timeRange), self.timeIndex, str(self.useTimeIndex) )
#            print "Time Step Labels: %s" % str( self.timeLabels )
           
    def execute(self, **args ):
        import api
        from packages.vtDV3D.CDMS_DatasetReaders import CDMSDataset
#        memoryLogger.log("start CDMS_DataReader:execute")
        cdms_vars = self.getInputValues( "variable"  ) 
        if cdms_vars and len(cdms_vars):
            iVar = 1
            cdms_var = cdms_vars.pop(0)
            self.cdmsDataset = CDMSDataset()
            var, dsetId = self.addCDMSVariable( cdms_var, iVar )
            self.newDataset = ( self.datasetId <> dsetId )
            if self.newDataset: ModuleStore.archiveCdmsDataset( dsetId, self.cdmsDataset )
            self.newLayerConfiguration = self.newDataset
            self.datasetId = dsetId
            self.designateAxes(var)
            self.setupTimeAxis( var, **args )
            intersectedRoi = self.cdmsDataset.gridBounds
            intersectedRoi = self.getIntersectedRoi( cdms_var, intersectedRoi )
            while( len(cdms_vars) ):
                cdms_var2 = cdms_vars.pop(0)
                if cdms_var2: 
                    iVar = iVar+1
                    self.addCDMSVariable( cdms_var2, iVar )
                    intersectedRoi = self.getIntersectedRoi( cdms_var2, intersectedRoi )
                  
            for iVarInputIndex in range( 2,5 ):
                cdms_var2 = self.getInputValue( "variable%d" % iVarInputIndex  ) 
                if cdms_var2: 
                    iVar = iVar+1
                    self.addCDMSVariable( cdms_var2, iVar )
                    intersectedRoi = self.getIntersectedRoi( cdms_var2, intersectedRoi )
                    
            self.generateOutput(roi=intersectedRoi)
#            if self.newDataset: self.addAnnotation( "datasetId", self.datasetId )
        else:
            dset = self.getInputValue( "dataset"  ) 
            if dset: 
                self.cdmsDataset = dset
#                dsetid = self.getAnnotation( "datasetId" )
#                if dsetid: self.datasetId = dsetid 
                dsetId = self.cdmsDataset.getDsetId()
#                self.newDataset = ( self.datasetId <> dsetId )
                self.newLayerConfiguration = True # self.newDataset
                self.datasetId = dsetId
                ModuleStore.archiveCdmsDataset( self.datasetId, self.cdmsDataset )
                self.timeRange = self.cdmsDataset.timeRange
                timeData = args.get( 'timeData', None )
                if timeData:
                    self.timeValue = cdtime.reltime( float(timeData[0]), self.referenceTimeUnits )
                    self.timeIndex = timeData[1]
                    self.useTimeIndex = timeData[2]
                    self.timeLabels = self.cdmsDataset.getTimeValues()
                    self.nTimesteps = self.timeRange[1]
#                print "Set Time: %s, NTS: %d, Range: %s, Index: %d (use: %s)" % ( str(self.timeValue), self.nTimesteps, str(self.timeRange), self.timeIndex, str(self.useTimeIndex) )
#                print "Time Step Labels: %s" % str( self.timeLabels ) 
                self.generateOutput( **args )
#                if self.newDataset: self.addAnnotation( "datasetId", self.datasetId )
#        memoryLogger.log("finished CDMS_DataReader:execute")
 
            
    def getParameterId(self):
        return self.datasetId
            
    def getPortData( self, **args ):
        return self.getInputValue( "portData", **args )  

    def generateVariableOutput( self, cdms_var ): 
        print str(cdms_var.var)
        self.set3DOutput( name=cdms_var.name,  output=cdms_var.var )

    def refreshVersion(self):
        portData = self.getPortData()
        if portData:
            portDataVersion = portData[1] + 1
            serializedPortData = portData[0]
            self.persistParameter( 'portData', [ serializedPortData, portDataVersion ] )
        
    def getOutputRecord( self, ndim = -1 ):
        portData = self.getPortData()
        if portData:
            oRecMgr = OutputRecManager( portData[0]  )
            orecs = oRecMgr.getOutputRecs( self.datasetId ) if oRecMgr else None
            if not orecs: raise ModuleError( self, 'No Variable selected for dataset %s.' % self.datasetId )             
            for orec in orecs:
                if (ndim < 0 ) or (orec.ndim == ndim): return orec
        return None
             
    def generateOutput( self, **args ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper
        oRecMgr = None 
        varRecs = self.cdmsDataset.getVarRecValues()
        cell_coords = DV3DPipelineHelper.getCellCoordinates( self.moduleID ) 
        if len( varRecs ):
#            print " VolumeReader->generateOutput, varSpecs: ", str(varRecs)
            oRecMgr = OutputRecManager() 
#            varCombo = QComboBox()
#            for var in varRecs: varCombo.addItem( str(var) ) 
            orec = OutputRec( 'volume', ndim=3, varList=varRecs )  # varComboList=[ varCombo ], 
            oRecMgr.addOutputRec( self.datasetId, orec ) 
        else:
            portData = self.getPortData()
            if portData:
#                print " VolumeReader->generateOutput, portData: ", portData
                oRecMgr = OutputRecManager( portData[0]  )
        orecs = oRecMgr.getOutputRecs( self.datasetId ) if oRecMgr else None
        if not orecs: raise ModuleError( self, 'No Variable selected for dataset %s.' % self.datasetId )             
        for orec in orecs:
            cachedImageDataName = self.getImageData( orec, **args ) 
            if cachedImageDataName: 
                cachedImageData = self.getCachedImageData( cachedImageDataName, cell_coords )            
                if   orec.ndim >= 3: self.set3DOutput( name=orec.name,  output=cachedImageData )
                elif orec.ndim == 2: self.set2DOutput( name=orec.name,  output=cachedImageData )
        self.currentTime = self.getTimestep()
     
    def getTimestep( self ):
        dt = self.timeRange[3]
        return 0 if dt <= 0.0 else int( round( ( self.timeValue.value - self.timeRange[2] ) / dt ) )

    def setCurrentLevel(self, level ): 
        self.currentLevel = level
               
    def getImageData( self, orec, **args ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper
        """
        This method converts cdat data into vtkImageData objects. The ds object is a CDMSDataset instance which wraps a CDAT CDMS Dataset object. 
        The ds.getVarDataCube method execution extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).   
        The array is then rescaled, converted to a 1D unsigned short array, and then wrapped as a vtkUnsignedShortArray using the vtkdata.SetVoidArray method call.  
        The vtk data array is then attached as point data to a vtkImageData object, which is returned.
        The CDAT metadata is serialized, wrapped as a vtkStringArray, and then attached as field data to the vtkImageData object.  
        """
        memoryLogger.log("Begin getImageData")
        varList = orec.varList
        npts = -1
        if len( varList ) == 0: return False
        varDataIds = []
        intersectedRoi = args.get('roi', None )
        if intersectedRoi: self.cdmsDataset.setRoi( intersectedRoi )
        exampleVarDataSpecs = None
        dsid = None
        if (self.outputType == CDMSDataType.Vector ) and len(varList) < 3:
            if len(varList) == 2: 
                imageDataName = getItem( varList[0] )
                dsid = imageDataName.split('*')[0]
                varList.append( '*'.join( [ dsid, '__zeros__' ] ) )
            else: 
                print>>sys.stderr, "Not enough components for vector plot: %d" % len(varList)
#        print " Get Image Data: varList = %s " % str( varList )
        for varRec in varList:
            range_min, range_max, scale, shift  = 0.0, 0.0, 1.0, 0.0   
            imageDataName = getItem( varRec )
            varNameComponents = imageDataName.split('*')
            if len( varNameComponents ) == 1:
                dsid = self.cdmsDataset.getReferenceDsetId() 
                varName = varNameComponents[0]
            else:
                dsid = varNameComponents[0]
                varName = varNameComponents[1]
            ds = self.cdmsDataset[ dsid ]
            if ds:
                var = ds.getVariable( varName )
                self.setupTimeAxis( var, **args )
            portName = orec.name
            selectedLevel = orec.getSelectedLevel() if ( self.currentLevel == None ) else self.currentLevel
            ndim = 3 if ( orec.ndim == 4 ) else orec.ndim
 #           default_dtype = np.ushort if ( (self.outputType == CDMSDataType.Volume ) or (self.outputType == CDMSDataType.Hoffmuller ) )  else np.float 
            pipeline = self.getCurrentPipeline()
#            default_dtype = DV3DPipelineHelper.getDownstreamRequiredDType( pipeline, self.moduleID, np.float )
            default_dtype = np.float
            scalar_dtype = args.get( "dtype", default_dtype )
            self._max_scalar_value = getMaxScalarValue( scalar_dtype )
            self._range = [ 0.0, self._max_scalar_value ]  
            datatype = getDatatypeString( scalar_dtype )
            if (self.outputType == CDMSDataType.Hoffmuller):
                if ( selectedLevel == None ):
                    varDataIdIndex = 0
                else:
                    varDataIdIndex = selectedLevel  
                                      
            iTimestep = self.timeIndex if ( varName <> '__zeros__' ) else 0
            varDataIdIndex = iTimestep  
            cell_coords = DV3DPipelineHelper.getCellCoordinates( self.moduleID ) 
            roiStr = ":".join( [ ( "%.1f" % self.cdmsDataset.gridBounds[i] ) for i in range(4) ] ) if self.cdmsDataset.gridBounds else ""
            varDataId = '%s;%s;%d;%s;%s' % ( dsid, varName, self.outputType, str(varDataIdIndex), roiStr )
            varDataIds.append( varDataId )
            varDataSpecs = self.getCachedData( varDataId, cell_coords ) 
            flatArray = None
            if varDataSpecs == None:
                if varName == '__zeros__':
                    assert( npts > 0 )
                    newDataArray = np.zeros( npts, dtype=scalar_dtype ) 
                    varDataSpecs = copy.deepcopy( exampleVarDataSpecs )
                    varDataSpecs['newDataArray'] = newDataArray.ravel('F')  
                    self.setCachedData( varName, cell_coords, varDataSpecs ) 
                else: 
                    tval = None if (self.outputType == CDMSDataType.Hoffmuller) else [ self.timeValue, iTimestep, self.useTimeIndex ] 
                    varData = self.cdmsDataset.getVarDataCube( dsid, varName, tval, selectedLevel )
                    if varData.id <> 'NULL':
                        varDataSpecs = self.getGridSpecs( varData, self.cdmsDataset.gridBounds, self.cdmsDataset.zscale, self.outputType, ds )
                        if (exampleVarDataSpecs == None) and (varDataSpecs <> None): exampleVarDataSpecs = varDataSpecs
                        range_min = varData.min()
                        if type( range_min ).__name__ == "MaskedConstant": range_min = 0.0
                        range_max = varData.max()
                        if type( range_max ).__name__ == 'MaskedConstant': range_max = 0.0
                        var_md = copy.copy( varData.attributes )
                                                          
                        if scalar_dtype == np.float:
                            varData = varData.filled( 1.0e-15 * range_min ).ravel('F')
                        else:
                            shift = -range_min
                            scale = ( self._max_scalar_value ) / ( range_max - range_min ) if  ( range_max > range_min ) else 1.0        
                            varData = ( ( varData + shift ) * scale ).astype(scalar_dtype).filled( 0 ).ravel('F')
                        
                        array_size = varData.size
                        if npts == -1:  npts = array_size
                        else: assert( npts == array_size )
                            
                        var_md[ 'range' ] = ( range_min, range_max )
                        var_md[ 'scale' ] = ( shift, scale )   
                        varDataSpecs['newDataArray'] = varData                     
                        md =  varDataSpecs['md']                 
                        md['datatype'] = datatype
                        md['timeValue']= self.timeValue.value
                        md['timeUnits' ] = self.referenceTimeUnits
                        md[ 'attributes' ] = var_md
                        md[ 'plotType' ] = 'zyt' if (self.outputType == CDMSDataType.Hoffmuller) else 'xyz'
                                        
                self.setCachedData( varDataId, cell_coords, varDataSpecs )  
        
        if not varDataSpecs: return None            

        cachedImageDataName = '-'.join( varDataIds )
        image_data = self.getCachedImageData( cachedImageDataName, cell_coords ) 
        if not image_data:
#            print 'Building Image for cache: %s ' % cachedImageDataName
            image_data = vtk.vtkImageData() 
            outputOrigin = varDataSpecs[ 'outputOrigin' ]
            outputExtent = varDataSpecs[ 'outputExtent' ]
            gridSpacing = varDataSpecs[ 'gridSpacing' ]
            if   scalar_dtype == np.ushort: image_data.SetScalarTypeToUnsignedShort()
            elif scalar_dtype == np.ubyte:  image_data.SetScalarTypeToUnsignedChar()
            elif scalar_dtype == np.float:  image_data.SetScalarTypeToFloat()
            image_data.SetOrigin( outputOrigin[0], outputOrigin[1], outputOrigin[2] )
#            image_data.SetOrigin( 0.0, 0.0, 0.0 )
            if ndim == 3: extent = [ outputExtent[0], outputExtent[1], outputExtent[2], outputExtent[3], outputExtent[4], outputExtent[5] ]   
            elif ndim == 2: extent = [ outputExtent[0], outputExtent[1], outputExtent[2], outputExtent[3], 0, 0 ]   
            image_data.SetExtent( extent )
            image_data.SetWholeExtent( extent )
            image_data.SetSpacing(  gridSpacing[0], gridSpacing[1], gridSpacing[2] )
#            print " ********************* Create Image Data, extent = %s, spacing = %s ********************* " % ( str(extent), str(gridSpacing) )
#            offset = ( -gridSpacing[0]*gridExtent[0], -gridSpacing[1]*gridExtent[2], -gridSpacing[2]*gridExtent[4] )
            self.setCachedImageData( cachedImageDataName, cell_coords, image_data )
                
        nVars = len( varList )
#        npts = image_data.GetNumberOfPoints()
        pointData = image_data.GetPointData()
        for aname in range( pointData.GetNumberOfArrays() ): 
            pointData.RemoveArray( pointData.GetArrayName(aname) )
        fieldData = self.getFieldData()
        na = fieldData.GetNumberOfArrays()
        for ia in range(na):
            aname = fieldData.GetArrayName(ia)
            if aname.startswith('metadata'):
                fieldData.RemoveArray(aname)
#                print 'Remove fieldData Array: %s ' % aname
        extent = image_data.GetExtent()    
        scalars, nTup = None, 0
        vars = [] 
        for varDataId in varDataIds:
            try: 
                varDataSpecs = self.getCachedData( varDataId, cell_coords )   
                newDataArray = varDataSpecs.get( 'newDataArray', None )
                md = varDataSpecs[ 'md' ] 
                varName = varDataId.split(';')[1]
                var_md = md[ 'attributes' ]            
                if newDataArray <> None:
                    vars.append( varName ) 
                    md[ 'valueRange'] = var_md[ 'range' ] 
                    vtkdata = getNewVtkDataArray( scalar_dtype )
                    nTup = newDataArray.size
                    vtkdata.SetNumberOfTuples( nTup )
                    vtkdata.SetNumberOfComponents( 1 )
                    vtkdata.SetVoidArray( newDataArray, newDataArray.size, 0 )
                    vtkdata.SetName( varName )
                    vtkdata.Modified()
                    pointData.AddArray( vtkdata )
#                    print "Add array to PointData: %s " % ( varName  )  
                    if (scalars == None) and (varName <> '__zeros__'):
                        scalars = varName
                        pointData.SetActiveScalars( varName  ) 
                        md[ 'scalars'] = varName 
            except Exception, err:
                print>>sys.stderr, "Error creating variable metadata: %s " % str(err)
                traceback.print_exc()
#         for iArray in range(2):
#             scalars = pointData.GetArray(iArray) 
# #            print "Add array %d to PointData: %s (%s)" % ( iArray, pointData.GetArrayName(iArray), scalars.GetName()  )       
        try:                           
            if (self.outputType == CDMSDataType.Vector ): 
                vtkdata = getNewVtkDataArray( scalar_dtype )
                vtkdata.SetNumberOfComponents( 3 )
                vtkdata.SetNumberOfTuples( nTup )
                iComp = 0
                for varName in vars:
                    fromArray =  pointData.GetArray( varName )
                    fromNTup = fromArray.GetNumberOfTuples()
                    tup0 = fromArray.GetValue(0)
                    toNTup = vtkdata.GetNumberOfTuples()
                    vtkdata.CopyComponent( iComp, fromArray, 0 )
                    if iComp == 0: 
                        md[ 'scalars'] = varName 
                    iComp = iComp + 1                    
                vtkdata.SetName( 'vectors' )
                md[ 'vectors'] = ','.join( vars ) 
                vtkdata.Modified()
                pointData.SetVectors(vtkdata)
                pointData.SetActiveVectors( 'vectors'  )         
            if len( vars )== 0: raise ModuleError( self, 'No dataset variables selected for output %s.' % orec.name) 
            for varDataId in varDataIds:
                varDataFields = varDataId.split(';')
                dsid = varDataFields[0] 
                varName = varDataFields[1] 
                if varName <> '__zeros__':
                    varDataSpecs = self.getCachedData( varDataId, cell_coords )
                    vmd = varDataSpecs[ 'md' ] 
                    var_md = md[ 'attributes' ]               
#                    vmd[ 'vars' ] = vars               
                    vmd[ 'title' ] = getTitle( dsid, varName, var_md )                 
                    enc_mdata = encodeToString( vmd ) 
                    if enc_mdata: fieldData.AddArray( getStringDataArray( 'metadata:%s' % varName,   [ enc_mdata ]  ) ) 
            if enc_mdata: fieldData.AddArray( getStringDataArray( 'varlist',  vars  ) )                       
            image_data.Modified()
        except Exception, err:
            print>>sys.stderr, "Error encoding variable metadata: %s " % str(err)
            traceback.print_exc()
        memoryLogger.log("End getImageData")
        return cachedImageDataName


    def getAxisValues( self, axis, roi ):
        values = axis.getValue()
        bounds = None
        if roi:
            if   axis.isLongitude():  bounds = [ roi[0], roi[2] ]
            elif axis.isLatitude():   bounds = [ roi[1], roi[3] ] if ( roi[3] > roi[1] ) else [ roi[3], roi[1] ] 
        if bounds:
            if len( values ) < 2: values = bounds
            else:
                if axis.isLongitude() and (values[0] > values[-1]):
                    values[-1] = values[-1] + 360.0 
                value_bounds = [ min(values[0],values[-1]), max(values[0],values[-1]) ]
                mid_value = ( value_bounds[0] + value_bounds[1] ) / 2.0
                mid_bounds = ( bounds[0] + bounds[1] ) / 2.0
                offset = (360.0 if mid_bounds > mid_value else -360.0)
                trans_val = mid_value + offset
                if (trans_val > bounds[0]) and (trans_val < bounds[1]):
                    value_bounds[0] = value_bounds[0] + offset
                    value_bounds[1] = value_bounds[1] + offset           
                bounds[0] = max( [ bounds[0], value_bounds[0] ] )
                bounds[1] = min( [ bounds[1], value_bounds[1] ] )
        return bounds, values

    def getCoordType( self, axis, outputType ):
        iCoord = -2
        if axis.isLongitude(): 
            self.lon = axis
            iCoord  = 0
        if axis.isLatitude(): 
            self.lat = axis
            iCoord  = 1
        if isLevelAxis( axis ): 
            self.lev = axis
            iCoord  = 2 if ( outputType <> CDMSDataType.Hoffmuller ) else -1
        if axis.isTime():
            self.time = axis
            iCoord  = 2 if ( outputType == CDMSDataType.Hoffmuller ) else -1
        return iCoord

    def getIntersectedRoi( self, var, current_roi ):   
        try:
            newRoi = newList( 4, 0.0 )
            varname = var.outvar.name if hasattr( var,'outvar') else var.name
            tvar = self.cdmsDataset.getTransientVariable( varname )
            if id( tvar ) == id( None ): return current_roi
            current_roi_size = getRoiSize( current_roi )
            for iCoord in range(2):
                axis = None
                if iCoord == 0: axis = tvar.getLongitude()
                if iCoord == 1: axis = tvar.getLatitude()
                axisvals = axis.getValue()          
                if ( len( axisvals.shape) > 1 ):
#                    displayMessage( "Curvilinear grids not currently supported by DV3D.  Please regrid. ")
                    return current_roi
                newRoi[ iCoord ] = axisvals[0] # max( current_roi[iCoord], roiBounds[0] ) if current_roi else roiBounds[0]
                newRoi[ 2+iCoord ] = axisvals[-1] # min( current_roi[2+iCoord], roiBounds[1] ) if current_roi else roiBounds[1]
            if ( current_roi_size == 0 ): return newRoi
            new_roi_size = getRoiSize( newRoi )
            return newRoi if ( ( current_roi_size > new_roi_size ) and ( new_roi_size > 0.0 ) ) else current_roi
        except:
            print>>sys.stderr, "Error getting ROI for input variable"
            traceback.print_exc()
            return current_roi
       
    def getGridSpecs( self, var, roi, zscale, outputType, dset ):   
        dims = var.getAxisIds()
        gridOrigin = newList( 3, 0.0 )
        outputOrigin = newList( 3, 0.0 )
        gridBounds = newList( 6, 0.0 )
        gridSpacing = newList( 3, 1.0 )
        gridExtent = newList( 6, 0 )
        outputExtent = newList( 6, 0 )
        gridShape = newList( 3, 0 )
        gridSize = 1
        domain = var.getDomain()
        self.lev = var.getLevel()
        axis_list = var.getAxisList()
        isCurvilinear = False
        for axis in axis_list:
            size = len( axis )
            iCoord = self.getCoordType( axis, outputType )
            roiBounds, values = self.getAxisValues( axis, roi )
            if iCoord >= 0:
                iCoord2 = 2*iCoord
                gridShape[ iCoord ] = size
                gridSize = gridSize * size
                outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] = size-1 
                vmax =  max( values[0], values[-1] )                   
                vmin =  min( values[0], values[-1] )                   
                if iCoord < 2:
                    lonOffset = 0.0 #360.0 if ( ( iCoord == 0 ) and ( roiBounds[0] < -180.0 ) ) else 0.0
                    outputOrigin[ iCoord ] = gridOrigin[ iCoord ] = vmin + lonOffset
                    spacing = (vmax - vmin)/(size-1)
                    if roiBounds:
                        if ( roiBounds[1] < 0.0 ) and  ( roiBounds[0] >= 0.0 ): roiBounds[1] = roiBounds[1] + 360.0
                        gridExtent[ iCoord2 ] = int( round( ( roiBounds[0] - vmin )  / spacing ) )                
                        gridExtent[ iCoord2+1 ] = int( round( ( roiBounds[1] - vmin )  / spacing ) )
                        if gridExtent[ iCoord2 ] > gridExtent[ iCoord2+1 ]:
                            geTmp = gridExtent[ iCoord2+1 ]
                            gridExtent[ iCoord2+1 ] = gridExtent[ iCoord2 ] 
                            gridExtent[ iCoord2 ] = geTmp
                        outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ]
                        outputOrigin[ iCoord ] = lonOffset + roiBounds[0]
                    roisize = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ] + 1                  
                    gridSpacing[ iCoord ] = spacing
                    gridBounds[ iCoord2 ] = roiBounds[0] if roiBounds else vmin 
                    gridBounds[ iCoord2+1 ] = (roiBounds[0] + roisize*spacing) if roiBounds else vmax
                else:                                             
                    gridSpacing[ iCoord ] = 1.0
#                    gridSpacing[ iCoord ] = zscale
                    gridBounds[ iCoord2 ] = vmin  # 0.0
                    gridBounds[ iCoord2+1 ] = vmax # float( size-1 )
        if gridBounds[ 2 ] > gridBounds[ 3 ]:
            tmp = gridBounds[ 2 ]
            gridBounds[ 2 ] = gridBounds[ 3 ]
            gridBounds[ 3 ] = tmp
        gridSpecs = {}
        md = { 'datasetId' : self.datasetId,  'bounds':gridBounds, 'lat':self.lat, 'lon':self.lon, 'lev':self.lev, 'time': self.timeAxis }
        gridSpecs['gridOrigin'] = gridOrigin
        gridSpecs['outputOrigin'] = outputOrigin
        gridSpecs['gridBounds'] = gridBounds
        gridSpecs['gridSpacing'] = gridSpacing
        gridSpecs['gridExtent'] = gridExtent
        gridSpecs['outputExtent'] = outputExtent
        gridSpecs['gridShape'] = gridShape
        gridSpecs['gridSize'] = gridSize
        gridSpecs['md'] = md
        if dset:  gridSpecs['attributes'] = dset.dataset.attributes
        return gridSpecs   
                 
    def computeMetadata( self ):
        metadata = PersistentVisualizationModule.computeMetadata( self )
        if self.cdmsDataset:
            metadata[ 'vars2d' ] = self.cdmsDataset.getVariableList( 2 )
            metadata[ 'vars3d' ] = self.cdmsDataset.getVariableList( 3 )
        if self.fileSpecs: metadata[ 'fileSpecs' ] = self.fileSpecs
        if self.varSpecs:  metadata[ 'varSpecs' ]  = self.varSpecs
        if self.gridSpecs: metadata[ 'gridSpecs' ] = self.gridSpecs
        return metadata

class PM_CDMS_ChartDataReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.ChartData
        PM_CDMSDataReader.__init__( self, mid, **args)

class CDMS_ChartDataReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_ChartDataReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     
        
class PM_CDMS_VolumeReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.Volume
        PM_CDMSDataReader.__init__( self, mid, **args)

class CDMS_VolumeReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VolumeReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     

class PM_CDMS_HoffmullerReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.Hoffmuller
        PM_CDMSDataReader.__init__( self, mid, **args)
    
class CDMS_HoffmullerReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_HoffmullerReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     

class PM_CDMS_SliceReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.Slice
        PM_CDMSDataReader.__init__( self, mid, **args)

class CDMS_SliceReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_SliceReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
class PM_CDMS_VectorReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.Vector
        PM_CDMSDataReader.__init__( self, mid, **args)

class PM_CDMS_VariableSpaceReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = CDMSDataType.VariableSpace
        PM_CDMSDataReader.__init__( self, mid, **args)


class CDMS_VectorReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VectorReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 

class CDMS_VariableSpaceReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VariableSpaceReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 

        
class CDMSVariableSource( VariableSource ):
      
    def __init__( self, **args ):
        VariableSource.__init__(self)  
        self.var = None       

    def compute(self):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper           
        inputId = self.forceGetInputFromPort( "inputId", None ) 
        self.var = DV3DPipelineHelper.get_input_variable( inputId )
        self.setResult( "self", self )    
        self.setResult( "axes", self.getAxes() ) 
        
    def getAxes(self):
        strReps = []
        axisList = self.var.getAxisList() 
        for axis in axisList:
            axisBoundsStr = None            
            if axis.isLatitude() or axis.isLongitude() or axis.isLevel(): 
                values = axis.getValue()   
                axisBoundsStr = "%s=(%.3f,%.3f)" % ( axis.id, values[0], values[-1] )
            elif axis.isTime():      
                values = axis.asComponentTime()   
                axisBoundsStr = "%s=('%s','%s')" % ( axis.id, str(values[0]), str(values[-1]) )
            strReps.append( axisBoundsStr )
        return ','.join( strReps )
                           
class CDMSReaderConfigurationWidget(DV3DConfigurationWidget): 
    """
    CDMSReaderConfigurationWidget ...
    
    """
    
    def __init__(self, module, controller, outputType, parent=None):
        """ CDMSReaderConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> CDMSReaderConfigurationWidget
        Setup the dialog ...
        
        """
        self.outputType = outputType
        self.outRecMgr = None
        self.refVar = None
        self.levelsAxis = None
        self.variableList = None
        self.serializedPortData = ''
        self.datasetId = None
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Data Reader Configuration', parent)
        self.outRecMgr = OutputRecManager()  
        self.initializeOutput() 
        self.stateChanged( False )     
     
    def getParameters( self, module ):
        global PortDataVersion
        ( self.variableList, self.datasetId, self.timeRange, self.refVar, self.levelsAxis ) =  DV3DConfigurationWidget.getVariableList( module.id )
        pmod = self.getPersistentModule()
        if pmod: 
            portData = pmod.getPortData( dbmod=self.module, datasetId=self.datasetId ) # getFunctionParmStrValues( module, "portData" )
            if portData and portData[0]: 
                 self.serializedPortData = portData[0]   
                 PortDataVersion = int( portData[1] )    
                                                  
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        
        """        
        outputsTab = QWidget()        
        self.tabbedWidget.addTab( outputsTab, 'output' ) 
        self.tabbedWidget.setCurrentWidget(outputsTab)
        outputsLayout = QVBoxLayout()                
        outputsTab.setLayout( outputsLayout )
        
        noutLayout = QHBoxLayout()                 
        outputsLayout.addLayout( noutLayout )
                           
        self.outputsTabbedWidget = QTabWidget()
        outputsLayout.addWidget( self.outputsTabbedWidget )
        
    def updateController(self, controller):
        global PortDataVersion
        PortDataVersion = PortDataVersion + 1
        parameterList = [ ('portData', [ self.serializedPortData, PortDataVersion ] ) ]
        self.persistParameterList( parameterList, datasetId=self.datasetId )
        self.stateChanged(False)
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.serializePortData()
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
#        self.close()
                                       
    def initializeOutput( self ):
        print " initializeOutputs, serializedPortData: %s " % self.serializedPortData
        if self.serializedPortData:
            oRecMgr = OutputRecManager( self.serializedPortData )
            for oRec in oRecMgr.getOutputRecs( self.datasetId ):
                variableSelections = oRec.varList if oRec.varList else []
                self.addOutputTab( oRec.ndim, oRec.name, variableSelections, oRec.level )
                for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): oRec.varSelections = variableSelections
        if   self.outputType == CDMSDataType.Volume:    
            self.addOutputTab( 3, 'volume'  )
        if   self.outputType == CDMSDataType.Hoffmuller:
            self.addOutputTab( 4, 'volume'  )
        elif self.outputType == CDMSDataType.Slice:     
            self.addOutputTab( 2, 'slice' )
        elif self.outputType == CDMSDataType.Vector:    
            self.addOutputTab( 3, 'volume' )
        elif self.outputType == CDMSDataType.ChartData:    
            self.addOutputTab( 3, 'volume' )
        self.updateVariableLists()
                
    def getOutputTabIndex( self, name ):
        ntabs = self.outputsTabbedWidget.count()
        for iTab in range( ntabs ):
            tabName = str( self.outputsTabbedWidget.tabText( iTab ) )
            if tabName == name: return iTab # self.outputsTabbedWidget.widget(iTab)
        return -1
               
    def addOutputTab( self, ndim, output_name = None, variableSelections=[], level=None ): 
        if output_name == None:
            qtname, ok = QInputDialog.getText( self, 'Get Output Name', 'Output name:' )
            if ok: output_name = str(qtname).strip().replace( ' ', '_' ).translate( None, OutputRecManager.sep )
        if output_name <> None:
            iExistingTabIndex = self.getOutputTabIndex( output_name )
            if iExistingTabIndex < 0:
                outputTab = self.createOutputTab( ndim, output_name, variableSelections, level )  
                if outputTab <> None:
                    self.outputsTabbedWidget.addTab( outputTab, output_name ) 
                    self.outputsTabbedWidget.setCurrentWidget( outputTab )
                    return outputTab
        return None, None
        
    def removeOutputTab( self ):
        tabIndex = self.outputsTabbedWidget.currentIndex()
        outputName = str( self.outputsTabbedWidget.tabText(tabIndex) )
        self.outRecMgr.deleteOutput( self.datasetId, outputName )
        self.outputsTabbedWidget.removeTab( tabIndex )
        self.updatePorts()

#    def updateNOutouts( self, nout_str ):
#        noutputs = int( nout_str )
#        current_nout = len( self.outputRecs )
#        if noutputs > current_nout:
#            for iout in range( current_nout, noutputs ):
#                default_name = "data%d" % iout
                    
    def createOutputTab( self, ndim, name, variableSelections = [], level=None ):  
        otab = QWidget()  
        otabLayout = QVBoxLayout()                
        otab.setLayout( otabLayout )

        if self.outputType == CDMSDataType.ChartData:
            varsComboList = []
            nvars = 3
            
            for iVar in range(nvars):           
                variables_Layout = QHBoxLayout()      
                variables_label = QLabel( "Select Output Variable %d:" % iVar )
                variables_Layout.addWidget( variables_label ) 
                varsCombo =  QComboBox ( self )
                self.connect( varsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectedVariableChanged ) 
                variables_label.setBuddy( varsCombo )
                variables_Layout.addWidget( varsCombo )  
                otabLayout.addLayout( variables_Layout )
                varsComboList.append( varsCombo )
                               
            orec = OutputRec( name, ndim=ndim, varComboList=varsComboList, varSelections=variableSelections )
            self.outRecMgr.addOutputRec( self.datasetId, orec )            
        elif self.outputType == CDMSDataType.Vector:
            varsComboList = []
            for vector_component in [ 'x', 'y', 'z' ]:
                variables_Layout = QHBoxLayout()      
                variables_label = QLabel( "Select %s component:" % vector_component )
                variables_Layout.addWidget( variables_label ) 
                varsCombo =  QComboBox ( self )
                self.connect( varsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectedVariableChanged ) 
                variables_label.setBuddy( varsCombo )
                varsCombo.setMaximumHeight( 30 )
                variables_Layout.addWidget( varsCombo )  
                otabLayout.addLayout( variables_Layout )
                varsComboList.append( varsCombo )                  
            orec = OutputRec( name, ndim=ndim, varComboList=varsComboList, varSelections=variableSelections ) 
            self.outRecMgr.addOutputRec( self.datasetId, orec )            
        elif self.outputType == CDMSDataType.Hoffmuller:
            levels_Layout = QHBoxLayout() 
            
            levels_label = QLabel( "Select Level:"  )
            levels_Layout.addWidget( levels_label ) 
            levelsCombo =  QComboBox ( self )
            self.connect( levelsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectedLevelChanged ) 
            levels_label.setBuddy( levelsCombo )
            levels_Layout.addWidget( levelsCombo )  
            otabLayout.addLayout( levels_Layout )
             
            variables_Layout = QHBoxLayout()     
            variables_label = QLabel( "Select Output Variable:"  )
            variables_Layout.addWidget( variables_label ) 
            varsCombo =  QComboBox ( self )
            self.connect( varsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectedVariableChanged ) 
            variables_label.setBuddy( varsCombo )
            variables_Layout.addWidget( varsCombo )  
            otabLayout.addLayout( variables_Layout )
                    
            orec = OutputRec( name, ndim=ndim, varComboList=[varsCombo], levelsCombo=levelsCombo, varSelections=variableSelections, level=level ) 
            self.outRecMgr.addOutputRec( self.datasetId, orec ) 
        else:
            variables_Layout = QHBoxLayout()      
            variables_label = QLabel( "Select Output Variable:"  )
            variables_Layout.addWidget( variables_label ) 
            varsCombo =  QComboBox ( self )
            self.connect( varsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectedVariableChanged ) 
            variables_label.setBuddy( varsCombo )
            variables_Layout.addWidget( varsCombo )  
            otabLayout.addLayout( variables_Layout )
                    
            orec = OutputRec( name, ndim=ndim, varComboList=[varsCombo], varSelections=variableSelections ) 
            self.outRecMgr.addOutputRec( self.datasetId, orec ) 
        
        return otab
    
    def selectedVariableChanged(self, vname ):
        self.stateChanged()
        
    def selectedLevelChanged(self, vname ):
        self.stateChanged()
    
    def updateVariableLists(self):
        if self.outRecMgr:  
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): 
                for varCombo in oRec.varComboList: 
                    varCombo.clear()
                    if ( self.outputType == CDMSDataType.Vector ):  
                        varCombo.addItem( '__zeros__' ) 
                    if ( oRec.levelsCombo <> None) and ( self.levelsAxis <> None ): 
                        oRec.levelsCombo.clear()
                        levels = self.levelsAxis.getValue()
                        for level in levels: 
                            oRec.levelsCombo.addItem( QString( str(level) ) ) 
            if self.variableList:                    
                for ( var, var_ndim ) in self.variableList:               
                    for oRec in self.outRecMgr.getOutputRecs( self.datasetId ):
                        if (var_ndim == oRec.ndim) or ( (oRec.ndim == 4) and (var_ndim > 1) ) : 
                            for varCombo in oRec.varComboList: varCombo.addItem( str(var) ) 
                    
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): 
                if oRec.varSelections:
                    varIter = iter( oRec.varSelections )
                    for varCombo in oRec.varComboList: 
                        try:
                            varSelectionRec = varIter.next()
                            itemIndex = varCombo.findText( varSelectionRec[0], Qt.MatchFixedString )
                            if itemIndex >= 0: varCombo.setCurrentIndex( itemIndex )
                        except: pass
                if oRec.level:
                    itemIndex = oRec.levelsCombo.findText(  oRec.level, Qt.MatchFixedString )
                    oRec.levelsCombo.setCurrentIndex( itemIndex )
        
    def getCurentOutputRec(self):
        tabIndex = self.outputsTabbedWidget.currentIndex()
        outputName = str( self.outputsTabbedWidget.tabText(tabIndex) )
        return self.outRecMgr.getOutputRec( self.datasetId, outputName ) 
        
    def serializePortData( self ):
        oRec = self.getCurentOutputRec()
        if oRec: oRec.updateSelections()
        self.serializedPortData = self.outRecMgr.serialize()
        print " -- PortData: %s " % self.serializedPortData


class CDMS_HoffmullerReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.Hoffmuller, parent)

    def getParameters( self, module ):
        CDMSReaderConfigurationWidget.getParameters( self, module ) 

class CDMS_ChartDataConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.ChartData, parent)

    def getParameters( self, module ):
        CDMSReaderConfigurationWidget.getParameters( self, module ) 

class CDMS_VolumeReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.Volume, parent)

    def getParameters( self, module ):
        CDMSReaderConfigurationWidget.getParameters( self, module ) 

class CDMS_SliceReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.Slice, parent)


class CDMS_VectorReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.Vector, parent)

if __name__ == '__main__':
    dataFilePath = '/Developer/Data/AConaty/comp-ECMWF/ac-comp1-geos5.xml'
    dataset = cdms2.open( dataFilePath )
    var = dataset[ 'tmpu' ]
    pass
    
class CDMSTransientVariable(Variable):
    _input_ports = expand_port_specs([("name", "basic:String"),
                                      ("inputId", "basic:String"),
                                      ("url", "basic:String"),
                                      ("axes", "basic:String"),
                                      ("axesOperations", "basic:String"),
                                      ("attributes", "basic:Dictionary"),
                                      ("axisAttributes", "basic:Dictionary"),
                                      ("setTimeBounds", "basic:String")])
    
#    _output_ports = expand_port_specs([("self", "CDMSTransientVariable")])

    def __init__(self, source=None, name=None, axes=None, axesOperations=None, attributes=None, axisAttributes=None, timeBounds=None):
        Variable.__init__( self, None, None, source, name, False )
        self.axes = axes
        self.axesOperations = axesOperations
        self.attributes = attributes
        self.axisAttributes = axisAttributes
        self.timeBounds = timeBounds
        self.var = None
        self.inputId = None

    def __copy__(self):
        """__copy__() -> CDMSVariable - Returns a clone of itself"""
        cp = CDMSTransientVariable()
        cp.source = self.source
        cp.name = self.name
        cp.axes = self.axes
        cp.axesOperations = self.axesOperations
        cp.attributes = self.attributes
        cp.axisAttributes = self.axisAttributes
        cp.timeBounds = self.timeBounds
        cp.inputId = self.inputId
        return cp
        
    def to_module(self, controller):
        reg = get_module_registry()
        desc = reg.get_descriptor_by_name( identifier, self.__class__.__name__, 'cdms' )
        module = controller.create_module_from_descriptor( desc )
        functions = []
        if self.url is not None:
            functions.append(("url", [self.url]))
        if self.name is not None:
            functions.append(("name", [self.name]))
        if self.inputId is not None:
            functions.append(("inputId", [str(self.inputId)]))
        if self.axes is not None:
            functions.append(("axes", [self.axes]))
        if self.axesOperations is not None:
            functions.append(("axesOperations", [self.axesOperations]))
        if self.attributes is not None:
            functions.append(("attributes", [self.attributes]))
        if self.axisAttributes is not None:
            functions.append(("axisAttributes", [self.axisAttributes]))
        if self.timeBounds is not None:
            functions.append(("setTimeBounds", [self.timeBounds]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        
    
    def to_python(self):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper   
                 
        if self.source:
            var = self.source.var 
        elif self.inputId:          
            var = DV3DPipelineHelper.get_input_variable( self.inputId )
        else: 
            print>>sys.stderr, "Error, no Input to Pipeline"
            return None
      
        varName = self.name
            
        if self.axes is not None:
            try:
                var = eval("var.__call__(%s)"% self.axes)
            except Exception, e:
                raise ModuleError(self, "Invalid 'axes' specification: %s" % str(e))
            
        #make sure that var.id is the same as self.name
        var.id = self.name
        if self.attributes is not None:
            for attr in self.attributes:
                try:
                    attValue=eval(str(self.attributes[attr]).strip())
                except:
                    attValue=str(self.attributes[attr]).strip()
                setattr(var,attr, attValue) 
                       
        if self.axisAttributes is not None:
            for axName in self.axisAttributes:
                for attr in self.axisAttributes[axName]:
                    try:
                        attValue=eval(str(self.axisAttributes[axName][attr]).strip())
                    except:
                        attValue=str(self.axisAttributes[axName][attr]).strip()
                    ax = var.getAxis(var.getAxisIndex(axName))
                    setattr(ax,attr, attValue)
                    
        if self.timeBounds is not None:
            var = self.applySetTimeBounds(var, self.timeBounds)
                    
        return var
    
    def to_python_script(self, include_imports=False, ident=""):
        text = ''
        if include_imports:
            text += ident + "import cdms2, cdutil, genutil\n"
        var = self.source.var
        if self.axes is not None:
            text += ident + "%s = %s(%s)\n"% (self.name, self.name, self.axes)
        if self.axesOperations is not None:
            text += ident + "axesOperations = eval(\"%s\")\n"%self.axesOperations
            text += ident + "for axis in list(axesOperations):\n"
            text += ident + "    if axesOperations[axis] == 'sum':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal', action='sum')\n"% (self.name, self.name) 
            text += ident + "    elif axesOperations[axis] == 'avg':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal')\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'wgt':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'gtm':\n"
            text += ident + "        %s = genutil.statistics.geometricmean(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'std':\n"
            text += ident + "        %s = genutil.statistics.std(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
       
        if self.attributes is not None:
            text += "\n" + ident + "#modifying variable attributes\n"
            for attr in self.attributes:
                text += ident + "%s.%s = %s\n" % (self.name, attr,
                                                  repr(self.attributes[attr]))
                
        if self.axisAttributes is not None:
            text += "\n" + ident + "#modifying axis attributes\n"
            for axName in self.axisAttributes:
                text += ident + "ax = %s.getAxis(%s.getAxisIndex('%s'))\n" % (self.name,self.name,axName)
                for attr in self.axisAttributes[axName]:
                    text += ident + "ax.%s = %s\n" % ( attr,
                                        repr(self.axisAttributes[axName][attr]))
        
        if self.timeBounds is not None:
            data = self.timeBounds.split(":")
            if len(data) == 2:
                timeBounds = data[0]
                val = float(data[1])
            else:
                timeBounds = self.timeBounds
            text += "\n" + ident + "#%s\n"%timeBounds
            if timeBounds == "Set Bounds For Yearly Data":
                text += ident + "cdutil.times.setTimeBoundsYearly(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Monthly Data":
                text += ident + "cdutil.times.setTimeBoundsMonthly(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Twice-daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,2)\n"%self.name
            elif timeBounds == "Set Bounds For 6-Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,4)\n"%self.name
            elif timeBounds == "Set Bounds For Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,24)\n"%self.name
            elif timeBounds == "Set Bounds For X-Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,%g)\n"%(self.name,val)
                
        return text

        
    @staticmethod
    def from_module(module):
        var = CDMSTransientVariable()
        var.url = get_value_from_function(module, 'url')
        var.name = get_value_from_function(module, 'name')
        var.inputId = get_value_from_function(module, 'inputId')
        var.axes = get_value_from_function(module, 'axes')
        var.axesOperations = get_value_from_function(module, 'axesOperations')
        attrs = get_value_from_function(module, 'attributes')
        if attrs is not None:
            var.attributes = ast.literal_eval(attrs)
        else:
            var.attributes = attrs
            
        axattrs = get_value_from_function(module, 'axisAttributes')
        if axattrs is not None:
            var.axisAttributes = ast.literal_eval(axattrs)
        else:
            var.axisAttributes = axattrs
        var.timeBounds = get_value_from_function(module, 'setTimeBounds')
#        var.__class__ = CDMSTransientVariable
        return var
        
    def compute(self):
        self.axes = self.forceGetInputFromPort("axes")
        self.axesOperations = self.forceGetInputFromPort("axesOperations")
        self.attributes = self.forceGetInputFromPort("attributes")
        self.axisAttributes = self.forceGetInputFromPort("axisAttributes")
        self.timeBounds = self.forceGetInputFromPort("setTimeBounds")
        self.get_port_values()
        self.var = self.to_python()
        self.setResult("self", self)

    def get_port_values(self):
        self.url = self.forceGetInputFromPort( "url", None )
        self.source = self.forceGetInputFromPort( "source", None )
        self.inputId = self.forceGetInputFromPort( "inputId", None )  
        self.name = self.forceGetInputFromPort( "name", None )

    @staticmethod
    def applyAxesOperations(var, axesOperations):
        """ Apply axes operations to update the slab """
        try:
            axesOperations = ast.literal_eval(axesOperations)
        except:
            raise TypeError("Invalid string 'axesOperations': %s" % str(axesOperations) )

        for axis in list(axesOperations):
            if axesOperations[axis] == 'sum':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal',
                                      action='sum')
            elif axesOperations[axis] == 'avg':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal')
            elif axesOperations[axis] == 'wgt':
                var = cdutil.averager(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'gtm':
                var = genutil.statistics.geometricmean(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'std':
                var = genutil.statistics.std(var, axis="(%s)" % axis)
        return var

    @staticmethod
    def applySetTimeBounds(var, timeBounds):
        data = timeBounds.split(":")
        if len(data) == 2:
            timeBounds = data[0]
            val = float(data[1])
        if timeBounds == "Set Bounds For Yearly Data":
            cdutil.times.setTimeBoundsYearly(var)
        elif timeBounds == "Set Bounds For Monthly Data":
            cdutil.times.setTimeBoundsMonthly(var)
        elif timeBounds == "Set Bounds For Daily Data":
            cdutil.times.setTimeBoundsDaily(var)
        elif timeBounds == "Set Bounds For Twice-daily Data":
            cdutil.times.setTimeBoundsDaily(var,2)
        elif timeBounds == "Set Bounds For 6-Hourly Data":
            cdutil.times.setTimeBoundsDaily(var,4)
        elif timeBounds == "Set Bounds For Hourly Data":
            cdutil.times.setTimeBoundsDaily(var,24)
        elif timeBounds == "Set Bounds For X-Daily Data":
            cdutil.times.setTimeBoundsDaily(var,val)
        return var

