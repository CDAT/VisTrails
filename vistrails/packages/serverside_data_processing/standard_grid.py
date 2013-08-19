'''
Created on Jul 30, 2013

@author: tpmaxwel
Adapted from code by Peter Caldwell at LLNL (caldwell19@llnl.gov)

'''

import cdutil, genutil, sys, os, cdms2, MV2, time, traceback
from multicore_process_executable import ExecutionTarget
        
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
    product_cache = args.get( 'cache', None )
    iproc = args.get( 'iproc', 0 )

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
        
    corners_id = ".".join( [ lat_d01.id, lon_d01.id ] )
    corners_data = product_cache.get( corners_id, None ) if product_cache else None
    if corners_data:
        ( lat_corners, lon_corners, roi ) = corners_data
    else:           
        lat_corners, lon_corners, roi = make_corners( lat_d01, lon_d01 )
        if product_cache <> None: product_cache[ corners_id ] = ( lat_corners, lon_corners, roi )

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
            
#    regrid_Var = tVar.regrid( lat_lon_grid, regridTool = 'esmf', regridMethod = 'conserve' )   
#    regrid_Var = tVar.regrid( lat_lon_grid )   
    regrid_Var = tVar.regrid( lat_lon_grid, regridTool = 'libcf', regridMethod = 'linear' )   
       
    return regrid_Var

def getTimestampFromFilename( fname ):
    base_fname = os.path.splitext( os.path.basename( fname ) )[0]

def print_test_value( test_id, var ):
    sample_val = var[ var.shape[0]/2, var.shape[1]/2, var.shape[2]/2 ]
    print " ---- VAR TEST %s: %f " % ( test_id, sample_val )
     
#def standard_regrid_dataset_extend( args ):
#    from core.application import VistrailsApplicationInterface
#    import argparse
#    default_outfile = '~/regridded_WRF-%d.nc' % int( time.time() )
#    spec_file = os.path.expanduser( "~/WRF_Dataset.txt" )
#    specs = RegridDatasetSpecs( spec_file )
##     parser = argparse.ArgumentParser(description='Regrid WRF data files.')
##     parser.add_argument( '-f', '--files', dest='files', nargs='*', help='WRF data files')
##     parser.add_argument( '-r', '--result', dest='result', nargs='?', default=None, help='Resulting nc file (default: %s) ' % default_outfile)
##     parser.add_argument('-v', '--vars', dest='varnames', nargs='*', help='Variable name(s)')
##     parser.add_argument('-d', '--dir',  dest='directory', nargs='?', default=None, help='Data Directory')
##     parser.add_argument( 'FILE' )    
##     time_units = "hours since 2013-05-01"
##     dt = 1.0
##     t0 = 12.0
##     ns = parser.parse_args( args )
#    
#    rv = None
#    t0 = specs.getFloat( 't0', 0.0 ) 
#    dt = specs.getFloat( 'dt', 1.0 ) 
#    time_units = specs.getStr( 'time_units', 'hours since 2000-01-01' )
#    directory = specs.getStr( 'directory', None )
#    
#    varnames =  specs.getList( 'vars' ) 
#    if not varnames:
#        print>>sys.stderr, "Error, No variables specified"
#        return
#
#    files = specs.getList( 'files') 
#    if not files:
#        print>>sys.stderr, "Error, No WRF data files specified."
#        return
#    
#    result_file = specs.getStr( 'outfile', os.path.expanduser( default_outfile ) )
#    
#    outfile = cdms2.createDataset( result_file )
#    time_data = [ t0 + dt*istep for istep in range(len(files)) ]
#    time_axis = cdms2.createAxis( time_data )    
#    time_axis.designateTime()
#    time_axis.id = "Time"
#    time_axis.units = time_units
#    time_index = 0
#    axis_lists = {}
#    for time_index, fname in enumerate(files):
#        fpath = os.path.expanduser( fname if ( directory == None ) else os.path.join( directory, fname ) )
#        cdms_file = cdms2.open( fpath )
#        for varname in varnames:
#            wrf_var = cdms_file( varname )
#            var = standard_regrid( cdms_file, wrf_var )
#            axis_list = axis_lists.get( varname )
#            if not axis_list:
#                axis_list = [ time_axis ]
#                axis_list.extend( var.getAxisList() )
#                axis_lists[ varname ] = axis_list
#                rv = var
#            outfile.write( var, extend=1, axes=axis_list, index=time_index )
#    return rv


class RegridExecutionTarget(ExecutionTarget):
    
    def execute( self, args ): 
        ( time_index, fname, varname, specs ) = args
        default_outfile = 'wrfout'
        t0 = specs.getFloat( 't0', 0.0 ) 
        dt = specs.getFloat( 'dt', 1.0 ) 
        time_data = [ t0 + dt*time_index ]
        result_file = specs.getStr( 'outfile', os.path.expanduser( default_outfile ) )    
        time_units = specs.getStr( 'time_units', 'hours since 2000-01-01' )
        data_location = specs.getStr( 'data_location', '~' ) 
        output_dataset_directory = specs.getStr( 'output_dataset_directory', '.' ) 
        
        fpath = os.path.join( data_location, fname )   
        try:
            print " P[%d]: opening file: %s " % ( self.proc_index, fpath ); sys.stdout.flush()
            cdms_file = cdms2.open( fpath )
        except Exception:
            print>>sys.stderr, "Can't read file %s " % ( fpath )
            return
        
        try:
            print " P[%d]: opening var: %s. " % ( self.proc_index, varname ); sys.stdout.flush()
            wrf_var = cdms_file( varname )
            print " P[%d]: Done read. " % ( self.proc_index ); sys.stdout.flush()
        except Exception:
            print>>sys.stderr, "Variable %s does not seem to exist in file %s " % ( varname, fpath )
            return
        
        print " P[%d]: Regridding variable %s[%.2f] in file %s" % ( self.proc_index, varname, time_data[0], fpath ); sys.stdout.flush()
    
        try:
            time_axis = cdms2.createAxis( time_data )    
            time_axis.designateTime()
            time_axis.id = "Time"
            time_axis.units = time_units
            var = standard_regrid( cdms_file, wrf_var, logfile='/tmp/regrid_log_%s_%d.txt' % (varname,time_index), cache = self.product_cache, iproc = self.proc_index )
            axis_list = [ time_axis ]
            axis_list.extend( var.getAxisList() )
            var.coordinates = None
            var.name = varname
            outfile_path = os.path.join( output_dataset_directory, "%s-%s-%d.nc" % ( result_file, varname, time_index ) )
            print " P[%d]: Writing to outfile %s" % ( self.proc_index, outfile_path ); sys.stdout.flush()
            outfile = cdms2.createDataset( outfile_path )
            outfile.write( var, extend=1, axes=axis_list, index=0 )
            outfile.close()
        except Exception, err:
            print>>sys.stderr, " P[%d]: Error regridding data: %s " % ( self.proc_index, str(err ) ); sys.stderr.flush()
            traceback.print_exc()
            return 1
        return 0
        
#def exec_procs( exec_target, arg_tuple_list, ncores, **args ):
#    from multiprocessing import Process, Lock
#    sync_write = args.get('sync_write', False)
#    write_lock = Lock() if sync_write else None
#    proc_queue = [ ]                
#    for iP, arg_tuple in enumerate( arg_tuple_list ): 
#        proc_args = list( arg_tuple ) 
#        proc_args.insert(0,iP)
#        proc_args.append( write_lock )
#        p = Process( target=exec_target, args=( proc_args, ) )
#        proc_queue.append(  (iP, proc_args, p)  )
#    run_list = []
#    iPrestart = len( arg_tuple_list )
#    while True:
#        while ( len( run_list ) < ncores ):
#            try: ( iP, proc_args, p ) = proc_queue.pop(0)
#            except: break
#            p.start()
#            print "\n ** Starting proc %d, Args:  %s   "  % ( iP, str( proc_args[0:4] ) ); sys.stderr.flush()
#            run_list.append( ( iP, proc_args, p, 0 ) )
#        if len( run_list ) == 0: break
#        for pindex, ( iP, proc_args, p, iRestart ) in enumerate( run_list ):
#            if p.exitcode <> None:
#                if (p.exitcode <> 0) and (iRestart < maxNRestarts):
#                    print>>sys.stderr, "\n ** Error executing proc %d, exitcode = %d - restarting! ** "  % ( iP, p.exitcode ); sys.stderr.flush()
#                    print>>sys.stderr, " Proc Args:  %s   %s \n" % ( str( proc_args[0:4] ), str( proc_args[4] ) )
#                    proc_args[0] = iPrestart
#                    p1 = Process( target=exec_target, args=( proc_args, ) )
#                    proc_queue.insert( 0, (iPrestart, proc_args, p1, iRestart + 1)  )
#                    iPrestart = iPrestart + 1
#                run_list.pop( pindex ) 
#                break
#        time.sleep( 0.1 )  
#
#def exec_procs_queue( exec_target, arg_tuple_list, ncores, **args ):
#    from multiprocessing import Process, JoinableQueue, Lock
#    sync_write = args.get('sync_write', False)
#    q = JoinableQueue() 
#    write_lock = Lock() if sync_write else None
#    for arg_tuple in arg_tuple_list:
#        q.put( arg_tuple )
#    proc_queue = [ ]                
#    for iP in range( ncores ):   
#        p = Process( target=exec_target, args=( q, iP, write_lock ) )
#        proc_queue.append( ( iP, p ) )
#        p.start()
#    print " Running %d procs" % len( proc_queue ); sys.stdout.flush()
#    q.join()
#     while True:
#         if len( proc_queue ) == 0: break
#         for pindex, ( ip, p ) in enumerate( proc_queue ):
#             if not p.is_alive(): 
#                 proc_queue.pop( pindex ) 
#                 print "\n *** Removing dead proc %d, nprocs = %d *** \n" % ( ip, len( proc_queue ) ); sys.stdout.flush()
#                 break
#         time.sleep( 0.1 )  

#def exec_procs_pool( exec_target, arg_tuple_list, ncores ):
#    from multiprocessing import Pool
#    pool = Pool(processes=ncores) 
#    pool.map( exec_target, arg_tuple_list )
   
#--------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':   
    from multicore_process_executable import ExecutionSpecs, MulticoreExecutable
    from remote_dataset_retrieval import DatasetCatalogRetriever
    import argparse
    tg0 = time.time() 

    parser = argparse.ArgumentParser(description='Regrid WRF data files.')
    parser.add_argument( '-s', '--specs', dest='specfile', nargs='?', default=None, help='WRF regrid spec file')
    parser.add_argument( 'FILE' )
    ns = parser.parse_args( sys.argv )
    
    if ns.specfile == None:
        print>>sys.stderr, "Error, Must specify a Regrid Spec File."
        sys.exit(1) 
        
    spec_file = os.path.expanduser( ns.specfile )
    specs = ExecutionSpecs( spec_file )
       
    data_location = specs.getPath( 'data_location', '~' )
    out_directory = specs.getPath( 'out_directory', '.' )
    run_cdscan = specs.getBool( 'run_cdscan', False )
    ncores = specs.getInt( 'ncores', 4 )
    
    WRF_dataset_name = specs.getStr( 'name', 'WRF' )
    output_dataset_directory = os.path.expanduser( os.path.join( out_directory, "%s-%d" % ( WRF_dataset_name, int( time.time() ) ) ) ) 
    
    try:
        os.mkdir(  output_dataset_directory )
    except OSError:
        print>>sys.stderr, "Error, Can't create output directory: ", output_dataset_directory
        sys.exit(2) 
    
    print "Regridding WRF files to %s" % ( output_dataset_directory )
    specs.put( 'output_dataset_directory', output_dataset_directory )
    
    filename_patterns = specs.getList( 'files') 
    if not filename_patterns:
        print>>sys.stderr, "Error, No WRF data files specified."
        sys.exit(3) 
    
    remote_dset_cat = DatasetCatalogRetriever( data_location )
    files = remote_dset_cat.get_file_list( filename_patterns )

    varnames =  specs.getList( 'vars' ) 
    if not varnames:
        print>>sys.stderr, "Error, No variables specified"
        sys.exit(4) 
   
    arg_tuple_list = [ ]                
    for time_index, fname in enumerate(files):
        for varname in varnames:   
            arg_tuple_list.append( ( time_index, fname, varname, specs) )
     
    multicore_exec = MulticoreExecutable( RegridExecutionTarget, ncores=ncores ) 
    multicore_exec.execute( arg_tuple_list )      
          
    tg1 = time.time()
    print "Full Dataset Regrid required %.2f secs." % ( tg1-tg0 )
    
    if run_cdscan:
        cmd = " cd '%s'; cdscan -x dataset.xml *.nc" % output_dataset_directory
        os.system(cmd)

    
    