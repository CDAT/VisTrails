'''
Created on Jul 30, 2013

@author: tpmaxwel
Adapted from code by Peter Caldwell at LLNL (caldwell19@llnl.gov)

'''

import cdutil, genutil, sys, os, cdms2, MV2, time
        
def make_corners(lat,lon,fname=0):
    """
    This func computes corners by extrapolating cell center positions.

    INPUTS:
    lat  : 2d array of lat values (degrees)
    lon  : 2d array of lon values (degrees). size(lat) must = size(lon)
    fname: name of file to write this stuff to.  Since this function
           runs fast, saving isn't so important. Set this to zero or
           omit it and no file will be written.
    
    OUTPUTS:
    lat_corners
    lon_corners

    NOTES:                               4-3
    1. Corners are computed in the order |X| which is important b/c
       scrip requires counterclockwise   1-2  traversing of corners
       in order to compute conservative remapping correctly.  
                               
    
    """
    import time
    t0 = time.clock()

    edge_lats=MV2.zeros([lat.shape[0]+1,lat.shape[1]+1],MV2.float)
    edge_lons=MV2.zeros([lat.shape[0]+1,lat.shape[1]+1],MV2.float)

    #HANDLE INTERIOR:
    #=============================
    #compute the centroid of each quadrilaterals formed by joining
    #neighboring cell centers. This is easy b/c the centroid of a
    #quadrilateral is the midpoint of the line connecting the midpoints
    #of diagonals across quadrilateral
    #(http://mathworld.wolfram.com/Quadrilateral.html).
    
    lat1=(lat[0:-1,0:-1]+lat[1:,1:])/2.0
    lat2=(lat[1:,0:-1]+lat[0:-1,1:])/2.0
    edge_lats[1:-1,1:-1]=(lat1+lat2)/2.0

    lon1=(lon[0:-1,0:-1]+lon[1:,1:])/2.0
    lon2=(lon[1:,0:-1]+lon[0:-1,1:])/2.0
    edge_lons[1:-1,1:-1]=(lon1+lon2)/2.0
    
    roi = [ 1000, -1000, 1000, -1000 ]
    for iC in range(4):
        if iC == 0:     i0, i1 =  0,  0
        elif iC == 1:   i0, i1 =  0, -1
        elif iC == 2:   i0, i1 = -1,  0
        elif iC == 3:   i0, i1 = -1, -1
        latval = lat[i0,i1]
        lonval = lon[i0,i1]
        roi[0] = min( roi[0], lonval )
        roi[1] = max( roi[1], lonval )
        roi[2] = min( roi[2], latval )
        roi[3] = max( roi[3], latval )
            
    #NOW GET EDGES (NOT CORNERS)
    #=============================
    for i in range(1,edge_lats.shape[0]-1):
        edge_lats[i,0]=quad_extrap(edge_lats[i,1:4],-1)
        edge_lats[i,-1]=quad_extrap(edge_lats[i,-4:-1],1)
        edge_lons[i,0]=quad_extrap(edge_lons[i,1:4],-1)
        edge_lons[i,-1]=quad_extrap(edge_lons[i,-4:-1],1)

    for j in range(1,edge_lats.shape[1]-1):
        edge_lats[0,j]=quad_extrap(edge_lats[1:4,j],-1)
        edge_lats[-1,j]=quad_extrap(edge_lats[-4:-1,j],1)
        edge_lons[0,j]=quad_extrap(edge_lons[1:4,j],-1)
        edge_lons[-1,j]=quad_extrap(edge_lons[-4:-1,j],1)
        
    #NOW GET CORNERS:
    #=============================
    edge_lats[0,0]=0.5*(quad_extrap(edge_lats[1:4,0],-1)\
                    +quad_extrap(edge_lats[0,1:4],-1) )
    edge_lons[0,0]=0.5*(quad_extrap(edge_lons[1:4,0],-1)\
                    +quad_extrap(edge_lons[0,1:4],-1) )

    edge_lats[0,-1]=0.5*(quad_extrap(edge_lats[0,-4:-1],1)\
                    +quad_extrap(edge_lats[1:4,-1],-1) )
    edge_lons[0,-1]=0.5*(quad_extrap(edge_lons[0,-4:-1],1)\
                    +quad_extrap(edge_lons[1:4,-1],-1) )

    edge_lats[-1,0]=0.5*(quad_extrap(edge_lats[-4:-1,0],1)\
                    +quad_extrap(edge_lats[-1,1:4],-1) )
    edge_lons[-1,0]=0.5*(quad_extrap(edge_lons[-4:-1,0],1)\
                    +quad_extrap(edge_lons[-1,1:4],-1) )

    edge_lats[-1,-1]=0.5*(quad_extrap(edge_lats[-4:-1,-1],1)\
                    +quad_extrap(edge_lats[-1,-4:-1],1) )
    edge_lons[-1,-1]=0.5*(quad_extrap(edge_lons[-4:-1,-1],1)\
                    +quad_extrap(edge_lons[-1,-4:-1],1) )
    
    #CHECKED CORNERS LOOK GOOD 2/9/09 via test_edges.py.
    # using return edge_lats,edge_lons right here.

    #NOW CREATE 3D ARRAY OF CORNERS
    #=============================
    lat_corners=MV2.zeros([lat.shape[0],lat.shape[1],4],MV2.float)

    lat_corners[:,:,0]=edge_lats[0:-1,0:-1]
    lat_corners[:,:,1]=edge_lats[0:-1,1:]
    lat_corners[:,:,2]=edge_lats[1:,1:]
    lat_corners[:,:,3]=edge_lats[1:,0:-1]

    lon_corners=MV2.zeros([lat.shape[0],lat.shape[1],4],MV2.float)
    lon_corners[:,:,0]=edge_lons[0:-1,0:-1]
    lon_corners[:,:,1]=edge_lons[0:-1,1:]
    lon_corners[:,:,2]=edge_lons[1:,1:]
    lon_corners[:,:,3]=edge_lons[1:,0:-1]

    #NOW SAVE RESULTS:
    #==============================
    if fname!=0:
        lat.id='lat'
        lat.units='degrees'
        lat.history = 'Created '+time.asctime()+ \
                      ' from ~/scrip/make_corners.py' 
        
        lon.id='lon'
        lon.units='degrees'
        lon.history = 'Created '+time.asctime()+ \
                      ' from ~/scrip/make_corners.py' 
        
        lat_corners.id = 'lat_corners'
        lat_corners.units = 'degrees'
        lat_corners.history = 'Created '+time.asctime()+ \
                              ' from ~/scrip/make_corners.py' 
        
        lon_corners.id = 'lon_corners'
        lon_corners.units = 'degrees'
        lon_corners.history = 'Created '+time.asctime()+ \
                              ' from ~/scrip/make_corners.py' 
        
        f=cdms.open(fname,'w')
        f.write(lat)
        f.write(lon)
        f.write(lat_corners)
        f.write(lon_corners)
        f.close()

    t1 = time.clock()
    print "Make corners required %.2f secs." % ( t1-t0 )

    return lat_corners,lon_corners, roi

#======================================================================
def quad_extrap(val,pos):
    """
    val should be a length 3 vector of lats or lons
    defined in the grid.  These will be used to define
    a quadrilateral function through these lats or lons
    and the next point out will be extrapolated from this fn.
    pos=1 means extrap off right end of vector, pos=-1 means extrap
    off the left (negative) end of vector.
    """

    import numpy

    b=numpy.matrix(val)
    if b.shape[0]==1:
        if b.shape[1]!=3:
            raise Exception('Input must have length 3!')
        else:
            b=numpy.transpose(b)
    else:
        if b.shape[0]!=3 or b.shape[1]!=1:
            raise Exception('Input must have length 3!')

    A=numpy.matrix([[0,0,1],[1,1,1],[4,2,1]])

    x=numpy.linalg.solve(A,b)
    
    if pos==1:
        out=x[0]*9+x[1]*3+x[2]
    else:
        out=x[0]*1-x[1]+x[2]

    return out


def isLevelAxisId( id ):
    if ( id.find('level')  >= 0 ): return True
    if ( id.find('bottom') >= 0 ) and ( id.find('top') >= 0 ): return True
    return False

def standard_regrid( file, var, **args ):        
    from cdms2.coord import TransientVirtualAxis, TransientAxis2D
    from cdms2.hgrid import TransientCurveGrid
    isVolume = False
    levaxis = None

    if ( len( var.shape ) == 4 ):     
        Var = var[0,:,:,:]
        levaxis = Var.getLevel()
        if levaxis == None:
            domain = Var.getDomain()
            for axis in domain:
                if isLevelAxisId( axis[0].id.lower() ):
                    levaxis = axis[0]
                    break
    else:
        Var = var[0,:,:]
               
    if hasattr( Var, "coordinates" ):
        axis_ids = Var.coordinates.strip().split(' ')
        lat_d01 = file( axis_ids[1], squeeze=1 )  
        lon_d01 = file( axis_ids[0], squeeze=1 )
    elif hasattr( Var, "stagger" ):
        stagger = Var.stagger.strip()
        lat_d01 = file( "XLAT_%s" % stagger, squeeze=1 )  
        lon_d01 = file( "XLONG_%s" % stagger, squeeze=1 )
    else:
        lat_d01 = file( "XLAT", squeeze=1 )  
        lon_d01 = file( "XLONG", squeeze=1 )
            
    lat_corners, lon_corners, roi = make_corners( lat_d01, lon_d01 )
    
    ni,nj = lat_d01.shape
    iaxis = TransientVirtualAxis("i", ni)
    jaxis = TransientVirtualAxis("j", nj)
    
    lataxis = TransientAxis2D(lat_d01, axes=(iaxis, jaxis), bounds=lat_corners, attributes={'units':'degrees_east'}, id="latitude")
    lonaxis = TransientAxis2D(lon_d01, axes=(iaxis, jaxis), bounds=lon_corners, attributes={'units':'degrees_north'}, id="longitude")
    grid = TransientCurveGrid( lataxis, lonaxis, id='WRF_inner' )
    
    if levaxis:
        levaxis.designateLevel() 
        tVar = cdms2.createVariable( Var, axes=( levaxis, grid ), id=var.id, typecode=Var.typecode() )
    else:
        tVar = cdms2.createVariable( Var, axes=( grid, ), id=var.id, typecode=Var.typecode() )
    
    a=tVar.getAxis(0)
    a.name = 'Latitude'
    b=tVar.getAxis(1)
    b.name = 'Longitude' 
    dims = lat_d01.shape if ( lat_d01.MemoryOrder == 'XY' ) else [ lat_d01.shape[1], lat_d01.shape[0] ]
    lon0 = roi[0]
    dlon = ( roi[1] - roi[0] ) / dims[0]
    lat0 = roi[2]
    dlat = ( roi[3] - roi[2] ) / dims[1]
        
    lat_lon_grid = cdms2.createUniformGrid( lat0, dims[1], dlat, lon0, dims[0], dlon )  
          
    regrid_Var = tVar.regrid( lat_lon_grid, regridTool = 'esmf', regridMethod = 'conserve' )   
    return regrid_Var

def getTimestampFromFilename( fname ):
    base_fname = os.path.splitext( os.path.basename( fname ) )[0]

class RegridDatasetSpecs:
    
    def __init__( self, spec_file_path = None ):
        self.specs = {}
        if spec_file_path:
            self.parse_specs( spec_file_path )
        
    def parse_specs( self, spec_file_path ):
        self.specs = {}
        context = None
        spec_file = open( spec_file_path, "r" )  
        for line in spec_file.readlines():
            line_tokens = line.split('=')
            spec_name = line_tokens[0].strip()
            if spec_name:
                if len( line_tokens ) > 0:
                        values = [ elem.strip() for elem in line_tokens[1].split(',') ]
                        self.specs[ spec_name ] = values[0] if ( len(values) == 1 ) else values
                else:
                    if spec_name[0] == '[':
                        context = spec_name.strip('[]')
                        
    def getFloat(self, name, default_val = None ):
        return float( self.specs.get( name, default_val ) )

    def getInt(self, name, default_val = None ):
        return int( self.specs.get( name, default_val ) )

    def getStr(self, name, default_val = None ):
        return self.specs.get( name, default_val ) 

    def getList(self, name, default_val = [] ):
        val = self.specs.get( name, default_val ) 
        if type( val ) == type( [] ): return val
        return [ val ]
    
    def put( self, name, val ):
        self.specs[ name ] = str( val )

def print_test_value( test_id, var ):
    sample_val = var[ var.shape[0]/2, var.shape[1]/2, var.shape[2]/2 ]
    print " ---- VAR TEST %s: %f " % ( test_id, sample_val )
     
def standard_regrid_dataset_extend( args ):
    from core.application import VistrailsApplicationInterface
    import argparse
    default_outfile = '~/regridded_WRF-%d.nc' % int( time.time() )
    spec_file = os.path.expanduser( "~/WRF_Dataset.txt" )
    specs = RegridDatasetSpecs( spec_file )
#     parser = argparse.ArgumentParser(description='Regrid WRF data files.')
#     parser.add_argument( '-f', '--files', dest='files', nargs='*', help='WRF data files')
#     parser.add_argument( '-r', '--result', dest='result', nargs='?', default=None, help='Resulting nc file (default: %s) ' % default_outfile)
#     parser.add_argument('-v', '--vars', dest='varnames', nargs='*', help='Variable name(s)')
#     parser.add_argument('-d', '--dir',  dest='directory', nargs='?', default=None, help='Data Directory')
#     parser.add_argument( 'FILE' )    
#     time_units = "hours since 2013-05-01"
#     dt = 1.0
#     t0 = 12.0
#     ns = parser.parse_args( args )
    
    rv = None
    t0 = specs.getFloat( 't0', 0.0 ) 
    dt = specs.getFloat( 'dt', 1.0 ) 
    time_units = specs.getStr( 'time_units', 'hours since 2000-01-01' )
    directory = specs.getStr( 'directory', None )
    
    varnames =  specs.getList( 'vars' ) 
    if not varnames:
        print>>sys.stderr, "Error, No variables specified"
        return

    files = specs.getList( 'files') 
    if not files:
        print>>sys.stderr, "Error, No WRF data files specified."
        return
    
    result_file = specs.getStr( 'outfile', os.path.expanduser( default_outfile ) )
    
    outfile = cdms2.createDataset( result_file )
    time_data = [ t0 + dt*istep for istep in range(len(files)) ]
    time_axis = cdms2.createAxis( time_data )    
    time_axis.designateTime()
    time_axis.id = "Time"
    time_axis.units = time_units
    time_index = 0
    axis_lists = {}
    for time_index, fname in enumerate(files):
        fpath = os.path.expanduser( fname if ( directory == None ) else os.path.join( directory, fname ) )
        cdms_file = cdms2.open( fpath )
        for varname in varnames:
            wrf_var = cdms_file( varname )
            var = standard_regrid( cdms_file, wrf_var )
            axis_list = axis_lists.get( varname )
            if not axis_list:
                axis_list = [ time_axis ]
                axis_list.extend( var.getAxisList() )
                axis_lists[ varname ] = axis_list
                rv = var
            outfile.write( var, extend=1, axes=axis_list, index=time_index )
    return rv

def standard_regrid_file( args ): 
    ( time_index, fname, varname, specs ) = args
    default_outfile = 'wrfout'
    t0 = specs.getFloat( 't0', 0.0 ) 
    dt = specs.getFloat( 'dt', 1.0 ) 
    result_file = specs.getStr( 'outfile', os.path.expanduser( default_outfile ) )    
    time_units = specs.getStr( 'time_units', 'hours since 2000-01-01' )
    data_directory = specs.getStr( 'data_directory', '~' ) 
    output_dataset_directory = specs.getStr( 'output_dataset_directory', '~' ) 
    fpath = os.path.join( data_directory, fname )
    cdms_file = cdms2.open( fpath )
    outfile = cdms2.createDataset( os.path.join( output_dataset_directory, "%s-%d.nc" % ( result_file, time_index ) ) )
    time_data = [ t0 + dt*time_index ]
    time_axis = cdms2.createAxis( time_data )    
    time_axis.designateTime()
    time_axis.id = "Time"
    time_axis.units = time_units
    wrf_var = cdms_file( varname )
    var = standard_regrid( cdms_file, wrf_var, logfile='/tmp/regrid_log_%s_%d.txt' % (varname,time_index) )
    axis_list = [ time_axis ]
    axis_list.extend( var.getAxisList() )
    var.coordinates = None
    var.name = varname
    outfile.write( var, extend=1, axes=axis_list, index=0 )
    outfile.close()
    
def standard_regrid_dataset_multi( args ):
    from multiprocessing import Process, Pool
    from core.application import VistrailsApplicationInterface
    import argparse
    tg0 = time.time() 

    parser = argparse.ArgumentParser(description='Regrid WRF data files.')
    parser.add_argument( '-s', '--specs', dest='specfile', nargs='?', default=None, help='WRF regrid spec file')
    parser.add_argument( 'FILE' )
    ns = parser.parse_args( args )
    
    if ns.specfile == None:
        print>>sys.stderr, "Error, Must specify a Regrid Spec File."
        return 
        
    spec_file = os.path.expanduser( ns.specfile )
    specs = RegridDatasetSpecs( spec_file )
       
    data_directory = specs.getStr( 'data_directory', '~' )
    out_directory = specs.getStr( 'out_directory', '~' )
    max_nproc = specs.getInt( 'max_nproc', 4 )
    
    WRF_dataset_name = specs.getStr( 'name', 'WRF' )
    output_dataset_directory = os.path.expanduser( os.path.join( out_directory, "%s-%d" % ( WRF_dataset_name, int( time.time() ) ) ) ) 
    
    try:
        os.mkdir(  output_dataset_directory )
    except OSError:
        print>>sys.stderr, "Error, Can't create dataset directory: ", data_directory
        return
    
    print "Regridding WRF files to %s" % ( output_dataset_directory )
    specs.put( 'output_dataset_directory', output_dataset_directory )
    
    files = specs.getList( 'files') 
    if not files:
        print>>sys.stderr, "Error, No WRF data files specified."
        return

    varnames =  specs.getList( 'vars' ) 
    if not varnames:
        print>>sys.stderr, "Error, No variables specified"
        return

   
    proc_queue = [ ]                
    for time_index, fname in enumerate(files):
        for varname in varnames:   
            p = Process( target=standard_regrid_file, args=( ( time_index, fname, varname, specs), ) )
            proc_queue.append(  p  )
            
    run_list = []
    while True:
        while ( len( run_list ) < max_nproc ):
            try: p = proc_queue.pop()
            except: break
            p.start()
            run_list.append( p )
        if len( run_list ) == 0: break
        for pindex, p in enumerate( run_list ):
            if not p.is_alive(): run_list.pop( pindex ) 
        time.sleep( 0.1 )  
            
    tg1 = time.time()
    print "Full Dataset Regrid required %.2f secs." % ( tg1-tg0 )
   
#--------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    
    standard_regrid_dataset_multi(sys.argv)  
    
#     if testPlot:
#         try:
#             startup_app()
#             from packages.vtDV3D.API import UVCDAT_API, PlotType
#             uvcdat_api = UVCDAT_API()
#             uvcdat_api.createPlot( inputs=[ var ], type=PlotType.SLICER ) # , viz_parms=port_map )
#             uvcdat_api.run()
#         except Exception, err:
#             print str(err)
 
    