'''
Created on May 11, 2011

@author: tpmaxwel
'''

from PyQt4 import QtCore, QtGui
from core.modules.vistrails_module import Module, ModuleError
import sys, copy, os, cdms2, traceback
import numpy as np
import cdutil, genutil
from vtUtilities import getItem

def deserializeTaskData( taskData ):
    taskMap = {}
    taskItems = taskData.split( '|' )
    for task_item in taskItems:
        task_entries = task_item.split('&')
        taskMap[ task_entries[0] ] = task_entries[1:]
    return taskMap
    
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

    def getInput( self, iInputIndex, iTimeIndex ):
        varName = self.getInputName( iInputIndex )
        if varName:
            vNameComp =  varName.split('*')
            input = self.cdmsDataset.getVarDataTimeSlice( vNameComp[0], vNameComp[1], iTimeIndex )
            try:
                id0 = input.id
                if input.id <> "NULL": return input
            except Exception, err: pass            
        raise ModuleError( self, "Data is missing from dataset %s for input %d to module %s at timestep %d" %  ( self.cdmsDataset.getDsetId(), iInputIndex, self.__class__.__name__, iTimeIndex ) )               

    def setOutput( self, iOutputIndex, output ):
        outputName = self.getOutputName( iOutputIndex )
        varNameComp = outputName.split('*')
        self.cdmsDataset.addTransientVariable( varNameComp[1], output )
                    
    def getInputMap( self, module ):
        self.inputMap = {}
        self.outputMap = {}
        dsid = self.cdmsDataset.getDsetId()
        key_list = []
        self.module = module
        taskInputData = module.getInputValue( "task"  ) 
        print " ---> CDATTask.taskInputData: %s " % taskInputData
        taskMap =  deserializeTaskData( getItem( taskInputData ) ) if taskInputData else None   
        taskData =  taskMap.get( dsid, None ) if taskMap else None
        if taskData:
            inputRecs = taskData[1].split(';')
            key_list.append( dsid )
            for inputRec in inputRecs:
                inputData = inputRec.split('+')
                self.inputMap[ inputData[0] ] = inputData[1]
                key_list.append( inputData[1] )
            outputRecs = taskData[2].split(';')
            for outputRec in outputRecs:
                outputData = outputRec.split('+')
                self.outputMap[ outputData[0] ] = outputData[1]
            return '.'.join( key_list ) 
            
    def getInputName( self, iInputIndex  ):
        varName = self.inputMap.get( self.__class__.inputs[ iInputIndex ], None )
#        if not varName: print>>sys.stderr, " No input %d specified for AnomalyTask" % ( iInputIndex )
        return varName

    def getOutputName( self, iOutputIndex  ):
        outputLabel = self.__class__.outputs[ iOutputIndex ]
        outputName = self.outputMap.get( outputLabel, None )
        if not outputName:
            dsid = None 
            inputBaseNames = []
            for iInputIndex in len( self.__class__.inputs.keys() ):
                inputName = self.getInputName( iInputIndex )
                inputNameComp = inputName.split('*')
                if dsid == None: dsid = inputNameComp[0]
                inputBaseNames.append( inputNameComp[1] )
            inputBaseName = '-'.join( inputBaseNames )
            outputName = "%s*%s.%s.%s" % ( dsid, inputBaseName, self.name, outputLabel )
        return outputName

