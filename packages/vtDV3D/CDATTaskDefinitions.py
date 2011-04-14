'''
Created on Mar 22, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
import sys, copy, os, cdms2
import numpy as np
import cdutil, genutil
from vtUtilities import *

#########################################################################################################################

def anomaly (a, axis=None ):
    from cdms2.MV2 import _extractMetadata, _conv_axis_arg, _makeMaskedArg, TransientVariable
    axes, attributes, id, grid = _extractMetadata(a)
    axis = _conv_axis_arg(axis)
    input = _makeMaskedArg(a)
    mean = input.mean(axis)
    result = np.expand_dims( mean, axis )
    new_shape = result.shape
    result = mean.view()
    result = result.reshape( new_shape )
    maresult = input - result
    return TransientVariable( maresult, axes=axes, attributes=attributes, id=id, grid=grid )

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
        pass
    
    @staticmethod
    def addTask( task_class ):
        TaskManager.TaskMap[ task_class.name ] = task_class
        
    @staticmethod
    def getTaskList():
        return TaskManager.TaskMap.keys()

    @staticmethod
    def getTask( name ):
        return TaskManager.TaskMap[name]

    @staticmethod
    def getTaskInstance( name, **args ):
        instance = TaskManager.TaskMap[name]
        return instance( **args )

#########################################################################################################################

class CDATTask(QtCore.QObject):
    inputs = [ 'input', ]
    outputs = [ 'output', ]
    
    def __init__( self, cdmsDataset, **args ):
        self.cdmsDataset = cdmsDataset
        self.inputMap = None
        self.outputMap = None
        self.module = None
    
    @classmethod    
    def getOutputDimensionality( klass, output, varDimMap ):
        input = klass.inputs[0] 
        return varDimMap.get( input, None ) 
                
    def compute( self, iTimeIndex, **args ):
        self.execute( iTimeIndex )
        
    def getInputMap( self, module ):
        self.inputMap = {}
        self.outputMap = {}
        key_list = []
        self.module = module
        taskInputData = module.getInputValue( "task"  ) 
        taskMap =  decodeFromString( getItem( taskInputData ) ) if taskInputData else None   
        taskData =  taskMap.get( self.cdmsDataset.id, None ) if taskMap else None
        if taskData:
            inputRecs = taskData[1].split(';')
            key_list.append( self.cdmsDataset.dataset.id )
            for inputRec in inputRecs:
                inputData = inputRec.split(',')
                self.inputMap[ inputData[0] ] = inputData[1]
                key_list.append( inputData[1] )
            outputRecs = taskData[2].split(';')
            for outputRec in outputRecs:
                outputData = outputRec.split(',')
                self.outputMap[ outputData[0] ] = outputData[1]
            return '.'.join( key_list ) 
            
    def getInputName( self, iInputIndex  ):
        varName = self.inputMap.get( self.__class__.inputs[ iInputIndex ], None )
        if not varName: print>>sys.stderr, " No input %d specified for AnomalyTask" % ( iInputIndex )
        return varName

    def getOutputName( self, iOutputIndex  ):
        varName = self.outputMap.get( self.__class__.outputs[ iOutputIndex ], None )
        if not varName: print>>sys.stderr, " No output %d specified for AnomalyTask" % ( iOutputIndex )
        return varName

#########################################################################################################################
    
class AnomalyTask( CDATTask ):
    name = 'Anomaly'

    def __init__( self, cdmsDataset, **args ):
        CDATTask.__init__( self, cdmsDataset, **args )
        
    def execute( self, iTimeIndex ):
        varName = self.getInputName( 0 )
        if varName:
            input = self.cdmsDataset.getVarDataTimeSlice( varName, iTimeIndex )
            if input.id <> "NULL":
                print " Computing anomaly for variable %s " % varName
                lon_axis = input.getLongitude()
                lon_index = input.getAxisIndex( lon_axis.id ) 
                output = anomaly( input, lon_index )
                outputName = self.getOutputName( 0 )
                if not outputName: outputName = "%s.%s.%s" % ( varName, self.name, self.__class__.outputs[0] )
                self.cdmsDataset.addTransientVariable( outputName, output )
    
TaskManager.addTask( AnomalyTask )
        
#########################################################################################################################
        
class ZonalAveTask( CDATTask ):
    name = 'ZonalAve'

    def __init__( self, cdmsDataset, **args ):
        CDATTask.__init__( self, cdmsDataset, **args )
        
    def execute( self, iTimeIndex ):
        varName = self.getInputName( 0 )
        if varName:
            input = self.cdmsDataset.getVarDataTimeSlice( varName, iTimeIndex )
            if input.id <> "NULL":
                print " Computing average for variable %s " % varName
                lon_axis = input.getLongitude()
                lon_index = input.getAxisIndex( lon_axis.id ) 
                output = average( input, lon_index )
                outputName = self.getOutputName( 0 )
                if not outputName: outputName = "%s.%s.%s" % ( varName, self.name, self.__class__.outputs[0] )
                self.cdmsDataset.addTransientVariable( outputName, gridded_zonal_ave )
    
TaskManager.addTask( ZonalAveTask )
        
##########################################################################################################################

class DifferenceTask( CDATTask ):
    inputs = [ 'input0', 'input1' ]
    name = 'Difference'

    def __init__( self, cdmsDataset, **args ):
        CDATTask.__init__( self, cdmsDataset, **args )
                        
    def execute( self, iTimeIndex ):
        varName0 = self.getInputName( 0 )
        varName1 = self.getInputName( 1 )
        if varName0 and varName1: 
            print 'Execute Difference task, timestep = %d' % iTimeIndex
            input0 = self.cdmsDataset.getVarDataTimeSlice( varName0, iTimeIndex )
            input1 = self.cdmsDataset.getVarDataTimeSlice( varName1, iTimeIndex )
            try:
                id0, id1 = input0.id, input1.id  
            except Exception, err:
                print>>sys.stderr, "Error: Data is missing from dataset %s at timestep %d" %  ( self.cdmsDataset.id, iTimeIndex )
                return          
            if (input0.id <> "NULL") and (input1.id <> "NULL"):
                from cdms2.MV2 import subtract, minimum, maximum
                difference = subtract( input0, input1 )
                outputName = self.getOutputName( 0 )
                if not outputName: outputName = "%s.%s.%s.%s" % ( varName0, varName1, self.name, self.__class__.outputs[0] )
#                maxval = maximum( difference )
#                minval = minimum( difference )
                self.cdmsDataset.addTransientVariable( outputName, difference )
    
TaskManager.addTask( DifferenceTask )
        
#########################################################################################################################
        
        
        
        
        