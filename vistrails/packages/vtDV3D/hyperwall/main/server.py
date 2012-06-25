'''
Created on Jul 20, 2011

@author: tpmaxwel
'''

import sys, os, traceback
from PyQt4 import QtGui, QtCore
from core.requirements import check_all_vistrails_requirements
from gui.requirements import check_pyqt4, MissingRequirement
from gui.application import VistrailsApplicationSingleton, get_vistrails_application, set_vistrails_application
# from packages.vtDV3D.Main import *

def maximizeSpreadsheet():
    from packages.spreadsheet.spreadsheet_controller import spreadsheetController
    spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
    tabControllerStack = spreadsheetWindow.tabControllerStack
    spreadsheetWindow.stackedCentralWidget.removeWidget ( tabControllerStack )
    tabControllerStack.showMaximized()
    
class HWRunType :
     Client = 0
     Server = 1
     Desktop = 2 
    
def disable_lion_restore():
    """ Prevent Mac OS 10.7 to restore windows state since it would
    make Qt 4.7.3 unstable due to its lack of handling Cocoa's Main
    Window. """
    import platform
    if platform.system()!='Darwin': return
    release = platform.mac_ver()[0].split('.')
    if len(release)<2: return
    major = int(release[0])
    minor = int(release[1])
    if major*100+minor<107: return
    import os
    ssPath = os.path.expanduser('~/Library/Saved Application State/org.vistrails.savedState')
    if os.path.exists(ssPath):
        os.system('rm -rf "%s"' % ssPath)
    os.system('defaults write org.vistrails NSQuitAlwaysKeepsWindows -bool false')


def restore_stdout():
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

class vtDV3DApplicationSingleton( VistrailsApplicationSingleton ):

    def __init__(self, isClient):
        VistrailsApplicationSingleton.__init__( self )
        self.isClient = isClient

    def interactiveMode(self):
        """ interactiveMode() -> None
        Instantiate the GUI for interactive mode
        
        """     
        if self.temp_configuration.check('showSplash'):
            self.splashScreen.finish(self.builderWindow)
        # self.builderWindow.modulePalette.updateFromModuleRegistry()
        # self.builderWindow.modulePalette.connect_registry_signals()
        self.builderWindow.link_registry()
        self.uvcdatWindow.link_registry()
        
        self.process_interactive_input()
        if not self.temp_configuration.showSpreadsheetOnly:
            self.builderWindow.hide()
            self.showWindow(self.uvcdatWindow)
        self.builderWindow.create_first_vistrail( not self.isClient )
        

def shutdown():
    from packages.vtDV3D import HyperwallManager
    print " !! --shutdown-- !! "
    HyperwallManager.getInstance().shutdown()      

def start_uvcdat_application(optionsDict):
    """Initializes the application singleton."""
    VistrailsApplication = get_vistrails_application()
    if VistrailsApplication:
        debug.critical("Application already started.")
        return
    hw_role = optionsDict.get( "hw_role", 'global')
    spawn = optionsDict.get( "spawn", True )
    isClient = ( hw_role == 'hw_client' )
    VistrailsApplication = vtDV3DApplicationSingleton( isClient )
    set_vistrails_application( VistrailsApplication )
    if VistrailsApplication.is_running():
        debug.critical("Found another instance of VisTrails running")
        msg = str(sys.argv[1:])
        debug.critical("Will send parameters to main instance %s" % msg)
        res = VistrailsApplication.send_message(msg)
        if res:
            sys.exit(0)
        else:
            sys.exit(1)
    try:
        check_all_vistrails_requirements()
    except MissingRequirement, e:
        msg = ("VisTrails requires %s to properly run.\n" %
               e.requirement)
        debug.critical("Missing requirement", msg)
        sys.exit(1)
    x = VistrailsApplication.init(optionsDict)
    title =  ' UVCDAT - client ' if  isClient else " UVCDAT - server " 
    showBuilder = optionsDict.get( 'showBuilder', False )
    VistrailsApplication.uvcdatWindow.setWindowTitle( title )
    if showBuilder: VistrailsApplication.uvcdatWindow.showBuilderWindowActTriggered() 
    if x == True:
        return 0
    else:
        return 1
    
def init_hyperwall(optionsDict):
    from packages.vtDV3D import HyperwallManager
    hw_role = optionsDict.get( "hw_role", 'global')
    spawn = optionsDict.get( "spawn", True )
    HyperwallManager.getInstance().initialize( hw_role, spawn )      
     
def executeVistrail( *args, **kwargs ):
    disable_lion_restore()
    check_pyqt4()
    optionsDict = kwargs.get( 'options', None )

    try:
        v = start_uvcdat_application( optionsDict )
        if v != 0:
            app = get_vistrails_application()
            if app:
                app.finishSession()
            sys.exit(v)
        app = get_vistrails_application()
    except SystemExit, e:
        app = get_vistrails_application()
        if app:
            app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = get_vistrails_application()
        if app:
            app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
        
    init_hyperwall( optionsDict )
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), shutdown ) 
    v = app.exec_()
    

if __name__ == '__main__': 
    runType = HWRunType.Server 
    if runType == HWRunType.Desktop: optionsDict = { "hw_role" : 'global', "showBuilder": True, 'spawn': True }   #  'global'   'hw_client'  'hw_server' 
    if runType == HWRunType.Server:  optionsDict = {  'hw_role': 'hw_server', 'debug': 'False' } #, 'hw_nodes': 'localhost' }   
    if runType == HWRunType.Client:  
        node_index_str = os.environ.get('HW_NODE_INDEX',None)
        if node_index_str == None: raise EnvironmentError( 0, "Must set the HW_NODE_INDEX environment variable on client nodes")
        hw_node_index = int(node_index_str)
        optionsDict = {   'hw_role': 'hw_client',  'hw_node_index': hw_node_index, 'fullScreen': 'False'  } #, 'hw_nodes': 'localhost' }   
    executeVistrail( options = optionsDict )
