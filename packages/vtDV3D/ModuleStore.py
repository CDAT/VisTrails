'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

from vtUtilities import *

class ModuleStoreDatabase:
    
    moduleStoreDatabase = {}
    
    @staticmethod
    def getDatabase():
        return ModuleStoreDatabase.moduleStoreDatabase
    
    @staticmethod
    def getModule( mid ):
        return ModuleStoreDatabase.moduleStoreDatabase.get( mid, None )
    
    @staticmethod
    def forceGetModule( mid, default_instance ):
        return ModuleStoreDatabase.moduleStoreDatabase.setdefault( mid, default_instance )
    
    @staticmethod
    def getModuleList():
        return ModuleStoreDatabase.moduleStoreDatabase.values()
    
    @staticmethod
    def refreshParameters():
        executeWorkflow()
        moduleList = ModuleStoreDatabase.moduleStoreDatabase.values()
        for module in moduleList:  module.refreshParameters()
        for module in moduleList:  module.persistParameters()          
        executeWorkflow()
    
    
    
