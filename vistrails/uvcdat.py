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

if __name__ == '__main__':
    disable_lion_restore()

    import core.requirements
    core.requirements.check_pyqt4()

    from PyQt4 import QtGui
    import gui.application
    import sys
    import os
    try:
        v = gui.application.start_application()
        if v != 0:
            if gui.application.VistrailsApplication:
                gui.application.VistrailsApplication.finishSession()
            sys.exit(v)
        app = gui.application.VistrailsApplication()
    except SystemExit, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        sys.exit(e)
    except Exception, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
    if (app.temp_configuration.interactiveMode and
        not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
        
    gui.application.stop_application()
    sys.exit(v)
