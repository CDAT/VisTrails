'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

from vtUtilities import *   
from collections import OrderedDict 
moduleStoreDatabase = {}
cells = OrderedDict()

def getDatabase():
    import api
    global moduleStoreDatabase
    page_id = id( api.get_current_controller() )
    return moduleStoreDatabase.setdefault( page_id, {} )

def getModule( mid ):
    db = getDatabase()
    return db.get( mid, None )

def forceGetModule(  mid, default_instance ):
    db = getDatabase()        
    return db.setdefault( mid, default_instance )

def getModuleList():
    db = getDatabase()     
    return db.values()

def getModuleIDs():
    db = getDatabase()     
    return db.keys()

def refreshParameters(self):
    executeWorkflow()
    db = getDatabase()  
    moduleList = db.values()
    for module in moduleList:  module.refreshParameters()
    for module in moduleList:  module.persistParameters()          
    executeWorkflow()

def popCell():
    try:                return cells.popitem(False)
    except KeyError:    return None

def addCell( id, location ):
    cells[id] = location

def getNCells():
    return len(cells) 

def getCell(id):
    return cells.get(id,None) 
     
    
