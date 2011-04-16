'''
Created on Dec 11, 2010

@author: tpmaxwel
'''
import vtk, sys, os, copy, time
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from InteractiveConfiguration import *
from core.modules.vistrails_module import Module, ModuleError
from WorkflowModule import WorkflowModule 
from ModuleStore import ModuleStoreDatabase
from core.vistrail.port_spec import PortSpec
from vtUtilities import *
from PersistentModule import * 
from ROISelection import ROISelectionWidget
from vtDV3DConfiguration import configuration
import numpy.ma as ma
from vtk.util.misc import vtkGetDataRoot
packagePath = os.path.dirname( __file__ ) 
import cdms2, cdtime 
PortDataVersion = 0
DataSetVersion = 0

def getDataRoot():
    DATA_ROOT = vtkGetDataRoot() 
    if configuration.check( 'data_root' ): 
        DATA_ROOT = configuration.vtk_data_root
    return DATA_ROOT

def getComponentTimeValues( dataset ):
    rv = None
    if dataset <> None:
        dims = dataset.axes.keys()
        for dim in dims:
            axis = dataset.getAxis( dim )
            if axis.isTime():
                if axis.calendar.lower() == 'gregorian': 
                    cdtime.DefaultCalendar = cdtime.GregorianCalendar 
                if hasattr( axis, 'partition' ):
                    rv = []
                    for part in axis.partition:
                        for iTime in range( part[0], part[1] ):
                            tval = cdtime.reltime( iTime, axis.units )
                            rv.append( tval.tocomp() )
                    break
                else:
                    rv = axis.asComponentTime()
    return rv
    
class CDMSDataset(Module):
    
    NullVariable = cdms2.createVariable( np.array([]), id='NULL' )

    def __init__( self, id, dataset=None, dataFile = None ):
        Module.__init__(self)
        self.id = id
        self.dataset = dataset
        self.cdmsFile = dataFile
        self.transientVariables = {}

    def __del__( self ):
        self.dataset.close()
         
    def addTransientVariable( self, varName, variable, ndim = None ):
        self.transientVariables[ varName ] = variable

    def getTransientVariable( self, varName ):
        return self.transientVariables[ varName ]

    def getTransientVariableNames( self ):
        return self.transientVariables.keys()
    
    def getTimeValues(self):
        return self.dataset['time'].getValue() 
    
    def getLevAxis(self):
        for axis in self.dataset.axes.values():
            if axis.isLevel(): return axis
        return None

    def getLevBounds(self):
        levaxis, levbounds = self.getLevAxis(), None
        values = levaxis.getValue()
        ascending_values = ( values[-1] > values[0] )
        if levaxis:
            if   levaxis.attributes.get( 'positive', '' ) == 'down' and ascending_values:   levbounds = slice( None, None, -1 )
            elif levaxis.attributes.get( 'positive', '' ) == 'up' and not ascending_values: levbounds = slice( None, None, -1 )
        return levbounds
    
    def getVarData( self, varName ):
        if varName in self.dataset.variables:
            varData = self.dataset[ varName ]
            order = varData.getOrder()
            args = {}
            timevalues = getComponentTimeValues( self.dataset )
            levbounds = self.getLevBounds()
            if self.timeRange: args['time'] = ( timevalues[ self.timeRange[0] ], timevalues[ self.timeRange[1] ] )
            args['lon'] = slice( self.gridExtent[0], self.gridExtent[1] )
            args['lat'] = slice( self.gridExtent[2], self.gridExtent[3] )
            if levbounds: args['lev'] = levbounds
            args['order'] = 'xyz'
            print "Reading variable %s, axis order = %s, shape = %s, roi = %s " % ( varName, order, str(varData.shape), str(args) )
            return varData( **args )
        elif varName in self.transientVariables:
            return self.transientVariables[ varName ]
        else: 
            print>>sys.stderr, "Error: can't find variable %s in dataset" % varName
            return self.NullVariable

    def getVarDataTimeSlice( self, varName, iTimeIndex ):
        """
        This method extracts a VDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        if varName in self.dataset.variables:
            varData = self.dataset[ varName ]
            order = varData.getOrder()
            args = {}
            timevalues = getComponentTimeValues( self.dataset )
            levbounds = self.getLevBounds()
            try:
                tval = timevalues[ iTimeIndex ]
                args['time'] = tval
                args['lon'] = slice( self.gridExtent[0], self.gridExtent[1]+1 )
                args['lat'] = slice( self.gridExtent[2], self.gridExtent[3]+1 )
                if levbounds: args['lev'] = levbounds
                args['order'] = 'xyz'
    #            args['squeeze'] = 1
                print "Reading variable %s, time = %s(%d), shape = %s, args = %s " % ( varName, tval, iTimeIndex, str(varData.shape), str(args) )
                return varData( **args )
            except Exception, err:
                print>>sys.stderr, ' Exception getting var slice: %s ' % str( err )
                pass
        elif varName in self.transientVariables:
            return self.transientVariables[ varName ]
        else: 
            print>>sys.stderr, "Error: can't find variable %s in dataset" % varName
            return self.NullVariable

    def getAxisValues( self, axis, roi ):
        values = axis.getValue()
        bounds = None
        if roi:
            if   axis.isLongitude():  bounds = [ roi[0], roi[2] ]
            elif axis.isLatitude():   bounds = [ roi[1], roi[3] ] 
        if bounds:
            bounds[0] = max( [ bounds[0], values[0]  ] )
            bounds[1] = min( [ bounds[1], values[-1] ] )
        return bounds, values

    def getCoordType( self, axis ):
        iCoord = -2
        if axis.isLongitude(): 
            self.lon = axis
            iCoord  = 0
        if axis.isLatitude(): 
            self.lat = axis
            iCoord  = 1
        if axis.isLevel(): 
            self.lev = axis
            iCoord  = 2
        if axis.isTime(): 
            self.time = axis
            iCoord  = -1
        return iCoord
    
    @staticmethod
    def getInstance( dsetId, cdmsFile, timeRange=None, roi = None ):
        dsModule = None
        if cdmsFile:
            dataset = cdms2.open( cdmsFile ) 
            if dataset <> None:
                dsModule = CDMSDataset( dsetId, dataset, cdmsFile )
                dims = dsModule.dataset.axes.keys()
                dsModule.gridOrigin = newList( 3, 0.0 )
                dsModule.gridBounds = newList( 6, 0.0 )
                dsModule.gridSpacing = newList( 3, 1.0 )
                dsModule.gridExtent = newList( 6, 0 )
                dsModule.gridShape = newList( 3, 0 )
                dsModule.gridSize = 1
                dsModule.timeRange = timeRange
                for dim in dims:
                    axis = dsModule.dataset.getAxis( dim )
                    size = axis.length
                    iCoord = dsModule.getCoordType( axis )
                    roiBounds, values = dsModule.getAxisValues( axis, roi )
                    if iCoord == -1: timeValues = values
                    if iCoord >= 0:
                        iCoord2 = 2*iCoord
                        dsModule.gridShape[ iCoord ] = size
                        dsModule.gridSize = dsModule.gridSize * size
                        dsModule.gridExtent[ iCoord2+1 ] = size-1                    
                        if iCoord < 2:
                            spacing = (values[size-1] - values[0])/(size-1)
                            if roiBounds:
                                dsModule.gridExtent[ iCoord2 ] = int( round( ( roiBounds[0] - values[0] )  / spacing ) )                
                                dsModule.gridExtent[ iCoord2+1 ] = int( round( ( roiBounds[1] - values[0] )  / spacing ) )
                            roisize = dsModule.gridExtent[ iCoord2+1 ] - dsModule.gridExtent[ iCoord2 ] + 1                  
                            dsModule.gridSpacing[ iCoord ] = spacing
                            dsModule.gridOrigin[ iCoord ] = values[0]
                            dsModule.gridBounds[ iCoord2 ] = roiBounds[0] if roiBounds else values[0] 
                            dsModule.gridBounds[ iCoord2+1 ] = (roiBounds[0] + roisize*spacing) if roiBounds else values[ size-1 ]
                        else:                                             
                            dsModule.gridSpacing[ iCoord ] = 1.0
                            dsModule.gridOrigin[ iCoord ] = 0.0
                            dsModule.gridBounds[ iCoord2 ] = 0.0
                            dsModule.gridBounds[ iCoord2+1 ] = float( size-1 )
        return dsModule             

    
class PM_CDMS_FileReader( PersistentVisualizationModule ):

    def __init__(self, mid):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['timeRange','roi'] )
            
    def execute(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """  
        import api
        dsMapData = self.getInputValue( "datasets" )
        if dsMapData: 
            datasetMap = deserializeStrMap( getItem( dsMapData ) )
            dsData = self.getInputValue( "datasetId" )
            if dsData:
                self.datasetId = getItem( dsData ) 
                self.cdmsFile = datasetMap[ self.datasetId ]
                time_range = self.getInputValue( "timeRange"  )
                self.timeRange =[ int(sval) for sval in time_range ]        
                roi_data = self.getInputValue( "roi" )
                self.roi =[ float(sroi) for sroi in roi_data ]        
                self.datasetModule = CDMSDataset.getInstance( self.datasetId, self.cdmsFile, self.timeRange, self.roi )
                self.setParameter( "timeRange" , time_range )
                self.setParameter( "roi", roi_data )
                self.setResult( 'dataset', self.datasetModule )

    def dvUpdate(self):
        pass     
        
    def getMetadata( self, metadata={}, port=None ):
        PersistentVisualizationModule.getMetadata( metadata )
        if self.cdmsFile:
            dataset = cdms2.open( self.cdmsFile ) 
            if dataset <> None: 
                vars3d = []
                vars2d = []      
                for var in self.dataset.variables:               
                    vardata = self.dataset[var]
                    var_ndim = getVarNDim( vardata )
                    if var_ndim == 2: vars2d.append( var )
                    if var_ndim == 3: vars3d.append( var )
                metadata[ 'vars2d' ] = vars2d
                metadata[ 'vars3d' ] = vars3d
                metadata[ 'datasetId' ] = self.datasetId
                dataset.close()
        return metadata
      
#class PM_CDMSVariable( PersistentVisualizationModule ):
#
#    def __init__(self, mid):
#        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False )
#        self.timeIndex = 0
#        self.dataCache = {}
#        self.imageData = {}
#        self.currentTime = 0
#        self.primaryMetaDataPort = "dataset"
#        
#    def getCachedData(self, iTimestep, varName ):
#        if varName == '__zeros__': iTimestep = 0
#        varData = self.dataCache.setdefault(iTimestep, {} )
#        return varData.get( varName, ( None, None ) )
#
#    def setCachedData(self, iTimestep, varName, varDataTuple ):
#        if varName == '__zeros__': iTimestep = 0
#        varData = self.dataCache.setdefault(iTimestep, {} )
#        varData[ varName ] = varDataTuple
#        
##    def initializeOutputPorts( self, reg ):
##        import api
###        
##        descriptor = reg.get_descriptor_by_name( 'gov.nasa.nccs.vtdv3d', 'CDMSModule' )
##        vistrails_interpreter = getDefaultInterpreter()
##        controller = api.get_current_controller()
##        portData = wmod.forceGetInputFromPort( "portData", None )  
##        print  " --- initializePorts, data: %s "  % portData
##        if portData:
##            oRecMgr = OutputRecManager( portData )
##            for orec in oRecMgr.getOutputRecs():
##                self.createOutputPort( orec.name )
##    
##    def createOutputPort( self, port_name ):
##        reg = core.modules.module_registry.get_module_registry() 
##        port_spec = self.getOutputPortSpec( port_name ) 
##        if port_spec == None: 
##            reg.add_output_port( CDMSModule, port_name, AlgorithmOutputModule3D ) 
#
##    def getOutputPortSpec( self, port_name ):
##        controller, module = self.getRegisteredModule()
##        for port_spec in module.output_port_specs:
##            if port_spec.name == port_name:
##                return port_spec
##        return None
#                        
#    def getTimeStepData(self):
#        self.generateOutput()
#        
#    def getTimeIndex( self, timeCounterValue ):
#        time_range = self.timeRange if ( self.timeRange <> None ) else [ 0, self.nTimesteps-1 ]
#        nts = ( self.timeRange[1] - self.timeRange[0] ) if ( self.timeRange <> None ) else self.nTimesteps
#        return ( timeCounterValue %  nts ) + time_range[0]
#       
#    def processParameterChange( self, parameter_name, new_parameter_value ):
#        if parameter_name == 'timestep':
#            ts = self.getTimeIndex( int( getItem( new_parameter_value ) ) )
#            if ts <> self.timeIndex:
#                self.timeIndex = ts
#                self.getTimeStepData()
##                self.executeWorkflow()
#        self.parmUpdating[ parameter_name ] = False 
#                
#    def getParameterDisplay( self, parmName, parmValue ):
#        if parmName == 'timestep':
#            timestep = self.getTimeIndex( int( parmValue[0] ) )
#            return str( self.timeLabels[ timestep ] ), 10
#        return None, 1
#        
#    def execute(self):
#        """ compute() -> None
#        Dispatch the vtkRenderer to the actual rendering widget
#        """  
#        self.cdmsDataset = self.getInputValue( "dataset" )    
#        if self.cdmsDataset <> None:
#            self.nTimesteps = self.cdmsDataset.time.length
#            self.timeRange = self.cdmsDataset.timeRange
#            self.timeLabels = self.cdmsDataset.time.asComponentTime()
#            self.timeValues = self.cdmsDataset.time.asRelativeTime()
#            self.timeUnits = self.cdmsDataset.time.units
#            self.generateOutput()
# 
#    def generateOutput( self ):       
#        portData = self.getInputValue( "portData" )  
#        oRecMgr = OutputRecManager( portData[0] if portData else None )
#        wmod = self.getWorkflowModule()    
#        for orec in oRecMgr.getOutputRecs():
#            imageDataCreated = self.getImageData( orec )               
#            if imageDataCreated: 
#                if   orec.ndim == 3: self.set3DOutput( name=orec.name,  output=self.imageData[orec.name], wmod = wmod )
#                elif orec.ndim == 2: self.set2DOutput( name=orec.name,  output=self.imageData[orec.name], wmod = wmod  )
#
#    def getMetadata( self, metadata={}, port=None ):
#        PersistentVisualizationModule.getMetadata( metadata )
#        portData = self.getInputValue( "portData" )  
#        oRecMgr = OutputRecManager( portData[0] if portData else None )
#        orec = oRecMgr.getOutputRec( port )
#        if orec: metadata[ 'layers' ] = orec.varList
#        return metadata
#          
#    def getImageData( self, orec, **args ):
#        varList = orec.varList
#        if len( varList ) == 0: return False
##        printTime('Start getImageData')
#        portName = orec.name
#        ndim = orec.ndim
#        imageDataCreated = False
#        scalar_dtype = args.get( "dtype", np.ushort if (ndim == 3) else np.float )
#        self._max_scalar_value = getMaxScalarValue( scalar_dtype )
#        self._range = [ 0.0, self._max_scalar_value ]  
#        ds = self.cdmsDataset
#        self.timeRange = ds.timeRange
#        print " --- CDMS-GetImageData: Origin= %s, Spacing= %s, Extent= %s, Timestep= %d" % ( ds.gridOrigin, ds.gridSpacing, ds.gridExtent, self.timeIndex )
#
#        if not ( portName in self.imageData ):
#            image_data = vtk.vtkImageData() 
#            if   scalar_dtype == np.ushort: image_data.SetScalarTypeToUnsignedShort()
#            elif scalar_dtype == np.ubyte:  image_data.SetScalarTypeToUnsignedChar()
#            elif scalar_dtype == np.float:  image_data.SetScalarTypeToFloat()
#            image_data.SetOrigin( ds.gridOrigin[0], ds.gridOrigin[1], ds.gridOrigin[2] )
#            image_data.SetSpacing( ds.gridSpacing[0], ds.gridSpacing[1], ds.gridSpacing[2] )
#            if ndim == 3:    image_data.SetExtent( ds.gridExtent[0], ds.gridExtent[1], ds.gridExtent[2], ds.gridExtent[3], ds.gridExtent[4], ds.gridExtent[5] )
#            elif ndim == 2:  image_data.SetExtent( ds.gridExtent[0], ds.gridExtent[1], ds.gridExtent[2], ds.gridExtent[3], 0, 0 ) 
#            self.imageData[portName] = image_data
#            imageDataCreated = True
#        image_data = self.imageData[portName]
#        nVars = len( varList )
#        npts = image_data.GetNumberOfPoints()
#        pointData = image_data.GetPointData()
#        for id in range( pointData.GetNumberOfArrays() ): 
#            pointData.RemoveArray( pointData.GetArrayName(id) )
#        self.fieldData.RemoveArray('metadata')
#        scalars = None
#        vars = []
#        datatype = getDatatypeString( scalar_dtype )
#        md = { 'datatype':datatype,  'bounds':ds.gridBounds, 'lat':ds.lat, 'lon':ds.lon, 'time':ds.time, 'attributes':ds.dataset.attributes }
#        if ndim == 3: md[ 'lev' ] = ds.lev
#        for varRec in varList:
#            varName = varRec[0]
#            vars.append( varName )
#            newDataArray, var_md = self.getCachedData( self.timeIndex, varName )
#            if newDataArray == None:
#                if varName == '__zeros__':
#                    newDataArray = np.zeros( npts, dtype=scalar_dtype ) 
#                    var_md = {}
#                    var_md[ 'range' ] = ( 0.0, 0.0 )
#                    var_md[ 'scale' ] = ( 0.0, 1.0 )  
#                else:
#                    varData = ds.dataset[ varName ]
#                    dataArray = varData[ self.timeIndex ]
#                    dataArray = ma.transpose( dataArray )
#                    range_min = dataArray.min()
#                    range_max = dataArray.max()
#                    newDataArray = dataArray
#                    shift, scale = 0.0, 1.0
#                               
#                    if scalar_dtype <> np.float:
#                        shift = -range_min
#                        scale = ( self._max_scalar_value ) / ( range_max - range_min )            
#                        rescaledDataArray = ( ( dataArray + shift ) * scale )
#                        newDataArray = rescaledDataArray.astype(scalar_dtype) 
#                    
#                    newDataArray = newDataArray.data.ravel('F')  
#                    var_md = copy.copy( varData.attributes )
#                    var_md[ 'range' ] = ( range_min, range_max )
#                    var_md[ 'scale' ] = ( shift, scale )  
#                    
#                self.setCachedData( self.timeIndex, varName, ( newDataArray, var_md ) )               
#             
#            vtkdata = getNewVtkDataArray( scalar_dtype )
#            vtkdata.SetNumberOfTuples( newDataArray.size )
#            vtkdata.SetNumberOfComponents( 1 )
#            vtkdata.SetVoidArray( newDataArray, newDataArray.size, 1 )
#            vtkdata.SetName( varName )
#            vtkdata.Modified()
#            pointData.AddArray( vtkdata )
#            md[ varName ] = var_md
#            if (scalars == None) and (varName <> '__zeros__'):
#                scalars = varName
##                pointData.SetActiveScalars( varName  ) 
##                md[ 'valueRange'] = var_md[ 'range' ]                  
#        md[ 'vars' ] = vars
#        enc_mdata = encodeToString( md ) 
#        self.fieldData.AddArray( getStringDataArray( 'metadata',   [ enc_mdata ]  ) )                        
#        image_data.Modified()
##        na = image_data.GetPointData().GetNumberOfArrays()
##        printTime('Finish getImageData')
#        return imageDataCreated

#class CDMSVariable(WorkflowModule):
#    
#    PersistentModuleClass = PM_CDMSVariable
#    
#    def __init__( self, **args ):
#        WorkflowModule.__init__(self, **args)     
                      
class CDMS_FileReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_FileReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     
                           
class CDMSDatasetConfigurationWidget(DV3DConfigurationWidget):
    """
    CDMSDatasetConfigurationWidget ...
    
    """

    def __init__(self, module, controller, parent=None):
        """ DemoDataConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        
        """
        self.cdmsDataRoot = getDataRoot()
        self.timeRange = None
        self.currentRow = 0
        self.fullRoi = [ -180.0, -90.0, 180.0, 90.0 ]
        self.roi = self.fullRoi
        self.currentDatasetId = None
        self.datasets = {}
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Dataset Configuration', parent)
        if self.currentDatasetId <> None: 
            self.registerCurrentDataset( id=self.currentDatasetId )
        self.initTimeRange()
        self.initRoi()
        
    def initTimeRange( self ):
        timeRangeParams =  self.pmod.getInputValue( "timeRange", dbmod=self.module  ) # getFunctionParmStrValues( self.module, "timeRange"  )
        tRange = [ int(trs) for trs in timeRangeParams ] if timeRangeParams else None  
        if tRange and (tRange[0] >= 0) and (tRange[0] <= tRange[1]) and ( tRange[1] < self.nTS ):
            self.timeRange = tRange
            self.startCombo.setCurrentIndex( self.timeRange[0] ) 
            self.startIndexEdit.setText( str( self.timeRange[0] ) )  
            self.endCombo.setCurrentIndex( self.timeRange[1] ) 
            self.endIndexEdit.setText( str( self.timeRange[1] ) )  

    def initRoi( self ):
        roiParams = self.pmod.getInputValue( "roi", dbmod=self.module   ) #getFunctionParmStrValues( self.module, "roi"  )
        if roiParams:  self.roi = [ float(rois) for rois in roiParams ]
        else: self.roi = self.fullRoi 
        self.roiSelector.setROI( self.roi )
        
    def getParameters( self, module ):
        global DataSetVersion
        datasetMapParams = getFunctionParmStrValues( module, "datasets" )
        if datasetMapParams: self.datasets = deserializeStrMap( datasetMapParams[0] )
        datasetParams = getFunctionParmStrValues( module, "datasetId" )
        if datasetParams: 
            self.currentDatasetId = datasetParams[0]
            self.pmod.datasetId = self.currentDatasetId
            if( len(datasetParams) > 1 ): DataSetVersion = int( datasetParams[1] )
        
    def registerCurrentDataset( self, **args ):
        id = args.get( 'id', None ) 
        cdmsFile = args.get( 'file', None )
        self.pmod.setNewConfiguration( **args )
        if id: 
            self.currentDatasetId = str( id )
            cdmsFile = self.datasets.get( self.currentDatasetId, None ) 
        dataset = cdms2.open( cdmsFile ) 
        self.setDatasetProperties( dataset, cdmsFile )           
        self.timeRange = None
        self.nTS = 0
        self.updateTimeSeries( dataset )
        self.initTimeRange()
        self.initRoi()
        self.pmod.clearNewConfiguration()
        dataset.close()
        return cdmsFile
         
    def selectFile(self):
        dataset = None
        file = QFileDialog.getOpenFileName( self, "Find Dataset", self.cdmsDataRoot, "CDMS Files (*.xml *.cdms)") 
        if file <> None:
            cdmsFile = str( file ).strip() 
            if len( cdmsFile ) > 0:                             
                self.registerCurrentDataset( file=cdmsFile, newLayerConfig=True )  
                self.dsCombo.insertItem( 0, QString( self.currentDatasetId ) )  
                self.dsCombo.setCurrentIndex( 0 )

    def removeDataset(self):
        del self.datasets[ str(self.dsCombo.currentText()) ]
        self.dsCombo.removeItem( self.dsCombo.currentIndex() )
        if self.dsCombo.count() == 0: self.tableWidget.clearContents() 
        else:
            self.dsCombo.setCurrentIndex(0)
            self.registerCurrentDataset( id=self.dsCombo.currentText() )
     
    def updateTimeSeries( self, dataset ):
        self.startCombo.clear()
        self.endCombo.clear()
        time_values = getComponentTimeValues ( dataset )
        if time_values <> None:
            self.nTS = len(time_values)
            for time_value in time_values:
                tval = str( time_value ) 
                self.startCombo.addItem ( tval )
                self.endCombo.addItem ( tval )
            self.timeRange = [ 0, self.nTS-1 ]
            self.startCombo.setCurrentIndex( self.timeRange[0] ) 
            self.startIndexEdit.setText( str( self.timeRange[0] ) )  
            self.endCombo.setCurrentIndex( self.timeRange[1] ) 
            self.endIndexEdit.setText( str( self.timeRange[1] ) )  
       
    def selectDataset(self): 
        cdmsFile = self.registerCurrentDataset( id=str( self.dsCombo.currentText() ), newLayerConfig=True )
        
    def setDatasetProperty(self, property, value ):
        try:
            nRows = self.tableWidget.rowCount()
            if self.currentRow == nRows: self.tableWidget.insertRow(nRows)
            self.tableWidget.setItem ( self.currentRow, 0, QTableWidgetItem( property ) )
            self.tableWidget.setItem ( self.currentRow, 1, QTableWidgetItem( value ) )
            self.currentRow = self.currentRow + 1
        except:
            print>>sys.stderr, " Error setting property %s " % property

    def setDatasetAttributes(self, dataset ):
        for attribute in dataset.attributes:
            value = dataset.attributes[ attribute ]
            if type(value) == type(''): self.setDatasetAttribute( attribute, dataset )
        
    def setDatasetAttribute(self, attribute, dataset ):
        try:
            nRows = self.tableWidget.rowCount()
            if self.currentRow == nRows: self.tableWidget.insertRow(nRows)
            value = dataset.attributes.get( attribute, None )
            if value:
                self.tableWidget.setItem ( self.currentRow, 0, QTableWidgetItem( attribute ) )
                self.tableWidget.setItem ( self.currentRow, 1, QTableWidgetItem( value ) )
                self.currentRow = self.currentRow + 1
        except Exception, err:
            print>>sys.stderr, " Error setting dataset attribute %s: %s " % ( attribute, str(err) )
     
    def setDatasetProperties(self, dataset, cdmsFile ):
        self.currentDatasetId = dataset.id  
        self.pmod.datasetId = dataset.id 
        self.tableWidget.clearContents () 
        self.currentRow = 0
        self.setDatasetProperty( 'id', dataset.id )  
        self.setDatasetProperty( 'cdmsFile', cdmsFile ) 
        self.setDatasetAttributes( dataset )   
#        self.setDatasetAttribute( 'model', dataset )  
#        self.setDatasetAttribute( 'Conventions', dataset )  
#        self.setDatasetAttribute( 'center', dataset )  
#        self.setDatasetAttribute( 'calendar', dataset )  
#        self.setDatasetAttribute( 'comments', dataset ) 
        self.datasets[ self.currentDatasetId ] = cdmsFile  
        self.cdmsDataRoot = os.path.dirname( cdmsFile )
                                                
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """
        self.setLayout( QVBoxLayout() )
        self.layout().setMargin(0)
        self.layout().setSpacing(0)

        self.tabbedWidget = QTabWidget()
        self.layout().addWidget( self.tabbedWidget ) 

        self.createButtonLayout() 
        
        datasetTab = QWidget()        
        self.tabbedWidget.addTab( datasetTab, 'dataset' )                 
        layout = QVBoxLayout()
        datasetTab.setLayout( layout ) 
        
        ds_layout = QHBoxLayout()
        ds_label = QLabel( "Dataset:"  )
        ds_layout.addWidget( ds_label ) 

        self.dsCombo =  QComboBox ( self.parent() )
        ds_label.setBuddy( self.dsCombo )
        self.dsCombo.setMaximumHeight( 30 )
        ds_layout.addWidget( self.dsCombo  )
        for ds in self.datasets.keys(): self.dsCombo.addItem ( ds )
        if self.currentDatasetId:
            iCurrentDsIndex = self.dsCombo.findText( self.currentDatasetId )
            self.dsCombo.setCurrentIndex( iCurrentDsIndex )   
        self.connect( self.dsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectDataset ) 

        self.selectDirButton = QPushButton('Add New Dataset', self)
        ds_layout.addWidget( self.selectDirButton )
        self.connect( self.selectDirButton, SIGNAL('clicked(bool)'), self.selectFile )

        self.removeDatasetButton = QPushButton('Remove Selected Dataset', self)
        ds_layout.addWidget( self.removeDatasetButton )
        self.connect( self.removeDatasetButton, SIGNAL('clicked(bool)'), self.removeDataset )
                
        layout.addLayout( ds_layout )
                      
        tableGroupBox = QGroupBox("Current Dataset Properties")
        tableGroupLayout = QVBoxLayout()      
        tableGroupBox.setLayout( tableGroupLayout )
        layout.addWidget( tableGroupBox )
        
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setColumnWidth (0,200)
        self.tableWidget.setColumnWidth (1,1000)
        self.tableWidget.setFrameStyle( QFrame.Panel | QFrame.Raised )
        self.tableWidget.setSizePolicy( QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding ) )
        self.tableWidget.setHorizontalHeaderLabels( [ 'Property', 'Value'  ] )
        tableGroupLayout.addWidget( self.tableWidget )

        timeTab = QWidget()  
        self.tabbedWidget.addTab( timeTab, 'time' )                 
        time_layout = QVBoxLayout()
        timeTab.setLayout( time_layout ) 

        start_layout = QHBoxLayout()
        start_label = QLabel( "Start Time:"  )
        start_layout.addWidget( start_label ) 
        self.startCombo =  QComboBox ( self.parent() )
        start_label.setBuddy( self.startCombo )
        self.startCombo.setMaximumHeight( 30 )
        start_layout.addWidget( self.startCombo  )
        self.connect( self.startCombo, SIGNAL("currentIndexChanged(QString)"), self.updateStartTime ) 
        units_label = QLabel( ''  )
        start_layout.addWidget( units_label ) 
        self.startIndexEdit = QLineEdit( self.parent() )
        self.startIndexEdit.setValidator( QIntValidator() )
        start_layout.addWidget( self.startIndexEdit ) 
        self.connect( self.startIndexEdit, SIGNAL("editingFinished()"), self.updateStartIndex ) 
        time_layout.addLayout( start_layout ) 
        
        end_layout = QHBoxLayout()
        end_label = QLabel( "End Time:"  )
        end_layout.addWidget( end_label ) 
        self.endCombo =  QComboBox ( self.parent() )
        end_label.setBuddy( self.endCombo )
        self.endCombo.setMaximumHeight( 30 )
        end_layout.addWidget( self.endCombo  )
        self.connect( self.endCombo, SIGNAL("currentIndexChanged(QString)"), self.updateEndTime ) 
        units_label = QLabel( ''  )
        end_layout.addWidget( units_label ) 
        self.endIndexEdit = QLineEdit( self.parent() )
        self.endIndexEdit.setValidator( QIntValidator() )
        end_layout.addWidget( self.endIndexEdit ) 
        self.connect( self.endIndexEdit, SIGNAL("editingFinished()"), self.updateEndIndex ) 
        time_layout.addLayout( end_layout ) 
        time_layout.addStretch(1)

        roiTab = QWidget()  
        self.tabbedWidget.addTab( roiTab, 'roi' )                 
        panelLayout = QHBoxLayout()
        roiTab.setLayout( panelLayout ) 
        
        self.roiSelector = ROISelectionWidget( self.parent() )
        panelLayout.addWidget(self.roiSelector)
        if self.roi: self.roiSelector.setROI( self.roi )
        
#        ROICorner0Label = QLabel("<b><u>ROI Corner0:</u></b>")
#        ROICorner1Label = QLabel("<b><u>ROI Corner1:</u></b>")
#        self.ROICornerLon0 = QLineEdit(  )
#        self.ROICornerLat0 = QLineEdit(  )
#        self.ROICornerLon1 = QLineEdit(  )
#        self.ROICornerLat1 = QLineEdit(  )
#        self.ROICornerLon0.setValidator( QDoubleValidator() )
#        self.ROICornerLat0.setValidator( QDoubleValidator() )
#        self.ROICornerLon1.setValidator( QDoubleValidator() )
#        self.ROICornerLat1.setValidator( QDoubleValidator() )
#        
#        self.connect( self.ROICornerLon0, SIGNAL("editingFinished()"), self.adjustROIRect )
#        self.connect( self.ROICornerLat0, SIGNAL("editingFinished()"), self.adjustROIRect )
#        self.connect( self.ROICornerLon1, SIGNAL("editingFinished()"), self.adjustROIRect )
#        self.connect( self.ROICornerLat1, SIGNAL("editingFinished()"), self.adjustROIRect )
#      
#        LatLabel0 = QLabel("Lat: ")
#        LonLabel0 = QLabel("Lon: ")            
#        grid0 = QGridLayout()
#        grid0.addWidget( ROICorner0Label, 0, 0, 1, 2 )
#        grid0.addWidget( LonLabel0, 1, 0 )
#        grid0.addWidget( self.ROICornerLon0, 1, 1 )
#        grid0.addWidget( LatLabel0, 2, 0 )
#        grid0.addWidget( self.ROICornerLat0, 2, 1 )
#
#        w0 = QFrame()  
#        w0.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
#        w0.setLayout( grid0 )
#        panelLayout.addWidget( w0 )
#
#        LatLabel1 = QLabel("Lat: ")
#        LonLabel1 = QLabel("Lon: ")            
#        grid1 = QGridLayout()
#        grid1.addWidget( ROICorner1Label, 0, 0, 1, 2 )
#        grid1.addWidget( LonLabel1, 1, 0 )
#        grid1.addWidget( self.ROICornerLon1, 1, 1 )
#        grid1.addWidget( LatLabel1, 2, 0 )
#        grid1.addWidget( self.ROICornerLat1, 2, 1 )
#        
#        w1 = QFrame()  
#        w1.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
#        w1.setLayout( grid1 )
#        panelLayout.addWidget( w1 )
        
                        
    def updateStartTime( self, val ):
#        print " updateStartTime: %s " % str( val )
        iStartIndex = self.startCombo.currentIndex()
        self.startIndexEdit.setText( str(iStartIndex) )
        if self.timeRange: self.timeRange[0] = iStartIndex
    
    def updateEndTime( self, val ):
#        print " updateEndTime: %s " % str( val )
        iEndIndex = self.endCombo.currentIndex()
        self.endIndexEdit.setText( str(iEndIndex) )
        if self.timeRange: self.timeRange[1] = iEndIndex
        
    def updateStartIndex( self ):
        iStartIndex = int( str( self.startIndexEdit.text() ) )
        self.startCombo.setCurrentIndex( iStartIndex )
        if self.timeRange: self.timeRange[0] = iStartIndex

    def updateEndIndex( self ):
        iEndIndex = int( str( self.endIndexEdit.text() ) )
        self.endCombo.setCurrentIndex( iEndIndex )
        if self.timeRange: self.timeRange[1] = iEndIndex
                          
    def createButtonLayout(self):
        """ createButtonLayout() -> None
        Construct Ok & Cancel button
        
        """
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setMargin(5)
        self.okButton = QPushButton('&OK', self)
        self.okButton.setAutoDefault(False)
        self.okButton.setFixedWidth(100)
        self.buttonLayout.addWidget(self.okButton)
        self.cancelButton = QPushButton('&Cancel', self)
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.setShortcut('Esc')
        self.cancelButton.setFixedWidth(100)
        self.buttonLayout.addWidget(self.cancelButton)
        self.layout().addLayout(self.buttonLayout)
        self.connect(self.okButton, SIGNAL('clicked(bool)'), self.okTriggered)
        self.connect(self.cancelButton, SIGNAL('clicked(bool)'), self.close)

    def sizeHint(self):
        return QSize(1000,800)

    def updateController(self, controller=None):
        global DataSetVersion
        DataSetVersion = DataSetVersion + 1
        self.persistParameter( 'datasets', [ serializeStrMap(self.datasets), ] )
        self.persistParameter( 'datasetId', [ self.currentDatasetId, DataSetVersion ] )
        self.persistParameter( 'timeRange' , [ self.timeRange[0], self.timeRange[1] ]  )       
        self.persistParameter( 'roi' , [ self.roi[0], self.roi[1], self.roi[2], self.roi[3] ]  )       
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.timeRange = [ int( str( self.startIndexEdit.text() ) ), int( str( self.endIndexEdit.text() ) ) ]
        self.roi = self.roiSelector.getROI()
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
        self.close()
        if self.pmod: self.pmod.execute()
        
#class CDMSVariableConfigurationWidget(DV3DConfigurationWidget):
#    """
#    DemoDataConfigurationWidget ...
#    
#    """
#    AllowOutputTabCreation = False
#
#    def __init__(self, module, controller, parent=None):
#        """ DemoDataConfigurationWidget(module: Module,
#                                       controller: VistrailController,
#                                       parent: QWidget)
#                                       -> DemoDataConfigurationWidget
#        Setup the dialog ...
#        
#        """
#        self.cdmsFile = None
#        self.dataset = None
#        self.serializedPortData = ''
#        self.outRecMgr = OutputRecManager()
#        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Variable Configuration', parent)
#        self.initializeOutputs()
#        
#    def getParameters( self, module ):
#        import api
#        global PortDataVersion
#        controller = api.get_current_controller()
#        readerModuleId, portName = getConnectedModuleId( controller, module.id, 'dataset', True )
#        if readerModuleId <> None:
#            reader_module = controller.current_pipeline.modules[ readerModuleId ]
#            portData = getFunctionParmStrValues( reader_module, "cdmsFile" )
#            if portData <> None and ( len( portData ) > 0 ): 
#                self.dataset = cdms2.open( portData[0] ) 
#        portData = getFunctionParmStrValues( module, "portData" )
#        if portData: 
#            self.serializedPortData = portData[0]
#            PortDataVersion = int( portData[1] )
#                               
#    def createLayout(self):
#        """ createEditor() -> None
#        Configure sections
#        
#        """
#        self.setLayout( QVBoxLayout() )
#        self.layout().setMargin(0)
#        self.layout().setSpacing(0)
#
#        self.tabbedWidget = QTabWidget()
#        self.layout().addWidget( self.tabbedWidget ) 
#
#        self.createButtonLayout() 
#
#        outputsTab = QWidget()        
#        self.tabbedWidget.addTab( outputsTab, 'outputs' ) 
#        outputsLayout = QVBoxLayout()                
#        outputsTab.setLayout( outputsLayout )
#        
#        noutLayout = QHBoxLayout()  
#         
#        if self.AllowOutputTabCreation:    
#            addOutputButton = QPushButton('Add Output', self)
#            addOutputButton.setAutoDefault(False)
#            noutLayout.addWidget(addOutputButton)
#            self.connect( addOutputButton, SIGNAL('clicked(bool)'), self.addOutputTab )
#    
#            removeOutputButton = QPushButton('Remove Selected Output', self)
#            removeOutputButton.setAutoDefault(False)
#            noutLayout.addWidget(removeOutputButton)
#            self.connect( removeOutputButton, SIGNAL('clicked(bool)'), self.removeOutputTab )
#               
#        outputsLayout.addLayout( noutLayout )
#        
#        self.outputsTabbedWidget = QTabWidget()
#        outputsLayout.addWidget( self.outputsTabbedWidget )
#                       
#    def initializeOutputs( self ):
#        print " initializeOutputs, serializedPortData: %s " % self.serializedPortData
#        if self.serializedPortData:
#            oRecMgr = OutputRecManager( self.serializedPortData )
#            for oRec in oRecMgr.getOutputRecs():
#                self.createOutput( oRec.name, oRec.ndim, oRec.varList )
#        elif not self.AllowOutputTabCreation: 
#            self.addOutputTab( False, 3, 'volume'  )
#            self.addOutputTab( False, 2, 'slice' )
#                
#    def createOutput( self, name, ndim, variables ):
#        outputTab, tableWidget = self.addOutputTab( False, ndim, name )
#        if outputTab <> None:
#            for varRec in variables:
#                self.addVariable( [ varRec[0], tableWidget ] )
#                
#    def getOutputTabIndex( self, name ):
#        ntabs = self.outputsTabbedWidget.count()
#        for iTab in range( ntabs ):
#            tabName = str( self.outputsTabbedWidget.tabText( iTab ) )
#            if tabName == name: return iTab # self.outputsTabbedWidget.widget(iTab)
#        return -1
#               
#    def addOutputTab( self, bval, ndim, output_name = None ): 
#        if output_name == None:
#            qtname, ok = QInputDialog.getText( self, 'Get Output Name', 'Output name:' )
#            if ok: output_name = str(qtname).strip().replace( ' ', '_' ).translate( None, OutputRecManager.sep )
#        if output_name <> None:
#            iExistingTabIndex = self.getOutputTabIndex( output_name )
#            if iExistingTabIndex < 0:
#                outputTab, tableWidget = self.createOutputTab( ndim, output_name )  
#                if outputTab <> None:
#                    self.outputsTabbedWidget.addTab( outputTab, output_name ) 
#                    print "Added tab: %s " %  output_name 
#                    return outputTab, tableWidget
#        return None, None
#        
#    def removeOutputTab( self ):
#        tabIndex = self.outputsTabbedWidget.currentIndex()
#        outputName = str( self.outputsTabbedWidget.tabText(tabIndex) )
#        self.outRecMgr.deleteOutput( outputName )
#        self.outputsTabbedWidget.removeTab( tabIndex )
#        self.updatePorts()
#
##    def updateNOutouts( self, nout_str ):
##        noutputs = int( nout_str )
##        current_nout = len( self.outputRecs )
##        if noutputs > current_nout:
##            for iout in range( current_nout, noutputs ):
##                default_name = "data%d" % iout
#                    
#    def createOutputTab( self, ndim, name ):  
#        otab = QWidget()  
#        otabLayout = QVBoxLayout()                
#        otab.setLayout( otabLayout )
#       
#        variables_Layout = QHBoxLayout()      
#        variables_label = QLabel( "Select Variable:"  )
#        variables_Layout.addWidget( variables_label ) 
#        varsCombo =  QComboBox ( self )
#        variables_label.setBuddy( varsCombo )
##        varsCombo.setMaximumHeight( 30 )
#        variables_Layout.addWidget( varsCombo ) 
#        if self.dataset <> None:       
#            for var in self.dataset.variables:               
#                vardata = self.dataset[var]
#                var_ndim = getVarNDim( vardata )
#                if var_ndim == ndim:
#                    varsCombo.addItem( str(var) )  
# 
##        varsCombo.addItem( '__zeros__' )  
#        addVarButton = QPushButton( 'Add to Output', self )
#        addVarButton.setAutoDefault(False)
##        addVarButton.setFixedWidth(100)
#        variables_Layout.addWidget( addVarButton )
#        otabLayout.addLayout( variables_Layout )
#        
#        outputGroupBox = QGroupBox("Output Variables")
#        outputGroupLayout = QVBoxLayout()      
#        outputGroupBox.setLayout( outputGroupLayout )
#        otabLayout.addWidget( outputGroupBox )
#
#        tableWidget = QTableWidget(self)
#        tableWidget.setRowCount(0)
#        tableWidget.setColumnCount(4)
#        tableWidget.setHorizontalHeaderLabels( [ 'Variable Name', 'Color', 'Emphasis', '' ] )
#        outputGroupLayout.addWidget( tableWidget )
#
#        self.connect( addVarButton, SIGNAL('clicked(bool)'), callbackWrapper1( self.addVariable, [ varsCombo, tableWidget ] ) )
#
#        buttonLayout = QHBoxLayout()
#        buttonLayout.setMargin(5)
#        deleteButton = QPushButton( 'Delete Selected Variable', self )
#        deleteButton.setAutoDefault(False)
##        deleteButton.setFixedWidth(100)
#        buttonLayout.addWidget( deleteButton )
#        editButton = QPushButton('Edit Selected Variable', self)
#        editButton.setAutoDefault(False)
##        editButton.setFixedWidth(100)
#        buttonLayout.addWidget(editButton)
#        outputGroupLayout.addLayout(buttonLayout)
#        self.connect(deleteButton, SIGNAL('clicked(bool)'), callbackWrapper1( self.deleteVariable, [ varsCombo, tableWidget ] ) )
##        self.connect(self.cancelButton, SIGNAL('clicked(bool)'), self.close)
#        
#        orec = OutputRec( name, ndim=ndim, varTable=tableWidget, varCombo=varsCombo ) 
#        self.outRecMgr.addOutputRec( orec ) 
#        
#        return otab, tableWidget
#        
#    def addVariable( self, args, bval=False ):
#        var_name = None 
#        if type( args[0] ) == type( ' ' ):
#            var_name = args[0]
#        else:
#            var_name = str( args[0].currentText() )
#        tableWidget = args[1]        
#        tableWidget.insertRow(0)
#        varNameLabel = QLabel( var_name  )
#        tableWidget.setCellWidget( 0, 0, varNameLabel )
#        
#    def getCurentOutputRec(self):
#        tabIndex = self.outputsTabbedWidget.currentIndex()
#        outputName = str( self.outputsTabbedWidget.tabText(tabIndex) )
#        return self.outRecMgr.getOutputRec( outputName ) 
#
#    def deleteVariable( self, args, bval ): 
#        tableWidget = args[1]
#        currentRow = tableWidget.currentRow()
#        if (currentRow <> None) and (currentRow >= 0):
#            tableWidget.removeRow( currentRow )
#        else:
#             print>>sys.stderr, "No variable selected in table for deletion."   
#        
##    def setMaxNTimeSteps( self, val=None ):
##        self.maxNTimeSteps = int( str( val if val <> None else self.maxNTimeStepInput.text() ) )
#
#    def updateDataset( self, dset_name ): 
#        self.dataset = dset_name
#        
#    def serializePortData( self ):
#        self.serializedPortData = self.outRecMgr.serialize()
#        print " -- PortData: %s " % self.serializedPortData
#                   
#    def createButtonLayout(self):
#        """ createButtonLayout() -> None
#        Construct Ok & Cancel button
#        
#        """
#        self.buttonLayout = QHBoxLayout()
#        self.buttonLayout.setMargin(5)
#        self.okButton = QPushButton('&OK', self)
#        self.okButton.setAutoDefault(False)
#        self.okButton.setFixedWidth(100)
#        self.buttonLayout.addWidget(self.okButton)
#        self.cancelButton = QPushButton('&Cancel', self)
#        self.cancelButton.setAutoDefault(False)
#        self.cancelButton.setShortcut('Esc')
#        self.cancelButton.setFixedWidth(100)
#        self.buttonLayout.addWidget(self.cancelButton)
#        self.layout().addLayout(self.buttonLayout)
#        self.connect(self.okButton, SIGNAL('clicked(bool)'), self.okTriggered)
#        self.connect(self.cancelButton, SIGNAL('clicked(bool)'), self.close)
#
#    def sizeHint(self):
#        return QSize(500,500)
#
#    def updateController(self, controller):
#        global PortDataVersion
#        PortDataVersion = PortDataVersion + 1
#        self.persistParameter( 'portData', [ self.serializedPortData, PortDataVersion ] )
#          
#    def okTriggered(self, checked = False):
#        """ okTriggered(checked: bool) -> None
#        Update vistrail controller (if neccesssary) then close the widget
#        
#        """
#        self.serializePortData()
#        self.updateController(self.controller)
#        self.emit(SIGNAL('doneConfigure()'))
#        self.close()


class PM_CDMSDataReader( PersistentVisualizationModule ):

    def __init__(self, mid):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False )
        self.timeIndex = 0
        self.dataCache = {}
        self.imageData = {}
        self.currentTime = 0
        
    def getCachedData(self, iTimestep, varName ):
        if varName == '__zeros__': iTimestep = 0
        varData = self.dataCache.setdefault(iTimestep, {} )
        return varData.get( varName, ( None, None ) )

    def setCachedData(self, iTimestep, varName, varDataTuple ):
        if varName == '__zeros__': iTimestep = 0
        varData = self.dataCache.setdefault(iTimestep, {} )
        varData[ varName ] = varDataTuple
                       
    def getTimeStepData( self, **args ):
        self.initializeInputs( **args )
        self.generateOutput()
        
#    def getTimeIndex( self, iTimeCounter ):
#        nts = ( self.timeRange[1] - self.timeRange[0] ) + 1 
#        return ( iTimeCounter %  nts ) + self.timeRange[0]
       
    def processParameterChange( self, parameter_name, new_parameter_value ):
        if parameter_name == 'timestep':
#            ts = self.getTimeIndex( int( getItem( new_parameter_value ) ) )
            ts = int( getItem( new_parameter_value ) ) 
            if ts <> self.timeIndex:
                self.timeIndex = ts
                self.getTimeStepData()
#                self.executeWorkflow()
        self.parmUpdating[ parameter_name ] = False 
                
    def getParameterDisplay( self, parmName, parmValue ):
        if parmName == 'timestep':
#            timestep = self.getTimeIndex( int( parmValue[0] ) )
            timestep = int( parmValue[0] )
            return str( self.timeLabels[ timestep ] ), 10
        return None, 1
        
    def execute(self):
        import api
        dset = self.getInputValue( "dataset"  ) 
        if dset: self.cdmsDataset = dset
        dsptr = id( self.cdmsDataset )
        dsetid = self.getAnnotation( "datasetId" )
        if dsetid: self.datasetId = dsetid 
               
        if self.cdmsDataset:
            dsetId = self.cdmsDataset.id
            self.newDataset = ( self.datasetId <> dsetId )
            self.datasetId = dsetId
            self.cdmsFile = self.cdmsDataset.cdmsFile
            self.timeRange = self.cdmsDataset.timeRange
            self.timeLabels = getComponentTimeValues( self.cdmsDataset.dataset )
            self.nTimesteps = len( self.timeLabels )
            self.timeValues = self.cdmsDataset.time.asRelativeTime()
            self.timeUnits = self.cdmsDataset.time.units
            self.generateOutput()
            if self.newDataset: self.addAnnotation( "datasetId", self.datasetId )
 
            
    def getParameterId(self):
        return self.datasetId
            
    def getPortData( self, **args ):
        return self.getInputValue( "portData", **args )  
 
    def generateOutput( self ):       
        portData = self.getPortData()
        oRecMgr = OutputRecManager( portData[0] if portData else None  )
        wmod = self.getWorkflowModule()    
        for orec in oRecMgr.getOutputRecs( self.datasetId ):
            self.getImageData( orec ) 
            cachedImageDataName = "%s.%s" % ( self.datasetId, orec.name )              
            if   orec.ndim == 3: self.set3DOutput( name=orec.name,  output=self.imageData[cachedImageDataName], wmod = wmod )
            elif orec.ndim == 2: self.set2DOutput( name=orec.name,  output=self.imageData[cachedImageDataName], wmod = wmod  )

    def getMetadata( self, metadata={}, port=None ):
        PersistentVisualizationModule.getMetadata( metadata )
        portData = self.getPortData()  
        oRecMgr = OutputRecManager( portData[0] if portData else None )
        orec = oRecMgr.getOutputRec( self.datasetId, port )
        if orec: metadata[ 'layers' ] = orec.varList
        return metadata
          
    def getImageData( self, orec, **args ):
        """
        This method converts cdat data into vtkImageData objects. The ds object is a CDMSDataset instance which wraps a CDAT CDMS Dataset object. 
        The ds.getVarDataTimeSlice method execution extracts a VDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).   
        The array is then rescaled, converted to a 1D unsigned short array, and then wrapped as a vtkUnsignedShortArray using the vtkdata.SetVoidArray method call.  
        The vtk data array is then attached as point data to a vtkImageData object, which is returned.
        """
        varList = orec.varList
        if len( varList ) == 0: return False
#        printTime('Start getImageData')
        portName = orec.name
        ndim = orec.ndim
        imageDataCreated = False
        scalar_dtype = args.get( "dtype", np.ushort if (ndim == 3) else np.float )
        self._max_scalar_value = getMaxScalarValue( scalar_dtype )
        self._range = [ 0.0, self._max_scalar_value ]  
        ds = self.cdmsDataset
        self.timeRange = ds.timeRange
        print " ---@@@@@ CDMS-GetImageData: id=%s, Origin= %s, Spacing= %s, Extent= %s, Timestep= %d (%s)" % ( ds.id, ds.gridOrigin, ds.gridSpacing, ds.gridExtent, self.timeIndex, self.timeLabels[ self.timeIndex ]  )
        cachedImageDataName = "%s.%s" % ( ds.id, portName )
        
        if not ( cachedImageDataName in self.imageData ):
            image_data = vtk.vtkImageData() 
            if   scalar_dtype == np.ushort: image_data.SetScalarTypeToUnsignedShort()
            elif scalar_dtype == np.ubyte:  image_data.SetScalarTypeToUnsignedChar()
            elif scalar_dtype == np.float:  image_data.SetScalarTypeToFloat()
            image_data.SetOrigin( ds.gridOrigin[0], ds.gridOrigin[1], ds.gridOrigin[2] )
#            image_data.SetOrigin( 0.0, 0.0, 0.0 )
            if ndim == 3: extent = [ ds.gridExtent[0], ds.gridExtent[1], ds.gridExtent[2], ds.gridExtent[3], ds.gridExtent[4], ds.gridExtent[5] ]   
            elif ndim == 2: extent = [ ds.gridExtent[0], ds.gridExtent[1], ds.gridExtent[2], ds.gridExtent[3], 0, 0 ]   
            image_data.SetExtent( extent )
            image_data.SetWholeExtent( extent )
            image_data.SetSpacing(  ds.gridSpacing[0], ds.gridSpacing[1], ds.gridSpacing[2] )
#            offset = ( -ds.gridSpacing[0]*ds.gridExtent[0], -ds.gridSpacing[1]*ds.gridExtent[2], -ds.gridSpacing[2]*ds.gridExtent[4] )
            self.imageData[ cachedImageDataName ] = image_data
            extent = image_data.GetExtent()
            imageDataCreated = True
        image_data = self.imageData[ cachedImageDataName ]
        nVars = len( varList )
        npts = image_data.GetNumberOfPoints()
        pointData = image_data.GetPointData()
        for aname in range( pointData.GetNumberOfArrays() ): 
            pointData.RemoveArray( pointData.GetArrayName(aname) )
        self.fieldData.RemoveArray('metadata')
        extent = image_data.GetExtent()    
        scalars = None
        vars = []
        datatype = getDatatypeString( scalar_dtype )
        md = { 'datatype':datatype, 'datasetId' : ds.id,  'bounds':ds.gridBounds, 'lat':ds.lat, 'lon':ds.lon, 'time':ds.time, 'attributes':ds.dataset.attributes }
        if ndim == 3: md[ 'lev' ] = ds.lev
        for varRec in varList:
            varName = varRec[0]
            varDataId = '%s.%s' % ( ds.id, varName )
            newDataArray, var_md = self.getCachedData( self.timeIndex, varDataId )
            if newDataArray == None:
                if varName == '__zeros__':
                    newDataArray = np.zeros( npts, dtype=scalar_dtype ) 
                    var_md = {}
                    var_md[ 'range' ] = ( 0.0, 0.0 )
                    var_md[ 'scale' ] = ( 0.0, 1.0 ) 
                    self.setCachedData( self.timeIndex, varName, ( newDataArray, var_md ) )   
                else:
                    ds_addr = id( ds )
                    varData = ds.getVarDataTimeSlice( varName, self.timeIndex )
                    if varData.id <> 'NULL':
                        range_min = varData.min()
                        range_max = varData.max()
                        newDataArray = varData
                        shift, scale = 0.0, 1.0
                                   
                        if scalar_dtype <> np.float:
                            shift = -range_min
                            scale = ( self._max_scalar_value ) / ( range_max - range_min )            
                            rescaledDataArray = ( ( newDataArray + shift ) * scale )
                            newDataArray = rescaledDataArray.astype(scalar_dtype) 
                        
                        newDataArray = newDataArray.data.ravel('F') 
#                        ushrt_range_min = newDataArray.min()
#                        ushrt_range_max = newDataArray.max()
                        var_md = copy.copy( varData.attributes )
                        var_md[ 'range' ] = ( range_min, range_max )
                        var_md[ 'scale' ] = ( shift, scale )                     
                        self.setCachedData( self.timeIndex, varDataId, ( newDataArray, var_md ) )  
                             
            if newDataArray <> None:
                vars.append( varName ) 
                vtkdata = getNewVtkDataArray( scalar_dtype )
                vtkdata.SetNumberOfTuples( newDataArray.size )
                vtkdata.SetNumberOfComponents( 1 )
                vtkdata.SetVoidArray( newDataArray, newDataArray.size, 1 )
                vtkdata.SetName( varName )
                vtkdata.Modified()
                pointData.AddArray( vtkdata )
                md[ varName ] = var_md
                if (scalars == None) and (varName <> '__zeros__'):
                    scalars = varName
                    pointData.SetActiveScalars( varName  ) 
                    md[ 'valueRange'] = var_md[ 'range' ] 
                    md[ 'scalars'] = varName 
                    print " --- CDMS-SetScalars: %s, Range= %s" % ( varName, str( var_md[ 'range' ] ) )  
        if len( vars )== 0: raise ModuleError( self, 'No Variable selected in dataset.' )             
        md[ 'vars' ] = vars
        enc_mdata = encodeToString( md ) 
        self.fieldData.AddArray( getStringDataArray( 'metadata',   [ enc_mdata ]  ) )                        
        image_data.Modified()
        return imageDataCreated
            
    def getMetadata( self, metadata={}, port=None ):
        PersistentVisualizationModule.getMetadata( metadata )
        if self.cdmsFile:
            dataset = cdms2.open( self.cdmsFile ) 
            if self.dataset <> None: 
                vars3d = []
                vars2d = []      
                for var in self.dataset.variables:               
                    vardata = self.dataset[var]
                    var_ndim = getVarNDim( vardata )
                    if var_ndim == 2: vars2d.append( var )
                    if var_ndim == 3: vars3d.append( var )
                metadata[ 'vars2d' ] = vars2d
                metadata[ 'vars3d' ] = vars3d
                dataset.close()
        return metadata

class PM_CDMS_VolumeReader( PM_CDMSDataReader ):

    def __init__(self, mid):
        PM_CDMSDataReader.__init__( self, mid  )

        
class CDMS_VolumeReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VolumeReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     


class PM_CDMS_SliceReader( PM_CDMSDataReader ):

    def __init__(self, mid):
        PM_CDMSDataReader.__init__( self, mid  )

class CDMS_SliceReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_SliceReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
class PM_CDMS_VectorReader( PM_CDMSDataReader ):

    def __init__(self, mid):
        PM_CDMSDataReader.__init__( self, mid  )


class CDMS_VectorReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VectorReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 

                           
class CDMSReaderConfigurationWidget(DV3DConfigurationWidget):
    """
    CDMSReaderConfigurationWidget ...
    
    """
    VolumeOutput = 1
    SliceOutput = 2
    VectorOutput = 3

    def __init__(self, module, controller, outputType, parent=None):
        """ CDMSReaderConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> CDMSReaderConfigurationWidget
        Setup the dialog ...
        
        """
        self.outputType = outputType
        self.outRecMgr = None
        self.serializedPortData = ''
        self.datasetId = None
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Data Reader Configuration', parent)
        self.outRecMgr = OutputRecManager()  
        self.initializeOutput()      
     
    def getParameters( self, module ):
        global PortDataVersion
        portData = self.pmod.getPortData( dbmod=self.module ) # getFunctionParmStrValues( module, "portData" )
        if portData and portData[0]: 
             self.serializedPortData = portData[0]   
             PortDataVersion = int( portData[1] ) 
        ( self.variableList, self.datasetId, self.cdmsFile, self.timeRange ) =  DV3DConfigurationWidget.getVariableList( module.id )     
                                                  
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        
        """
        self.setLayout( QVBoxLayout() )
        self.layout().setMargin(0)
        self.layout().setSpacing(0)

        self.tabbedWidget = QTabWidget()
        self.layout().addWidget( self.tabbedWidget ) 

        self.createButtonLayout() 
        

        outputsTab = QWidget()        
        self.tabbedWidget.addTab( outputsTab, 'output' ) 
        outputsLayout = QVBoxLayout()                
        outputsTab.setLayout( outputsLayout )
        
        noutLayout = QHBoxLayout()                 
        outputsLayout.addLayout( noutLayout )
        
        self.outputsTabbedWidget = QTabWidget()
        outputsLayout.addWidget( self.outputsTabbedWidget )
                           
    def createButtonLayout(self):
        """ createButtonLayout() -> None
        Construct Ok & Cancel button
        
        """
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setMargin(5)
        self.okButton = QPushButton('&OK', self)
        self.okButton.setAutoDefault(False)
        self.okButton.setFixedWidth(100)
        self.buttonLayout.addWidget(self.okButton)
        self.cancelButton = QPushButton('&Cancel', self)
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.setShortcut('Esc')
        self.cancelButton.setFixedWidth(100)
        self.buttonLayout.addWidget(self.cancelButton)
        self.layout().addLayout(self.buttonLayout)
        self.connect(self.okButton, SIGNAL('clicked(bool)'), self.okTriggered)
        self.connect(self.cancelButton, SIGNAL('clicked(bool)'), self.close)

    def sizeHint(self):
        return QSize(500,250)

    def updateController(self, controller):
        global PortDataVersion
        PortDataVersion = PortDataVersion + 1
        self.persistParameter( 'portData', [ self.serializedPortData, PortDataVersion ], parameter_id=self.datasetId )
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.serializePortData()
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
        self.close()
                                       
    def initializeOutput( self ):
        print " initializeOutputs, serializedPortData: %s " % self.serializedPortData
        if self.serializedPortData:
            oRecMgr = OutputRecManager( self.serializedPortData )
            for oRec in oRecMgr.getOutputRecs( self.datasetId ):
                variableSelection = oRec.varList[0][0] if oRec.varList else None
                self.addOutputTab( False, oRec.ndim, oRec.name, variableSelection )
        if   self.outputType == self.VolumeOutput:   self.addOutputTab( False, 3, 'volume'  )
        elif self.outputType == self.SliceOutput:    self.addOutputTab( False, 2, 'slice' )
        self.updateVariableLists()
                
    def getOutputTabIndex( self, name ):
        ntabs = self.outputsTabbedWidget.count()
        for iTab in range( ntabs ):
            tabName = str( self.outputsTabbedWidget.tabText( iTab ) )
            if tabName == name: return iTab # self.outputsTabbedWidget.widget(iTab)
        return -1
               
    def addOutputTab( self, bval, ndim, output_name = None, variableSelection=None ): 
        if output_name == None:
            qtname, ok = QInputDialog.getText( self, 'Get Output Name', 'Output name:' )
            if ok: output_name = str(qtname).strip().replace( ' ', '_' ).translate( None, OutputRecManager.sep )
        if output_name <> None:
            iExistingTabIndex = self.getOutputTabIndex( output_name )
            if iExistingTabIndex < 0:
                outputTab = self.createOutputTab( ndim, output_name, variableSelection )  
                if outputTab <> None:
                    self.outputsTabbedWidget.addTab( outputTab, output_name ) 
                    print "Added tab: %s " %  output_name 
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
                    
    def createOutputTab( self, ndim, name, variableSelection = None ):  
        otab = QWidget()  
        otabLayout = QVBoxLayout()                
        otab.setLayout( otabLayout )

        
        variables_Layout = QHBoxLayout()      
        variables_label = QLabel( "Select Output Variable:"  )
        variables_Layout.addWidget( variables_label ) 
        varsCombo =  QComboBox ( self )
        variables_label.setBuddy( varsCombo )
#        varsCombo.setMaximumHeight( 30 )
        variables_Layout.addWidget( varsCombo )  
#        varsCombo.addItem( '__zeros__' )  
        otabLayout.addLayout( variables_Layout )
                
        orec = OutputRec( name, ndim=ndim, varCombo=varsCombo, varSelection=variableSelection ) 
        self.outRecMgr.addOutputRec( self.datasetId, orec ) 
        
        return otab
    
    def updateVariableLists(self):
        if self.outRecMgr:  
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): oRec.varCombo.clear()
            for ( var, var_ndim ) in self.variableList:               
                for oRec in self.outRecMgr.getOutputRecs( self.datasetId ):
                    if var_ndim == oRec.ndim:
                        oRec.varCombo.addItem( str(var) ) 
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): 
                if oRec.varSelection:
                    itemIndex = oRec.varCombo.findText( oRec.varSelection, Qt.MatchFixedString )
                    if itemIndex >= 0: oRec.varCombo.setCurrentIndex( itemIndex )
        
    def getCurentOutputRec(self):
        tabIndex = self.outputsTabbedWidget.currentIndex()
        outputName = str( self.outputsTabbedWidget.tabText(tabIndex) )
        return self.outRecMgr.getOutputRec( self.datasetId, outputName ) 
        
    def serializePortData( self ):
        self.serializedPortData = self.outRecMgr.serialize()
        print " -- PortData: %s " % self.serializedPortData


class CDMS_VolumeReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, self.VolumeOutput, parent)


class CDMS_SliceReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, self.SliceOutput, parent)


class CDMS_VectorReaderConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, self.VectorOutput, parent)

        
if __name__ == '__main__':
    executeVistrail( 'CDMSPipeline' )


