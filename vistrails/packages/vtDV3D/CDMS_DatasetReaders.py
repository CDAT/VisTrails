'''
Created on Dec 11, 2010

@author: tpmaxwel
'''
import vtk, sys, os, copy, time
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from packages.vtDV3D.InteractiveConfiguration import *
from core.modules.vistrails_module import Module, ModuleError
from packages.vtDV3D.WorkflowModule import WorkflowModule 
from core.utils import getHomeRelativePath, getFullPath
from packages.vtDV3D import HyperwallManager, ModuleStore
#from core.vistrail.port_spec import PortSpec
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.ROISelection import ROISelectionDialog

import numpy.ma as ma
# from vtk.util.misc import vtkGetDataRoot
# packagePath = os.path.dirname( __file__ ) 
import cdms2, cdtime, cdutil, MV2 
DataSetVersion = 0
DefaultDecimation = [ 0, 7 ]
cdms2.axis.level_aliases.append('isobaric')

messageDialog = QErrorMessage()
messageDialog.hide()

def setDecimation( decimation_factor, isServer=False ):
    index = 1 if isServer else 0
    DefaultDecimation[ index ] = decimation_factor

def getDecimation( isServer=False ):
    index = 1 if isServer else 0
    return DefaultDecimation[ index ] 

def normalize_lon( lon ):
    return lon if lon <= 180.0 else (lon - 360.0)

def splitGridSpecs( gridSpecs ):
    inParen = False
    sliceStart = 0
    slices = []
    for i in range( len( gridSpecs ) ):
        sVal = gridSpecs[i]
        if sVal == '(': inParen = True
        elif sVal == ')': inParen = False
        elif sVal == ',' and not inParen: 
            slices.append( gridSpecs[sliceStart:i] )
            sliceStart = i+1
    slices.append( gridSpecs[sliceStart:] )
    return slices

def getCompTime( timeString ):
    print " >> GetCompTime: ", timeString
    timeStringFields = timeString.strip("'").split(' ')
    date = timeStringFields[0].split('-')
    if len( timeStringFields ) == 1:
        return cdtime.comptime( int(date[0]), int(date[1]), float(date[2]) )
    else:
        time = timeStringFields[1].split(':')
        for iT in range(3): time.append(0)
        return cdtime.comptime( int(date[0]), int(date[1]), int(date[2]), int(time[0]), int(time[1]), float(time[2]) )
                   
def deserializeFileMap( serialized_strMap ): 
    stringMap = {}
    if serialized_strMap:
        for dsrec in serialized_strMap.split(';'):
            dsitems = dsrec.split('#')
            if len( dsitems ) == 2: stringMap[ dsitems[0] ] = dsitems[1]
            elif len( dsitems ) == 1:
                fileId = os.path.splitext( os.path.basename( dsitems[0] ) )[0]
                stringMap[ fileId ] = dsitems[0]
    return stringMap

def getDataRoot():
    defaults = { 'data_root': '~',  }
    datasetConfig, appConfig = getConfiguration( defaults )
    hw_role = appConfig.hw_role if hasattr( appConfig, 'hw_role' ) else 'global'
    return os.path.expanduser( datasetConfig.get( hw_role, 'data_root' ) )

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
            rv0 = rv[0].torel(ReferenceTimeUnits)
            rv1 = rv[1].torel(ReferenceTimeUnits)
            dt = rv1.value - rv0.value
    return rv, dt

def getRelativeTimeValues( dataset ):
    rv = []
    dt = 0.0
    time_units = None
    if dataset <> None:
        dims = dataset.axes.keys()
        for dim in dims:
            axis = dataset.getAxis( dim )
            if axis.isTime():
                time_units = axis.units
                try:
                    if axis.calendar.lower() == 'gregorian': 
                        cdtime.DefaultCalendar = cdtime.GregorianCalendar 
                except: pass
                if hasattr( axis, 'partition' ):
                    for part in axis.partition:
                        for iTime in range( part[0], part[1] ):
                            rval = cdtime.reltime( axis[iTime], time_units )
                            rv.append( rval.torel(ReferenceTimeUnits) )
                    break
                else:
                    for tval in axis:
                        rval = cdtime.reltime( tval, time_units )
                        rv.append( rval.torel(ReferenceTimeUnits) )
        if (len(rv) > 1):
            dt = rv[1].value - rv[0].value
    return rv, dt, time_units

class CDMSDatasetRecord(): 
   
    def __init__( self, id, dataset=None, dataFile = None ):
        self.id = id
        self.lev = None
        self.dataset = dataset
        self.cdmsFile = dataFile
        self.cachedFileVariables = {} 

    def getTimeValues( self, dsid ):
        return self.dataset['time'].getValue() 
    
    def clearDataCache( self ):
         self.cachedFileVariables = {} 
    
    def getLevAxis(self ):
        for axis in self.dataset.axes.values():
            if isLevelAxis( axis ): return axis
        return None

    def getLevBounds( self, levaxis ):
        levbounds = None
        if levaxis:
            values = levaxis.getValue()
            ascending_values = ( values[-1] > values[0] )
            if levaxis:
                if   levaxis.attributes.get( 'positive', '' ) == 'down' and ascending_values:   levbounds = slice( None, None, -1 )
                elif levaxis.attributes.get( 'positive', '' ) == 'up' and not ascending_values: levbounds = slice( None, None, -1 )
        return levbounds
    
#    def getVarData( self, varName ):
#        varData = self.dataset[ varName ]
#        order = varData.getOrder()
#        args = {}
#        timevalues, dt = getComponentTimeValues( self.dataset )
#        levbounds = self.getLevBounds()
#        if self.timeRange: args['time'] = ( timevalues[ self.timeRange[0] ], timevalues[ self.timeRange[1] ] )
#        args['lon'] = slice( self.gridExtent[0], self.gridExtent[1] )
#        args['lat'] = slice( self.gridExtent[2], self.gridExtent[3] )
#        if levbounds: args['lev'] = levbounds
#        args['order'] = 'xyz'
#        print "Reading variable %s, axis order = %s, shape = %s, roi = %s " % ( varName, order, str(varData.shape), str(args) )
#        return varData( **args )

    def getVarDataTimeSlice( self, varName, timeValue, gridBounds, decimation, referenceVar=None, referenceLev=None ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """        
        cachedFileVariableRec = self.cachedFileVariables.get( varName )
        if cachedFileVariableRec:
            cachedTimeVal = cachedFileVariableRec[ 0 ]
            if cachedTimeVal.value == timeValue.value:
                return cachedFileVariableRec[ 1 ]
        
        rv = CDMSDataset.NullVariable
        varData = self.dataset[ varName ] 
#        print "Reading Variable %s, attributes: %s" % ( varName, str(varData.attributes) )

        refFile = self.cdmsFile
        refVar = varName
        refGrid = None
        if referenceVar:
            referenceData = referenceVar.split('*')
            refDsid = referenceData[0]
            refFileRelPath = referenceData[1]
            refVar  = referenceData[2]
            try:
                refFile = getFullPath( refFileRelPath )
                f=cdms2.open( refFile )
                refGrid=f[refVar].getGrid()
            except cdms2.error.CDMSError, err:
                print>>sys.stderr, " --- Error[1] opening dataset file %s: %s " % ( refFile, str( err ) )
        if not refGrid: refGrid = varData.getGrid()
        if not refGrid: 
            mb = QMessageBox.warning( None, "DV3D Error", "CDAT is unable to create a grid for this dataset."  )
            return None
        refLat=refGrid.getLatitude()
        refLon=refGrid.getLongitude()
        nRefLat, nRefLon = len(refLat) - 1, len(refLon) - 1
        LatMin, LatMax =  float(refLat[0]), float(refLat[-1]) 
        LonMin, LonMax =  float(refLon[0]), float(refLon[-1]) 
        if LatMin > LatMax:
            tmpLatMin = LatMin
            LatMin = LatMax
            LatMax = tmpLatMin
        
        args1 = {} 
        gridMaker = None
        decimationFactor = 1
        if decimation: decimationFactor = decimation[1]+1 if HyperwallManager.getInstance().isServer else decimation[0]+1
#        try:
        args1['time'] = timeValue
        if gridBounds[0] < LonMin and gridBounds[0]+360.0<LonMax: gridBounds[0] = gridBounds[0] + 360.0
        if gridBounds[2] < LonMin and gridBounds[2]+360.0<LonMax: gridBounds[2] = gridBounds[2] + 360.0
        if gridBounds[0] > LonMax and gridBounds[0]-360.0>LonMin: gridBounds[0] = gridBounds[0] - 360.0
        if gridBounds[2] > LonMax and gridBounds[2]-360.0>LonMin: gridBounds[2] = gridBounds[2] - 360.0
        if decimationFactor == 1:
            args1['lon'] = ( gridBounds[0], gridBounds[2] )
            args1['lat'] = ( gridBounds[1], gridBounds[3] )
        else:
            varGrid = varData.getGrid() 
            if varGrid: 
                varLonInt = varGrid.getLongitude().mapIntervalExt( [ gridBounds[0], gridBounds[2] ] )
                latAxis = varGrid.getLatitude()
                latVals = latAxis.getValue()
                latBounds =  [ gridBounds[3], gridBounds[1] ] if latVals[0] > latVals[1] else  [ gridBounds[1], gridBounds[3] ]            
                varLatInt = latAxis.mapIntervalExt( latBounds )
                args1['lon'] = slice( varLonInt[0], varLonInt[1], decimationFactor )
                args1['lat'] = slice( varLatInt[0], varLatInt[1], decimationFactor )
                print " ---- Decimate(%d) grid %s: varLonInt=%s, varLatInt=%s, lonSlice=%s, latSlice=%s" % ( decimationFactor, str(gridBounds), str(varLonInt), str(varLatInt), str(args1['lon']), str(args1['lat']) )
#        args1['squeeze'] = 1
        start_t = time.time() 
            
#        if (gridMaker == None) or ( gridMaker.grid == varData.getGrid() ):
                   
        if ( (referenceVar==None) or ( ( referenceVar[0] == self.cdmsFile ) and ( referenceVar[1] == varName ) ) ) and ( decimationFactor == 1):
            levbounds = self.getLevBounds( referenceLev )
            if levbounds: args1['lev'] = levbounds
            args1['order'] = 'xyz'
            rv = varData( **args1 )
        else:
            refDelLat = ( LatMax - LatMin ) / nRefLat
            refDelLon = ( LonMax - LonMin ) / nRefLon
#            nodataMask = cdutil.WeightsMaker( source=self.cdmsFile, var=varName,  actions=[ MV2.not_equal ], values=[ nodata_value ] ) if nodata_value else None
            gridMaker = cdutil.WeightedGridMaker( flat=LatMin, flon=LonMin, nlat=int(nRefLat/decimationFactor), nlon=int(nRefLon/decimationFactor), dellat=(refDelLat*decimationFactor), dellon=(refDelLon*decimationFactor) ) # weightsMaker=nodataMask  )                    
            
            vc = cdutil.VariableConditioner( source=self.cdmsFile, var=varName,  cdmsKeywords=args1, weightedGridMaker=gridMaker ) 
            regridded_var_slice = vc.get( returnTuple=0 )
            if referenceLev: regridded_var_slice = regridded_var_slice.pressureRegrid( referenceLev )
            args2 = { 'order':'xyz', 'squeeze':1 }
            levbounds = self.getLevBounds( referenceLev )
            if levbounds: args2['lev'] = levbounds
            rv = regridded_var_slice( **args2 ) 
            try: rv = MV2.masked_equal( rv, rv.fill_value ) 
            except: pass
#            max_values = [ regridded_var_slice.max(), rv.max()  ]
#            print " Regrid variable %s: max values = %s " % ( varName, str(max_values) )
            
            end_t = time.time() 
            self.cachedFileVariables[ varName ] = ( timeValue, rv )
#            print  "Reading variable %s, shape = %s, base shape = %s, time = %s (%s), args = %s, slice duration = %.4f sec." % ( varName, str(rv.shape), str(varData.shape), str(timeValue), str(timeValue.tocomp()), str(args1), end_t-start_t  ) 
#        except Exception, err:
#            print>>sys.stderr, ' Exception getting var slice: %s ' % str( err )
        return rv

    def getFileVarDataCube( self, varName, decimation, **args ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """ 
        lonBounds = args.get( 'lon', None )
        latBounds = args.get( 'lat', None )
        levBounds = args.get( 'lev', None )
        timeBounds = args.get( 'time', None )
        [ timeValue, timeIndex, useTimeIndex ] = timeBounds if timeBounds else [ None, None, None ]
        referenceVar = args.get( 'refVar', None )
        referenceLev = args.get( 'refLev', None )

#        nSliceDims = 0
#        for bounds in (lonBounds, latBounds, levBounds, timeBounds):
#            if ( bounds <> None ) and ( len(bounds) == 1 ):  
#               nSliceDims = nSliceDims + 1
#        if nSliceDims <> 1:
#            print "Error, Wrong number of data dimensions:  %d slice dims " %  nSliceDims
#            return None
        cachedFileVariableRec = self.cachedFileVariables.get( varName )
        if cachedFileVariableRec:
            cachedTimeVal = cachedFileVariableRec[ 0 ]
            if cachedTimeVal.value == timeValue.value:
                return cachedFileVariableRec[ 1 ]
        
        rv = CDMSDataset.NullVariable
        varData = self.dataset[ varName ] 
        currentLevel = varData.getLevel()
#        print "Reading Variable %s, attributes: %s" % ( varName, str(varData.attributes) )

        refFile = self.cdmsFile
        refVar = varName
        refGrid = None
        if referenceVar:
            referenceData = referenceVar.split('*')
            refDsid = referenceData[0]
            relFilePath = referenceData[1]
            refVar  = referenceData[2]
            try:
                cdmsFile = getFullPath( relFilePath )
                f=cdms2.open( cdmsFile )
                refGrid=f[refVar].getGrid()
            except cdms2.error.CDMSError, err:
                print>>sys.stderr, " --- Error[2] opening dataset file %s: %s " % ( cdmsFile, str( err ) )
        if not refGrid: refGrid = varData.getGrid()
        if not refGrid: 
            mb = QMessageBox.warning( None, "DV3D Error", "CDAT is unable to create a grid for this dataset."  )
            return None
        refLat=refGrid.getLatitude()
        refLon=refGrid.getLongitude()
        nRefLat, nRefLon = len(refLat) - 1, len(refLon) - 1
        LatMin, LatMax =  float(refLat[0]), float(refLat[-1]) 
        LonMin, LonMax =  float(refLon[0]), float(refLon[-1]) 
        if LatMin > LatMax:
            tmpLatMin = LatMin
            LatMin = LatMax
            LatMax = tmpLatMin
        
        args1 = {} 
        gridMaker = None
        decimationFactor = 1
        order = 'xyt' if ( timeBounds == None) else 'xyz'
        if decimation: decimationFactor = decimation[1]+1 if HyperwallManager.getInstance().isServer else decimation[0]+1
        try:
            nts = self.dataset['time'].shape[0]
            if ( timeIndex <> None ) and  useTimeIndex: 
                args1['time'] = slice( timeIndex, timeIndex+1, 1 )
            elif timeValue and (nts>1): 
                args1['time'] = timeValue
        except: pass
        
        if lonBounds <> None:
            if (lonBounds[1] - lonBounds[0]) < 355.0:
                if lonBounds[0] < LonMin: lonBounds[0] = LonMin
                if lonBounds[1] > LonMax: lonBounds[1] = LonMax
#            if lonBounds[0] < LonMin and lonBounds[0]+360.0 < LonMax: lonBounds[0] = lonBounds[0] + 360.0
#            if lonBounds[0] > LonMax and lonBounds[0]-360.0 > LonMin: lonBounds[0] = lonBounds[0] - 360.0
#            if len( lonBounds ) > 1:
#                if lonBounds[1] < LonMin and lonBounds[1]+360.0<LonMax: lonBounds[1] = lonBounds[1] + 360.0
#                if lonBounds[1] > LonMax and lonBounds[1]-360.0>LonMin: lonBounds[1] = lonBounds[1] - 360.0                       
            if (decimationFactor == 1) or len( lonBounds ) == 1:
                args1['lon'] = lonBounds[0] if ( len( lonBounds ) == 1 ) else lonBounds
            else:
                varGrid = varData.getGrid() 
                varLonInt = varGrid.getLongitude().mapIntervalExt( [ lonBounds[0], lonBounds[1] ] )
                args1['lon'] = slice( varLonInt[0], varLonInt[1], decimationFactor )
               
        if latBounds <> None:
            if decimationFactor == 1:
                args1['lat'] = latBounds[0] if ( len( latBounds ) == 1 ) else latBounds
            else:
                latAxis = varGrid.getLatitude()
                latVals = latAxis.getValue()
                latBounds =  [ latBounds[1], latBounds[0] ] if latVals[0] > latVals[1] else  [ latBounds[0], latBounds[1] ]            
                varLatInt = latAxis.mapIntervalExt( latBounds )
                args1['lat'] = slice( varLatInt[0], varLatInt[1], decimationFactor )
                
        start_t = time.time() 
        
        if ( (referenceVar==None) or ( ( referenceVar[0] == self.cdmsFile ) and ( referenceVar[1] == varName ) ) ) and ( decimationFactor == 1):
            if levBounds <> None:
                args1['lev'] =  levbounds[0] if ( len( levbounds ) == 1 ) else levbounds                        
            else:
                levbounds = self.getLevBounds( referenceLev )
                if levbounds: args1['lev'] = levbounds
            args1['order'] = order
            rv = varData( **args1 )
        else:
            refDelLat = ( LatMax - LatMin ) / nRefLat
            refDelLon = ( LonMax - LonMin ) / nRefLon
#            nodataMask = cdutil.WeightsMaker( source=self.cdmsFile, var=varName,  actions=[ MV2.not_equal ], values=[ nodata_value ] ) if nodata_value else None
            gridMaker = cdutil.WeightedGridMaker( flat=LatMin, flon=LonMin, nlat=int(nRefLat/decimationFactor), nlon=int(nRefLon/decimationFactor), dellat=(refDelLat*decimationFactor), dellon=(refDelLon*decimationFactor) ) # weightsMaker=nodataMask  )                    
                
            from packages.vtDV3D.CDMS_DatasetReaders import getRelativeTimeValues 
            time_values, dt, time_units = getRelativeTimeValues ( cdms2.open( self.cdmsFile ) ) 
            
            vc = cdutil.VariableConditioner( source=self.cdmsFile, var=varName,  cdmsKeywords=args1, weightedGridMaker=gridMaker ) 
            print " regridded_var_slice(%s:%s): %s " % ( self.dataset.id, varName, str( args1 ) )
            regridded_var_slice = vc.get( returnTuple=0 )
#            if (referenceLev <> None) and ( referenceLev.shape[0] <> currentLevel.shape[0] ): 
#                regridded_var_slice = regridded_var_slice.pressureRegrid( referenceLev ) 
            
            args2 = { 'order' : order, 'squeeze' : 1 }
            if levBounds <> None:
                args2['lev'] = levBounds[0] if ( len( levBounds ) == 1 ) else levBounds                            
            else:
                levBounds = self.getLevBounds( currentLevel )
                if levBounds: args2['lev'] = levBounds
            rv = regridded_var_slice( **args2 ) 
            try: rv = MV2.masked_equal( rv, rv.fill_value )
            except: pass
#            max_values = [ regridded_var_slice.max(), rv.max()  ]
#            print " Regrid variable %s: max values = %s " % ( varName, str(max_values) )
            
            end_t = time.time() 
            self.cachedFileVariables[ varName ] = ( timeValue, rv )
            print  "Reading variable %s, shape = %s, base shape = %s, args = %s" % ( varName, str(rv.shape), str(varData.shape), str(args1) ) 
#        except Exception, err:
#            print>>sys.stderr, ' Exception getting var slice: %s ' % str( err )
        return rv


#    def init( self, timeRange, roi, zscale ):
#        self.timeRange = timeRange
#        self.roi = roi
#        self.zscale = zscale

#    def getGridSpecs( self, var, roi, zscale, outputType ):   
#        dims = self.dataset.axes.keys()
#        gridOrigin = newList( 3, 0.0 )
#        outputOrigin = newList( 3, 0.0 )
#        gridBounds = newList( 6, 0.0 )
#        gridSpacing = newList( 3, 1.0 )
#        gridExtent = newList( 6, 0 )
#        outputExtent = newList( 6, 0 )
#        gridShape = newList( 3, 0 )
#        gridSize = 1
#        domain = var.getDomain()
#        if not self.lev: self.lev = var.getLevel()
#        axis_list = var.getAxisList()
#        for axis in axis_list:
#            size = len( axis )
#            iCoord = self.getCoordType( axis, outputType )
#            roiBounds, values = self.getAxisValues( axis, roi )
#            if iCoord >= 0:
#                iCoord2 = 2*iCoord
#                gridShape[ iCoord ] = size
#                gridSize = gridSize * size
#                outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] = size-1                    
#                if iCoord < 2:
#                    lonOffset = 0.0 #360.0 if ( ( iCoord == 0 ) and ( roiBounds[0] < -180.0 ) ) else 0.0
#                    outputOrigin[ iCoord ] = gridOrigin[ iCoord ] = values[0] + lonOffset
#                    spacing = (values[size-1] - values[0])/(size-1)
#                    if roiBounds:
#                        if ( roiBounds[1] < 0.0 ) and  ( roiBounds[0] >= 0.0 ): roiBounds[1] = roiBounds[1] + 360.0
#                        gridExtent[ iCoord2 ] = int( round( ( roiBounds[0] - values[0] )  / spacing ) )                
#                        gridExtent[ iCoord2+1 ] = int( round( ( roiBounds[1] - values[0] )  / spacing ) )
#                        outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ]
#                        outputOrigin[ iCoord ] = lonOffset + roiBounds[0]
#                    roisize = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ] + 1                  
#                    gridSpacing[ iCoord ] = spacing
#                    gridBounds[ iCoord2 ] = roiBounds[0] if roiBounds else values[0] 
#                    gridBounds[ iCoord2+1 ] = (roiBounds[0] + roisize*spacing) if roiBounds else values[ size-1 ]
#                else:                                             
#                    gridSpacing[ iCoord ] = zscale
#                    gridBounds[ iCoord2 ] = values[0]  # 0.0
#                    gridBounds[ iCoord2+1 ] = values[ size-1 ] # float( size-1 )
#        if gridBounds[ 2 ] > gridBounds[ 3 ]:
#            tmp = gridBounds[ 2 ]
#            gridBounds[ 2 ] = gridBounds[ 3 ]
#            gridBounds[ 3 ] = tmp
#        gridSpecs = {}
#        md = { 'datasetId' : self.id,  'bounds':gridBounds, 'lat':self.lat, 'lon':self.lon, 'lev':self.lev, 'attributes':self.dataset.attributes }
#        gridSpecs['gridOrigin'] = gridOrigin
#        gridSpecs['outputOrigin'] = outputOrigin
#        gridSpecs['gridBounds'] = gridBounds
#        gridSpecs['gridSpacing'] = gridSpacing
#        gridSpecs['gridExtent'] = gridExtent
#        gridSpecs['outputExtent'] = outputExtent
#        gridSpecs['gridShape'] = gridShape
#        gridSpecs['gridSize'] = gridSize
#        gridSpecs['md'] = md
#        return gridSpecs

class CDMSDataset(Module): 
    
    NullVariable = cdms2.createVariable( np.array([]), id='NULL' )

    def __init__( self ):
        Module.__init__(self)
        self.datasetRecs = {}
        self.variableRecs = {}
        self.transientVariables = {}
        self.cachedTransVariables = {}
        self.outputVariables = {}
        self.referenceVariable = None
        self.timeRange = None
        self.gridBounds = None
        self.decimation = DefaultDecimation
        self.zscale = 1.0
        self.cells = []
        
    def setCells( self, cells ):
        self.cells[:] = cells[:]
      
    def setVariableRecord( self, id, varName ):
        self.variableRecs[id] = varName

    def getVariableRecord( self, id ):
        return self.variableRecs[id] 

    def getVarRecValues( self ):
        return self.variableRecs.values() 

    def getVarRecKeys( self ):
        return self.variableRecs.keys() 

    def setBounds( self, timeRange, roi, zscale, decimation ): 
        self.timeRange = timeRange
        self.gridBounds = roi
        self.zscale = zscale
        self.decimation = decimation
        
    def getTimeValues( self, asComp = True ):
        if self.timeRange == None: return None
        start_rel_time = cdtime.reltime( float( self.timeRange[2] ), ReferenceTimeUnits )
        time_values = []
        for iTime in range( self.timeRange[0], self.timeRange[1]+1 ):
            rval = start_rel_time.value + iTime * self.timeRange[3]
            tval = cdtime.reltime( float( rval ), ReferenceTimeUnits )
            if asComp:   time_values.append( tval.tocomp() )
            else:        time_values.append( tval )
        return time_values
    
    def getGrid( self, gridData ):
        dsetRec = self.datasetRecs.get( gridData[0], None )
        if dsetRec:
            grids = dsetRec.dataset.grids
            return grids.get( gridData[1], None  )
        return None

    def setReferenceVariable( self, selected_grid_id ):
        try:
            if (selected_grid_id == None) or (selected_grid_id == 'None'): return
            grid_id = getItem( selected_grid_id )
            refVarData = grid_id.split('*')
            if len( refVarData ) > 1:
                dsid = refVarData[0]
                varName = refVarData[1].split('(')[0].strip()
                dsetRec = self.datasetRecs.get( dsid, None )
                if dsetRec:
                    variable = dsetRec.dataset.variables.get( varName, None )
                    if variable: 
                        self.referenceVariable = "*".join( [ dsid, dsetRec.cdmsFile, varName ] )
                        self.referenceLev = variable.getLevel()
        except Exception, err:
            print>>sys.stderr, " Error in setReferenceVariable: ", str(err)
            
    def getReferenceDsetId(self):
        if self.referenceVariable == None: return self.datasetRecs.keys()[0]
        return self.referenceVariable.split("*")[0]
                                                             
    def getStartTime(self):
        return cdtime.reltime( float( self.timeRange[2] ), ReferenceTimeUnits )

    def __del__( self ):
        for dsetRec in self.datasetRecs.values(): dsetRec.dataset.close()
        Module.__del__( self )
         
    def addTransientVariable( self, varName, variable, ndim = None ):
        self.transientVariables[ varName ] = variable

    def getTransientVariable( self, varName ):
        return self.transientVariables.get( varName, None )

    def getTransientVariableNames( self ):
        return self.transientVariables.keys()

    def addOutputVariable( self, varName, variable, ndim = None ):
        self.outputVariables[ varName ] = variable

    def getOutputVariable( self, varName ):
        return self.outputVariables.get( varName, None )

    def getOutputVariableNames( self ):
        return self.outputVariables.keys()

    def __getitem__(self, dsid ):
        return self.datasetRecs.get( dsid, None )

    def __delitem__(self, dsid ):
        dsetRec = self.datasetRecs[ dsid ]
        dsetRec.dataset.close()
        del self.datasetRecs[ dsid ]
    
#    def getVarData( self, dsid, varName ):
#        dsetRec = self.datasetRecs[ dsid ]
#        if varName in dsetRec.dataset.variables:
#            return dsetRec.getVarData( self, varName )
#        elif varName in self.transientVariables:
#            return self.transientVariables[ varName ]
#        else: 
#            print>>sys.stderr, "Error: can't find variable %s in dataset" % varName
#            return self.NullVariable

    def clearDataCache( self ):
        for dsetRec in self.datasetRecs.values(): dsetRec.clearDataCache()

    def getVarDataTimeSlice( self, dsid, varName, timeValue ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        rv = CDMSDataset.NullVariable
        if dsid:
            dsetRec = self.datasetRecs[ dsid ]
            if varName in dsetRec.dataset.variables:
                rv = dsetRec.getVarDataTimeSlice( varName, timeValue, self.gridBounds, self.decimation, self.referenceVariable, self.referenceLev )   
        if (rv.id == "NULL") and (varName in self.transientVariables):
            rv = self.transientVariables[ varName ]
        if rv.id <> "NULL": 
            return rv 
#            current_grid = rv.getGrid()
#            if ( gridMaker == None ) or SameGrid( current_grid, gridMaker.grid ): return rv
#            else:       
#                vc = cdutil.VariableConditioner( source=rv, weightedGridMaker=gridMaker )
#                return vc.get( returnTuple=0 )
        print>>sys.stderr, "Error: can't find time slice variable %s in dataset" % varName
        return rv

    def getVarDataCube( self, dsid, varName, timeValues, levelValues = None ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        rv = CDMSDataset.NullVariable
        if dsid:
            dsetRec = self.datasetRecs.get( dsid, None )
            if dsetRec:
                if varName in dsetRec.dataset.variables:
                    rv = dsetRec.getFileVarDataCube( varName, self.decimation, time=timeValues, lev=levelValues, lon=[self.gridBounds[0],self.gridBounds[2]], lat=[self.gridBounds[1],self.gridBounds[3]], refVar=self.referenceVariable, refLev=self.referenceLev )  
            elif varName in self.getTransientVariableNames():
                tvar = self.getTransientVariable( varName ) 
                rv = self.getTransVarDataCube( varName, tvar, self.decimation, time=timeValues, lev=levelValues )  
        if (rv.id == "NULL") and (varName in self.outputVariables):
            rv = self.outputVariables[ varName ]
        if rv.id <> "NULL": 
            return rv 
#            current_grid = rv.getGrid()
#            if ( gridMaker == None ) or SameGrid( current_grid, gridMaker.grid ): return rv
#            else:       
#                vc = cdutil.VariableConditioner( source=rv, weightedGridMaker=gridMaker )
#                return vc.get( returnTuple=0 )
        print>>sys.stderr, "Error: can't find time slice data cube for variable %s in dataset" % varName
        return rv


    def getTransVarDataCube( self, varName, transVar, decimation, **args ):
        """
        This method returns a data slice with the correct axis ordering (returning a NumPy masked array).
        """ 
        invert_z = False
        levaxis = transVar.getLevel() 
        timeaxis = transVar.getTime() 
        level = args.get( 'lev', None )
        if levaxis:
            values = levaxis.getValue()
            ascending_values = ( values[-1] > values[0] )
            invert_z = ( (levaxis.attributes.get( 'positive', '' ) == 'down') and ascending_values ) or ( (levaxis.attributes.get( 'positive', '' ) == 'up') and not ascending_values )
               
        timeBounds = args.get( 'time', None )
        [ timeValue, timeIndex, useTimeIndex ] = timeBounds if timeBounds else [ None, None, None ]

        cachedTransVariableRec = self.cachedTransVariables.get( varName )
        if cachedTransVariableRec:
            cachedTimeVal = cachedTransVariableRec[ 0 ]
            if cachedTimeVal.value == timeValue.value:
                return cachedTransVariableRec[ 1 ]
        
        rv = CDMSDataset.NullVariable 
        currentLevel = transVar.getLevel()
#        print "Reading Variable %s, attributes: %s" % ( varName, str(transVar.attributes) )

        decimationFactor = 1
        if decimation: decimationFactor = decimation[1]+1 if HyperwallManager.getInstance().isServer else decimation[0]+1
        
        args1 = {} 
        order = 'xyt' if ( timeBounds == None) else 'xyz'
        try:
            nts = self.timeRange[1]
            if ( timeIndex <> None ) and  useTimeIndex: 
                args1['time'] = slice( timeIndex, timeIndex+1 )
            elif timeValue and (nts>1): 
                args1['time'] = timeValue
        except: pass

        if decimationFactor > 1:
            lonAxis = transVar.getLongitude() 
            lonVals = lonAxis.getValue()
            varLonInt = lonAxis.mapIntervalExt( [ lonVals[0], lonVals[-1] ], 'ccn' )
            args1['lon'] = slice( varLonInt[0], varLonInt[1], decimationFactor )
           
            latAxis = transVar.getLatitude() 
            latVals = latAxis.getValue()
            latRange = [ latVals[0], latVals[-1] ] if (latVals[-1] > latVals[0]) else [ latVals[-1], latVals[0] ]
            varLatInt = latAxis.mapIntervalExt( latRange, 'ccn' )
            args1['lat'] = slice( varLatInt[0], varLatInt[1], decimationFactor )
        
        args1['order'] = order
        if levaxis:
            if level: args1['lev'] = float( level )
            elif invert_z:  args1['lev'] = slice( None, None, -1 )
        try: 
            rv = transVar( **args1 )
        except Exception, err: 
            messageDialog.setWindowTitle( "Error Reading Variable" )
            messageDialog.showMessage( str(err) )
            return CDMSDataset.NullVariable
        try: rv = MV2.masked_equal( rv, rv.fill_value )
        except: pass          
        self.cachedTransVariables[ varName ] = ( timeValue, rv )
        print  "Reading variable %s, shape = %s, base shape = %s, args = %s" % ( varName, str(rv.shape), str(transVar.shape), str(args1) ) 
        return rv

    def getVarDataTimeSlices( self, varList, timeValue ):
        """
        This method extracts a CDMS variable object (varName) and then cuts out a data slice with the correct axis ordering (returning a NumPy masked array).
        """
        timeSlices, condTimeSlices = [], []
        vc0 = None
        for ( dsid, varName ) in varList:
            varTimeSlice = self.getVarDataTimeSlice( dsid, varName, timeValue )
            if not vc0: vc0 = cdutil.VariableConditioner( varTimeSlice )    
            else:       timeSlices.append( varTimeSlice )                
        for varTimeSlice in timeSlices:
            vc1 = cdutil.VariableConditioner( varTimeSlice ) 
            VM = cdutil.VariablesMatcher( vc0, vc1 )
            condTimeSlice0, condTimeSlice1 = VM.get( returnTuple=0 )
            if not condTimeSlices: condTimeSlices.append( condTimeSlice0 )
            condTimeSlices.append( condTimeSlice1 )
        return condTimeSlices
    
    def addDatasetRecord( self, dsetId, relFilePath ):
        cdmsDSet = self.datasetRecs.get( dsetId, None )
        if (cdmsDSet <> None) and (cdmsDSet.cdmsFile == relFilePath):
            return cdmsDSet
        try:
            relFilePath = relFilePath.strip()
            if relFilePath:
                cdmsFile = getFullPath( relFilePath )
                dataset = cdms2.open( cdmsFile ) 
                cdmsDSet = CDMSDatasetRecord( dsetId, dataset, cdmsFile )
                self.datasetRecs[ dsetId ] = cdmsDSet
        except Exception, err:
            print>>sys.stderr, " --- Error[3] opening dataset file %s: %s " % ( cdmsFile, str( err ) )
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

class CDMS_VCDATInterfaceSpecs(WorkflowModule):
        
    def __init__( self, configParms, **args ):
        WorkflowModule.__init__(self, **args) 
        self.inputs = {}
        self.configParms = configParms
        
    def addInput(self, inputName, fileId, fileName, variableName, axes ):
        print " --- AddInput: ", inputName, fileName, variableName
        self.inputs[ inputName ] = ( fileId, fileName, variableName, axes )
        
    def getNInputs(self):
        return len(self.inputs)
        
    def getInput(self, **args ):
        inputName = args.get( 'name', None )
        if not inputName: 
            inputIndex = args.get( 'index', 0 )
            keys = self.inputs.keys()
            if len(keys) > inputIndex:
                keys.sort()
                inputName = keys[inputIndex]        
        return self.inputs.get( inputName )

class SerializedInterfaceSpecs:
        
    def __init__( self, serializedConfiguration = None ):
        self.inputs = {}
        self.cells = []
        self.configParms = None
        if serializedConfiguration and (serializedConfiguration <> 'None'):
            self.parseInputSpecs( serializedConfiguration )
            
    def parseInputSpecs( self, serializedConfiguration ):
        inputSpecElements = serializedConfiguration.split(';')
        fileInputSpecs = inputSpecElements[0].split('|')
        varInputSpecs = inputSpecElements[1].split('|')
        gridInputSpecs = inputSpecElements[2].split('|')
        cellInputSpecs = inputSpecElements[3].split('|')
        if fileInputSpecs[0]:
            if len( fileInputSpecs ) == 1:
                fileMetadata = fileInputSpecs[0].split('!')
                fileId = fileMetadata[1]
                fileName = fileMetadata[2] if fileMetadata[2] else fileId
                for iVar in range( len(varInputSpecs) ):
                    varSpecs = varInputSpecs[iVar].split('!')
                    if len( varSpecs ) > 2:
                        varName = varSpecs[2] if varSpecs[2] else varSpecs[1]
                        axes = gridInputSpecs[iVar].split('!')[1]
                        self.addInput( ("Input%d" % iVar), fileId, fileName, varName, axes )
            elif len( fileInputSpecs ) == len( varInputSpecs ):
                for iVar in range( len(varInputSpecs) ):
                    fileMetadata = fileInputSpecs[iVar].split('!')
                    fileId = fileMetadata[1]
                    fileName = fileMetadata[2] if fileMetadata[2] else fileId
                    varSpecs = varInputSpecs[iVar].split('!')
                    if len( varSpecs ) > 2:
                        varName = varSpecs[2] if varSpecs[2] else varSpecs[1]
                        axes = gridInputSpecs[iVar].split('!')[1]
                        self.addInput( ("Input%d" % iVar), fileId, fileName, varName, axes )
            else:
                print>>sys.stderr, " ERROR: Number of Files and number of Variables do not match."
        for iCell in range( len(cellInputSpecs) ):
            cellMetadata = cellInputSpecs[iCell].split('!')
            if len( cellMetadata ) > 1: self.cells.append( ( cellMetadata[0], cellMetadata[1] ) )
                
        
    def addInput(self, inputName, fileId, fileName, variableName, axes ):
        print " --- AddInput: ", inputName, fileId, fileName, variableName, axes
        relFilePath = getHomeRelativePath( fileName )
        self.inputs[ inputName ] = ( fileId, relFilePath, variableName, axes )
        
    def getNInputs(self):
        return len(self.inputs)
            
    def getInput(self, **args ):
        inputName = args.get( 'name', None )
        if not inputName: 
            inputIndex = args.get( 'index', 0 )
            keys = self.inputs.keys()
            if len(keys) > inputIndex:
                keys.sort()
                inputName = keys[inputIndex]        
        return self.inputs.get( inputName )
        

#class PM_CDMS_VCDATInterface( PersistentVisualizationModule ):
#    
#    def __init__(self, mid, **args):
#        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['timeRange','roi'], **args)
#        self.filenum = 1
#        self.varnum = 1
#        self.cellnum = 1
#        
#    def getIntInputValue(self, portName, default_value ):
#        rv = default_value 
#        try: rv = int( getItem( self.getInputValue( portName, default_value ) )  ) 
#        except: pass
#        return rv
#
#    def getFloatInputValue(self, portName, default_value ):
#        rv = default_value 
#        try: rv = float( getItem( self.getInputValue( portName, default_value ) ) ) 
#        except: pass
#        return rv
#        
#    def execute(self, **args ):
#        """ compute() -> None
#        Dispatch the vtkRenderer to the actual rendering widget
#        """  
#        self.file = self.getInputValue( "FileName" )
#        self.variable = self.getInputValue( "VariableName" )
#        self.variable1 = self.getInputValue( "VariableName1" )
#        self.variable2 = self.getInputValue( "VariableName2" )
#        self.variable3 = self.getInputValue( "VariableName3" )
#        self.vcdatInputSpecs = self.getInputValue( "vcdatInputSpecs" )       
#        self.axes = self.getInputValue( "Axes" )
#        self.row = self.getIntInputValue( "Row", 0 )  
#        self.column = self.getIntInputValue( "Column", 0  ) 
#        self.row1 = self.getIntInputValue( "Row1", 0 )  
#        self.column1 = self.getIntInputValue( "Column1", 0  ) 
#        self.row2 = self.getIntInputValue( "Row2", 0 )  
#        self.column2 = self.getIntInputValue( "Column2", 0  ) 
#        zscale = self.getFloatInputValue( "zscale",   5.0  )  
#        configParms = { 'zscale' : zscale }
#        interfaceSpecs = CDMS_VCDATInterfaceSpecs( configParms )
#        if self.variable  <> None: interfaceSpecs.addInput( 'Input', self.file, self.variable, self.axes )
#        if self.variable1 <> None: interfaceSpecs.addInput( 'Input1', self.file, self.variable1, self.axes )
#        if self.variable2 <> None: interfaceSpecs.addInput( 'Input2', self.file, self.variable2, self.axes )         
#        if self.variable3 <> None: interfaceSpecs.addInput( 'Input3', self.file, self.variable3, self.axes )         
#        self.setResult( 'executionSpecs', [ interfaceSpecs ] )
#        print "  ------------------- VCDATInterface Inputs: -------------------  "
#        print " * FileName: ", self.file
#        print " * VariableName: ", self.variable
#        print " * VariableName1: ", self.variable1
#        print " * VariableName2: ", self.variable2
#        print " * VariableName3: ", self.variable3
#        print " * Axes: ", self.axes
#        print " * Row: ", self.row
#        print " * Column: ", self.column
#        print " * Row1: ", self.row1
#        print " * Column1: ", self.column1
#        print " * Row2: ", self.row2
#        print " * Column2: ", self.column2
#        print " * VcdatInputSpecs: ", self.vcdatInputSpecs
#        print "  -------------------                         -------------------  "
##        executionSpecs = ';'.join( [ self.file, self.variable, self.axes ] ) if self.file else None
##        if executionSpecs: 
##            print " >>>--->>> ExecutionSpecs: { %s } " % executionSpecs
##            self.setResult( 'executionSpecs', [ self.file, self.variable, self.axes ] )
#        cellLocation = "A1" 
#        if ( (self.row >= 0) and (self.column >= 0) ):
#             cellLocation = "%s%d" % ( chr( ord('A') + self.column ), self.row + 1 )    
#        self.setResult( 'cellLocation', [ cellLocation ] )
#        
#        cellLocation = "B1" 
#        if ( (self.row1 >= 0) and (self.column1 >= 0) ):
#             cellLocation = "%s%d" % ( chr( ord('A') + self.column1 ), self.row1 + 1 )    
#        self.setResult( 'cellLocation1', [ cellLocation ] )
#
#        cellLocation = "C1" 
#        if ( (self.row2 >= 0) and (self.column2 >= 0) ):
#             cellLocation = "%s%d" % ( chr( ord('A') + self.column2 ), self.row2 + 1 )    
#        self.setResult( 'cellLocation2', [ cellLocation ] )
#
##        print " >>>--->>> CellLocation: { %s } " % cellLocation
#
##        fileAliases = ','.join( [ "%s:%s" % ( self.files[i], aliases[self.files[i]] )  for i in range(self.filenum) ] )
##        varAliases = ','.join( [ "%s:%s" % ( self.vars[i], aliases[self.vars[i]] )  for i in range(self.varnum) ] )
##        gridAliases = ','.join( [ "%s:%s" % ( self.axes[i], aliases[self.axes[i]] )  for i in range(self.varnum) ] )
##        aliases[ 'inputSpecs' ] = ';'.join( [ fileAliases, varAliases, gridAliases ] )
##        print " inputSpecs: ", str( aliases[ 'inputSpecs' ] )
##        aliases[ 'cellSpecs' ] = ','.join( [ "%s%s" % ( chr( ord('A') + int(aliases[self.cells[i].col_name]) ), aliases[self.cells[i].row_name] )  for i in range(self.cellnum) ] )
##        print " cellSpecs: ", str( aliases[ 'cellSpecs' ] )

                    
class PM_CDMS_FileReader( PersistentVisualizationModule ):

    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, layerDepParms=['timeRange','roi'], **args)
        self.datasetModule = CDMSDataset()
        
    def clearDataCache(self):
        from packages.vtDV3D.CDMS_VariableReaders import PM_CDMSDataReader
        self.datasetModule.clearDataCache()
        PM_CDMSDataReader.clearCache() 
        
    def computeGridFromSpecs(self):
        start_time, end_time, min_dt  = -float('inf'), float('inf'), float('inf')
        self.roi = [ 0.0, -90.0, 360.0, 90.0 ]
        for gridSpec in self.gridSpecs:
            print " -- GridSpec: ", gridSpec
            gridFields = gridSpec.split('=')
            if len( gridFields ) == 2:
                type = gridFields[0].strip()
                values = gridFields[1].strip('() ').split(',')
                if len(values) == 1: values = values[0].strip(' ').split(' ')
                if type == 'time':
                    cval = getCompTime( values[0].strip(" ") )
                    start_time = cval.torel(ReferenceTimeUnits).value
                    cval = getCompTime( values[1].strip(" ") )
                    end_time = cval.torel(ReferenceTimeUnits).value
#                    print " TimeRange Specs: ", str( values ), str( start_time ), str( end_time ), str( ReferenceTimeUnits )
                elif type.startswith('lat' ):
                    lat_bounds = [ float( values[0] ), float( values[1] ) ]
                    self.roi[1] = lat_bounds[0] if lat_bounds[0] < lat_bounds[1] else lat_bounds[1]
                    self.roi[3] = lat_bounds[1] if lat_bounds[0] < lat_bounds[1] else lat_bounds[0] 
                elif type.startswith('lon' ):
                    self.roi[0] = float( values[0] ) 
                    self.roi[2] = float( values[1] )                   
        dataset_list = []
        for relFilePath in self.fileSpecs:
            try:
                cdmsFile = getFullPath( relFilePath )
                dataset = cdms2.open( cdmsFile ) 
                dataset_list.append( dataset )
            except:
                print "Error opening dataset: %s" % str(cdmsFile)
        for dataset in dataset_list:
            time_values, dt, time_units = getRelativeTimeValues ( dataset )
            if time_values:
                nTS = len( time_values )
                tbounds = [ time_values[0].value, time_values[nTS-1].value ]
                if  tbounds[0] > start_time: start_time  = tbounds[0]
                if dt == 0.0: end_time = start_time
                elif tbounds[1] < end_time:   end_time = tbounds[1]
                if dt < min_dt: min_dt = dt               
        for dataset in dataset_list: dataset.close()
        if min_dt == float('inf'): 
            nTS = 1
            start_time = 0 
            end_time = 0
            min_dt = 0.0
        elif min_dt == 0.0:
           nTS = 1 
        else: nTS = int( ( ( end_time - start_time ) / min_dt ) + 0.0001 )  
        self.timeRange = [ 0, nTS, start_time, min_dt ]
        print "Compute TimeRange From Specs: ", str( [ start_time, end_time, min_dt ] ), str( self.timeRange )

            
    def execute(self, **args ):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """  
        self.fileSpecs, self.varSpecs, self.gridSpecs, self.datasetMap, self.ref_var = None, None, None, None, None         
        decimation = self.getInputValue( "decimation" )
        zscale = getItem( self.getInputValue( "zscale",   1.0  )  )
        
        serializedInputSpecs = getItem( self.getInputValue( "executionSpecs" ) )
        if serializedInputSpecs:
            inputSpecs = SerializedInterfaceSpecs( serializedInputSpecs ) if serializedInputSpecs else None
            print " ** serializedInputSpecs: ", str( serializedInputSpecs ) 
            print " ** InputSpecs: ", str( inputSpecs ) 
            self.idSpecs, self.fileSpecs, self.varSpecs, self.gridSpecs = [], [], [], []
            nInputs = inputSpecs.getNInputs() if inputSpecs else 0
            if nInputs: 
                print " _____________________ File Reader _____________________ "    
                for iInput in range( nInputs  ):
                    inputSpec = inputSpecs.getInput(  index=iInput )
                    print " ** InputSpec: ", str( inputSpec ) 
                    self.idSpecs.append( inputSpec[0] ) 
                    self.fileSpecs.append( inputSpec[1] )
                    self.varSpecs.append( inputSpec[2] )
                    if( not len(self.gridSpecs) and len(inputSpec[3]) ): 
                        self.gridSpecs = splitGridSpecs( inputSpec[3] )                   
                        print " ** Grid Specs: ", str( self.gridSpecs )  
                dsMapData = ';'.join( self.fileSpecs )   
                self.computeGridFromSpecs()
                print " ** ID Specs: ", str( self.idSpecs )
                print " ** File Specs: ", str( self.fileSpecs )
                print " ** Var Specs: ", str( self.varSpecs )            
                print " ** dsMapData: ", str( dsMapData )
                print " ** ROI: ", str( self.roi )
                print " ** zscale: ", str( zscale )
                print " ** decimation: ", str( decimation )
                print " ________________________________________________________ "   
                self.datasetMap = deserializeFileMap( getItem( dsMapData ) )
                dsKeys = self.datasetMap.keys()
                for iVar in range( len(self.varSpecs) ):
                    iDset = 0 if ( len( dsKeys ) == 1 ) else iVar
                    varSpec = "%s*%s" % ( dsKeys[ iDset ], self.varSpecs[iVar] )
                    if iVar == 0: self.ref_var = varSpec
                    self.datasetModule.setVariableRecord( "VariableName%d" % iVar, varSpec )
            else:    
                time_range = self.getInputValue( "timeRange"  )
                self.timeRange =[ int(time_range[0]), int(time_range[1]), float(time_range[2]), float(time_range[3])  ] if time_range else None
                roi_data = self.getInputValue( "roi" )
                self.roi = [ float(sroi) for sroi in roi_data ] if roi_data else None
                dsMapData = self.getInputValue( "datasets" ) 
                self.datasetMap = deserializeFileMap( getItem( dsMapData ) )
                self.ref_var = self.getInputValue( "grid"  )
            
            self.datasetModule.setBounds( self.timeRange, self.roi, zscale, decimation ) 
            self.datasetModule.setCells( inputSpecs.cells )
      
            if self.datasetMap:             
                for datasetId in self.datasetMap:
                    relFilePath = self.datasetMap[ datasetId ]
                    if relFilePath.strip():
                        self.datasetModule.addDatasetRecord( datasetId, relFilePath )
    #                print " - addDatasetRecord: ", str( datasetId ), str( cdmsFile )
            self.setParameter( "timeRange" , self.timeRange )
            self.setParameter( "roi", self.roi )
            self.datasetModule.timeRange = self.timeRange
            self.datasetModule.setReferenceVariable( self.ref_var )
            if inputSpecs: self.persistDatasetParameters() 
            self.setResult( 'dataset', self.datasetModule )
            print " ......  Start Workflow, dsid=%s, zscale = %.2f ......  " % ( self.datasetModule.getDsetId(), zscale )

    def persistDatasetParameters( self ):
        parmRecList = []
        parmRecList.append( ( 'datasets', [ serializeStrMap(self.datasetMap), ] ), )
        if self.ref_var:    parmRecList.append( ( 'grid', [ self.ref_var, ] ), )
        if self.timeRange:  parmRecList.append( ( 'timeRange' , [ self.timeRange[0], self.timeRange[1], self.timeRange[2], self.timeRange[3] ]  ), )      
        if self.roi:        parmRecList.append( ( 'roi' , [ self.roi[0], self.roi[1], self.roi[2], self.roi[3] ]  ), )                  
        self.persistParameterList( parmRecList ) 

    def dvUpdate( self, **args ):
        pass     
        
    def computeMetadata( self ):
        metadata = PersistentVisualizationModule.computeMetadata( self )
        metadata[ 'vars2d' ] =  self.datasetModule.getVariableList( 2 )
        metadata[ 'vars3d' ] =  self.datasetModule.getVariableList( 3)
        metadata[ 'datasetId' ] = self.datasetId
        if self.fileSpecs: metadata[ 'fileSpecs' ] = self.fileSpecs
        if self.varSpecs: metadata[ 'varSpecs' ] = self.varSpecs
        if self.gridSpecs: metadata[ 'gridSpecs' ] = self.gridSpecs
        return metadata

#class CDMS_VCDATInterface(WorkflowModule):
#    
#    PersistentModuleClass = PM_CDMS_VCDATInterface
#    
#    def __init__( self, **args ):
#        WorkflowModule.__init__(self, **args)     
      
                      
class CDMS_FileReader(WorkflowModule):
    
    PersistentModuleClass = PM_CDMS_FileReader
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args)     
        
        
class VCDATInterfaceWidget(DV3DConfigurationWidget):   

    def __init__(self, module, controller, parent=None):
        DV3DConfigurationWidget.__init__(self, module, controller, 'VCDAT Interface Configuration', parent)
        self.zscale = 4.0
                
    def initZScale( self ):
         self.selectZScaleLineEdit.setText( "%.2f" % self.zscale )
#        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 
                                                                       
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """        

        zscaleTab = QWidget()  
        self.tabbedWidget.addTab( zscaleTab, 'vertScale' ) 
        self.tabbedWidget.setCurrentWidget(zscaleTab)
        zscaleTab_layout = QVBoxLayout()
        zscaleTab.setLayout( zscaleTab_layout ) 
        
        self.zscaleLabel = QLabel( "Vertical Scale:"  )
        zscaleTab_layout.addWidget(self.zscaleLabel)
        
        self.selectZScaleLineEdit =  QLineEdit( self.parent() )
        self.selectZScaleLineEdit.setValidator( QDoubleValidator(self) )
        self.selectZScaleLineEdit.setText( "%.2f" % self.zscale)
        self.connect( self.selectZScaleLineEdit, SIGNAL('editingFinished()'), self.stateChanged )
        
        zscaleTab_layout.addWidget( self.selectZScaleLineEdit )

    def updateController(self, controller=None):
        parmRecList = []
        parmRecList.append( ( 'zscale' , [ self.zscale ]  ), )  
        self.persistParameterList( parmRecList ) 
        self.stateChanged(False)
           
    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.zscale = float( self.selectZScaleLineEdit.text() )
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
                          
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
        self.timeRange = None
        self.nTS = 0
        self.variableList = ( [], [] )
        self.lonRangeType = 1
        self.fullRoi = [ [ 0.0, -90.0, 360.0, 90.0 ], [ -180.0, -90.0, 180.0, 90.0 ] ]
        self.decimation = DefaultDecimation
        self.roi = self.fullRoi[ self.lonRangeType ]
        self.zscale = 1.0
        self.relativeStartTime = None
        self.relativeTimeStep = None
        self.currentDatasetId = None
        self.datasetChanged = False
        self.datasets = {}
        self.grids = []
        self.gridCombo = None
        self.selectedGrid = None
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Dataset Configuration', parent)
        self.metadataViewer = MetadataViewerDialog( self )
        if self.pmod: self.pmod.clearNewConfiguration()
        if self.currentDatasetId: self.registerCurrentDataset( id=self.currentDatasetId )
        self.stateChanged( False )
        
    def initTimeRange( self ):
        timeRangeParams =   self.pmod.getInputValue( "timeRange"  ) # getFunctionParmStrValues( self.module, "timeRange"  )
        tRange = [ int(timeRangeParams[0]), int(timeRangeParams[1]) ] if timeRangeParams else None
        if tRange:
            for iParam in range( 2, len(timeRangeParams) ): tRange.append( float(timeRangeParams[iParam] ) ) 
            self.timeRange = tRange
            self.relativeStartTime = cdtime.reltime( float(tRange[2]), ReferenceTimeUnits)
            self.relativeTimeStep = float(tRange[3])
            self.startCombo.setCurrentIndex( self.timeRange[0] ) 
            self.startIndexEdit.setText( str( self.timeRange[0] ) )  
            self.endCombo.setCurrentIndex( self.timeRange[1] ) 
            self.endIndexEdit.setText( str( self.timeRange[1] ) )  

    def initRoi( self ):
        roiParams = self.pmod.getInputValue( "roi" ) #getFunctionParmStrValues( self.module, "roi"  )self.getParameterId()
        if roiParams:  self.roi = [ float(rois) for rois in roiParams ]
        else: self.roi = self.fullRoi[ self.lonRangeType ] 
        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 

    def initDecimation( self ):
        decimationParams = self.pmod.getInputValue( "decimation" ) #getFunctionParmStrValues( self.module, "roi"  )self.getParameterId()
        if decimationParams:  self.decimation = [ int(dec) for dec in decimationParams ]
        else: self.decimation = DefaultDecimation
        self.clientDecimationCombo.setCurrentIndex( self.decimation[0] ) 
        self.serverDecimationCombo.setCurrentIndex( self.decimation[1] ) 
        
    def initZScale( self ):
        zsParams = self.pmod.getInputValue( "zscale" )
        if zsParams:  self.zscale = float( getItem( zsParams ) )
        self.selectZScaleLineEdit.setText( "%.2f" % self.zscale)
#        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 
                
    def getParameters( self, module ):
        global DataSetVersion
        datasetMapParams = getFunctionParmStrValues( module, "datasets" )
        if datasetMapParams: self.datasets = deserializeFileMap( datasetMapParams[0] )
        datasetParams = getFunctionParmStrValues( module, "datasetId" )
        if datasetParams: 
            gridParams = getFunctionParmStrValues( module, "grid" )
            if gridParams:  self.selectedGrid = gridParams[0]
            self.currentDatasetId = datasetParams[0] 
            self.pmod.datasetId = self.currentDatasetId
            if( len(datasetParams) > 1 ): DataSetVersion = int( datasetParams[1] )

    def setDatasetProperties(self, dataset, cdmsFile ):
        self.currentDatasetId = dataset.id  
        self.pmod.datasetId = dataset.id 
        relFilePath = getHomeRelativePath( cdmsFile )
        self.datasets[ self.currentDatasetId ] = relFilePath  
        self.metadataViewer.setDatasetProperties( dataset, cdmsFile ) 
        
    def registerCurrentDataset( self, **args ):
        id = args.get( 'id', None ) 
        relFilePath = args.get( 'file', None )
        cdmsFile = None
        if self.pmod: self.pmod.setNewConfiguration( **args )
        if id: 
            self.currentDatasetId = str( id )
            relFilePath = self.datasets.get( self.currentDatasetId, None ) 
        try:
            cdmsFile = getFullPath( relFilePath )
            dataset = cdms2.open( cdmsFile ) 
            self.setDatasetProperties( dataset, cdmsFile )
            self.updateGrids( dataset )           
            self.timeRange = None
            self.nTS = 0
            if not self.updateTimeValues( dataset ):
                self.initTimeRange()
            self.initRoi()
            self.initDecimation()
            self.initZScale()
            if self.pmod: 
                self.pmod.clearNewConfiguration()
            dataset.close()
        except Exception, err:
            print>>sys.stderr, " Error initializing dataset '%s': %s " % ( str(relFilePath), str( err ) )
        return cdmsFile
         
    def selectFile(self):
        dataset = None
        file = QFileDialog.getOpenFileName( self, "Find Dataset", os.path.expanduser('~'), "CDMS Files (*.xml *.cdms *.nc *.nc4)") 
        if file <> None:
            cdmsFile = str( file ).strip() 
            if len( cdmsFile ) > 0:                             
                try:
                    dataset = cdms2.open( cdmsFile )
                    relFilePath = getHomeRelativePath( cdmsFile )
                    self.currentDatasetId = dataset.id 
                    self.datasets[ self.currentDatasetId ] = relFilePath  
                    self.dsCombo.insertItem( 0, QString( self.currentDatasetId ) )  
                    self.dsCombo.setCurrentIndex( 0 )
                    self.pmod.datasetId = '*'.join( self.datasets.keys() )
                    dataset.close()
                except:
                    print "Error opening dataset: %s" % str(cdmsFile)
                self.registerCurrentDataset( file=cdmsFile, newLayerConfig=True ) 
                global DataSetVersion 
                DataSetVersion = DataSetVersion + 1 
                self.stateChanged()
                self.datasetChanged = True
        
    def viewMetadata(self):
        self.metadataViewer.show()
        
    def removeDataset(self):
        del self.datasets[ str(self.dsCombo.currentText()) ]
        self.dsCombo.removeItem( self.dsCombo.currentIndex() )
        if self.dsCombo.count() == 0: self.metadataViewer.clear() 
        else:
            self.dsCombo.setCurrentIndex(0) 
            self.pmod.datasetId = '*'.join( self.datasets.keys() )                         
            self.registerCurrentDataset( id=self.dsCombo.currentText() )
        global DataSetVersion 
        DataSetVersion = DataSetVersion + 1 
            
    def updateGrids( self, dataset ):
        self.grids = []
        self.variableList = ( [], [] )
        try:
            for var in dataset.variables:
                vardata = dataset[var]
                var_ndim = getVarNDim( vardata )
                if (var_ndim) == 2 or (var_ndim == 3):
                    self.variableList[var_ndim-2].append( '%s*%s' % ( dataset.id, var ) )
#            if not self.selectedGrid:
#                if len( self.variableList[1] ): self.selectedGrid = self.variableList[1][0]
#                elif len( self.variableList[0] ): self.selectedGrid = self.variableList[0][0]
            for grid_id in dataset.grids:
                self.grids.append( '*'.join( [ dataset.id, grid_id ] ) )
                grid = dataset.grids[ grid_id ]
                lonAxis = grid.getLongitude()
                if lonAxis:
                    lonVals = lonAxis.getValue()
                    if lonVals[0] < 0.0: self.lonRangeType = 1
        except Exception, err:
            print>>sys.stderr, " Error opening dataset: ", str( err ) 
                
        self.updateRefVarSelection() 

    def updateMultiGrids(self):
        self.grids = []
        self.variableList = ( [], [] )
        for datasetId in self.datasets:
            if datasetId:
                relFilePath = self.datasets[ datasetId ]
                cdmsFile = getFullPath( relFilePath )
                try:
                    dataset = cdms2.open( cdmsFile ) 
                    for var in dataset.variables:
                        vardata = dataset[var]
                        var_ndim = getVarNDim( vardata )
                        if (var_ndim) == 2 or (var_ndim == 3):
                            self.variableList[var_ndim-2].append( '%s*%s' % ( datasetId, var ) )
        #            if not self.selectedGrid:
        #                if len( self.variableList[1] ): self.selectedGrid = self.variableList[1][0]
        #                elif len( self.variableList[0] ): self.selectedGrid = self.variableList[0][0]
                    for grid_id in dataset.grids:
                        self.grids.append( '*'.join( [ datasetId, grid_id ] ) )
                        grid = dataset.grids[ grid_id ]
                        lonAxis = grid.getLongitude()
                        if lonAxis:
                            lonVals = lonAxis.getValue()
                            if lonVals[0] < 0.0: self.lonRangeType = 1
                    dataset.close() 
                except Exception, err:
                    print>>sys.stderr, " Error opening dataset file %s: %s " % ( cdmsFile, str( err ) )
                
        self.updateRefVarSelection() 

    def updateTimeValues( self, dataset ):
        self.startCombo.clear()
        self.endCombo.clear()
        if dataset:
            time_values, dt, time_units = getRelativeTimeValues ( dataset )
            if time_values:
                iStart = 0
                iEnd = ( len( time_values ) - 1 )                            
                self.nTS = len(time_values) if time_values else 0
                self.relativeTimeStep = dt
                self.relativeTimeUnits = time_units
                self.relativeStartTime = time_values[ iStart ]
                for iT in range( iStart, iEnd+1 ):
                    time_value = time_values[ iT ].tocomp()
                    tval = str( time_value ) 
                    self.startCombo.addItem ( tval )
                    self.endCombo.addItem ( tval )
                self.timeRange = [ 0, iEnd-iStart ]
                self.startCombo.setCurrentIndex( self.timeRange[0] ) 
                self.startIndexEdit.setText( str( self.timeRange[0] ) )  
                self.endCombo.setCurrentIndex( self.timeRange[1] ) 
                self.endIndexEdit.setText( str( self.timeRange[1] ) ) 
                return True
        return False 
         
    def updateMultiTimeValues( self):
        self.startCombo.clear()
        self.endCombo.clear()
        current_time_values = None
        current_dt = 100000.0
        current_dsetid = None
        current_units = None
        dataset_list = []
        time_values_list = []
        for datasetId in self.datasets:
            if datasetId:
                relFilePath = self.datasets[ datasetId ]
                cdmsFile = getFullPath( relFilePath )
                try:
                    dataset = cdms2.open( cdmsFile ) 
                    dataset_list.append( dataset )
                except Exception, err:
                    print>>sys.stderr, " Error opening dataset file %s: %s " % ( cdmsFile, str( err ) )
        for dataset in dataset_list:
            time_values, dt, time_units = getRelativeTimeValues ( dataset )
            time_values_list.append( (dataset.id, time_values) )
            if time_values and ( dt < current_dt ):
                current_time_values = time_values
                current_dt = dt
                current_units = time_units
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
            self.relativeTimeUnits = current_units
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
        self.registerCurrentDataset( id=str( self.dsCombo.currentText() ), newLayerConfig=True )
        self.updateController()
                                                       
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        """        
        datasetTab = QWidget()        
        self.tabbedWidget.addTab( datasetTab, 'dataset' )                 
        self.tabbedWidget.setCurrentWidget(datasetTab)
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
        
        timeTab = QWidget() 
#        timeTab.setFocusPolicy( Qt.NoFocus ) 
        self.tabbedWidget.addTab( timeTab, 'time' )                 
        self.tabbedWidget.setCurrentWidget(timeTab)
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
        self.tabbedWidget.setCurrentWidget(roiTab)
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
        self.tabbedWidget.setCurrentWidget(zscaleTab)
        zscaleTab_layout = QVBoxLayout()
        zscaleTab.setLayout( zscaleTab_layout ) 
        
        self.zscaleLabel = QLabel( "Vertical Scale:"  )
        zscaleTab_layout.addWidget(self.zscaleLabel)
        
        self.selectZScaleLineEdit =  QLineEdit( self.parent() )
        self.selectZScaleLineEdit.setValidator( QDoubleValidator(self) )
        self.selectZScaleLineEdit.setText( "%.2f" % self.zscale)
        self.connect( self.selectZScaleLineEdit, SIGNAL('editingFinished()'), self.stateChanged )
        
        zscaleTab_layout.addWidget( self.selectZScaleLineEdit )

        gridTab = QWidget()  
        self.tabbedWidget.addTab( gridTab, 'grid' ) 
        self.tabbedWidget.setCurrentWidget(gridTab)
        gridTab_layout = QVBoxLayout()
        gridTab.setLayout( gridTab_layout ) 

        grid_selection_layout = QHBoxLayout()
        grid_selection_label = QLabel( "Grid Reference Variable:" )
        grid_selection_layout.addWidget( grid_selection_label ) 

        self.gridCombo =  QComboBox ( self.parent() )
        grid_selection_label.setBuddy( self.gridCombo )
        self.gridCombo.setMaximumHeight( 30 )
        grid_selection_layout.addWidget( self.gridCombo  )
        self.updateRefVarSelection()
        self.connect( self.gridCombo, SIGNAL("currentIndexChanged(QString)"), self.gridChanged ) 
        gridTab_layout.addLayout(grid_selection_layout)
         
        client_decimation_layout = QHBoxLayout()        
        client_decimation_label = QLabel( "Client Decimation:"  )
        client_decimation_layout.addWidget( client_decimation_label ) 
        self.clientDecimationCombo =  QComboBox ( self.parent() )
        client_decimation_label.setBuddy( self.clientDecimationCombo )
        self.clientDecimationCombo.setMaximumHeight( 30 )
        client_decimation_layout.addWidget( self.clientDecimationCombo  )
        gridTab_layout.addLayout(client_decimation_layout)

        server_decimation_layout = QHBoxLayout()        
        server_decimation_label = QLabel( "Server Decimation:"  )
        server_decimation_layout.addWidget( server_decimation_label ) 
        self.serverDecimationCombo =  QComboBox ( self.parent() )
        server_decimation_label.setBuddy( self.serverDecimationCombo )
        self.serverDecimationCombo.setMaximumHeight( 30 )
        server_decimation_layout.addWidget( self.serverDecimationCombo  )
        gridTab_layout.addLayout(server_decimation_layout)
        
        for iD in range( 0, 11 ):
            self.clientDecimationCombo.addItem ( str(iD) )
            self.serverDecimationCombo.addItem ( str(iD) )
                                      
    def updateRefVarSelection( self ):
        if self.gridCombo == None: return 
        updateSelectedGrid = True
        item = None
        for iItem in range( self.gridCombo.count() ):
            self.gridCombo.removeItem ( iItem )
        for var in self.variableList[0]: 
            item = getVariableSelectionLabel( var, 2 )
            if updateSelectedGrid and (item == self.selectedGrid): updateSelectedGrid = False
            self.gridCombo.addItem( item )
        for var in self.variableList[1]:
            item = getVariableSelectionLabel( var, 3 )
            if updateSelectedGrid and (item == self.selectedGrid): updateSelectedGrid = False
            self.gridCombo.addItem( item )
        if updateSelectedGrid: 
            self.selectedGrid = item
        if self.selectedGrid:
            iSelection = self.gridCombo.findText( self.selectedGrid )
            self.gridCombo.setCurrentIndex( iSelection )

    def gridChanged( self, value ):
        self.selectedGrid = str( self.gridCombo.currentText() )
    
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
        roi0 = self.fullRoi[ self.lonRangeType ]
        self.roiSelector.setROI( roi0 )        
        self.roiLabel.setText( "ROI: %s" % str( roi0 )  ) 
        for i in range( len( self.roi ) ): self.roi[i] = roi0[i] 
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
        parmRecList.append( ( 'grid', [ self.selectedGrid, ] ), )
        try: parmRecList.append( ( 'timeRange' , [ self.timeRange[0], self.timeRange[1], float(self.relativeStartTime.value), self.relativeTimeStep ]  ), )  
        except: pass     
        parmRecList.append( ( 'roi' , [ self.roi[0], self.roi[1], self.roi[2], self.roi[3] ]  ), )          
        parmRecList.append( ( 'zscale' , [ self.zscale ]  ), )  
        parmRecList.append( ( 'decimation' , self.decimation  ), )  
        fileInputSpecs = '' # '!'.join( [self.currentDatasetId, self.currentDatasetId, self.datasets[ self.currentDatasetId ] ] )       
        varInputSpecs = ''
        gridInputSpecs = ''
        cellInputSpecs = '' 
        executionSpecs = ';'.join( [ fileInputSpecs, varInputSpecs, gridInputSpecs, cellInputSpecs ] )
        parmRecList.append( ( 'executionSpecs' , [ executionSpecs, ]  ), )         
        self.persistParameterList( parmRecList ) 
        self.pmod.clearDataCache()
        self.stateChanged(False)
           
    def okTriggered(self, checked = False):
        
        try: 
            t0, t1 = self.startIndexEdit.text(), self.endIndexEdit.text()
            self.timeRange = [ int( str( t0 ) ), int( str( t1 ) ) ]
        except:  self.timeRange = [ 0, 0 ]
        try: self.zscale = float( self.selectZScaleLineEdit.text() )
        except: self.zscale = 1.0
        try: self.decimation = [  self.clientDecimationCombo.currentIndex(), self.serverDecimationCombo.currentIndex() ]
        except: self.decimation = DefaultDecimation
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

#    from packages.vtDV3D.Main import executeVistrail
#    optionsDict = {  'hw_role'  : 'none' }
#    try:
#        executeVistrail( options=optionsDict )
#    except Exception, err:
#        print " executeVistrail exception: %s " % str( err )

