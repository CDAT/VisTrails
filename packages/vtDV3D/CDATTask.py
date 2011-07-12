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
        self.gridMap = None
        self.module = None
        self.name = 'task'
        self.grid = None
    
    @classmethod    
    def getOutputDimensionality( klass, output, varDimMap ):
        input = klass.inputs[0] 
        return varDimMap.get( input, None ) 
                
    def compute( self, timeValue ):
        self.execute( timeValue )

    def getInput( self, iInputIndex, timeValue, **args ):
        nInputs = len( self.__class__.inputs )
        varName = self.getInputName( iInputIndex )
        iOutputIndex = args.get( 'output', 0 )
        if varName:
            vNameComp =  varName.split('*')          
            input = self.cdmsDataset.getVarDataTimeSlice( vNameComp[0], vNameComp[1], timeValue )
            current_grid = input.getGrid()
            print " Get Input for task %s: %s[%.3f], grid=%s" % ( self.__class__.name, varName, timeValue.value, str(current_grid) )
#            if (nInputs > 1) and (self.grid == None): 
#                gridData = self.getGridData( iOutputIndex  )
#                gridRec = self.cdmsDataset.getGrid( gridData ) 
#                if gridRec: 
#                self.grid = cdutil.WeightedGridMaker( source=current_grid )
            try:
                id0 = input.id
                if input.id <> "NULL": return input
            except Exception, err: pass            
        raise ModuleError( self, "Data is missing from dataset %s for input %d to module %s at time %f" %  ( self.cdmsDataset.getDsetId(), iInputIndex, self.__class__.__name__, timeValue.value ) )               

    def getInputs( self, timeValue, **args ):
        nInputs = len( self.__class__.inputs )
        varList = []
        for iInputIndex in range( nInputs ):
            varName = self.getInputName( iInputIndex )
            iOutputIndex = args.get( 'output', 0 )
            if varName: varList.append( varName.split('*')  )            
        inputs = self.cdmsDataset.getVarDataTimeSlices( varList, timeValue )
        return inputs
 
    def setOutput( self, iOutputIndex, output ):
        outputName = self.getOutputName( iOutputIndex )
        varNameComp = outputName.split('*')
        self.cdmsDataset.addTransientVariable( varNameComp[-1], output )
        if output.rank() == 3: output.getAxis(2).designateLevel() 
        output._grid_ = None
        current_grid = output.getGrid()
        print " Set Output[%d] for task %s: var=%s, grid=%s" % ( iOutputIndex, self.__class__.name, varNameComp[-1], str(current_grid) )
                    
    def getInputMap( self, module ):
        self.inputMap = {}
        self.outputMap = {}
        self.gridMap = {}
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
                self.gridMap[ outputData[0] ] = outputData[3].split('*') if (len( outputData ) > 3) else None
            return '.'.join( key_list ) 
            
    def getInputName( self, iInputIndex  ):
        varName = self.inputMap.get( self.__class__.inputs[ iInputIndex ], None )
#        if not varName: print>>sys.stderr, " No input %d specified for AnomalyTask" % ( iInputIndex )
        return varName

    def getGridData( self, iOutputIndex  ):
        outputLabel = self.__class__.outputs[ iOutputIndex ]
        return self.gridMap.get( outputLabel, None )

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

