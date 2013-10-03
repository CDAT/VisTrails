'''
Created on Sep 18, 2013

@author: tpmaxwel
'''

import sys, os
import numpy
import vtk,  time,  math
from vtk.util import numpy_support
from PointCollection import PointCollection, PlotType, isNone
from multiprocessing import Process, Queue
from PyQt4 import QtCore # import SIGNAL, QObject

class ScalarRangeType:         
    Full = 0
    Thresholded = 1

class ExecutionDataPacket:
    NONE = -1
    POINTS = 0
    INDICES = 1
    VARDATA = 2
    
    def __init__( self, msg_type, node_index, data_object  ):
        self.type = msg_type
        self.data = data_object
        self.node_index = node_index
        self.metadata = {}

    def printLogMessage(self, msg_str ):
        print " DataPacket %d: %s" % ( self.node_index, msg_str )
        sys.stdout.flush()      
        
    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, key):
        return self.metadata.get( key, None )

    def __setitem__(self, key, value):
        self.metadata[key] = value

    def __delitem__(self, key):
        del self.values[key]    

class PointCollectionExecutionTarget:

    def __init__( self, collection_index, ncollections, init_args=None ):
        self.point_collection = PointCollection() 
        self.point_collection.setDataSlice( collection_index, ncollections )
        self.collection_index = collection_index
        self.ncollections = ncollections
        self.init_args = init_args

    def printLogMessage(self, msg_str ):
        print " PointCollectionExecutionTarget %d: %s" % ( self.collection_index, msg_str )
        sys.stdout.flush()      

    def __call__( self, args_queue, result_queue ):
        self.results = result_queue
        self.initialize()
        while True:
            args = list( args_queue.get( True ) )
            self.execute( args )
                
    def initialize( self ):
        self.point_collection.initialize( self.init_args )
        self.point_collection.setDataSlice( self.collection_index, self.ncollections )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.POINTS, self.collection_index, self.point_collection.getPoints() )
        self.results.put( data_packet )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.VARDATA, self.collection_index, self.point_collection.getVarData() )
        data_packet[ 'vrange' ] = self.point_collection.getVarDataRange() 
        data_packet[ 'grid' ] = self.point_collection.getGridType()  
        data_packet[ 'nlevels' ] = self.point_collection.getNLevels()
        data_packet[ 'bounds' ] = self.point_collection.getBounds()
        self.results.put( data_packet )

    def execute( self, args ):
        self.point_collection.execute( args )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.INDICES, self.collection_index, self.point_collection.getPointIndices() )
        target = self.point_collection.getThresholdTarget()
        range_type = 'trange' if ( target == "vardata" ) else "crange"
        data_packet[ range_type ] = self.point_collection.getThresholdedRange() 
        data_packet[ 'target' ] = target
        data_packet[ 'args' ] = args
        self.results.put( data_packet )

class vtkPointCloud(QtCore.QObject):

    shperical_to_xyz_trans = vtk.vtkSphericalTransform()
    radian_scaling = math.pi / 180.0 

    def __init__( self, pcIndex=0, nPartitions=1 ):
        QtCore.QObject.__init__( self )
        self.nPartitions = nPartitions
        self.vardata = None
        self.vrange = None
        self.trange = None
        self.crange = None
        self.np_index_seq = None
        self.points = None
        self.pcIndex = pcIndex
        self.earth_radius = 100.0
        self.vtk_planar_points = None
        self.vtk_spherical_points = None
        self.np_points_data = None
        self.topo = PlotType.Planar
        self.grid = None
        self.threshold_target = "vardata"
        self.current_scalar_range = None
        self.nlevels  = None
        self.current_subset_specs = None
        self.updated_subset_specs = None
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        self.actor = vtk.vtkActor()
        self.actor.SetMapper( self.mapper )
      
    def getPoint( self, iPt ):
        dval = self.vardata[ iPt ]
        pt = self.vtk_planar_points.GetPoint( iPt ) 
        self.printLogMessage( " getPoint: dval=%s, pt=%s " % ( str(dval), str(pt) ) ) 
        return pt, dval
        
    def printLogMessage(self, msg_str ):
        print " Proxy Node %d: %s" % ( self.pcIndex, msg_str )
        sys.stdout.flush() 
        
    def getNLevels(self): 
#        if self.nlevels == None: 
#            print>>sys.stderr, " Undefined nlevels in getNLevels, proc %d " % self.pcIndex
        return self.nlevels    
    
    def getGrid(self):
        return self.grid
    
    def hasResultWaiting(self):
        return False
    
    def getThresholdingRange(self):       
        return self.trange if ( self.threshold_target == "vardata" ) else self.crange
    
    def getValueRange( self, range_type ):
        return self.vrange if ( range_type == ScalarRangeType.Full ) else self.trange
   
    def generateSubset(self, subset_spec ):
        pass
    
    def refresh(self, force=False ):
        if self.current_subset_specs and (self.current_subset_specs <> self.updated_subset_specs):
            self.generateSubset( self.current_subset_specs, force )
            self.updated_subset_specs = self.current_subset_specs
    
    def getData( self, dtype ):
        if dtype == ExecutionDataPacket.VARDATA:
            return self.vardata
        elif dtype == ExecutionDataPacket.INDICES:
            return self.np_index_seq 
        elif dtype == ExecutionDataPacket.POINTS:
            return self.np_points_data 
   
    def updateVertices( self, **args ): 
        self.vertices = vtk.vtkCellArray()  
        if isNone(self.np_index_seq):
            wait = args.get( 'wait', False )  
            if wait: self.waitForData( ExecutionDataPacket.INDICES )
            else: return
        cell_sizes   = numpy.ones_like( self.np_index_seq )
        self.np_cell_data = numpy.dstack( ( cell_sizes, self.np_index_seq ) ).flatten()         
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( self.np_cell_data ) 
        self.vertices.SetCells( cell_sizes.size, self.vtk_cell_data )     
        self.polydata.SetVerts(self.vertices)
        self.polydata.Modified()
        self.mapper.Modified()
        self.actor.Modified()
#        self.emit( "NewSubset", self.pcIndex )
        
    def getPolydata(self):
        return self.polydata
        
    def setScalarRange( self, scalar_range ):
        try:
            self.mapper.SetScalarRange( scalar_range[0], scalar_range[1] )
            self.printLogMessage(  " Set Scalar Range: %s " % str( scalar_range ) )
            self.mapper.Modified()
            self.actor.Modified()
            self.current_scalar_range = scalar_range
        except TypeError: 
            pass
        
    def getScalarRange( self ):
        return self.current_scalar_range
    
    def getUnscaledRange( self, srange ):
        dv = self.vrange[1] - self.vrange[0]
        vmin = self.vrange[0] + srange[0] * dv
        vmax = self.vrange[0] + srange[1] * dv
        return ( vmin, vmax )
                                             
    def updateScalars( self, **args ):
        if isNone(self.vardata):
            wait = args.get( 'wait', True ) 
            if wait: self.waitForData( ExecutionDataPacket.VARDATA )
            else: return
        vtk_color_data = numpy_support.numpy_to_vtk( self.vardata ) 
        vtk_color_data.SetName( 'vardata' )       
        self.polydata.GetPointData().SetScalars( vtk_color_data )
        
    def initPoints( self, **args ):
        if isNone(self.np_points_data):
            wait = args.get( 'wait', True ) 
            if wait: self.waitForData( ExecutionDataPacket.POINTS )
            else: return
        vtk_points_data = numpy_support.numpy_to_vtk( self.np_points_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( len( self.np_points_data ) / 3 )     
        self.vtk_planar_points = vtk.vtkPoints()
        self.vtk_planar_points.SetData( vtk_points_data )
        self.createPolydata()
        
    def createPolydata( self, **args  ):
        self.polydata = vtk.vtkPolyData()
        vtk_pts = self.getPoints()
        self.polydata.SetPoints( vtk_pts )                         
        self.initializePointsActor( self.polydata, **args )

    def computeSphericalPoints( self, **args ):
        lon_data = self.np_points_data[0::3]
        lat_data = self.np_points_data[1::3]
        radian_scaling = math.pi / 180.0 
        theta =  ( 90.0 - lat_data ) * radian_scaling
        phi = lon_data * radian_scaling
        if self.grid == PlotType.List:
            r = numpy.empty( lon_data.shape, lon_data.dtype )      
            r.fill(  self.earth_radius )
            np_sp_grid_data = numpy.dstack( ( r, theta, phi ) ).flatten()
            vtk_sp_grid_data = numpy_support.numpy_to_vtk( np_sp_grid_data ) 
        elif self.grid == PlotType.Grid:
            thetaB = theta.reshape( [ theta.shape[0], 1 ] )  
            phiB = phi.reshape( [ 1, phi.shape[0] ] )
            grid_data = numpy.array( [ ( self.earth_radius, t, p ) for (t,p) in numpy.broadcast(thetaB,phiB) ] )
            sp_points_data = grid_data.flatten() 
            vtk_sp_grid_data = numpy_support.numpy_to_vtk( sp_points_data ) 
        size = vtk_sp_grid_data.GetSize()                    
        vtk_sp_grid_data.SetNumberOfComponents( 3 )
        vtk_sp_grid_data.SetNumberOfTuples( size/3 )   
        vtk_sp_grid_points = vtk.vtkPoints()
        vtk_sp_grid_points.SetData( vtk_sp_grid_data )
        self.vtk_spherical_points = vtk.vtkPoints()
        self.shperical_to_xyz_trans.TransformPoints( vtk_sp_grid_points, self.vtk_spherical_points ) 
                
    def initializePointsActor( self, polydata, **args ):
        lut = args.get( 'lut', self.create_LUT() )
        self.mapper.SetInput( self.polydata ) 
        if lut: 
            self.mapper.SetLookupTable( lut )                
        if self.vrange:
            self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
            self.printLogMessage( " init scalar range %s " % str(self.vrange) )    

    def getNumberOfPoints(self): 
        return len( self.np_points_data ) / 3             
    
    def getPoints( self, **args ):
        if self.topo == PlotType.Spherical:
            if not self.vtk_spherical_points:
                self.refresh()
                self.computeSphericalPoints()
            return self.vtk_spherical_points
        if self.topo == PlotType.Planar:
            if not self.vtk_planar_points: 
                self.initPoints()
            return self.vtk_planar_points
        
    def updatePoints(self):
        self.polydata.SetPoints( self.getPoints() ) 

    @classmethod    
    def getXYZPoint( cls, lon, lat, r = None ):
        theta =  ( 90.0 - lat ) * cls.radian_scaling
        phi = lon * cls.radian_scaling
        spherical_coords = ( r, theta, phi )
        return cls.shperical_to_xyz_trans.TransformDoublePoint( *spherical_coords )

    def setTopo( self, topo, **args ):
        if topo <> self.topo:
            self.topo = topo
            self.clearClipping()
#            if self.actor.GetVisibility():
            pts = self.getPoints( **args )
            self.polydata.SetPoints( pts ) 
            return pts
        return None 
        
    def setVisiblity(self, visibleLevelIndex ):
        isVisible = ( visibleLevelIndex < 0 ) or ( visibleLevelIndex == self.iLevel )
        if isVisible: self.updatePoints()
        self.actor.SetVisibility( isVisible  )
        return isVisible
    
    def isVisible(self):
        return self.actor.GetVisibility()
    
    def hide(self):
        self.actor.VisibilityOff()

    def show(self):
        if not self.actor.GetVisibility():
            self.actor.VisibilityOn()
        
    def getBounds( self, **args ):
        topo = args.get( 'topo', self.topo )
        lev = args.get( 'lev', None )
        if topo == PlotType.Spherical:
            return [ -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius ]
        else:
            b = list( self.grid_bounds )
            if lev:
                lev_bounds = ( lev[0], lev[-1] )
                b[4] = lev_bounds[0] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[1]
                b[5] = lev_bounds[1] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[0]
            elif ( b[4] == b[5] ):
                b[4] = b[4] - 100.0
                b[5] = b[5] + 100.0
            return b
                
    def setClipping( self, clippingPlanes ):
        self.mapper.SetClippingPlanes( clippingPlanes )
        
    def clearClipping( self ):
        self.mapper.RemoveAllClippingPlanes()    

    def setPointSize( self, point_size ):
        self.actor.GetProperty().SetPointSize( point_size )
        
    def getLUT(self):
        return self.mapper.GetLookupTable()
        
    def getPointValue( self, iPt ):
        return self.var_data[ iPt ]

    def create_LUT( self, **args ):
        lut = vtk.vtkLookupTable()
        lut_type = args.get( 'type', "blue-red" )
        invert = args.get( 'invert', False )
        number_of_colors = args.get( 'number_of_colors', 256 )
        alpha_range = 1.0, 1.0
        
        if lut_type=="blue-red":
            if invert:  hue_range = 0.0, 0.6667
            else:       hue_range = 0.6667, 0.0
            saturation_range = 1.0, 1.0
            value_range = 1.0, 1.0
         
        lut.SetHueRange( hue_range )
        lut.SetSaturationRange( saturation_range )
        lut.SetValueRange( value_range )
        lut.SetAlphaRange( alpha_range )
        lut.SetNumberOfTableValues( number_of_colors )
        lut.SetRampToSQRT()            
        lut.Modified()
        lut.ForceBuild()
        return lut   

class vtkSubProcPointCloud( vtkPointCloud ):

    def __init__( self, pcIndex=0, nPartitions=1 ):
        vtkPointCloud.__init__( self, pcIndex, nPartitions )
        self.arg_queue = Queue() # JoinableQueue() 
        self.result_queue = Queue() # JoinableQueue()

    def generateSubset(self, subset_spec, force=False ):
        self.current_subset_specs = subset_spec
        if force or self.actor.GetVisibility():
            self.clearQueues()
            self.threshold_target = subset_spec[0]
            self.np_index_seq = None
#            self.printLogMessage( " --->> Generate subset: %s " % str(subset_spec) )
            self.arg_queue.put( subset_spec,  False ) 
            self.updated_subset_specs = subset_spec
        
    def getResults( self, block = False ):
        try:
            result = self.result_queue.get( block )
        except Exception:
            return False
        if result.type == ExecutionDataPacket.VARDATA:
            self.vardata = result.data 
            self.vrange = result['vrange']
            self.grid = result['grid']
            self.nlevels = result['nlevels']
            self.grid_bounds = result['bounds']
            self.current_scalar_range = self.vrange
#            self.printLogMessage( " update vrange %s " % str(self.vrange) )      
        elif result.type == ExecutionDataPacket.INDICES:
            self.np_index_seq = result.data 
            self.trange = result['trange']
            self.threshold_target = result['target']
            if self.pcIndex == 1: self.printLogMessage(  " vtkSubProcPointCloud-> Get Results, Args: %s " % str(result['args']) )
        elif result.type == ExecutionDataPacket.POINTS:
            self.np_points_data = result.data 
        return True

    def processResults( self ):
        try:
            result = self.result_queue.get( False )
        except Exception:
            return ExecutionDataPacket.NONE
        if result.type == ExecutionDataPacket.VARDATA:
            self.vardata = result.data 
            self.vrange = result['vrange']
            self.grid = result['grid']
            self.nlevels = result['nlevels']
            self.grid_bounds = result['bounds']
            self.updateScalars()   
#            print " processResults[ %d ] : VARDATA" % self.pcIndex; sys.stdout.flush()
        elif result.type == ExecutionDataPacket.INDICES:
            self.np_index_seq = result.data 
            self.threshold_target = result['target']
            if self.threshold_target == "vardata":
                self.trange = result['trange']
            else:
                self.crange = result['crange']                
            if self.pcIndex == 1: self.printLogMessage(  " vtkSubProcPointCloud-> Process Results, Args: %s " % str(result['args']) )
            self.updateVertices()  
#            print " processResults[ %d ] : INDICES" % self.pcIndex; sys.stdout.flush()
        elif result.type == ExecutionDataPacket.POINTS:
            self.np_points_data = result.data 
            self.initPoints()  
#            print " processResults[ %d ] : POINTS" % self.pcIndex; sys.stdout.flush()
        return True
        
    def waitForData( self, dtype ):
        self.printLogMessage( " waitForData type %d" % ( dtype ) )   
        while( self.getData( dtype ) == None ):
            self.getResults(True)
            time.sleep(0.05)
                                             
        
    def start_subprocess( self, init_args, **args ):
        exec_target =  PointCollectionExecutionTarget( self.pcIndex, self.nPartitions, init_args ) 
        self.process = Process( target=exec_target, args=( self.arg_queue, self.result_queue ) )
        self.process.start()
        
    def clearQueues(self):
        try: 
            while True: self.arg_queue.get_nowait()
        except: pass
        try: 
            while True: self.result_queue.get_nowait()
        except: pass
               
    def terminate(self):
        self.process.terminate()
        
        
class vtkLocalPointCloud( vtkPointCloud ):

    def __init__( self, istart=0, istep=1 ):
        vtkPointCloud.__init__( self, istart, istep )
        self.point_collection = PointCollection()
        self.point_collection.setDataSlice( istart, istep )

    def generateSubset(self, subset_spec, force=False ):
        self.current_subset_specs = subset_spec
        self.threshold_target = subset_spec[0]
        if force or self.actor.GetVisibility():
            vmin, vmax = self.point_collection.execute( subset_spec )       
            self.np_index_seq = self.point_collection.selected_index_array
            if subset_spec == "vardata": self.trange = ( vmin, vmax )
            else: self.crange = ( vmin, vmax )
            self.grid = self.point_collection.getGridType()
            self.nlevels = self.point_collection.getNLevels()
            self.current_scalar_range = self.vrange
            self.updateVertices() 
            self.updated_subset_specs = subset_spec
        
    def initialize(self, init_args ):
        self.point_collection.initialize( init_args )
        self.np_points_data = self.point_collection.np_points_data
        self.vrange = self.point_collection.vrange
        self.initPoints() 
        self.createPolydata()
        self.vardata = self.point_collection.var_data
        self.updateScalars() 
        self.grid_bounds = self.point_collection.getBounds()
        self.actor.VisibilityOff()
          
class vtkPartitionedPointCloud( QtCore.QObject ):
    
    def __init__( self, nPartitions, init_args  ):
        QtCore.QObject.__init__( self )
        self.point_clouds = {}
        self.point_cloud_map = {}
        self.nPartitions = nPartitions
        self.nActiveCollections =  self.nPartitions 
        self.current_subset_spec = None
        self.timerId = 0
        for pcIndex in range( nPartitions ):
            pc = vtkSubProcPointCloud( pcIndex, nPartitions )
            pc.start_subprocess( init_args )
            self.point_clouds[ pcIndex ] = pc
        for pc in self.point_clouds.values():
            pc.createPolydata()
            pc.updateScalars()
            self.point_cloud_map[ pc.actor ] = pc
#        self.scalingTimer = self.startTimer(1000)
            
    def startCheckingProcQueues(self):
        self.dataQueueTimer = self.startTimer(100)
    
    def refresh( self, force=False ): 
        for pc in self.point_clouds.values():
            pc.refresh( force )

    def stopCheckingProcQueues(self):
        if self.timerId: self.killTimer( self.dataQueueTimer )
        
    def timerEvent( self, event ):
        if event.timerId() == self.dataQueueTimer: self.checkProcQueues()
#        if event.timerId() == self.scalingTimer: self.emit( QtCore.SIGNAL('updateScaling') )
        
    def processProcQueue(self):
        for pc_item in self.point_clouds.items():
            rv = pc_item[1].processResults()
            if rv <> ExecutionDataPacket.NONE:
                return pc_item, rv 
        return None, None
                    
    def checkProcQueues(self):
        pc_item, rv = self.processProcQueue()
        if rv:
            self.emit( QtCore.SIGNAL('newDataAvailable'), pc_item[0], rv )
            self.stopCheckingProcQueues()
            pc_item[1].show()
            
    def updateNumActiveCollections( self, ncollections_inc ):
        self.nActiveCollections = max( self.nActiveCollections + ncollections_inc, 1 )
        self.nActiveCollections = min( self.nActiveCollections, self.nPartitions )
        self.generateSubset()
        print " --> updateNumActiveCollections: %d " % self.nActiveCollections; sys.stdout.flush()
            
    def clear(self, activePCIndex = -1 ):
        for pc_item in self.point_clouds.items():
            if pc_item[0] <> activePCIndex:
                pc_item[1].hide()
                
    def show(self): 
        for pc_item in self.point_clouds.items():
            if pc_item[0] < self.nActiveCollections:
                pc_item[1].show()
            
    def getPoint( self, actor, iPt ):
        pc = self.point_cloud_map.get( actor, None )
        if pc: return pc.getPoint( iPt )
        else: return ( "", "" ), ""

    def printLogMessage(self, msg_str ):
        print " vtkPartitionedPointCloud: %s" % ( msg_str )
        sys.stdout.flush()      
            
    def getActors(self):
        return [ pc.actor for pc in self.point_clouds.values() ]
    
    def generateSubset(self, subset_spec = None, force=False ):
        if subset_spec: self.current_subset_spec = subset_spec
        self.clearProcQueues()
#        print " generateSubset: subset_spec = %s " % str( self.current_subset_spec )R
        for pc_item in self.point_clouds.items():
            if pc_item[0] < self.nActiveCollections:
                pc_item[1].generateSubset( self.current_subset_spec, force )
        self.startCheckingProcQueues()
        
    def clearProcQueues(self):
        for pc_item in self.point_clouds.items():
            if pc_item[0] < self.nActiveCollections:
                pc_item[1].clearQueues()
                
#    def setNewSubsetCallback( self, callback ):
#        'NewSubset'
                       
    def getPointCloud(self, pcIndex ):
        return self.point_clouds.get( pcIndex, None )

    def setScalarRange( self, scalar_range ):
        for pc in self.point_clouds.values():
            pc.setScalarRange( scalar_range )
            
    def applyColorRange( self, range_type ):
        color_range = [ float("inf"), -float("inf") ]
        for pc in self.point_clouds.values():
            crange = pc.getValueRange( range_type )
            color_range[0] = min( color_range[0], crange[0])
            color_range[1] = max( color_range[1], crange[1])
        self.setScalarRange( color_range )
        return color_range
            
    def getNLevels(self):
        for pc in self.point_clouds.values():
            nlev = pc.getNLevels()
            if nlev: return nlev
        return None
        
    def setPointSize( self, point_size ) :  
        for pc in self.point_clouds.values():
            pc.setPointSize( point_size )
    
    def values(self):
        return self.point_clouds.values()
    
    def setTopo( self, topo, **args ):
        pts = None
        for pc_item in self.point_clouds.items():
            if pc_item[0] < self.nActiveCollections:
                pts = pc_item[1].setTopo( topo, **args )
        return pts

    def postDataQueueEvent( self ):
        QtCore.QCoreApplication.postEvent( self, QtCore.QTimerEvent( self.dataQueueTimer ) ) 
    

def destroy_all_monsters():
#                                              Cleanup abandoned processes
    import subprocess, signal    
    proc_specs = subprocess.check_output('ps').split('\n')
    for proc_spec in proc_specs:
        if 'CPCViewer' in proc_spec:
            pid = int( proc_spec.split()[0] )
            if pid <> os.getpid():
                os.kill( pid, signal.SIGKILL )
                print "Killing proc: ", proc_spec
      
if __name__ == '__main__':
    
    destroy_all_monsters()

    
        
        
            