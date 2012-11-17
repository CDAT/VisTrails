'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

from packages.vtDV3D.vtUtilities import *   
from collections import OrderedDict 
moduleStoreDatabase = {}
cdmsStoreDatabase = {}
#cells = OrderedDict()

def getDatabase():
    import api
    global moduleStoreDatabase
    page_id = 0
#    try: page_id = id( api.get_current_controller() )
#    except: pass
    return moduleStoreDatabase.setdefault( page_id, {} )

def getCdmsDatabase():
    import api
    global cdmsStoreDatabase
    page_id = 0
#    try: page_id = id( api.get_current_controller() )
#    except: pass
    return cdmsStoreDatabase.setdefault( page_id, {} )

def getModule( mid ):
    db = getDatabase()
    return db.get( mid, None )

def removeModule( mid ):
    db = getDatabase()
    try:        
        del db[ mid ]
        print>>sys.stderr, "  ______________________________ ModuleStore: deleting module %d ______________________________" % mid
    except:     return False
    return True

def forceGetModule(  mid, default_instance ):
    module = getModule( mid )
    if module == None:
        db = getDatabase()
        module = default_instance
        db[ mid ] = module   
        print>>sys.stderr, " ______________________________ Add module to ModuleStore: %d ______________________________ " %  mid   
    return module

def getModuleList():
    db = getDatabase()     
    return db.values()

def getModuleIDs():
    db = getDatabase()     
    return db.keys()

def getCdmsDataset( dsid ):
    db = getDatabase()
    return db.get( dsid, None )

def archiveCdmsDataset( dsid, ds ):
    db = getDatabase()
    db[ dsid ] = ds

def refreshParameters(self):
    executeWorkflow()
    db = getDatabase()  
    moduleList = db.values()
    for module in moduleList:  module.refreshParameters()
    for module in moduleList:  module.persistParameters()          
    executeWorkflow()

#def popCell():
#    try:                return cells.popitem(False)
#    except KeyError:    return None
#
#def addCell( id, location ):
#    cells[id] = location
#
#def getNCells():
#    return len(cells) 
#
#def getCell(id):
#    return cells.get(id,None) 
     
    
