
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
        pass
    
    def get_grid_specs(self, var_data, grid_bounds, zscale):
        pass
    
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
        
#        writer = vtk.vtkDataSetWriter()
#        writer.SetFileName("/home/aashish/Desktop/foo.vtk")
#        writer.SetInput(image_data)
#        writer.Write()
        
        print image_data
               
        return image_data
         
        