'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

from vtUtilities import *

class ModuleStoreDatabase:
    
    moduleStoreDatabase = {}
    
    @staticmethod
    def getDatabase():
        import api
        page_id = id( api.get_current_controller() )
        return ModuleStoreDatabase.moduleStoreDatabase.setdefault( page_id, {} )
    
    @staticmethod
    def getModule( mid ):
        db = ModuleStoreDatabase.getDatabase()
        return db.get( mid, None )
    
    @staticmethod
    def forceGetModule( mid, default_instance ):
        db = ModuleStoreDatabase.getDatabase()        
        return db.setdefault( mid, default_instance )
    
    @staticmethod
    def getModuleList():
        db = ModuleStoreDatabase.getDatabase()     
        return db.values()
    
    @staticmethod
    def refreshParameters():
        executeWorkflow()
        db = ModuleStoreDatabase.getDatabase()  
        moduleList = db.values()
        for module in moduleList:  module.refreshParameters()
        for module in moduleList:  module.persistParameters()          
        executeWorkflow()
    
    
    
