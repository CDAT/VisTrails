'''
Created on Sep 18, 2013

@author: tpmaxwel
'''
import sys
import numpy
import cdms2

def isNone(obj):
    return ( id(obj) == id(None) )

class PlotType:
    Planar = 0
    Spherical = 1
    List = 0
    Grid = 1
    LevelAliases = [ 'isobaric' ]
    
    @classmethod
    def validCoords( cls, lat, lon ):
        return ( id(lat) <> id(None) ) and ( id(lon) <> id(None) )
    
    @classmethod
    def isLevelAxis( cls, pid ):
        if ( pid.find('level')  >= 0 ): return True
        if ( pid.find('bottom') >= 0 ) and ( pid.find('top') >= 0 ): return True
        if pid in cls.LevelAliases: return True
        return False    

    @classmethod
    def getPointsLayout( cls, grid ):
        if grid <> None:
            if (grid.__class__.__name__ in ( "RectGrid", "FileRectGrid") ): 
                return cls.Grid
        return cls.List  

class PointCollection():

    def __init__( self ):
        self.iTimeStep = 0
        self.point_data = None
        self.vtk_planar_points = None                                  
        self.cameraOrientation = {}
        self.topo = PlotType.Planar
        self.lon_data = None
        self.lat_data = None 
        self.z_spacing = 1.0 
        self.metadata = {}
        self.istart = 0
        self.istep = 1
        self.point_data_arrays = {}
        self.thresholded_range = [ 0, 0 ]
        self.point_layout = None
        self.axis_bounds = {}
        self.threshold_target = None
        self.vertical_bounds = None
        self.maxStageHeight = 100.0
        
    def configure(self, **args ):
        self.maxStageHeight = args.get('maxStageHeight', self.maxStageHeight )
        
    def getGridType(self):
        return self.point_layout
       
    def getDataBlock( self, var ):
        if self.lev == None:
            if len( var.shape ) == 2:
                np_var_data_block = var[ self.iTimeStep, self.istart::self.istep ].data
            elif len( var.shape ) == 3:
                np_var_data_block = var[ self.iTimeStep, :, self.istart::self.istep ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0] * np_var_data_block.shape[1], ] )
            self.nLevels = 1
        else:
            if len( var.shape ) == 3:               
                np_var_data_block = var[ self.iTimeStep, :, self.istart::self.istep ].data
            elif len( var.shape ) == 4:
                np_var_data_block = var[ self.iTimeStep, :, :, self.istart::self.istep ].data
                np_var_data_block = np_var_data_block.reshape( [ np_var_data_block.shape[0], np_var_data_block.shape[1] * np_var_data_block.shape[2] ] )

        return np_var_data_block
    
    def processCoordinates( self, lat, lon ):
        self.point_layout = self.getPointsLayout()
        nz = len( self.lev ) 
        self.n_input_points = lat.shape[0] * nz if ( self.point_layout == PlotType.List ) else lat.shape[0] * lon.shape[0] * nz
        if self.istep <= 0: self.istep = max( self.n_input_points / self.max_points, 1 )
        if len( lat.shape ) == 1:
            self.lat_data = lat[self.istart::self.istep] if ( self.point_layout == PlotType.List ) else lat[::]
            self.lon_data = lon[self.istart::self.istep] 
           
        else:
            self.lat_data = lat.flat[self.istart::self.istep] if ( self.point_layout == PlotType.List ) else lat.flat[::]
            self.lon_data = lon.flat[self.istart::self.istep] 
        if self.lon_data.__class__.__name__ == "TransientVariable":
            self.lat_data = self.lat_data.data
            self.lon_data = self.lon_data.data        
        xmax, xmin = self.lon_data.max(), self.lon_data.min()
        self.axis_bounds[ 'x' ] = ( xmin, xmax )
        self.axis_bounds[ 'y' ] = ( self.lat_data.min(), self.lat_data.max() )
        self.xcenter =  ( xmax + xmin ) / 2.0       
        self.xwidth =  ( xmax - xmin ) 
        return lon, lat

    def getNumberOfInputPoints(self): 
        return self.n_input_points
    
    def getNumberOfPoints(self): 
        return len( self.point_data_arrays['x'] ) 
    
    def setPointHeights( self, **args ): 
        height_varname = args.get( 'height_var', None )
        z_scaling = args.get( 'z_scale', 1.0 )
        self.data_height = args.get( 'data_height', None )
        print " setPointHeights: %s " % str( args ); sys.stdout.flush()
        ascending = True
        if self.lev.attributes.get('positive',None) == "down": ascending = False
        
        nz = len( self.lev ) 
        if height_varname:
            hgt_var = self.df[ height_varname ]
            np_hgt_var_data_block = self.getDataBlock(hgt_var).flatten() 
            if self.missing_value: np_hgt_var_data_block = numpy.ma.masked_equal( np_hgt_var_data_block, self.missing_value, False )
            zdata = np_hgt_var_data_block.astype( numpy.float32 ) 
            self.vertical_bounds = ( zdata.min(), zdata.max() )  
            if self.data_height == None: self.data_height = ( self.vertical_bounds[1] - self.vertical_bounds[0] )
            self.point_data_arrays['z'] = zdata * ( ( self.maxStageHeight * z_scaling ) / self.data_height ) 
        else:
            np_points_data_list = []
            stage_height = ( self.maxStageHeight * z_scaling )
            zstep = stage_height / nz
            for iz in range( nz ):
                zvalue = iz * zstep
                if self.point_layout == PlotType.List:
                    z_data = numpy.empty( self.lon_data.shape, self.lon_data.dtype ) 
                elif self.point_layout == PlotType.Grid: 
                    z_data = numpy.empty( [ self.lon_data.shape[0] * self.lat_data.shape[0] ], self.lon_data.dtype ) 
                z_data.fill( zvalue )
                if ascending: np_points_data_list.append( z_data )
                else: np_points_data_list.insert( 0, z_data )
            self.point_data_arrays['z'] = numpy.concatenate( np_points_data_list ).astype( numpy.float32 ) 
            self.vertical_bounds =  ( 0.0, stage_height )  
        self.axis_bounds[ 'z' ] = self.vertical_bounds

    def computePoints( self, **args ):
        nz = len( self.lev ) 
        if self.point_layout == PlotType.List:
            self.point_data_arrays['x'] = numpy.tile( self.lon_data.astype( numpy.float32 ), nz ) 
            self.point_data_arrays['y'] = numpy.tile( self.lat_data.astype( numpy.float32 ), nz )  
        elif self.point_layout == PlotType.Grid: 
            grid_data_x = numpy.tile( self.lon_data, self.lat_data.shape[0] )  
            grid_data_y = numpy.repeat( self.lat_data, self.lon_data.shape[0] )  
            self.point_data_arrays['x'] = numpy.tile( grid_data_x, nz )  
            self.point_data_arrays['y'] = numpy.tile( grid_data_y, nz )  
        
        
#        
#        np_points_data_list = []
#        for iz in range( len( self.lev ) ):
#            zvalue = iz * self.z_spacing
#            if self.point_layout == PlotType.List:
#                z_data = numpy.empty( self.lon_data.shape, self.lon_data.dtype ) 
#                z_data.fill( zvalue )
#                np_points_data_list.append( numpy.dstack( ( self.lon_data, self.lat_data, z_data ) ).flatten() )            
#            elif self.point_layout == PlotType.Grid: 
#                latB = self.lat_data.reshape( [ self.lat_data.shape[0], 1 ] )  
#                lonB = self.lon_data.reshape( [ 1, self.lon_data.shape[0] ] )
#                grid_data = numpy.array( [ (x,y,zvalue) for (x,y) in numpy.broadcast(lonB,latB) ] )
#                np_points_data_list.append( grid_data.flatten() ) 
#        np_points_data = numpy.concatenate( np_points_data_list )
#        self.point_data_arrays['x'] = np_points_data[0::3].astype( numpy.float32 ) 
#        self.point_data_arrays['y'] = np_points_data[1::3].astype( numpy.float32 ) 
#        self.point_data_arrays['z'] = np_points_data[2::3].astype( numpy.float32 ) 
#        self.axis_bounds[ 'z' ] = ( 0.0, self.z_spacing * len( self.lev ) )  
              
    def computePoints1( self, **args ):
        np_points_data_list = []
        for iz in range( len( self.lev ) ):
            zvalue = iz * self.z_spacing
            if self.point_layout == PlotType.List:
                z_data = numpy.empty( self.lon_data.shape, self.lon_data.dtype ) 
                z_data.fill( zvalue )
                np_points_data_list.append( numpy.dstack( ( self.lon_data, self.lat_data, z_data ) ).flatten() )            
            elif self.point_layout == PlotType.Grid: 
                latB = self.lat_data.reshape( [ self.lat_data.shape[0], 1 ] )  
                lonB = self.lon_data.reshape( [ 1, self.lon_data.shape[0] ] )
                grid_data = numpy.array( [ (x,y,zvalue) for (x,y) in numpy.broadcast(lonB,latB) ] )
                np_points_data_list.append( grid_data.flatten() ) 
        np_points_data = numpy.concatenate( np_points_data_list )
        self.point_data_arrays['x'] = np_points_data[0::3].astype( numpy.float32 ) 
        self.point_data_arrays['y'] = np_points_data[1::3].astype( numpy.float32 ) 
        self.point_data_arrays['z'] = np_points_data[2::3].astype( numpy.float32 ) 
        self.axis_bounds[ 'z' ] = ( 0.0, self.z_spacing * len( self.lev ) )  
        
    def getBounds(self):
        return self.axis_bounds[ 'x' ] + self.axis_bounds[ 'y' ] + self.axis_bounds[ 'z' ] 

    def getPointsLayout( self ):
        return PlotType.getPointsLayout( self.grid )

    def getLatLon( self, varname, **args ):
        data_file = args.get('df',self.df)
        grid_file = args.get('dg',self.gf)
        if grid_file:
            lat = grid_file['lat']
            lon = grid_file['lon']
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )
        Var = data_file[ varname ]
        if isNone(Var):
            print>>sys.stderr, "Error, can't find variable '%s' in data file." % ( varname )
            return None, None
        if hasattr( Var, "coordinates" ):
            axis_ids = Var.coordinates.strip().split(' ')
            lat = data_file( axis_ids[1], squeeze=1 )  
            lon = data_file( axis_ids[0], squeeze=1 )
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )
        elif hasattr( Var, "stagger" ):
            stagger = Var.stagger.strip()
            lat = data_file( "XLAT_%s" % stagger, squeeze=1 )  
            lon = data_file( "XLONG_%s" % stagger, squeeze=1 )
            if PlotType.validCoords( lat, lon ): 
                return  self.processCoordinates( lat, lon )

        lat = Var.getLatitude()  
        lon = Var.getLongitude()
        if PlotType.validCoords( lat, lon ): 
            return  self.processCoordinates( lat.getValue(), lon.getValue() )
        
        lat = data_file( "XLAT", squeeze=1 )  
        lon = data_file( "XLONG", squeeze=1 )
        if PlotType.validCoords( lat, lon ): 
            return  self.processCoordinates( lat, lon )       
        return None, None
    
    def setDataSlice(self, istart, **args ):
        self.istart = istart
        self.istep = args.get( 'istep', -1 )
        self.max_points = args.get( 'max_points', -1 )
        
    def getLevel(self, var ):
        lev_aliases =  [ "isobaric", "bottom_top" ]
        lev = var.getLevel()
        if lev == None:
            for axis_spec in var.domain:
                axis = axis_spec[0]
                if axis.id in lev_aliases:
                    lev = axis
                    break
        return lev

    def initialize( self, args, **cfg_args ): 
        self.configure( **cfg_args )
        ( grid_file, data_file, varname, height_varname ) = args
        self.gf = cdms2.open( grid_file ) if grid_file else None
        self.df = cdms2.open( data_file )       
        var = self.df[ varname ]
        self.grid = var.getGrid()
        self.lev = self.getLevel(var)
        lon, lat = self.getLatLon( varname )                              
        self.time = var.getTime()
        z_scale = 0.5
        self.missing_value = var.attributes.get( 'missing_value', None )
        if self.lev == None:
            domain = var.getDomain()
            for axis in domain:
                if PlotType.isLevelAxis( axis[0].id.lower() ):
                    self.lev = axis[0]
                    break        
        self.computePoints()
        self.setPointHeights( height_var=height_varname, z_scale=z_scale )
        np_var_data_block = self.getDataBlock(var).flatten()     
        if self.missing_value: var_data = numpy.ma.masked_equal( np_var_data_block, self.missing_value, False )
        else: var_data = np_var_data_block
        self.point_data_arrays['vardata'] = var_data
        self.vrange = ( var_data.min(), var_data.max() ) 
        print "Read %d points." % self.getNumberOfPoints(); sys.stdout.flush()
        
    def getPoints(self):
        point_comps = [ self.point_data_arrays[comp] for comp in [ 'x', 'y', 'z'] ]
        return numpy.dstack( point_comps ).flatten()

    def getPointIndices(self):
        return self.selected_index_array
    
    def getPointHeights(self):
        return self.point_data_arrays['z'] 

    def getVarData(self):
        return  self.point_data_arrays.get( 'vardata', None )

    def getVarDataRange(self):
        return self.vrange

    def getThresholdedRange(self):
        return self.thresholded_range
    
    def getThresholdTarget(self):
        return self.threshold_target
    
    def getNLevels(self):
        return len( self.lev )
    
    def computeThresholdRange( self, args ):
        ( self.threshold_target, rmin, rmax ) = args
        var_data = self.point_data_arrays.get( self.threshold_target, None)
        if not isNone(var_data):
            arange = self.axis_bounds.get( self.threshold_target )
            if arange:
                dv = arange[1] - arange[0]
                vmin = arange[0] + rmin * dv
                vmax = arange[0] + rmax * dv  
            elif self.threshold_target == 'vardata':
                dv = self.vrange[1] - self.vrange[0]
                try:
                    vmin = self.vrange[0] + rmin * dv
                    vmax = self.vrange[0] + rmax * dv
                except TypeError, err:
                    pass
            if vmin:
                self.thresholded_range = [ vmin, vmax ]
                return var_data, vmin, vmax
        return None, None, None
                    
    def execute( self, args, **kwargs ): 
        op = args[0] 
        if op == 'indices':    
            var_data, vmin, vmax = self.computeThresholdRange( args[1:] )
            if not isNone(var_data):
                threshold_mask = numpy.logical_and( numpy.greater( var_data, vmin ), numpy.less( var_data, vmax ) ) 
                index_array = numpy.arange( 0, len(var_data) )
                self.selected_index_array = index_array[ threshold_mask ]  
            return vmin, vmax   
        elif op == 'points': 
            print " Process points request, args = %s " % str( args ); sys.stdout.flush()
            self.setPointHeights( height_var=args[1], z_scale=args[2] )  
            
