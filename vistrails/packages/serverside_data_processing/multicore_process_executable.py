'''
Created on Aug 14, 2013

@author: tpmaxwell
'''
import os, sys
from multiprocessing import Process, JoinableQueue, Lock
      

class ExecutionSpecs:
    
    def __init__( self, spec_file_path = None ):
        self.specs = {}
        if spec_file_path:
            self.parse_specs( spec_file_path )
        self.spec_directory = os.path.dirname( spec_file_path )
        
    def __str__(self):
        return str( self.specs )
        
    def parse_specs( self, spec_file_path ):
        self.specs = {}
        context = None
        try:
            spec_file = open( spec_file_path, "r" )  
            for line in spec_file.readlines():
                line = line.strip()
                if line and (line[0] <> '#'):
                    if '=' in line:      line_tokens = line.split('=')
                    elif ':' in line:    line_tokens = line.split(':')
                    else:                line_tokens = [ line ]
                    spec_name = line_tokens[0].strip()
                    if spec_name:
                        if len( line_tokens ) > 1:
                                values = [ elem.strip() for elem in line_tokens[1].split(',') ]
                                self.specs[ spec_name ] = values[0] if ( len(values) == 1 ) else values
                        else:
                            if spec_name[0] == '[':
                                context = spec_name.strip('[]')
        except Exception, err:
            print>>sys.stderr, "Error parsing spec file %s:\n %s " % ( spec_file_path, str(err) )
                        
    def getFloat(self, name, default_val = None ):
        return float( self.specs.get( name, default_val ) )

    def getInt(self, name, default_val = None ):
        return int( self.specs.get( name, default_val ) )

    def getBool(self, name, default_val = None ):
        val = self.specs.get( name, default_val )
        if ( type( val ) == type( "" ) ): return val.lower() in ( "yes", "true", "t", "1", "y" )
        return bool( val )

    def getStr(self, name, default_val = None ):
        return self.specs.get( name, default_val ) 

    def getPath(self, name, default_val = None ):
        value = self.specs.get( name, default_val ) 
        if value == ".": value = self.spec_directory
        return os.path.expanduser( os.path.expandvars( value ) )

    def getList(self, name, default_val = [] ):
        val = self.specs.get( name, default_val ) 
        if type( val ) == type( [] ): return val
        return [ val ]
    
    def put( self, name, val ):
        self.specs[ name ] = str( val )


class MulticoreExecutable :

    def __init__( self, executionTargetSubclass, **args ):
        self.nlocks = args.get('nlocks', 0 )
        self.ncores = args.get('ncores', 4 )
        self.executionTargetSubclass = executionTargetSubclass
        self.reset_queues()
        
    def reset_queues(self):              
        self.arg_queue = None
        self.proc_queue = [ ]
        self.locks = []  
    
    def execute( self, arg_tuple_list, **args ):
        if self.arg_queue <> None:
            print>>sys.stderr, " MulticoreExecutable error: processes currently running.  "
            return
        self.ncores = args.get('ncores', self.ncores )
        if self.ncores > 1:
            self.nlocks = args.get('nlocks', self.nlocks )
            block = args.get('block', True )
            self.locks = [ Lock() for iLock in range(self.nlocks) ]
            self.arg_queue = JoinableQueue() 
            for arg_tuple in arg_tuple_list:
                self.arg_queue.put( arg_tuple )
            
            for iP in range( self.ncores ):   
                p = Process( target=self.executionTargetSubclass(iP), args=( self.arg_queue, self.locks  ) )
                self.proc_queue.append( ( iP, p ) )
                p.start()
            print " Running %d procs" % len( self.proc_queue ); sys.stdout.flush()
            if block: self.block()
        else:
            target=self.executionTargetSubclass(0)
            for arg_tuple in arg_tuple_list:
                target.execute( arg_tuple )
                    
    def terminated(self):
        for p in self.proc_queue:
            if p.is_alive(): return False
        self.reset_queues()   
        return True
        
    def block(self):
        if self.arg_queue <> None: 
            self.arg_queue.join()
            self.reset_queues()              
        
    def terminate(self):
        for p in self.proc_queue:
            p.terminate()
        self.reset_queues()
        

class ExecutionTarget:
    
    def __init__( self, proc_index ):
        self.product_cache = {}
        self.proc_index = proc_index
        self.sync_locks = []
            
    def __call__( self, args_queue, sync_locks = [] ):
        from Queue import Empty
        self.sync_locks = sync_locks
        try:
            while True:
                args = list( args_queue.get( False ) )
                self.execute( args )
                args_queue.task_done()
        except Empty:
            print "\n *** P[%d]: Terminating process execution. *** \n" % self.proc_index; sys.stdout.flush()
            return
        
    def execute( self, args ):
        pass

if __name__ == '__main__':
    pass