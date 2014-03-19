'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

import sys, time, threading, inspect
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core.modules.module_registry import get_module_registry, ModuleRegistryException   
from packages.vtDV3D import ModuleStore
from packages.vtDV3D.InteractiveConfiguration import DV3DConfigurationWidget
from packages.vtDV3D.vtUtilities import *

################################################################################

class WorkflowModule( NotCacheable,  Module ):
      
    def __init__( self, **args ):
        Module.__init__(self) 
        
#     def __del__( self ):
#         print " $$$$$$$$$$$$$$$$$$$$$$ deleting WorkflowModule, id = %d $$$$$$$$$$$$$$$$$$$$$$ " % ( self.moduleInfo['moduleId'] )
# #         self.getPersistentModule( invalidate=True )
#         Module.__del__( self )

    def clear( self ):
        print " -------------------------------- clearing WorkflowModule, id = %d -------------------------------- " % ( self.moduleInfo['moduleId'] )
        self.getPersistentModule( invalidate=True )
        Module.clear( self )
        
    def compute(self):
        start_t = time.time() 
        DV3DConfigurationWidget.saveNewConfigurations()            
        pmod = self.getPersistentModule( force=True )
        pmod.dvCompute( wmod=self )
        end_t = time.time() 
#        print " +----------------------------------{ Computed Module %s: time = %.3f }----------------------------------+ " % ( self.__class__.__name__, ( end_t-start_t ) )

    def refreshVersion(self): 
        pmod = self.getPersistentModule( force=True )
        pmod.refreshVersion()
        return pmod
               
#    @classmethod    
#    def forceGetPersistentModule( klass, mid, **args ):
#        module = ModuleStore.getModule( mid ) 
#        if not module: module = ModuleStore.forceGetModule(  mid, klass.PersistentModuleClass( mid, **args ) )        
#        return module
    
    def getPersistentModule( self, **args ):
        mid = self.moduleInfo['moduleId']
        force = args.get('force',False)
        module = ModuleStore.getModule( mid ) 
        if force and ( module == None ):
            module = ModuleStore.forceGetModule(  mid, self.__class__.PersistentModuleClass( mid, **args ) ) 
        if module:     
            invalidate = args.get('invalidate',False)
            if invalidate:  module.invalidateWorkflowModule( self )
            else:           module.setWorkflowModule( self ) 
        return module
        
#    def updatePersistentModule( self ):
#        if not self._pmod: 
#            self._pmod = self.__class__.forceGetPersistentModule( self.moduleInfo['moduleId'], pipeline=self.moduleInfo['pipeline'] )
#        self._pmod.setWorkflowModule( self )
      
    @classmethod
    def registerConfigurableFunctions( klass, reg ):
        pmod = klass.PersistentModuleClass( -1 )
        for configFunct in pmod.configurableFunctions.values():
            if configFunct.args:
                reg.add_input_port(  klass, configFunct.name, configFunct.args, True )
                reg.add_output_port( klass, configFunct.name, configFunct.args, True )
                
    def getModuleID( self ):
        return self.moduleInfo['moduleId'] 


         

 
# if __name__ == '__main__':      
