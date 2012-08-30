'''
Created on Mar 22, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
import sys, copy, os, cdms2, md5, imp, traceback
import numpy as np
import cdutil, genutil
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.CDATTask import CDATTask

enable_user_tasks = False

#########################################################################################################################

def average (a, axis=None ):
    from cdms2.MV2 import _extractMetadata, _conv_axis_arg, _makeMaskedArg, TransientVariable
    axes, attributes, id, grid = _extractMetadata(a)
    axis = _conv_axis_arg(axis)
    input = _makeMaskedArg(a)
    mean = input.mean(axis)
    result = np.expand_dims( mean, axis )
    new_shape = result.shape
    result = mean.view()
    result = result.reshape( new_shape )
    return TransientVariable( result, axes=axes, attributes=attributes, id=id, grid=grid )

#########################################################################################################################

class TaskManager(QtCore.QObject):
    
    TaskMap = {}
    
    def __init__( self, **args ):
        QtCore.QObject.__init__( self )
        pass
    
    @staticmethod
    def addTask( task_class ):
        TaskManager.TaskMap[ task_class.name ] = task_class
#        print " Add task %s to task map %d " % ( task_class.name, id(TaskManager.TaskMap) )

    @staticmethod
    def addUserTask( task_class ):
        try:
            user_task_name = '.'.join( [ os.getlogin(), task_class.name ] )
            TaskManager.TaskMap[ user_task_name ] = task_class
#            print " Add user task %s to task map %d " % ( user_task_name, id(TaskManager.TaskMap) )
        except Exception, err:
            print>>sys.stderr, "Can't add %s entity to TaskMap: %s " % ( str( task_class ), str(err) )
        
    @staticmethod
    def getTaskList():
        tasks = TaskManager.TaskMap.keys()
#        print " **** TaskMap{%d}--> getTaskList: %s  " % ( id(TaskManager.TaskMap), str( tasks ) )
        return tasks

    @staticmethod
    def getTask( name ):
        try:
            return TaskManager.TaskMap[name]
        except KeyError:
            return None

    @staticmethod
    def getTaskInstance( name, **args ):
        try:
            instance = TaskManager.TaskMap[name]
            return instance( **args )
        except KeyError:
            return None

#########################################################################################################################

        
#########################################################################################################################
        
class ZonalAveTask( CDATTask ):
    name = 'ZonalAve'
        
    def execute( self, timeValue ):
        input = self.getInput( 0, timeValue )
        lon_axis = input.getLongitude()
        lon_index = input.getAxisIndex( lon_axis.id ) 
        output = average( input, lon_index )
        self.setOutput( 0, output )
    
TaskManager.addTask( ZonalAveTask )
        
##########################################################################################################################

from cdms2.MV2 import subtract

class DifferenceTask( CDATTask ):
    inputs = [ 'input0', 'input1' ]
    name = 'Difference'
                        
    def execute( self, timeValue ):
        input0 = self.getInput( 0, timeValue )
        lev0 = input0.getLevel()
        input1 = self.getInput( 1, timeValue )
        lev1 = input1.getLevel()
        difference = subtract( input1, input0 )
        difference.setAxisList( input0.getAxisList() )
        self.setOutput( 0, difference )
    
TaskManager.addTask( DifferenceTask )

#########################################################################################################################

from cdms2.MV2 import hypot

class MagnitudeTask( CDATTask ):
    inputs = [ 'input0', 'input1' ]
    name = 'Magnitude'
                        
    def execute( self, timeValue ):
        input0 = self.getInput( 0, timeValue )        
        input1 = self.getInput( 1, timeValue )        
        magnitude = hypot( input0, input1 )
        self.setOutput( 0, magnitude )
    
TaskManager.addTask( MagnitudeTask )
       
#########################################################################################################################

def load_usr_task_modules( **args ):
    modules = []
    try:
        code_dir = os.path.expanduser(  args.get( 'dir', '~/.vistrails/tasks' )   )
        if os.path.isdir( code_dir ):
            code_dir_entries = os.listdir( code_dir )
            for entry in code_dir_entries:
                if os.path.splitext(entry)[1] == '.py':
                    code_path = os.path.join( code_dir, entry )
                    try:
                        try:
#                            print "Importing user task code from file %s " % code_path
                            fin = open( code_path, 'rb' )
                            mod = imp.load_source( md5.new(code_path).hexdigest(), code_path, fin )
                            modules.append( mod )
                            for attrName in vars(mod).keys():
                                userCodeEntity = getattr( mod, attrName )
                                isCDATTask = isinstance( userCodeEntity, CDATTask ) 
                                isCDATTaskType =  type(userCodeEntity) == type(CDATTask) 
                                isCDATTaskSubclass = isCDATTaskType and issubclass( userCodeEntity, CDATTask )
#                                print " Importing %s: %s " % ( str(userCodeEntity), str([isCDATTask,isCDATTaskType,isCDATTaskSubclass]) )
                                if isCDATTaskSubclass and hasattr( userCodeEntity, "name" ):
                                    TaskManager.addUserTask( userCodeEntity )
                        finally:
                            try: fin.close()
                            except: pass
                    except ImportError, x:
                        traceback.print_exc(file = sys.stderr)
                        raise
        else: print>>sys.stderr, " Alert-- task code extensions dir does not exist: '%s' " % code_dir
    except:
        traceback.print_exc(file = sys.stderr)
        raise
    return modules
        
if enable_user_tasks: load_usr_task_modules()        
        
        
        