'''
Created on Jan 27, 2011

@author: tpmaxwel
'''

'''
Created on Feb 18, 2010

@author: tpmaxwel

'''
import os, time, copy, sys, re, vtk
from netCDF4 import Dataset
from packages.vtDV3D.vtUtilities import *
import numpy as np
import numpy.ma as ma
localDebug = False

SCALARMAX = 256*256-1

module_data = {
    # axis names (will be overriden in ncvtk!)
    'time': r'^(time|Time|TIME|.*time|.*Time|.*TIME)',
    'elev' : r'^(elev|Elev|ELEV|.?lev|.?Lev|.?LEV|phalf|pfull)',
    'lat'  : r'^(.?la|.?La|.?LA|.?north)',
    'lon'  : r'^(.?lo|.?Lo|.?LO|.?east)',
}

def GetAxisName( variableList, type ): # type: time elev lat lon
    pattern = module_data[ type ]
    foundVar = None
    for varName in variableList:
        if re.match( pattern, varName ) and ( (foundVar == None) or (len(varName) < len(foundVar)) ):
            foundVar = varName
    return foundVar


class NetCDFDataWrapper:
    
    def __init__( self, fileName,  **args ):
        dataDir = args.pop( "dir", None )
        self.packagePath = os.path.dirname(__file__) 
        if dataDir == None:  dataDir = os.path.normpath( "%s/../../data" % self.packagePath )

        self.invertZ = args.pop( "invertZ", False )
        self.undef = args.pop( "undef", None )
        self.variableList = {}

        self.dataDir = dataDir
        self.inputFilePath = os.path.join( self.dataDir, fileName )
        self.reductionFactor = 1
        self.ROI = None
        self.hasData = False
        self.varName = args.pop( "var", None )
        if self.varName <> None: self.varName = self.varName.lower()
        self.zscale = 1.0
        self.currentDataArray = None  
        self.iTImeIndex = -1  
        self.ReadMetaData()          

    def GetCoordVars(self): 
        latvar = self.variableList[ self.latVarName ]
        lonvar = self.variableList[ self.lonVarName ]
        vertvar = self.variableList[ self.vertVarName ]
        vars = [ lonvar, latvar, vertvar ]
        return vars
    
    def GetDataBounds( self ):
        vars = self.GetCoordVars()
        bounds = []      
        for iv in range( len(vars) ):
            var = vars[iv]
            nv = len(var)
            minv = var[0][0] 
            maxv = var[nv-1][0] 
            dv = ( maxv - minv ) / (nv-1)
            bounds.append( minv )
            bounds.append( maxv + dv )          
        return bounds
    
    def GetCurrentVarName(self):
        return self.varName
    
    def GetShortImageData( self, varName, iTimeIndex, fieldData ):
        vtkdata = vtk.vtkUnsignedShortArray()
        SCALARMAX = vtkdata.GetDataTypeMax( vtkdata.GetDataType() )
        
        img = vtk.vtkImageData()
        img.SetScalarTypeToUnsignedShort()
        img.GetPointData().SetScalars(vtkdata)
        
        dataArray = self.GetDataArray( varName, iTimeIndex )

        dmin = dataArray.min()
        dmax = dataArray.max()
        scaledData = SCALARMAX * ( dataArray - dmin ) / ( dmax - dmin )

        usData = scaledData.astype(N.UInt16)
        vtkdata.SetNumberOfTuples(N.size(data))
        vtkdata.SetVoidArray( data, N.size(data), 1)
        vtkdata.Modified()
        self.enc_mdata = encodeToString( { 'bounds' : self.GetDataBounds() } ) 
        fieldData.AddArray( getStringDataArray( 'metadata',   [ self.enc_mdata ]  ) )
        fieldData.AddArray( getFloatDataArray(  'valueRange', self.dataRange ) )      
        
        return img
    
    def GetFloatImageData( self, varName, iTimeIndex, fieldData ):
        vtkdata = vtk.vtkFloatArray()
        
        img = vtk.vtkImageData()
        img.SetScalarTypeToFloat()
        img.GetPointData().SetScalars(vtkdata)
        
        dataArray, newVarData = self.GetDataArray( varName, iTimeIndex )
        print dir( dataArray )

        vtkdata.SetNumberOfTuples(np.size(dataArray))
        vtkdata.SetVoidArray( dataArray, np.size(dataArray), 1)
        vtkdata.Modified()
        self.enc_mdata = encodeToString( { 'bounds' : self.GetDataBounds() } ) 
        fieldData.AddArray( getStringDataArray( 'metadata',   [ self.enc_mdata ]  ) )
        fieldData.AddArray( getFloatDataArray(  'valueRange', self.dataRange ) )      
        
        return img

    def GetFloatVectorImageData( self, varNameList, iTimeIndex, fieldData ):
        vtkVectorData = vtk.vtkFloatArray()
        varNameListIter = iter( varNameList )
        nComponents = len(varNameList)
        vtkVectorData.SetNumberOfComponents( 3 )
        vtkVectorData.SetName('vectors')
        img = vtk.vtkImageData()
        
        dataArrays = []
        ntuples = 0
        for iComp in range( nComponents ):
            varName = varNameListIter.next()
            dataArray, newVarData = self.GetDataArray( varName, iTimeIndex )  
            dataArrays.append( dataArray )
            vtkdata = vtk.vtkFloatArray()
            if iComp == 0: 
                ntuples = np.size(dataArray)          
                vtkVectorData.SetNumberOfTuples( ntuples )
                img.SetOrigin(  self.grid_origin )
                img.SetSpacing( self.grid_spacing )
                img.SetExtent( self.ROIExtent[0], self.ROIExtent[1], self.ROIExtent[2], self.ROIExtent[3], self.ROIExtent[4], self.ROIExtent[5] )
                img.SetScalarTypeToFloat()
            vtkdata.SetNumberOfTuples( ntuples )
            vtkdata.SetVoidArray( dataArray, ntuples, 1)
            vtkVectorData.CopyComponent( iComp, vtkdata, 0 )
            
        for iComp in range( nComponents, 3 ):
            vtkVectorData.FillComponent ( iComp, 0.0 )
            
        cellData = img.GetCellData()            
#        cellData.SetScalars( vtkVectorData )        
        cellData.SetVectors( vtkVectorData )        
        print " ---- Image created, ncells: %d, npts: %d, ncomp: %d, ntup: %d " % ( img.GetNumberOfCells(), img.GetNumberOfPoints(), vtkVectorData.GetNumberOfComponents(), vtkVectorData.GetNumberOfTuples() )
        self.enc_mdata = encodeToString( { 'bounds' : self.GetDataBounds() } ) 
        fieldData.AddArray( getStringDataArray( 'metadata',   [ self.enc_mdata ]  ) )
#        fieldData.AddArray( getFloatDataArray(  'position',   self.grid_origin    ) ) 
        fieldData.AddArray( getFloatDataArray(  'valueRange', self.dataRange ) )      
        return img
    
    def GetDataArray( self, varName, iTimeIndex ):
        newVarData = ( varName <> self.varName ) or not self.hasData 
        newTimeData = ( iTimeIndex <> self.iTImeIndex )
        if newVarData:
            self.varName = varName.lower()
            self.Read()
        if newVarData or newTimeData:
            self.iTImeIndex = iTimeIndex
            try:
                self.dataArray = self._dataArray[:,:,:,iTimeIndex]
            except:
                return None, False, False
        return self.dataArray, newVarData, newTimeData

    def GetLevelValue( self, iLev ):
        iL = iLev / ( 1 + self.nInterpLayers )
        return self.vertvar[iL][0]

    def GetLevelUnits( self ):
        try:
            return  self.vertvar.units
        except:
            return ""
    
    def GetLatValue( self, iY ):
        return self.dataOffset[1] + (float(iY)/self.roishape[1])*self.dataRange[1]

    def GetLonValue( self, iX ):
        return self.dataOffset[0] + (float(iX)/self.roishape[0])*self.dataRange[0]
    
    def GetTimeIndexRange( self ):
        return [ 0, len(self.timeDim) * ( self.nInterpSteps + 1 ) ]
        
    def GetSize( self, shape ):
        size = 1
        for i in range(len(shape)):
            size *= shape[i]
        return size
    
    def GetDefaultVarName(self):
        varlist = self.variableList 
        maxSize = 0
        maxVarName = None
        for varName in varlist.keys():
            var = varlist[varName]
            size = self.GetSize( var.shape )
            if size > maxSize:
                maxSize = size
                maxVarName = varName
        return maxVarName
            
    def isCoordVar( self, varName ):  
        dimNameList = [ self.latVarName, self.lonVarName, self.vertVarName, self.timeVarName ]
        for dimName in dimNameList: 
            if varName.find( dimName ) >= 0:
                return True
        return False
                    
    def GetFileVariableMetadata(self):
        varlist = self.variableList 
        traitstVarList = []
        for varName in varlist.keys():
            if not self.isCoordVar( varName ):
                var = varlist[varName]
                if localDebug: 
                    print " var: %s, shape: %s " % ( varName, str(var.shape) )
                    print var.ncattrs()
                long_name = varName
                units = ''
                try: long_name = var.long_name
                except: pass
                try: units = var.units
                except: pass
                traitsVar = Variable( name=varName,  shape=var.shape[0:5],  long_name=long_name,  dimensions=str(var.dimensions), units = units )
                traitstVarList.append( traitsVar )
        return traitstVarList
    
    def GetSlice(self, iTimeIndx, **args ):
        dataArray, newVarData = self.GetDataArray( self.varName, iTimeIndx )
        slice = None
        if 'x' in args:
            iS = args['x']
            slice = dataArray[iS,:,:]
             
        if 'y' in args:
            iS = args['y']
            slice = dataArray[:,iS,:]
                      
        if 'z' in args:
            iS = args['z'] + self.dimmd.zi[0]
            slice = dataArray[:,:,iS]  
                     
        return slice
    
    def ReadMetaData(self):
        print "Reading file %s" % ( self.inputFilePath )
        self.inputDataset = Dataset( self.inputFilePath, 'r' )
        for vName in self.inputDataset.variables.keys():
           self.variableList[vName.lower()]= self.inputDataset.variables[vName]
        self.latVarName = GetAxisName( self.variableList, 'lat' )
        self.lonVarName = GetAxisName( self.variableList, 'lon' )
        self.vertVarName = GetAxisName( self.variableList, 'elev' )
        self.timeVarName = GetAxisName( self.variableList, 'time' )
        self.timeDim = None if ( self.timeVarName == None ) else self.inputDataset.dimensions[ self.timeVarName ]
        
    def GetInitialTimeIndex( self ):
        return 0
         
    def Read( self, **args ):
#        self.dsetname = self.runConfig.get( 'input', 'Dataset' )
#        cfgDir = os.path.dirname( self.runConfigFile )  
#        datasetConfigFile =  os.path.expanduser( os.path.join( cfgDir, 'datasets.cfg' ) )
#        self.datasetConfig = ConfigParser.RawConfigParser()
#        self.datasetConfig.read( datasetConfigFile )  
#                
#        inputDatasetDir = self.datasetConfig.get( self.dsetname, 'DataDir' )       
#        self.latVarName = self.datasetConfig.get( self.dsetname, 'LatVarName' )
#        self.lonVarName = self.datasetConfig.get( self.dsetname, 'LonVarName' )
#        self.vertVarName = self.datasetConfig.get( self.dsetname, 'VertVarName' )
#        self.timeVarName = self.datasetConfig.get( self.dsetname, 'TimeVarName' ) 


#        inputFileName = self.runConfig.get( 'input', 'Datafile' )
#        inputFilePath = os.path.join(inputDatasetDir,inputFileName)
        self.zscale = args.pop( "zscale", self.zscale )
 
        if self.varName == None:
            self.varName = self.GetDefaultVarName()   
        try:     
            var = self.variableList[ self.varName ]
        except:
            print >> sys.stderr, "\n\n Error reading var %s from variable list: %s\n" % ( self.varName, str(self.variableList.keys() ) )
            return
#        self.missingValue = var.fmissing_value

        inputDataBounds = self.GetDataBounds()
        shapeT = np.array( var.shape ) 
        self.shape = np.ndarray( [ len(shapeT) ], dtype=int  )
        self.shape[::1] = shapeT[::-1]
        self.nTimeFrames = 1 if len( self.shape ) < 4 else self.shape[3]
        self.vertvar = self.variableList[ self.vertVarName ]
        
        self.ROIExtent = np.array( [ 0, self.shape[0], 0, self.shape[1], 0, self.shape[2] ] )
        self.dataRange = np.array([ inputDataBounds[1]-inputDataBounds[0], inputDataBounds[3]-inputDataBounds[2], inputDataBounds[5]-inputDataBounds[4] ])
        self.dataOffset = np.array([ inputDataBounds[0], inputDataBounds[2], inputDataBounds[4] ])
        offset = [ 180, 90 ]
        if self.ROI != None:
            for iD in range(4):
                self.ROI[iD] = self.ROI[iD] + offset[iD/2]
            for iD in range(0,6,2):
                if self.ROI[iD] < inputDataBounds[iD]: self.ROI[iD] = inputDataBounds[iD]
            for iD1 in range(1,6,2):
                if self.ROI[iD1] > inputDataBounds[iD1]: self.ROI[iD1] = inputDataBounds[iD1]
            for i in range(6):
                i0 = i/2
                ROIFraction =  ( self.ROI[i] - self.dataOffset[i0] ) / self.dataRange[i0]
                self.ROIExtent[i] = int( ROIFraction * self.shape[ i0 ] )
    
        roishapeT = list( var.shape )  
        roishapeT[-1] =  self.ROIExtent[1]-self.ROIExtent[0]      
        roishapeT[-2] =  self.ROIExtent[3]-self.ROIExtent[2]      
        roishapeT[-3] =  self.ROIExtent[5]-self.ROIExtent[4]  
                
        self.roishape = np.ndarray( [ len(roishapeT) ], dtype=int  )
        self.roishape = roishapeT[::-1]
            
#        tempvar = np.zeros( roishapeT, dtype=var.dtype )
       
        subvar = var[ ..., self.ROIExtent[4]:self.ROIExtent[5], self.ROIExtent[2]:self.ROIExtent[3], self.ROIExtent[0]:self.ROIExtent[1]  ]
#        tempvar = subvar
        
#        tempvar = ma.masked_array( subvar )
#        undef_value_mask = tempvar == self.missingValue
#        tempvar.mask = undef_value_mask
        tempvar = ma.masked_values( subvar, self.undef )
#        undef_value_mask = tempvar == self.missingValue
#        tempvar.mask = undef_value_mask
        
        tempvar = tempvar.transpose() 
        
        newvar =  tempvar 
        if self.reductionFactor > 1:
            newshape = np.array( self.roishape )
            for i in range(-2,0):
                self.shape[i] /= self.reductionFactor
                newshape[i] /= self.reductionFactor
            newvar = ma.zeros( newshape, dtype=var.dtype )
            bounds = newshape * self.reductionFactor
            for ix in range(0,self.reductionFactor):
                for iy in range(0,self.reductionFactor):
                    subarray = tempvar[ ix:bounds[0]:self.reductionFactor, iy:bounds[1]:self.reductionFactor, ... ]
                    newvar[...] +=  subarray
            newvar /= ( self.reductionFactor * self.reductionFactor )   
 
        print "ReadNetCDFVariable '" + self.varName + "', roi shape = " + str(self.roishape) + ", data var shape = " + str(var.shape)+ ", new var shape = " + str(newvar.shape) + ", ROI Extent = " + str(self.ROIExtent) + ", reductionFactor = " + str(self.reductionFactor) + ", InvertZ = " + str(self.invertZ)
        
        if self.invertZ:
            self._dataArray = newvar.copy()
            self._dataArray = newvar[...,::-1,:] 
            del newvar
        else:
            self._dataArray = newvar
            
        range_min = self._dataArray.min()
        range_max = self._dataArray.max() 
        self.timeseries_range = [ range_min, range_max ]
        self.grid_origin = self.GetDataCornerPosition()
        self.grid_spacing = self.GetDataRangeScaling( self.zscale )           
        self.hasData = True

    def GetExpandedLevelIndex(self, iLev ):
        return iLev * ( 1 + self.nInterpLayers )

    def GetDataRangeScaling( self, zscale ):
        sscale = np.array( [ self.dataRange[0]/self.shape[0], self.dataRange[1]/self.shape[1],  zscale ] )
        return sscale
    
    def GetDataRange( self ):
        return self.dataRange
    
    def GetDataCornerPosition( self ):
        pos = np.array( [ self.dataOffset[0], self.dataOffset[1],  0.0 ] )
        return pos
                
    def ImportTimeSeries( self, varName, timeSeries, **args ):
        self.zscale = args.pop( "zscale", 1.0 )
        start = time.time()   
        fillval = args.pop( "fill", 0.0 )
        scalar_nbytes = args.pop( "nbytes", 2 )
        timestep = args.pop( "timestep", -1 )
        self.nInterpLayers = args.pop( "interpLayers", 0 )
        timeSeries.SetSeriesRange( args.pop( "scaling_range", None ) )
        assert ((scalar_nbytes == 1) or (scalar_nbytes == 2)), "Error, illegal scalar byte size: %d" % scalar_nbytes
        scalar_dtype = np.ushort
        if scalar_nbytes == 2:
            self._max_scalar_value = 65536.0
        elif scalar_nbytes == 1:
            self._max_scalar_value = 256.0 
            scalar_dtype = np.ubyte
        else:
            scalar_dtype = np.float
            f = np.finfo(float) 
            self._max_scalar_value = f.max
        self._range = [ 0.0, self._max_scalar_value ] 

        time_range = self.GetTimeIndexRange()
        prevDataArray = None
        iTStep = 0
        for it in range( time_range[0], time_range[1] ):
            if ( timestep < 0 ) or ( timestep == it ):
                dataArray, newVarData = self.GetDataArray( varName, it )
                if timeSeries.uniformScaling:
                    range_min = timeSeries.seriesRange[0]
                    range_max = timeSeries.seriesRange[1]
                else:               
                    range_min = dataArray.min()
                    range_max = dataArray.max()
                dataArray.fill_value = fillval
                shift = -range_min
                scale = self._max_scalar_value / ( range_max - range_min )    
                t0 = time.time()
                newDataArray = dataArray
                if scalar_nbytes < 4:
                    rescaledDataArray = ( ( dataArray + shift ) * scale ) + 1
                    rescaledDataArray[ dataArray > range_max ] = self._max_scalar_value
                    rescaledDataArray[ dataArray < range_min ] = 0
                    newDataArray = rescaledDataArray.astype(scalar_dtype) 
                if self.nInterpLayers > 0:
                    layerExpansionFactor = (1+self.nInterpLayers)
                    newshape = [ newDataArray.shape[0], newDataArray.shape[1], newDataArray.shape[2]*layerExpansionFactor ]
                    expandedDataArray = ma.array( np.ndarray( shape=newshape, dtype=scalar_dtype ) )
                    currentSlice = newSlice = None
                    for iz in range( newDataArray.shape[2] ):
                        newSlice = newDataArray[ :,:,iz ]
                        if iz > 0:
                            iz0 = (iz-1)*layerExpansionFactor + 1
                            for ie in range( self.nInterpLayers ):
                                s = float(ie+1)/layerExpansionFactor
                                interpSlice = (1-s)*currentSlice + s*newSlice
#                                    print " -- IL%d: %d " % ( ie, interpSlice[ testPoint[0], testPoint[1] ] )
                                expandedDataArray[ :, :, iz0+ie ] = interpSlice.astype(scalar_dtype) 
                        iS = iz*layerExpansionFactor
#                            print "     L%d: %d " % ( iS, newSlice[ testPoint[0], testPoint[1] ] )
                        expandedDataArray[ :, :, iS ] = newSlice
                        currentSlice = newSlice
                    del newDataArray
                    newDataArray = expandedDataArray
                if (self.nInterpSteps > 0) and not (prevDataArray is None):
                    for iIS in range(self.nInterpSteps):
                        s = float(iIS+1)/(self.nInterpSteps+1)
                        interpDataArray = ma.array( (1.0-s)*prevDataArray )
                        interpDataArray += s*newDataArray
#                        print " -- -- IS%d: %f %f " % ( iIS, interpDataArray[ testPoint[0], testPoint[1], 10 ], interpDataArray[ testPoint[0], testPoint[1], 20 ] )
                        tField = TimeStepField( interpDataArray.astype(scalar_dtype), ( range_min, range_max ) ) 
                        timeSeries.AddField( iTStep, tField )
                        iTStep = iTStep+1 
                tField = TimeStepField( newDataArray, ( range_min, range_max ) ) 
                prevDataArray = newDataArray
#                print " --- --- Rescale time: %f sec." % (time.time()-t0)
                print "Add timestep %d" % iTStep
                timeSeries.AddField( iTStep, tField ) 
                iTStep = iTStep+1 
        elapsed = time.time() - start
        print " --- --- Timeseries import time: %f sec." % elapsed
        sys.stdout.flush()
                
if __name__ == '__main__':   
    dataFile = "yotc_UV_1.nc"
    undefVal = -999000000.0
    invertZVal = False
    NCDR = NetCDFDataWrapper( dataFile, invertZ=invertZVal, undef=undefVal)  
    wind = NCDR.GetFloatVectorImageData( [ "u", "v" ],  0 )
    pass  
