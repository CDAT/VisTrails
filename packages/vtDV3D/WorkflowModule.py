'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

import sys, time, threading, inspect
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry, ModuleRegistryException   
from ModuleStore import ModuleStoreDatabase 
from InteractiveConfiguration import DV3DConfigurationWidget
from vtUtilities import *

################################################################################

class WorkflowModule( Module ):
      
    def __init__( self, **args ):
        Module.__init__(self) 
        self.pmod = None 
        
    def __del__( self ):
#        print " $$$$$$$$$$$$$$$$$$$$$$ deleting class %s $$$$$$$$$$$$$$$$$$$$$$ " % ( self.__class__.__name__ )
        self.pmod.invalidateWorkflowModule( self ) 

    def compute(self):
        self.updatePersistentModule()
        self.pmod.dvCompute( wmod=self )
    
    @classmethod    
    def forceGetPersistentModule( klass, mid, **args ):            
        return ModuleStoreDatabase.forceGetModule(  mid, klass.PersistentModuleClass( mid, **args ) ) 

    @classmethod    
    def getPersistentModule( klass, mid ):            
        return ModuleStoreDatabase.forceGetModule(  mid, None ) 

    def updatePersistentModule( self ):
        DV3DConfigurationWidget.saveNewConfigurations()            
        if not self.pmod: 
            self.pmod = self.__class__.forceGetPersistentModule( self.moduleInfo['moduleId'], pipeline=self.moduleInfo['pipeline'] )
        self.pmod.setWorkflowModule( self )
      
    @classmethod
    def registerConfigurableFunctions( klass, reg ):
        pmod = klass.PersistentModuleClass( -1 )
        for configFunct in pmod.configurableFunctions.values():
            reg.add_input_port(  klass, configFunct.name, configFunct.args, True )
            reg.add_output_port( klass, configFunct.name, configFunct.args, True )
                
    def getModuleID( self ):
        return self.moduleInfo['moduleId'] 


         

 
# if __name__ == '__main__':      
