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
from ROISelection import ROISelectionDialog
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
    dt = 0.0
    if dataset <> None:
        dims = dataset.axes.keys()
        for dim in dims:
            axis = dataset.getAxis( dim )
            if axis.isTime():
                if axis.calendar.lower() == 'gregorian': 
                    cdtime.DefaultCalendar = cdtime.GregorianCalendar 
                if hasattr( axis, 'partition' ):
                    rv = []
                    tvals = axis.asRelativeTime()
                    for part in axis.partition:
                        for iTime in range( part[0], part[1] ):
                            rv.append( tvals[iTime].tocomp() )
                    break
                else:
                    rv = axis.asComponentTime()
        if rv and (len(rv) > 1):
            rv0 = rv[0].torel("days since 1900")
            rv1 = rv[1].torel("days since 1900")
            dt = rv1.value - rv0.value
    return rv, dt

def getRelativeTimeValues( dataset ):
    rv = None
    dt = 0.0
    if dataset <> None:
        dims = dataset.axes.keys()
        for dim in dims:
            axis = dataset.getAxis( dim )
            if axis.isTime():
                if axis.calendar.lower() == 'gregorian': 
                    cdtime.DefaultCalendar = cdtime.GregorianCalendar 
                if hasattr( axis, 'partition' ):
                    rv = []
                    tvals = axis.asRelativeTime("days since 1900")
                    for part in axis.partition:
                        for iTime in range( part[0], part[1] ):
                            rv.append( tvals[iTime] )
                    break
                else:
                    rv = axis.asRelativeTime("days since 1900")
        if rv and (len(rv) > 1):
            dt = rv[1].value - rv[0].value
    return rv, dt

class CDMSDatasetRecord(): 
    
    def __init__( self, id, dataset=None, dataFile = None ):
        self.id = id
        self.dataset = dataset
        self.cdmsFile = dataFile   

    def getTimeValues( self, dsid ):
        return self.dataset['time'].getValue() 
    
    def getLevAxis(self ):
        for axis in self.dataset.axes.values():
            if isLevelAxis( axis ): return axis
        return None

    def getLevBounds(self ):
        levaxis, levbounds = self.getLevAxis(), None
        values = levaxis.getValue()
        ascending_values = ( values[-1] > values[0] )
        if levaxis:
            if   levaxis.attributes.get( 'positive', '' ) == 'down' and ascending_values:   levbounds = slice( None, None, -1 )
            elif levaxis.attributes.get( 'positive', '' ) == 'up' and not ascending_values: levbounds = slice( None, None, -1 )
        return levbounds
    
    def getVarData( self, varName ):
        varData = self.dataset[ varName ]
        order = varData.getOrder()
        args = {}
        timevalues, dt = getComponentTimeValues( self.dataset )
        levbounds = self.getLevBounds()
        if self.timeRange: args['time'] = ( timevalues[ self.timeRange[0] ], timevalues[ self.timeRange[1] ] )
        args['lon'] = slice( self.gridExtent[0], self.gridExtent[1] )
        args['lat'] = slice( self.gridExtent[2], self.gridExtent[3] )
        if levbounds: args['lev'] = levbounds
        args['order'] = 'xyz'
        print "Reading variable %s, axis order = %s, shape = %s, roi = %s " % ( varName, order, str(varData.shape), str(args) )
        return varData( **args )

    def getVarDataTimeSlice( self, varName, iTimeIndex ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        rv = None
        varData = self.dataset[ varName ]
        order = varData.getOrder()
        args = {}
        timevalues, dt = getComponentTimeValues( self.dataset )
        levbounds = self.getLevBounds()
        try:
            tval = timevalues[ iTimeIndex ]
            args['time'] = tval
            args['lon'] = slice( self.gridExtent[0], self.gridExtent[1]+1 )
            args['lat'] = slice( self.gridExtent[2], self.gridExtent[3]+1 )
            if levbounds: args['lev'] = levbounds
            args['order'] = 'xyz'
#            args['squeeze'] = 1
#                print "Reading variable %s, time = %s(%d), shape = %s, args = %s " % ( varName, tval, iTimeIndex, str(varData.shape), str(args) )
            start_t = time.time() 
            rv = varData( **args )
            end_t = time.time() 
            print  "Reading variable %s, time = %s(%d), shape = %s, args = %s, slice duration = %.4f sec." % ( varName, tval, iTimeIndex, str(varData.shape), str(args), end_t-start_t  ) 
        except Exception, err:
            print>>sys.stderr, ' Exception getting var slice: %s ' % str( err )
        return rv

    def init( self, timeRange, roi, zscale ):
        dims = self.dataset.axes.keys()
        self.gridOrigin = newList( 3, 0.0 )
        self.outputOrigin = newList( 3, 0.0 )
        self.gridBounds = newList( 6, 0.0 )
        self.gridSpacing = newList( 3, 1.0 )
        self.gridExtent = newList( 6, 0 )
        self.outputExtent = newList( 6, 0 )
        self.gridShape = newList( 3, 0 )
        self.gridSize = 1
        self.timeRange = timeRange
        for dim in dims:
            axis = self.dataset.getAxis( dim )
            size = axis.length
            iCoord = self.getCoordType( axis )
            roiBounds, values = self.getAxisValues( axis, roi )
            if iCoord == -1: timeValues = values
            if iCoord >= 0:
                iCoord2 = 2*iCoord
                self.gridShape[ iCoord ] = size
                self.gridSize = self.gridSize * size
                self.outputExtent[ iCoord2+1 ] = self.gridExtent[ iCoord2+1 ] = size-1                    
                if iCoord < 2:
                    lonOffset = 360.0 if ( ( iCoord == 0 ) and ( roiBounds[0] < 0.0 ) ) else 0.0
                    self.outputOrigin[ iCoord ] = self.gridOrigin[ iCoord ] = values[0] + lonOffset
                    spacing = (values[size-1] - values[0])/(size-1)
                    if roiBounds:
                        self.gridExtent[ iCoord2 ] = int( round( ( roiBounds[0] - values[0] )  / spacing ) )                
                        self.gridExtent[ iCoord2+1 ] = int( round( ( roiBounds[1] - values[0] )  / spacing ) )
                        self.outputExtent[ iCoord2+1 ] = self.gridExtent[ iCoord2+1 ] - self.gridExtent[ iCoord2 ]
                        self.outputOrigin[ iCoord ] = lonOffset + roiBounds[0]
                    roisize = self.gridExtent[ iCoord2+1 ] - self.gridExtent[ iCoord2 ] + 1                  
                    self.gridSpacing[ iCoord ] = spacing
                    self.gridBounds[ iCoord2 ] = roiBounds[0] if roiBounds else values[0] 
                    self.gridBounds[ iCoord2+1 ] = (roiBounds[0] + roisize*spacing) if roiBounds else values[ size-1 ]
                else:                                             
                    self.gridSpacing[ iCoord ] = zscale
                    self.outputOrigin[ iCoord ] = self.gridOrigin[ iCoord ] = 0.0
                    self.gridBounds[ iCoord2 ] = values[0]  # 0.0
                    self.gridBounds[ iCoord2+1 ] = values[ size-1 ] # float( size-1 )

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
        if isLevelAxis( axis ): 
            self.lev = axis
            iCoord  = 2
        if axis.isTime(): 
            self.time = axis
            iCoord  = -1
        return iCoord
       
class CDMSDataset(Module):
    
    NullVariable = cdms2.createVariable( np.array([]), id='NULL' )

    def __init__( self ):
        Module.__init__(self)
        self.datasetRecs = {}
        self.transientVariables = {}
        self.timeRange = None
        
    def getTimeValues( self, asComp = True ):
        if self.timeRange == None: return None
        start_rel_time = cdtime.reltime( float( self.timeRange[2] ), "days since 1900" )
        time_values = []
        for iTime in range( self.timeRange[0], self.timeRange[1]+1 ):
            rval = start_rel_time.value + iTime * self.timeRange[3]
            tval = cdtime.reltime( float( rval ), "days since 1900" )
            if asComp:   time_values.append( tval.tocomp() )
            else:        time_values.append( tval )
        return time_values

    def __del__( self ):
        for dsetRec in self.datasetRecs.values(): dsetRec.dataset.close()
         
    def addTransientVariable( self, varName, variable, ndim = None ):
        self.transientVariables[ varName ] = variable

    def getTransientVariable( self, varName ):
        return self.transientVariables[ varName ]

    def getTransientVariableNames( self ):
        return self.transientVariables.keys()

    def __getitem__(self, dsid ):
        return self.datasetRecs[ dsid ]

    def __delitem__(self, dsid ):
        dsetRec = self.datasetRecs[ dsid ]
        dsetRec.dataset.close()
        del self.datasetRecs[ dsid ]
    
    def getVarData( self, dsid, varName ):
        dsetRec = self.datasetRecs[ dsid ]
        if varName in dsetRec.dataset.variables:
            return dsetRec.getVarData( self, varName )
        elif varName in self.transientVariables:
            return self.transientVariables[ varName ]
        else: 
            print>>sys.stderr, "Error: can't find variable %s in dataset" % varName
            return self.NullVariable

    def getVarDataTimeSlice( self, dsid, varName, iTimeIndex ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        if dsid:
            dsetRec = self.datasetRecs[ dsid ]
            if varName in dsetRec.dataset.variables:
                return dsetRec.getVarDataTimeSlice( varName, iTimeIndex )   
        if varName in self.transientVariables:
            return self.transientVariables[ varName ] 
        print>>sys.stderr, "Error: can't find time slice variable %s in dataset" % varName
        return self.NullVariable
    
    def addDatasetRecord( self, dsetId, cdmsFile, timeRange=None, roi = None, zscale = 1.0 ):
        cdmsDSet = self.datasetRecs.get( dsetId, None )
        if (cdmsDSet <> None) and (cdmsDSet.cdmsFile == cdmsFile):
            return cdmsDSet
        if cdmsFile:
            dataset = cdms2.open( cdmsFile ) 
            if dataset <> None:
                cdmsDSet = CDMSDatasetRecord( dsetId, dataset, cdmsFile )
                self.datasetRecs[ dsetId ] = cdmsDSet
                cdmsDSet.init(timeRange, roi, zscale)
        return cdmsDSet             

    def getVariableList( self, ndims ):
        vars = []     
        for dsetRec in self.datasetRecs.values(): 
            for var in dsetRec.dataset.variables:               
                vardata = dsetRec.dataset[var]
                var_ndim = getVarNDim( vardata )
                if var_ndim == ndims: vars.append( '%s*%s' % ( dsetRec.id, var ) )
        return vars
    
    def getDsetId(self): 
        rv = '-'.join( self.datasetRecs.keys() )
        return rv
                    
class PM_CDMS_FileReader( PersistentVisualizationModule ):

    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['timeRange','roi'], **args)
        self.datasetModule = CDMSDataset()
            
    def execute(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """  
        dsMapData = self.getInputValue( "datasets" )
        time_range = self.getInputValue( "timeRange"  )
        self.timeRange =[ int(time_range[0]), int(time_range[1]), float(time_range[2]), float(time_range[3])  ]
        roi_data = self.getInputValue( "roi" )
        self.roi =[ float(sroi) for sroi in roi_data ]     
        if dsMapData: 
            zscale = getItem( self.getInputValue( "zscale",   1.0  )  )
            datasetMap = deserializeStrMap( getItem( dsMapData ) )
            for datasetId in datasetMap:
                cdmsFile = datasetMap[ datasetId ]
                self.datasetModule.addDatasetRecord( datasetId, cdmsFile, self.timeRange, self.roi, zscale )
        self.setParameter( "timeRange" , time_range )
        self.setParameter( "roi", roi_data )
        self.datasetModule.timeRange = self.timeRange 
        self.setResult( 'dataset', self.datasetModule )
        print " ......  Start Workflow, dsid=%s ......  " % ( self.datasetModule.getDsetId() )

    def dvUpdate(self):
        pass     
        
    def getMetadata( self, metadata={}, port=None ):
        PersistentVisualizationModule.getMetadata( metadata )
        metadata[ 'vars2d' ] =  self.datasetModule.getVariableList( 2 )
        metadata[ 'vars3d' ] =  self.datasetModule.getVariableList( 3)
        metadata[ 'datasetId' ] = self.datasetId
        return metadata
      
                      
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
        self.fullRoi = [ -180.0, -90.0, 180.0, 90.0 ]
        self.roi = self.fullRoi
        self.nTS = 0
        self.zscale = 1.0
        self.relativeStartTime = None
        self.relativeTimeStep = None
        self.multiFileSelection = True
        self.currentDatasetId = None
        self.datasetChanged = False
        self.datasets = {}
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Dataset Configuration', parent)
        self.metadataViewer = MetadataViewerDialog( self )
        if self.multiFileSelection:
            self.updateTimeSeries()
            self.initTimeRange()
            self.initRoi()
            self.initZScale()
            if self.pmod: self.pmod.clearNewConfiguration()
        elif (self.currentDatasetId <> None): 
            self.registerCurrentDataset( id=self.currentDatasetId )           
        self.stateChanged( False )
#        self.initTimeRange()
#        self.initRoi()
        
    def initTimeRange( self ):
        timeRangeParams =   self.pmod.getInputValue( "timeRange"  ) # getFunctionParmStrValues( self.module, "timeRange"  )
        tRange = [ int(timeRangeParams[0]), int(timeRangeParams[1]), float(timeRangeParams[2]), float(timeRangeParams[3])  ] if timeRangeParams else None
        if tRange:
            self.timeRange = tRange
            self.relativeStartTime = cdtime.reltime( float(tRange[2]), "days since 1900")
            self.relativeTimeStep = float(tRange[3])
            self.startCombo.setCurrentIndex( self.timeRange[0] ) 
            self.startIndexEdit.setText( str( self.timeRange[0] ) )  
            self.endCombo.setCurrentIndex( self.timeRange[1] ) 
            self.endIndexEdit.setText( str( self.timeRange[1] ) )  

    def initRoi( self ):
        roiParams = self.pmod.getInputValue( "roi" ) #getFunctionParmStrValues( self.module, "roi"  )self.getParameterId()
        if roiParams:  self.roi = [ float(rois) for rois in roiParams ]
        else: self.roi = self.fullRoi 
        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 
        
    def initZScale( self ):
        zsParams = self.pmod.getInputValue( "zscale" )
        if zsParams:  self.zscale = float( getItem( zsParams ) )
        self.selectZScaleLineEdit.setText( "%.2f" % self.zscale)
#        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 
                
    def getParameters( self, module ):
        global DataSetVersion
        datasetMapParams = getFunctionParmStrValues( module, "datasets" )
        if datasetMapParams: self.datasets = deserializeStrMap( datasetMapParams[0] )
        datasetParams = getFunctionParmStrValues( module, "datasetId" )
        if datasetParams: 
            self.currentDatasetId = datasetParams[0]
            self.pmod.datasetId = self.currentDatasetId
            if( len(datasetParams) > 1 ): DataSetVersion = int( datasetParams[1] )

    def setDatasetProperties(self, dataset, cdmsFile ):
        self.currentDatasetId = dataset.id  
        self.pmod.datasetId = dataset.id 
        self.datasets[ self.currentDatasetId ] = cdmsFile  
        self.cdmsDataRoot = os.path.dirname( cdmsFile )
        self.metadataViewer.setDatasetProperties( dataset, cdmsFile ) 
        
    def registerCurrentDataset( self, **args ):
        id = args.get( 'id', None ) 
        cdmsFile = args.get( 'file', None )
        if self.pmod: self.pmod.setNewConfiguration( **args )
        if id: 
            self.currentDatasetId = str( id )
            cdmsFile = self.datasets.get( self.currentDatasetId, None ) 
        try:
            dataset = cdms2.open( cdmsFile ) 
            self.setDatasetProperties( dataset, cdmsFile )           
            self.timeRange = None
            self.nTS = 0
            self.updateTimeSeries()
            self.initTimeRange()
            self.initRoi()
            self.initZScale()
            if self.pmod: self.pmod.clearNewConfiguration()
            dataset.close()
        except:
            print "Error initializing dataset: %s" % str(cdmsFile)
        return cdmsFile
         
    def selectFile(self):
        dataset = None
        file = QFileDialog.getOpenFileName( self, "Find Dataset", self.cdmsDataRoot, "CDMS Files (*.xml *.cdms)") 
        if file <> None:
            cdmsFile = str( file ).strip() 
            if len( cdmsFile ) > 0:                             
                if self.multiFileSelection:
                    dataset = cdms2.open( cdmsFile )
                    self.currentDatasetId = dataset.id 
                    self.datasets[ self.currentDatasetId ] = cdmsFile  
                    self.cdmsDataRoot = os.path.dirname( cdmsFile )
                    self.updateTimeSeries()
                    self.initTimeRange()        
                    self.dsCombo.insertItem( 0, QString( self.currentDatasetId ) )  
                    self.dsCombo.setCurrentIndex( 0 )
                    self.pmod.datasetId = '*'.join( self.datasets.keys() )
                    dataset.close()
                else:
                    self.registerCurrentDataset( file=cdmsFile, newLayerConfig=True ) 
                    self.dataset_selection.setText( QString( self.currentDatasetId ) ) 
                global DataSetVersion 
                DataSetVersion = DataSetVersion + 1 
                self.stateChanged()
                self.datasetChanged = True
        
    def viewMetadata(self):
        self.metadataViewer.show()
        
    def removeDataset(self):
        if self.multiFileSelection:
            del self.datasets[ str(self.dsCombo.currentText()) ]
            self.dsCombo.removeItem( self.dsCombo.currentIndex() )
            if self.dsCombo.count() == 0: self.metadataViewer.clear() 
            else:
                self.dsCombo.setCurrentIndex(0)
                if self.multiFileSelection: 
                    self.updateTimeSeries( )
                    self.initTimeRange()
                    self.pmod.datasetId = '*'.join( self.datasets.keys() )     
                else:                       
                    self.registerCurrentDataset( id=self.dsCombo.currentText() )
            global DataSetVersion 
            DataSetVersion = DataSetVersion + 1 
     
    def updateTimeSeries( self):
        self.startCombo.clear()
        self.endCombo.clear()
        current_time_values = None
        current_dt = 100000.0
        current_dsetid = None
        dataset_list = []
        time_values_list = []
        for datasetId in self.datasets:
            cdmsFile = self.datasets[ datasetId ]
            dataset = cdms2.open( cdmsFile ) 
            dataset_list.append( dataset )
        for dataset in dataset_list:
            time_values, dt = getRelativeTimeValues ( dataset )
            time_values_list.append( (dataset.id, time_values) )
            if time_values and ( dt < current_dt ):
                current_time_values = time_values
                current_dt = dt
                current_dsetid = dataset.id
        if current_time_values:
            iStart = 0
            iEnd = ( len( current_time_values ) - 1 ) 
            for time_values_rec in time_values_list:
                if time_values_rec[0] <> current_dsetid:
                    time_values = time_values_rec[1]
                    if time_values[0].value > current_time_values[ iStart ].value:
                        for iT in range( iStart+1, iEnd+1 ):
                            if current_time_values[ iT ].value >= time_values[0].value:
                                iStart = iT
                                break
                    if time_values[-1].value < current_time_values[ iEnd ].value:
                        for iT in range( iEnd, iStart, -1 ):
                            if current_time_values[ iT ].value <= time_values[-1].value:
                                iEnd = iT
                                break               
            for dataset in dataset_list: dataset.close()  
                     
            self.nTS = len(current_time_values) if current_time_values else 0
            self.relativeTimeStep = current_dt
            self.relativeStartTime = current_time_values[ iStart ]
            for iT in range( iStart, iEnd+1 ):
                time_value = current_time_values[ iT ].tocomp()
                tval = str( time_value ) 
                self.startCombo.addItem ( tval )
                self.endCombo.addItem ( tval )
            self.timeRange = [ 0, iEnd-iStart ]
            self.startCombo.setCurrentIndex( self.timeRange[0] ) 
            self.startIndexEdit.setText( str( self.timeRange[0] ) )  
            self.endCombo.setCurrentIndex( self.timeRange[1] ) 
            self.endIndexEdit.setText( str( self.timeRange[1] ) )  
       
    def selectDataset(self): 
        self.datasetChanged = True
        if self.multiFileSelection:
            self.registerCurrentDataset( id=str( self.dsCombo.currentText() ), newLayerConfig=True )
            self.updateController()
                                                       
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
                
        if self.multiFileSelection:
            self.dsCombo =  QComboBox ( self.parent() )
            ds_label.setBuddy( self.dsCombo )
            self.dsCombo.setMaximumHeight( 30 )
            ds_layout.addWidget( self.dsCombo  )
            for ds in self.datasets.keys(): self.dsCombo.addItem ( ds )
            if self.currentDatasetId:
                iCurrentDsIndex = self.dsCombo.findText( self.currentDatasetId )
                self.dsCombo.setCurrentIndex( iCurrentDsIndex )   
            self.connect( self.dsCombo, SIGNAL("currentIndexChanged(QString)"), self.selectDataset )
            
            layout.addLayout( ds_layout )
            ds_button_layout = QHBoxLayout()
    
            self.selectDirButton = QPushButton('Add Dataset', self)
            ds_button_layout.addWidget( self.selectDirButton )
            self.connect( self.selectDirButton, SIGNAL('clicked(bool)'), self.selectFile )
    
            self.removeDatasetButton = QPushButton('Remove Dataset', self)
            ds_button_layout.addWidget( self.removeDatasetButton )
            self.connect( self.removeDatasetButton, SIGNAL('clicked(bool)'), self.removeDataset )

            self.viewMetadataButton = QPushButton('View Metadata', self)
            ds_button_layout.addWidget( self.viewMetadataButton )
            self.connect( self.viewMetadataButton, SIGNAL('clicked(bool)'), self.viewMetadata )
    
            layout.addLayout( ds_button_layout )
        else:              
            self.dataset_selection  = QLabel( )
            self.dataset_selection.setFrameStyle( QFrame.Panel|QFrame.Raised )
            self.dataset_selection.setLineWidth(2)
            ds_layout.addWidget( self.dataset_selection )
            if self.currentDatasetId: self.dataset_selection.setText( QString( self.currentDatasetId ) )  
            
            layout.addLayout( ds_layout )
            ds_button_layout = QHBoxLayout()
    
            self.selectDirButton = QPushButton('Select Dataset', self)
            ds_button_layout.addWidget( self.selectDirButton )
            self.connect( self.selectDirButton, SIGNAL('clicked(bool)'), self.selectFile )
    
            self.viewMetadataButton = QPushButton('View Metadata', self)
            ds_button_layout.addWidget( self.viewMetadataButton )
            self.connect( self.viewMetadataButton, SIGNAL('clicked(bool)'), self.viewMetadata )
    
            layout.addLayout( ds_button_layout )
            ds_button1_layout = QHBoxLayout()

        timeTab = QWidget() 
#        timeTab.setFocusPolicy( Qt.NoFocus ) 
        self.tabbedWidget.addTab( timeTab, 'time' )                 
        time_layout = QVBoxLayout()
        timeTab.setLayout( time_layout ) 

        start_layout = QHBoxLayout()
        start_label = QLabel( "Start Time:"  )
        start_layout.addWidget( start_label ) 
        self.startCombo =  QComboBox ( self.parent() )
#        self.startCombo.setFocusPolicy( Qt.NoFocus )
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
#        self.endCombo.setFocusPolicy( Qt.NoFocus )
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
        roiTab_layout = QVBoxLayout()
        roiTab.setLayout( roiTab_layout ) 
        
        self.roiLabel = QLabel( "ROI: %s" % str( self.roi )  )
        roiTab_layout.addWidget(self.roiLabel)
        
        roiButton_layout = QHBoxLayout()
        roiTab_layout.addLayout(roiButton_layout )
                 
        self.selectRoiButton = QPushButton('Select ROI', self)
        roiButton_layout.addWidget( self.selectRoiButton )
        self.connect( self.selectRoiButton, SIGNAL('clicked(bool)'), self.selectRoi )

        self.resetRoiButton = QPushButton('Reset ROI', self)
        roiButton_layout.addWidget( self.resetRoiButton )
        self.connect( self.resetRoiButton, SIGNAL('clicked(bool)'), self.resetRoi )
        
        self.roiSelector = ROISelectionDialog( self.parent() )
        if self.roi: self.roiSelector.setROI( self.roi )
        self.connect(self.roiSelector, SIGNAL('doneConfigure()'), self.setRoi )

        zscaleTab = QWidget()  
        self.tabbedWidget.addTab( zscaleTab, 'vertScale' ) 
        zscaleTab_layout = QVBoxLayout()
        zscaleTab.setLayout( zscaleTab_layout ) 
        
        self.zscaleLabel = QLabel( "Vertical Scale:"  )
        zscaleTab_layout.addWidget(self.zscaleLabel)
        
        self.selectZScaleLineEdit =  QLineEdit( self.parent() )
        self.selectZScaleLineEdit.setValidator( QDoubleValidator() )
        self.selectZScaleLineEdit.setText( "%.2f" % self.zscale)
        self.connect( self.selectZScaleLineEdit, SIGNAL('editingFinished()'), self.stateChanged )
        
        zscaleTab_layout.addWidget( self.selectZScaleLineEdit )

    def setRoi(self):
        self.roi = self.roiSelector.getROI()
        self.roiLabel.setText( "ROI: %s" % str( self.roi )  )  

        
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
        
    def selectRoi( self ): 
        if self.roi: self.roiSelector.setROI( self.roi )
        self.roiSelector.show()
        self.stateChanged()

    def resetRoi( self ): 
        self.roiSelector.setROI( self.fullRoi ) 
        self.roiLabel.setText( "ROI: %s" % str( self.fullRoi )  ) 
        for i in range( len( self.roi ) ): self.roi[i] = self.fullRoi[i] 
        self.stateChanged()    
                               
    def updateStartTime( self, val ):
#        print " updateStartTime: %s " % str( val )
        iStartIndex = self.startCombo.currentIndex()
        self.startIndexEdit.setText( str(iStartIndex) )
        if self.timeRange: self.timeRange[0] = iStartIndex
        self.stateChanged()
    
    def updateEndTime( self, val ):
#        print " updateEndTime: %s " % str( val )
        iEndIndex = self.endCombo.currentIndex()
        self.endIndexEdit.setText( str(iEndIndex) )
        if self.timeRange: self.timeRange[1] = iEndIndex
        self.stateChanged()
        
    def updateStartIndex( self ):
        iStartIndex = int( str( self.startIndexEdit.text() ) )
        self.startCombo.setCurrentIndex( iStartIndex )
        if self.timeRange: 
            self.timeRange[0] = iStartIndex
        self.stateChanged()

    def updateEndIndex( self ):
        iEndIndex = int( str( self.endIndexEdit.text() ) )
        self.endCombo.setCurrentIndex( iEndIndex )
        if self.timeRange: 
            self.timeRange[1] = iEndIndex
        self.stateChanged()

    def updateController(self, controller=None):
        global DataSetVersion
        parmRecList = []
        if self.datasetChanged:
            DataSetVersion = DataSetVersion + 1
            parmRecList.append( ( 'datasets', [ serializeStrMap(self.datasets), ] ), )
            parmRecList.append( ( 'datasetId', [ self.currentDatasetId, DataSetVersion ] ), )
            self.datasetChanged = False
        parmRecList.append( ( 'timeRange' , [ self.timeRange[0], self.timeRange[1], float(self.relativeStartTime.value), self.relativeTimeStep ]  ), )       
        parmRecList.append( ( 'roi' , [ self.roi[0], self.roi[1], self.roi[2], self.roi[3] ]  ), )          
        parmRecList.append( ( 'zscale' , [ self.zscale ]  ), )  
        self.persistParameterList( parmRecList ) 
        self.stateChanged(False)
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        t0, t1 = self.startIndexEdit.text(), self.endIndexEdit.text()
        self.timeRange = [ int( str( t0 ) ), int( str( t1 ) ) ]
        self.zscale = float( self.selectZScaleLineEdit.text() )
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))

################################################################################

class MetadataViewerDialog( QDialog ):
    """
    MetadataViewerDialog is a dialog for showing dataset documentation.  

    """
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.currentRow = 0
        self.setWindowTitle('Dataset Metadata')
        self.setLayout(QVBoxLayout())
        self.buildTable()
        self.closeButton = QPushButton('Ok', self)
        self.layout().addWidget(self.closeButton)
        self.connect(self.closeButton, SIGNAL('clicked(bool)'), self.close)
        self.closeButton.setShortcut('Enter')

    def clear(self):
        self.tableWidget.clearContents() 

    def buildTable(self):
        tableGroupBox = QGroupBox("Current Dataset Properties")
        tableGroupLayout = QVBoxLayout()      
        tableGroupBox.setLayout( tableGroupLayout )
        self.layout().addWidget( tableGroupBox )
        
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setColumnWidth (0,200)
        self.tableWidget.setColumnWidth (1,1000)
        self.tableWidget.setFrameStyle( QFrame.Panel | QFrame.Raised )
        self.tableWidget.setSizePolicy( QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding ) )
        self.tableWidget.setHorizontalHeaderLabels( [ 'Property', 'Value'  ] )
        tableGroupLayout.addWidget( self.tableWidget )

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
        self.tableWidget.clearContents () 
        self.currentRow = 0
        self.setDatasetProperty( 'id', dataset.id )  
        self.setDatasetProperty( 'cdmsFile', cdmsFile ) 
        self.setDatasetAttributes( dataset )   
        
    def getTable(self):
        return self.tableWidget
        
    def addCloseObserver( self, observer ):
        self.connect(self.closeButton, SIGNAL('clicked(bool)'), observer )
           
    def show(self):
        QDialog.show(self)   
             
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
    
    dataCache = {}
    VolumeOutput = 1
    SliceOutput = 2
    VectorOutput = 3

    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['portData'], **args)
        self.imageData = {}
        self.currentTime = 0
        
    def getCachedData(self, iTimestep, varName ):
        if varName == '__zeros__': iTimestep = 0
        cache_key = '%s.%d' % ( self.datasetId, iTimestep )
        varData = self.dataCache.setdefault( cache_key, {} )
        return varData.get( varName, ( None, None ) )

    def setCachedData(self, iTimestep, varName, varDataTuple ):
        if varName == '__zeros__': iTimestep = 0
        cache_key = '%s.%d' % ( self.datasetId, iTimestep )
        varData = self.dataCache.setdefault( cache_key, {} )
        varData[ varName ] = varDataTuple
                
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
            dsetId = self.cdmsDataset.getDsetId()
            self.newDataset = ( self.datasetId <> dsetId )
            self.newLayerConfiguration = self.newDataset
            self.datasetId = dsetId
            self.timeRange = self.cdmsDataset.timeRange
            self.timeLabels = self.cdmsDataset.getTimeValues()
            self.nTimesteps = len( self.timeLabels )
            self.generateOutput()
            if self.newDataset: self.addAnnotation( "datasetId", self.datasetId )
 
            
    def getParameterId(self):
        return self.datasetId
            
    def getPortData( self, **args ):
        return self.getInputValue( "portData", **args )  
 
    def generateOutput( self ):       
        portData = self.getPortData()
        oRecMgr = OutputRecManager( portData[0] if portData else None  )
        orecs = oRecMgr.getOutputRecs( self.datasetId )  
        if not orecs: raise ModuleError( self, 'No Variable selected for dataset %s.' % self.datasetId )             
        for orec in orecs:
            cachedImageDataName = self.getImageData( orec ) 
            if cachedImageDataName:             
                if   orec.ndim == 3: self.set3DOutput( name=orec.name,  output=self.imageData[cachedImageDataName] )
                elif orec.ndim == 2: self.set2DOutput( name=orec.name,  output=self.imageData[cachedImageDataName] )

#    def getMetadata( self, metadata={}, port=None ):
#        PersistentVisualizationModule.getMetadata( metadata )
#        portData = self.getPortData()  
#        oRecMgr = OutputRecManager( portData[0] if portData else None )
#        orec = oRecMgr.getOutputRec( self.datasetId, port )
#        if orec: metadata[ 'layers' ] = orec.varList
#        return metadata
          
    def getImageData( self, orec, **args ):
        """
        This method converts cdat data into vtkImageData objects. The ds object is a CDMSDataset instance which wraps a CDAT CDMS Dataset object. 
        The ds.getVarDataTimeSlice method execution extracts a VDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).   
        The array is then rescaled, converted to a 1D unsigned short array, and then wrapped as a vtkUnsignedShortArray using the vtkdata.SetVoidArray method call.  
        The vtk data array is then attached as point data to a vtkImageData object, which is returned.
        The CDAT metadata is serialized, wrapped as a vtkStringArray, and then attached as field data to the vtkImageData object.  
        """
        varList = orec.varList
        if len( varList ) == 0: return False
        cachedImageDataName = getItem( varList[-1] )
        varNameComponents = cachedImageDataName.split('*')
        dsid = varNameComponents[0]
        varName = varNameComponents[1]
        
#        printTime('Start getImageData')
        portName = orec.name
        ndim = orec.ndim
        imageDataCreated = False
        default_dtype = np.ushort if (self.outputType == self.VolumeOutput ) else np.float
        scalar_dtype = args.get( "dtype", default_dtype )
        self._max_scalar_value = getMaxScalarValue( scalar_dtype )
        self._range = [ 0.0, self._max_scalar_value ]  
        ds = self.cdmsDataset[ dsid ]
        self.timeRange = ds.timeRange
        
        if not ( cachedImageDataName in self.imageData ):
            image_data = vtk.vtkImageData() 
            if   scalar_dtype == np.ushort: image_data.SetScalarTypeToUnsignedShort()
            elif scalar_dtype == np.ubyte:  image_data.SetScalarTypeToUnsignedChar()
            elif scalar_dtype == np.float:  image_data.SetScalarTypeToFloat()
            image_data.SetOrigin( ds.outputOrigin[0], ds.outputOrigin[1], ds.outputOrigin[2] )
#            image_data.SetOrigin( 0.0, 0.0, 0.0 )
            if ndim == 3: extent = [ ds.outputExtent[0], ds.outputExtent[1], ds.outputExtent[2], ds.outputExtent[3], ds.outputExtent[4], ds.outputExtent[5] ]   
            elif ndim == 2: extent = [ ds.outputExtent[0], ds.outputExtent[1], ds.outputExtent[2], ds.outputExtent[3], 0, 0 ]   
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
        scalars, nTup = None, 0
        vars = []
        datatype = getDatatypeString( scalar_dtype )
        md = { 'datatype':datatype, 'datasetId' : ds.id,  'bounds':ds.gridBounds, 'lat':ds.lat, 'lon':ds.lon, 'time':ds.time, 'attributes':ds.dataset.attributes }
        if ndim == 3: md[ 'lev' ] = ds.lev
        varDataId = '%s.%s.%d' % ( dsid, varName, self.outputType )
        newDataArray, var_md = self.getCachedData( self.iTimestep, varDataId )
        if newDataArray == None:
            if varName == '__zeros__':
                newDataArray = np.zeros( npts, dtype=scalar_dtype ) 
                var_md = {}
                var_md[ 'range' ] = ( 0.0, 0.0 )
                var_md[ 'scale' ] = ( 0.0, 1.0 ) 
                self.setCachedData( self.iTimestep, varName, ( newDataArray, var_md ) )   
            else:
                varData = self.cdmsDataset.getVarDataTimeSlice( dsid, varName, self.iTimestep )
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
                    self.setCachedData( self.iTimestep, varDataId, ( newDataArray, var_md ) )  
                         
        if newDataArray <> None:
            vars.append( varName ) 
            vtkdata = getNewVtkDataArray( scalar_dtype )
            nTup = newDataArray.size
            vtkdata.SetNumberOfTuples( nTup )
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
        if (self.outputType == self.VectorOutput ): 
            vtkdata = getNewVtkDataArray( scalar_dtype )
            vtkdata.SetNumberOfComponents( 3 )
            vtkdata.SetNumberOfTuples( nTup )
            iComp = 0
            for varRec in varList:
                varName = varRec[0]
                fromArray =  pointData.GetArray( varName )
                fromNTup = fromArray.GetNumberOfTuples()
                tup0 = fromArray.GetValue(0)
                toNTup = vtkdata.GetNumberOfTuples()
                vtkdata.CopyComponent( iComp, fromArray, 0 )
                iComp = iComp + 1
            vtkdata.SetName( 'vectors' )
            vtkdata.Modified()
            pointData.SetVectors(vtkdata)
            pointData.SetActiveVectors( 'vectors'  )         
        if len( vars )== 0: raise ModuleError( self, 'No dataset variables selected for output %s.' % orec.name)             
        md[ 'vars' ] = vars
        enc_mdata = encodeToString( md ) 
        self.fieldData.AddArray( getStringDataArray( 'metadata',   [ enc_mdata ]  ) )                        
        image_data.Modified()
        return cachedImageDataName if imageDataCreated else None
            
    def getMetadata( self, metadata={}, port=None ):
        PersistentVisualizationModule.getMetadata( metadata )
        if self.cdmsDataset:
            metadata[ 'vars2d' ] = self.cdmsDataset.getVariableList( 2 )
            metadata[ 'vars3d' ] = self.cdmsDataset.getVariableList( 3 )
        return metadata

class PM_CDMS_VolumeReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = self.VolumeOutput
        PM_CDMSDataReader.__init__( self, mid, **args)
        
class CDMS_VolumeReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_VolumeReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     

class PM_CDMS_SliceReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = self.SliceOutput
        PM_CDMSDataReader.__init__( self, mid, **args)

class CDMS_SliceReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_SliceReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
class PM_CDMS_VectorReader( PM_CDMSDataReader ):

    def __init__(self, mid, **args):
        self.outputType = self.VectorOutput
        PM_CDMSDataReader.__init__( self, mid, **args)


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
        self.stateChanged( False )     
     
    def getParameters( self, module ):
        global PortDataVersion
        ( self.variableList, self.datasetId, self.timeRange ) =  DV3DConfigurationWidget.getVariableList( module.id ) 
        portData = self.pmod.getPortData( dbmod=self.module, datasetId=self.datasetId ) # getFunctionParmStrValues( module, "portData" )
        if portData and portData[0]: 
             self.serializedPortData = portData[0]   
             PortDataVersion = int( portData[1] )    
                                                  
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

    def updateController(self, controller):
        global PortDataVersion
        PortDataVersion = PortDataVersion + 1
        self.persistParameterList( [ ('portData', [ self.serializedPortData, PortDataVersion ] ) ], datasetId=self.datasetId )
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
                self.addOutputTab( oRec.ndim, oRec.name, variableSelections )
        if   self.outputType == self.VolumeOutput:    self.addOutputTab( 3, 'volume'  )
        elif self.outputType == self.SliceOutput:     self.addOutputTab( 2, 'slice' )
        elif self.outputType == self.VectorOutput:    self.addOutputTab( 3, 'vector' )
        self.updateVariableLists()
                
    def getOutputTabIndex( self, name ):
        ntabs = self.outputsTabbedWidget.count()
        for iTab in range( ntabs ):
            tabName = str( self.outputsTabbedWidget.tabText( iTab ) )
            if tabName == name: return iTab # self.outputsTabbedWidget.widget(iTab)
        return -1
               
    def addOutputTab( self, ndim, output_name = None, variableSelections=[] ): 
        if output_name == None:
            qtname, ok = QInputDialog.getText( self, 'Get Output Name', 'Output name:' )
            if ok: output_name = str(qtname).strip().replace( ' ', '_' ).translate( None, OutputRecManager.sep )
        if output_name <> None:
            iExistingTabIndex = self.getOutputTabIndex( output_name )
            if iExistingTabIndex < 0:
                outputTab = self.createOutputTab( ndim, output_name, variableSelections )  
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
                    
    def createOutputTab( self, ndim, name, variableSelections = [] ):  
        otab = QWidget()  
        otabLayout = QVBoxLayout()                
        otab.setLayout( otabLayout )

        if self.outputType == self.VectorOutput:
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
    
    def updateVariableLists(self):
        if self.outRecMgr:  
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): 
                for varCombo in oRec.varComboList: 
                    varCombo.clear()
                    if self.outputType == self.VectorOutput:  varCombo.addItem( '__zeros__' )  
            for ( var, var_ndim ) in self.variableList:               
                for oRec in self.outRecMgr.getOutputRecs( self.datasetId ):
                    if var_ndim == oRec.ndim: 
                        for varCombo in oRec.varComboList: varCombo.addItem( str(var) ) 
                    
            for oRec in self.outRecMgr.getOutputRecs( self.datasetId ): 
                if oRec.varSelections:
                    varIter = iter( oRec.varSelections )
                    for varCombo in oRec.varComboList: 
                        varSelectionRec = varIter.next()
                        itemIndex = varCombo.findText( varSelectionRec[0], Qt.MatchFixedString )
                        if itemIndex >= 0: varCombo.setCurrentIndex( itemIndex )
        
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
#    config_path=os.path.expanduser('~/.vistrails/hwserver') 
#    config_path=os.path.expanduser('~/.vistrails/hwclient') 
    config_path=os.path.expanduser('~/.vistrails/') 
    sys.argv.append('-S'+config_path)
#    optionsDict = { 'dotVistrails':
    executeVistrail( 'workflows/DemoWorkflow6' )
#    executeVistrail( )

