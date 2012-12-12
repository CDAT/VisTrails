
# Import system libraries
import sys, os, time

# CDAT
import cdms2, cdtime, cdutil, MV2

# VTK
import vtk

# Others
import numpy

class PVCDMSReader():
    def __init__(self):
        self.grid_bounds = None
        self.zscale = 1
        self.output_type = None
        self.lon = None
        self.lat = None
        self.lev = None
        self.time = None
        pass
    
    def isLevelAxis(self, axis):
        if axis.isLevel(): return True
        # @note: What's so special about isobaric?
        if ( axis.id == 'isobaric' ): 
            axis.designateLevel(1)
            return True
        return False
    
    def getCoordType(self, axis):
        icoord = -2
        if axis.isLongitude():
            self.lon = axis
            icoord  = 0
        if axis.isLatitude():
            self.lat = axis
            icoord  = 1
        if self.isLevelAxis(axis):
            self.lev = axis
            icoord  = 2
        # @todo: Not sure if this is needed here
        if axis.isTime():
            self.time = axis
            icoord  = 2
        return icoord
    
    def getAxisValues( self, axis, roi ):
        values = axis.getValue()
        bounds = None
        if roi:
            if   axis.isLongitude():  bounds = [ roi[0], roi[2] ]
            elif axis.isLatitude():   bounds = [ roi[1], roi[3] ] 
        if bounds:
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
    
    def newList( self, size, init_value ):
        return [ init_value for i in range(size) ]       
    
    def get_grid_specs(self, var, roi, zscale):        
        gridOrigin = self.newList( 3, 0.0 )
        outputOrigin = self.newList( 3, 0.0 )
        gridBounds = self.newList( 6, 0.0 )
        gridSpacing = self.newList( 3, 1.0 )
        gridExtent = self.newList( 6, 0 )
        outputExtent = self.newList( 6, 0 )
        gridShape = self.newList( 3, 0 )
        gridSize = 1        
        self.lev = var.getLevel()
        axis_list = var.getAxisList()
        for axis in axis_list:
            size = len( axis )
            iCoord = self.getCoordType( axis )
            roiBounds, values = self.getAxisValues( axis, roi )
            if iCoord >= 0:
                iCoord2 = 2*iCoord
                gridShape[ iCoord ] = size
                gridSize = gridSize * size
                outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] = size-1                    
                if iCoord < 2:
                    lonOffset = 0.0 #360.0 if ( ( iCoord == 0 ) and ( roiBounds[0] < -180.0 ) ) else 0.0
                    outputOrigin[ iCoord ] = gridOrigin[ iCoord ] = values[0] + lonOffset
                    spacing = (values[size-1] - values[0])/(size-1)
                    if roiBounds:
                        if ( roiBounds[1] < 0.0 ) and  ( roiBounds[0] >= 0.0 ): roiBounds[1] = roiBounds[1] + 360.0
                        gridExtent[ iCoord2 ] = int( round( ( roiBounds[0] - values[0] )  / spacing ) )                
                        gridExtent[ iCoord2+1 ] = int( round( ( roiBounds[1] - values[0] )  / spacing ) )
                        if gridExtent[ iCoord2 ] > gridExtent[ iCoord2+1 ]:
                            geTmp = gridExtent[ iCoord2+1 ]
                            gridExtent[ iCoord2+1 ] = gridExtent[ iCoord2 ] 
                            gridExtent[ iCoord2 ] = geTmp
                        outputExtent[ iCoord2+1 ] = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ]
                        outputOrigin[ iCoord ] = lonOffset + roiBounds[0]
                    roisize = gridExtent[ iCoord2+1 ] - gridExtent[ iCoord2 ] + 1                  
                    gridSpacing[ iCoord ] = spacing
                    gridBounds[ iCoord2 ] = roiBounds[0] if roiBounds else values[0] 
                    gridBounds[ iCoord2+1 ] = (roiBounds[0] + roisize*spacing) if roiBounds else values[ size-1 ]
                else:                                             
                    gridSpacing[ iCoord ] = 1.0
#                    gridSpacing[ iCoord ] = zscale
                    gridBounds[ iCoord2 ] = values[0]  # 0.0
                    gridBounds[ iCoord2+1 ] = values[ size-1 ] # float( size-1 )
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
    
    def convert(self, cdms_var, **args):
        '''Convert a cdms data to vtk image data
        
        '''
        
        # @todo: Check if cdms_var is not none and if none check 
        # appropriately
        print 'cdms_var is ', cdms_var
        trans_var = cdms_var.var                
        level_axis = trans_var.getLevel()
        time_axis = trans_var.getTime()
        npts = -1
        
        if level_axis:
            values = level_axis.getValue()
            ascending_values = (values[-1] > values[0])
            invert_z = ( (level_axis.attributes.get( 'positive', '' ) == 'down') and ascending_values ) or ( (levaxis.attributes.get( 'positive', '' ) == 'up') and not ascending_values )
         
        time_bounds = args.get('time', None)        
        [ time_value, time_index, use_time_index ] = time_bounds if time_bounds else [ None, None, None ]
        
        raw_data_array = None
       
       # @todo: Pass decimation required
        decimation_factor = 1
        
        # @todo: Worry about order later
        data_args = {}
        
        try:
            if (time_index != None and use_time_index):
                print >> sys.stderr, "Using time index"
                data_args['time'] = slice(time_index, time_index + 1)
            elif time_value:
                data_args['time'] = time_value            
        except:
            pass
        
        try:
            raw_data_array = trans_var( **data_args )
        except Exception, err:
            print >> sys.stderr,  "Error Reading Variable " + str(err)
            return None       
        
        print 'raw_data_array shape is ', raw_data_array.shape
        
        # @note: Need to ask this to Thomas
        try: 
            raw_data_array = MV2.masked_equal( raw_data_array, raw_data_array.fill_value )
        except:
            pass
        
        data_shape = raw_data_array.shape
        print 'raw_data_array shape is (post mask) ', data_shape
        print 'raw_data_array id is ', raw_data_array.id
        
        data_array = raw_data_array
        
        # @todo: Ignore the scaling for now
        #flat_array = data_array.ravel('F')        
        
#        if npts == -1:
#            npts = flat_array.size
#        else:
#            assert( npts == flat_array.size)
        
        # @todo: Handle attributes later        
        
        # Now create a vtk image data
        image_data = vtk.vtkImageData()
        
        # @note: Assuming certain 
        image_data.SetScalarTypeToFloat()
        image_data.SetOrigin(0.0, 0.0, 0.0)
        image_data.SetSpacing(1.0, 1.0, 1.0)        
#        image_data.SetDimensions(data_shape[0], data_shape[1], data_shape[2])
        image_data.SetDimensions(data_shape[0], data_shape[2], data_shape[1]) 
        no_tuples = data_array.size
        
        print 'data_array ', data_array
        print 'data_array type', type(data_array)
        
        # Assuming float right now
        vtk_data_array = vtk.vtkFloatArray()
        
        vtk_data_array.SetNumberOfComponents(1)
        print 'number of tuples ', no_tuples
        vtk_data_array.SetNumberOfTuples(no_tuples)
        vtk_data_array.SetVoidArray(data_array, data_array.size, 1)
        vtk_data_array.SetName(cdms_var.varNameInFile)
        
        image_point_data = image_data.GetPointData()        
        image_point_data.SetScalars(vtk_data_array)
        
        writer = vtk.vtkDataSetWriter()
        writer.SetFileName("/home/aashish/Desktop/foo.vtk")
        writer.SetInput(image_data)
        writer.Write()
        
        image_data_copy = vtk.vtkImageData()
        image_data_copy.DeepCopy(image_data)
               
        return image_data_copy
         
        