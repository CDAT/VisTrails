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
from PyQt4.QtCore import SIGNAL, QObject

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
        data_packet = ExecutionDataPacket( ExecutionDataPacket.VARDATA, self.collection_index, self.point_collection.getVarData() )
        data_packet[ 'vrange' ] = self.point_collection.getVarDataRange() 
        data_packet[ 'grid' ] = self.point_collection.getGridType()  
        self.results.put( data_packet )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.POINTS, self.collection_index, self.point_collection.getPoints() )
        self.results.put( data_packet )

    def execute( self, args ):
        self.point_collection.execute( args )
        data_packet = ExecutionDataPacket( ExecutionDataPacket.INDICES, self.collection_index, self.point_collection.getPointIndices() )
        data_packet[ 'trange' ] = self.point_collection.getThresholdedRange() 
        self.results.put( data_packet )

class vtkPointCloud(QObject):

    shperical_to_xyz_trans = vtk.vtkSphericalTransform()
    radian_scaling = math.pi / 180.0 

    def __init__( self, pcIndex=0, nPartitions=1 ):
        QObject.__init__( self )
        self.nPartitions = nPartitions
        self.vardata = None
        self.vrange = None
        self.trange = None
        self.np_index_seq = None
        self.points = None
        self.pcIndex = pcIndex
        self.arg_queue = Queue() # JoinableQueue() 
        self.result_queue = Queue() # JoinableQueue()
        self.earth_radius = 100.0
        self.vtk_planar_points = None
        self.vtk_spherical_points = None
        self.np_points_data = None
        self.topo = PlotType.Planar
        self.grid = None
       
    def getPoint( self, iPt ):
        dval = self.vardata[ iPt ]
        pt = self.vtk_planar_points.GetPoint( iPt ) 
        self.printLogMessage( " getPoint: dval=%s, pt=%s " % ( str(dval), str(pt) ) ) 
        return pt, dval
        
    def printLogMessage(self, msg_str ):
        print " Proxy Node %d: %s" % ( self.pcIndex, msg_str )
        sys.stdout.flush()      
        
    def getResults( self, block = False ):
        try:
            result = self.result_queue.get( block )
        except Exception:
            return False
        if result.type == ExecutionDataPacket.VARDATA:
            self.vardata = result.data 
            self.vrange = result['vrange']
            self.grid = result['grid']
#            self.printLogMessage( " update vrange %s " % str(self.vrange) )      
        elif result.type == ExecutionDataPacket.INDICES:
            self.np_index_seq = result.data 
            self.trange = result['trange']
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
            self.updateScalars()   
        elif result.type == ExecutionDataPacket.INDICES:
            self.np_index_seq = result.data 
            self.trange = result['trange']
            self.updateVertices()  
        elif result.type == ExecutionDataPacket.POINTS:
            self.np_points_data = result.data 
            self.initPoints()  
        return True
    
    def getGrid(self):
        return self.grid
    
    def hasResultWaiting(self):
        return False
    
    def getThresholdingRange(self):
        return self.trange
    
    def generateSubset(self, subset_spec ):
        self.np_index_seq = None
#        self.printLogMessage( " Push on Arg queue: %s " % str( subset_spec ) )
        self.arg_queue.put( subset_spec,  False ) 
    
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
            self.waitForData( ExecutionDataPacket.INDICES )
        cell_sizes   = numpy.ones_like( self.np_index_seq )
        self.np_cell_data = numpy.dstack( ( cell_sizes, self.np_index_seq ) ).flatten()         
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray( self.np_cell_data ) 
        self.vertices.SetCells( cell_sizes.size, self.vtk_cell_data )     
        self.polydata.SetVerts(self.vertices)
        self.mapper.SetScalarRange( self.trange[0], self.trange[1] ) 
        self.polydata.Modified()
        self.mapper.Modified()
        self.actor.Modified()
        
    def waitForData( self, dtype ):
        self.printLogMessage( " waitForData type %d" % ( dtype ) )   
        while( self.getData( dtype ) == None ):
            self.getResults(True)
            time.sleep(0.05)
                                             
    def updateScalars( self, **args ):
        if isNone(self.vardata): 
            self.waitForData( ExecutionDataPacket.VARDATA )
        vtk_color_data = numpy_support.numpy_to_vtk( self.vardata ) 
        vtk_color_data.SetName( 'vardata' )       
        self.polydata.GetPointData().SetScalars( vtk_color_data )
        
    def initPoints( self, **args ):
        if isNone(self.np_points_data):
            self.waitForData( ExecutionDataPacket.POINTS )
        vtk_points_data = numpy_support.numpy_to_vtk( self.np_points_data )    
        vtk_points_data.SetNumberOfComponents( 3 )
        vtk_points_data.SetNumberOfTuples( len( self.np_points_data ) / 3 )     
        self.vtk_planar_points = vtk.vtkPoints()
        self.vtk_planar_points.SetData( vtk_points_data )
        
    def createPolydata( self, **args  ):
        self.polydata = vtk.vtkPolyData()
        vtk_pts = self.getPoints()
        self.polydata.SetPoints( vtk_pts )                         
        self.createPointsActor( self.polydata, **args )

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
                
    def createPointsActor( self, polydata, **args ):
        lut = args.get( 'lut', self.create_LUT() )
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetInput( self.polydata ) 
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        if lut: 
            self.mapper.SetLookupTable( lut )                
        self.actor = vtk.vtkActor()
        self.actor.SetMapper( self.mapper )
        if self.vrange:
            self.mapper.SetScalarRange( self.vrange[0], self.vrange[1] ) 
#            self.printLogMessage( " init vrange %s " % str(self.vrange) )    
        
    def start_subprocess( self, init_args, **args ):
        exec_target =  PointCollectionExecutionTarget( self.pcIndex, self.nPartitions, init_args ) 
        self.process = Process( target=exec_target, args=( self.arg_queue, self.result_queue ) )
        self.process.start()
               
    def terminate(self):
        self.process.terminate()

    def getNumberOfPoints(self): 
        return len( self.np_points_data ) / 3             
    
    def getPoints( self, **args ):
        if self.topo == PlotType.Spherical:
            if not self.vtk_spherical_points:
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
            if self.actor.GetVisibility():
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
          
class vtkPartitionedPointCloud( QObject ):
    
    def __init__( self, nPartitions, init_args  ):
        QObject.__init__( self )
        self.point_clouds = {}
        self.point_cloud_map = {}
        self.nPartitions = nPartitions
        self.nActiveCollections = ( nPartitions / 2 ) if self.nPartitions > 3 else 1
        self.current_subset_spec = None
        for pcIndex in range( nPartitions ):
            pc = vtkPointCloud( pcIndex, nPartitions )
            pc.start_subprocess( init_args )
            self.point_clouds[ pcIndex ] = pc
        for pc in self.point_clouds.values():
            pc.createPolydata()
            pc.updateScalars()
            self.point_cloud_map[ pc.actor ] = pc
            
    def startCheckingProcQueues(self):
        self.startTimer(100)
        
    def timerEvent( self, event ):
        self.checkProcQueues()
        
    def checkProcQueues(self):
        for pc_item in self.point_clouds.items():
            rv = pc_item[1].processResults()
            if rv <> ExecutionDataPacket.NONE:
                self.emit( SIGNAL('newDataAvailable'), pc_item[0], rv )
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
            
    def getPoint( self, actor, iPt ):
        pc = self.point_cloud_map.get( actor, None )
        if pc: return pc.getPoint( iPt )
        else: return ( "", "" ), ""

    def printLogMessage(self, msg_str ):
        print " vtkPartitionedPointCloud: %s" % ( msg_str )
        sys.stdout.flush()      
            
    def getActors(self):
        return [ pc.actor for pc in self.point_clouds.values() ]
    
    def generateSubset(self, subset_spec = None ):
        if subset_spec: self.current_subset_spec = subset_spec
        for pc_item in self.point_clouds.items():
            if pc_item[0] < self.nActiveCollections:
                pc_item[1].generateSubset( self.current_subset_spec )
                
    def getPointCloud(self, pcIndex ):
        return self.point_clouds.get( pcIndex, None )
    
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
    
    
if __name__ == '__main__':
#                                              Cleanup abandoned processes
    import subprocess, signal    
    proc_specs = subprocess.check_output('ps').split('\n')
    for proc_spec in proc_specs:
        if 'CPCViewer' in proc_spec:
            pid = proc_spec.split()[0]
            os.kill( int(pid), signal.SIGKILL )
            print "Killing proc: ", proc_spec
    
        
        
            