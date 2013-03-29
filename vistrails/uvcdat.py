"""Main file for the VisTrails distribution."""

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

def execute_vistrail( *args, **kwargs ):
    from core.db.locator import FileLocator
    disable_lion_restore()

    import gui.requirements
    gui.requirements.check_pyqt4()

    from PyQt4 import QtGui
    import gui.application
    import sys
    import os
    try:
        v = gui.application.start_application()
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

    resource_path = kwargs.get( 'dir', None )
    version = kwargs.get( 'version', None )
    if not resource_path:
        resource_path = app.resource_path if hasattr( app, "resource_path" ) else None
    for vistrail_name in args:
        workflow_dir =  resource_path if resource_path else os.path.join( packagePath, "workflows" )
        vistrail_filename = os.path.join( workflow_dir, vistrail_name + '.vt' )
        print " Reading vistrail: ", vistrail_filename
        f = FileLocator(vistrail_filename)
        app.builderWindow.open_vistrail_without_prompt( f, version, True ) 

    if (app.temp_configuration.interactiveMode and not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
        
    gui.application.stop_application()
    sys.exit(v)

if __name__ == '__main__':
    disable_lion_restore()

    import gui.requirements
    gui.requirements.check_pyqt4()

    from PyQt4 import QtGui
    import gui.application
    import sys
    import os
    try:
        v = gui.application.start_application()
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
    ## trying to load up file/var
    print app.uvcdatLoadFileStart,app.uvcdatLoadVariableStart
    if app.uvcdatLoadFileStart is not None:
        w = app.uvcdatWindow.dockVariable.widget()
        var= w.newVariable()
        var.setFileName(app.uvcdatLoadFileStart)
        var.updateFile()
        if app.uvcdatLoadVariableStart is not None:
            for i in range(var.varCombo.count()):
                if str(var.varCombo.itemText(i)).split()[0]==app.uvcdatLoadVariableStart:
                    var.varCombo.setCurrentIndex(i)
        #var.show()
        
    if (app.temp_configuration.interactiveMode and
        not app.temp_configuration.check('spreadsheetDumpCells')): 

        v = app.exec_()
        
    gui.application.stop_application()
    sys.exit(v)

