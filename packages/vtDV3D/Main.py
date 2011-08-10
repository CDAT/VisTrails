'''
Created on Jul 20, 2011

@author: tpmaxwel
'''
import sys, os
from PyQt4 import QtGui
import gui.application, core.requirements
from HyperwallManager import HyperwallManager

def restore_stdout():
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

class vtDV3DApplicationSingleton( gui.application.VistrailsApplicationSingleton ):

    def __init__(self):
        gui.application.VistrailsApplicationSingleton.__init__(self)
        self.vtPathList = []
        
    def open_vistrails(self):
        from core.db.locator import FileLocator
        if self.input:
            vtpath  = os.environ.get('VTPATH','')
            self.vtPathList = vtpath.split(':')
            if hasattr( self, "resource_path" ): self.vtPathList.append( self.resource_path )
            dotVistrails = self.temp_configuration.dotVistrails
            self.vtPathList.append( os.path.join( dotVistrails, "workflows" ) ) 
            for vistrail_filename in self.input:
                for workflow_dir in self.vtPathList:
                    if workflow_dir: vistrail_filename = os.path.join( workflow_dir, vistrail_filename + '.vt' )
                    if os.path.isfile( vistrail_filename ):
                        print " Reading vistrail: ", vistrail_filename
                        f = FileLocator(vistrail_filename)
                        self.builderWindow.viewManager.open_vistrail(f) 
                        break
            self.builderWindow.viewModeChanged(0)   

    def interactiveMode(self):  
        if self.temp_configuration.check('showSplash'):
            self.splashScreen.finish(self.builderWindow)
        self.builderWindow.create_first_vistrail()
        self.builderWindow.modulePalette.updateFromModuleRegistry()
        self.builderWindow.modulePalette.connect_registry_signals()
        
        if not self.temp_configuration.showSpreadsheetOnly:
            if self.builderWindow.is_main_window:
                self.setActiveWindow(self.builderWindow)
                self.builderWindow.activateWindow()
                self.builderWindow.show()
                self.builderWindow.raise_()
            else:
                self.builderWindow.hide()
        else:
            self.builderWindow.hide()
                        
    def init( self, optionsDict ):
        rv = gui.application.VistrailsApplicationSingleton.init( self, optionsDict )
        restore_stdout()
        return rv
        
def start_application(optionsDict=None):
    """Initializes the application singleton."""
    if gui.application.VistrailsApplication:
        debug.critical("Application already started.")
        return
    VistrailsApplication = vtDV3DApplicationSingleton()
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
        core.requirements.check_all_vistrails_requirements()
    except core.requirements.MissingRequirement, e:
        msg = ("VisTrails requires %s to properly run.\n" % e.requirement)
        debug.critical("Missing requirement", msg)
        sys.exit(1)
    gui.application.VistrailsApplication = VistrailsApplication
    x = VistrailsApplication.init(optionsDict)
    if x == True: return VistrailsApplication
    if gui.application.VistrailsApplication:
        gui.application.VistrailsApplication.finishSession()
    sys.exit(v)
    
                
def executeVistrail( *args, **kwargs ):
    core.requirements.check_pyqt4()     
    try:
        optionsDict = kwargs.get( 'options', None )
        app = start_application( optionsDict )
        app.open_vistrails()
    except SystemExit, e:
        restore_stdout()
        print "Uncaught exception on initialization: %s" % e
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        sys.exit(e)
    except Exception, e:
        restore_stdout()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        sys.exit(255)
    if (app.temp_configuration.interactiveMode and not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
     
    HyperwallManager.shutdown()   
#    gui.application.stop_application()
    sys.exit(v)

if __name__ == '__main__':
    optionsDict = {  'hw_role'  : 'none'  }         
    executeVistrail( options=optionsDict )
 
