'''
Created on Jul 3, 2013

@author: tpmaxwel
'''
import vtk, os

EnableMemoryLogging = True

class MemoryLogger:
    def __init__( self, enabled = True ):
        self.logfile = None
        self.enabled = enabled
        
    def close(self):
        if self.logfile <> None: 
            self.logfile.close( )
            self.logfile = None
        
    def log( self, label ):
        import shlex, subprocess, gc
        if self.enabled:
            gc.collect()
            args = ['ps', 'u', '-p', str(os.getpid())]
            psout = subprocess.check_output( args ).split('\n')
            ps_vals = psout[1].split()
            try:
                mem_usage_MB = float( ps_vals[5] ) / 1024.0
                mem_usage_GB = mem_usage_MB / 1024.0
            except ValueError, err:
                print>>sys.stderr, "Error parsing psout: ", str(err)
                print>>sys.stderr, str(psout)
                return
                    
            if self.logfile == None:
                self.logfile = open( "/tmp/TestAlloc-memory_usage.log", 'w' )
            self.logfile.write(" %10.2f (%6.3f): %s\n" % ( mem_usage_MB, mem_usage_GB, label ) )
            self.logfile.flush()
        
memoryLogger = MemoryLogger( EnableMemoryLogging )        

if __name__ == '__main__':
    
    memoryLogger.log('Start')
    
    array = vtk.vtkUnsignedShortArray()
    array.SetNumberOfComponents(1)
    array.Allocate(100000000)
    array.InsertTuple( 95000000, ( 1.0, ) )
    s0 = array.GetSize()
    print "Allocate, size = %d" % s0
    
    memoryLogger.log('Allocate')
    
    array.Initialize()
    array.Squeeze()
    s1 = array.GetSize()
    print "Free, size = %d" % s1
       
    memoryLogger.log('Free')
   
    
