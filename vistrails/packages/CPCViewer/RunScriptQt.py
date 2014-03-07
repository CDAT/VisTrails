'''
Created on Feb 4, 2014

@author: tpmaxwel
'''

from __future__ import with_statement
from __future__ import division

_TRY_PYSIDE = True

try:
    if not _TRY_PYSIDE:
        raise ImportError()
    import PySide.QtCore as _QtCore
    QtCore = _QtCore
    import PySide.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = True
except ImportError:
    import sip
    try: sip.setapi('QString', 2)
    except: pass
    try: sip.setapi('QVariant', 2)
    except: pass
    import PyQt4.QtCore as _QtCore
    QtCore = _QtCore
    import PyQt4.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = False


# def _pyside_import_module(moduleName):
#     pyside = __import__('PySide', globals(), locals(), [moduleName], -1)
#     return getattr(pyside, moduleName)
# 
# 
# def _pyqt4_import_module(moduleName):
#     pyside = __import__('PyQt4', globals(), locals(), [moduleName], -1)
#     return getattr(pyside, moduleName)
# 
# 
# if USES_PYSIDE:
#     import_module = _pyside_import_module
# 
#     Signal = QtCore.Signal
#     Slot = QtCore.Slot
#     Property = QtCore.Property
# else:
#     import_module = _pyqt4_import_module
# 
#     Signal = QtCore.pyqtSignal
#     Slot = QtCore.pyqtSlot
#     Property = QtCore.pyqtProperty

import os, os.path, sys, argparse, time, multiprocessing
from packages.CPCViewer.DistributedPointCollections import kill_all_zombies
from packages.CPCViewer.PointCloudViewer import CPCPlot

parser = argparse.ArgumentParser(description='DV3D Point Cloud Viewer')
parser.add_argument( 'PATH' )
parser.add_argument( '-d', '--data_dir', dest='data_dir', nargs='?', default="~/data", help='input data dir')
parser.add_argument( '-t', '--data_type', dest='data_type', nargs='?', default="ECMWF", help='input data type')
ns = parser.parse_args( sys.argv )

kill_all_zombies()
app = QtGui.QApplication(['Point Cloud Plotter'])
point_size = 1
n_overview_points = 500000
grid_coords = ( None, None, None, None )
data_dir = os.path.expanduser( ns.data_dir )
height_varnames = []
var_proc_op = None
showGui = True

if ns.data_type == "WRF":
    data_file = os.path.join( data_dir, "WRF/wrfout_d01_2013-07-01_00-00-00.nc" )
    grid_file = None
    varname = "U"        
elif ns.data_type == "CAM":
    data_file = os.path.join( data_dir, "CAM/CAM_data.nc" )
    grid_file = os.path.join( data_dir, "CAM/ne120np4_latlon.nc" )
    varname = "U"
    height_varnames = [ "Z3" ]
elif ns.data_type == "ECMWF":
    data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ecmwf.xml" )
    grid_file = None
    varname = "U_velocity"   
elif ns.data_type == "GEOS5":
    data_file = os.path.join( data_dir, "AConaty/comp-ECMWF/ac-comp1-geos5.xml" )
    grid_file = None
    varname = "uwnd"   
elif ns.data_type == "MMF":
    data_file = os.path.join( data_dir, "MMF/diag_prs.20080101.nc" )
    grid_file = None
    varname = "u"
elif ns.data_type == "GEOD":
    file_name =  "temperature_19010101_000000.nc" # "vorticity_19010102_000000.nc" # 
    data_file = os.path.join( data_dir, "GeodesicGrid", file_name )
    grid_file = os.path.join( data_dir, "GeodesicGrid", "grid.nc" )
    varname = "temperature_ifc" # "vorticity" # 
elif ns.data_type == "CubedSphere":
    file_name =  "vsnow00-10.cam.h1.2006-12-01-00000.nc" # "vorticity_19010102_000000.nc" # 
    data_file = os.path.join( data_dir, "CubedSphere/3d", file_name )
    grid_file = None
#    grid_coords = ( 'lon', 'lat', 'lev', None )
    varname = "U"
elif ns.data_type == "CSU":
    file_name =  "psfc.nc" 
    data_file = os.path.join( data_dir, "ColoState", file_name )
    grid_file = os.path.join( data_dir, "ColoState", "grid.nc" )
    varname = "pressure" 

g = CPCPlot( ) 
g.init( init_args = ( grid_file, data_file, varname, grid_coords, var_proc_op ), n_overview_points=n_overview_points, n_cores=multiprocessing.cpu_count(), show=showGui  )
g.createConfigDialog( showGui )

renderWindow = g.renderWindow
 
app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
app.exec_() 
g.terminate() 
