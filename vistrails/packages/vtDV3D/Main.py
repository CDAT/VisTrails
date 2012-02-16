'''
Created on Jul 20, 2011

@author: tpmaxwel
'''

import sys, os, traceback
from PyQt4 import QtGui
import core.application, gui.application, gui.requirements
from HyperwallManager import HyperwallManager
from packages.spreadsheet.spreadsheet_controller import spreadsheetController

def maximizeSpreadsheet():
    spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
#    spreadsheetWindow.show()
#    spreadsheetWindow.activateWindow()
#    spreadsheetWindow.raise_()
    tabControllerStack = spreadsheetWindow.tabControllerStack
    spreadsheetWindow.stackedCentralWidget.removeWidget ( tabControllerStack )
    tabControllerStack.showMaximized()
    
    
    
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


#def restore_stdout():
#    sys.stdout = sys.__stdout__
#    sys.stderr = sys.__stderr__
#
#class vtDV3DApplicationSingleton( gui.application.VistrailsApplicationSingleton ):
#
#    def __init__(self):
#        gui.application.VistrailsApplicationSingleton.__init__(self)
#        self.vtPathList = []
#        
#    def open_vistrails(self):
#        from core.db.locator import FileLocator
#        if self.input:
#            vtpath  = os.environ.get('VTPATH','')
#            self.vtPathList = vtpath.split(':')
#            if hasattr( self, "resource_path" ): self.vtPathList.append( self.resource_path )
#            dotVistrails = self.temp_configuration.dotVistrails
#            self.vtPathList.append( os.path.join( dotVistrails, "workflows" ) ) 
#            for vistrail_filename in self.input:
#                for workflow_dir in self.vtPathList:
#                    if workflow_dir: vistrail_filename = os.path.join( workflow_dir, vistrail_filename + '.vt' )
#                    if os.path.isfile( vistrail_filename ):
#                        print " Reading vistrail: ", vistrail_filename
#                        f = FileLocator(vistrail_filename)
#                        self.builderWindow.open_vistrail(f) 
#                        break
#
#    def setwindowTitle( self, title ):
#       self.uvcdatWindow.setWindowTitle( title )
#
##    def interactiveMode(self): 
##        if self.temp_configuration.check('showSplash'):
##            self.splashScreen.finish(self.builderWindow)
##        self.builderWindow.create_first_vistrail()
##        self.builderWindow.modulePalette.updateFromModuleRegistry()
##        self.builderWindow.modulePalette.connect_registry_signals()
##        
##        self.process_interactive_input()
##        
##        if not self.temp_configuration.showSpreadsheetOnly:
##            if self.builderWindow.is_main_window:
##                self.setActiveWindow(self.builderWindow)
##                self.builderWindow.activateWindow()
##                self.builderWindow.show()
##                self.builderWindow.raise_()
##            else:
##                self.builderWindow.hide()
##        else:
##            self.builderWindow.hide()
#                        
#    def init( self, optionsDict=None ):
#        rv = gui.application.VistrailsApplicationSingleton.init( self, optionsDict )
#        restore_stdout()
#        return rv
#def start_application1(optionsDict):
#    """Initializes the application singleton."""
#    if gui.application.get_vistrails_application():
#        debug.critical("Application already started.")
#        return
#    VistrailsApplication = vtDV3DApplicationSingleton()
#    if VistrailsApplication.is_running():
#        debug.critical("Found another instance of VisTrails running")
#        msg = str(sys.argv[1:])
#        debug.critical("Will send parameters to main instance %s" % msg)
#        res = VistrailsApplication.send_message(msg)
#        if res:
#            sys.exit(0)
#        else:
#            sys.exit(1)
#    try:
#        core.requirements.check_all_vistrails_requirements()
#    except core.requirements.MissingRequirement, e:
#        msg = ("VisTrails requires %s to properly run.\n" % e.requirement)
#        debug.critical("Missing requirement", msg)
#        sys.exit(1)
#    core.application.VistrailsApplication = VistrailsApplication
#    x = VistrailsApplication.init(optionsDict)
#    if x == True:
#        title = optionsDict.get( 'title', 'UVCDAT' )
#        VistrailsApplication.uvcdatWindow.setWindowTitle( title )
#        VistrailsApplication.uvcdatWindow.showBuilderWindowActTriggered() 
#        return VistrailsApplication
#    app = gui.application.get_vistrails_application()
#    if app:
#        app.finishSession()
#    sys.exit(v)
    
                
def executeVistrail1( *args, **kwargs ):
    disable_lion_restore()
    gui.requirements.check_pyqt4()
    
    title = kwargs.get( 'title', 'UVCDAT' )
    hw_role = kwargs.get( 'role', None ) 
    node_index = kwargs.get( 'node_index', -1 ) 
    full_screen = kwargs.get( 'full_screen', True ) 
    HyperwallManager.hw_role = hw_role 
    HyperwallManager.node_index = node_index 
    HyperwallManager.full_screen = full_screen 

    try:
        optionsDict = kwargs.get( 'options', None )
        v = gui.application.start_application()
        if v != 0:
            app = gui.application.get_vistrails_application()
            if app: app.finishSession()
            sys.exit(v)
        app = gui.application.get_vistrails_application()
    except SystemExit, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
    
    app.uvcdatWindow.setWindowTitle( title )
    app.uvcdatWindow.showBuilderWindowActTriggered() 
    v = app.exec_()
    if hw_role: HyperwallManager.shutdown()      
    gui.application.stop_application()
    sys.exit(v)

 
def executeVistrail( *args, **kwargs ):
    disable_lion_restore()
    gui.requirements.check_pyqt4()
    optionsDict = kwargs.get( 'options', None )
    title = kwargs.get( 'title', 'UVCDAT' )
    showBuilder = kwargs.get( 'showBuilder', False )

    try:
        v = gui.application.start_application( optionsDict )
        if v != 0:
            app = gui.application.get_vistrails_application()
            if app:
                app.finishSession()
            sys.exit(v)
        app = gui.application.get_vistrails_application()
    except SystemExit, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
                
    app.uvcdatWindow.setWindowTitle( title )
    if showBuilder: app.uvcdatWindow.showBuilderWindowActTriggered() 
    v = app.exec_()
    HyperwallManager.shutdown()      
    gui.application.stop_application()
    sys.exit(v)

if __name__ == '__main__':  
    optionsDict = { "hw_role" : 'hw_server' }   #  'global'   'hw_client'  'hw_server'    
    executeVistrail( options = optionsDict, title = " UVCDAT - server" )
