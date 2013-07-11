'''
Created on Mar 10, 2011

@author: tpmaxwel
'''

import gc
from packages.vtDV3D.vtUtilities import *   
from collections import OrderedDict 
moduleStoreDatabase = {}
cdmsStoreDatabase = {}
activeVariables = {}
activeVariable = None
debug = False

#cells = OrderedDict()

def getDatabase():
    import api
    global moduleStoreDatabase
    page_id = 0
    prj_controller = api.get_current_project_controller()
    try: page_id = prj_controller.name
    except: pass
    return moduleStoreDatabase.setdefault( page_id, {} )

def addActiveVariable( name, variable ):
    global activeVariables, activeVariable, debug
    activeVariables[name] = variable
    activeVariable = name
    if debug: print "^^^^^^^^vvvvvvvvv add Active Variable: ", name

def removeActiveVariable( name ):
    global activeVariables, activeVariable, debug
    if name in activeVariables:
        del activeVariables[name]
        if len( activeVariables ) == 0: activeVariable = None
        else: activeVariable = activeVariables.keys()[0]
        if debug: print "^^^^^^^^vvvvvvvvv remove Active Variable: %s, new: %s" % ( name, activeVariable )

def setActiveVariable( name ):
    global activeVariable, debug
    activeVariable = name   
    if debug: print "^^^^^^^^vvvvvvvvv set Active Variable: ", name

def getActiveVariable():
    global activeVariables, activeVariable, debug
    if debug: print "^^^^^^^^vvvvvvvvv get Active Variable: ", activeVariable
    return activeVariables.get( activeVariable, None )    

def getCdmsDatabase():
    import api
    global cdmsStoreDatabase
    page_id = 0
    prj_controller = api.get_current_project_controller()
    try: page_id = prj_controller.name
    except: pass
    return cdmsStoreDatabase.setdefault( page_id, {} )

def getModule( mid ):
    if mid == None: return None
    db = getDatabase()
    return db.get( mid, None )

def removeModule( mid ):
    db = getDatabase()
    try: 
        m = db.get( mid, None )
        if m:     
            m.clearReferrents()
            del db[ mid ]
            gc.collect()
#            referents = gc.get_referents(m)
            referrers = gc.get_referrers(m)
            del m
#            print "  ______________________________ ModuleStore: deleting module %d ______________________________" % mid
    except Exception, ex: 
        print>>sys.stderr, " _________ ModuleStore: Error deleting module %d : %s " % ( mid, str(ex) )    
        return False
    return True

def forceGetModule(  mid, default_instance ):
    module = getModule( mid )
    if module == None:
        db = getDatabase()
        module = default_instance
        db[ mid ] = module   
#        print>>sys.stderr, " ______________________________ Add module to ModuleStore: %d ______________________________ " %  mid   
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
     
    
