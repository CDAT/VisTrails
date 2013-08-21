from PyQt4 import QtGui, QtCore
import cdms2, cdutil, genutil, sys, os
import gui.application

def disable_lion_restore():
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

def startup_app():
    from core.requirements import MissingRequirement, check_all_vistrails_requirements
    import platform, os
    
    disable_lion_restore()

    try:
        check_all_vistrails_requirements()
    except MissingRequirement, e:
        msg = ("VisTrails requires %s to properly run.\n" % e.requirement)
        debug.critical("Missing requirement", msg)
        sys.exit(1)
    
    try:
        v =  gui.application.start_application()
    except SystemExit, e:
        app = gui.application.get_vistrails_application()
        if app: app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = gui.application.get_vistrails_application()
        if app: app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        sys.exit(255)
        
startup_app() 
      
from packages.vtDV3D.API import UVCDAT_API, PlotType
uvcdat_api = UVCDAT_API()
cdmsfile = cdms2.open('/Developer/Data/AConaty/comp-ECMWF/ecmwf.xml')
Temperature = cdmsfile('Temperature')
Temperature = Temperature(lat=(90.0, -90.0),isobaric=(1000.0, 10.0),lon=(0.0, 359.0),time=('2011-5-1 0:0:0.0', '2011-5-1 18:0:0.0'),)
axesOperations = eval("{'lat': 'def', 'isobaric': 'def', 'lon': 'def', 'time': 'def'}")
for axis in list(axesOperations):
    if axesOperations[axis] == 'sum':
        Temperature = cdutil.averager(Temperature, axis='(%s)'%axis, weight='equal', action='sum')
    elif axesOperations[axis] == 'avg':
        Temperature = cdutil.averager(Temperature, axis='(%s)'%axis, weight='equal')
    elif axesOperations[axis] == 'wgt':
        Temperature = cdutil.averager(Temperature, axis='(%s)'%axis)
    elif axesOperations[axis] == 'gtm':
        Temperature = genutil.statistics.geometricmean(Temperature, axis='(%s)'%axis)
    elif axesOperations[axis] == 'std':
        Temperature = genutil.statistics.std(Temperature, axis='(%s)'%axis)
port_map = {'zScale': [2.0, 4.0, 1, 0.0, 1.0], 'colormap': ['jet', 0, 0, 1], 'colorScale': [208.39464294433594, 304.16563934326172, 1, 0.0, 1.0]}
uvcdat_api.createPlot( inputs=[Temperature], type=PlotType.SLICER, viz_parms=port_map )
uvcdat_api.run()
