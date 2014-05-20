'''
Created on Feb 4, 2014

@author: tpmaxwel
'''

import os.path, sys, argparse
from PyQt4 import QtCore, QtGui
from packages.CPCViewer.DistributedPointCollections import kill_all_zombies
from packages.CPCViewer.PointCloudViewer import CPCPlot
from packages.CPCViewer.ControlPanel import ConfigManager

def displayRenderWindowQt( renderWindow ):
    from packages.CPCViewer.PointCloudViewer import QVTKAdaptor
    import vtk
       
    app = QtGui.QApplication(['Point Cloud Plotter'])    
    widget = QVTKAdaptor( rw=renderWindow )
    widget.Initialize()
    widget.Start()        
    renderWindowInteractor = renderWindow.GetInteractor()           
    style = vtk.vtkInteractorStyleTrackballCamera()   
    renderWindowInteractor.SetInteractorStyle( style )
    g.connect( widget, QtCore.SIGNAL('event'), g.processEvent )  
    g.connect( widget, QtCore.SIGNAL("Close"), g.closeConfigDialog  ) 
    widget.show()      
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
    app.exec_() 
    g.terminate() 

parser = argparse.ArgumentParser(description='DV3D Point Cloud Viewer')
parser.add_argument( 'PATH' )
parser.add_argument( '-d', '--data_dir', dest='data_dir', nargs='?', default="~/data", help='input data dir')
parser.add_argument( '-t', '--data_type', dest='data_type', nargs='?', default="CAM", help='input data type')
ns = parser.parse_args( sys.argv )

kill_all_zombies()
point_size = 1
n_overview_points = 50000000
height_varname = None
data_dir = os.path.expanduser( ns.data_dir )
height_varnames = []
var_proc_op = None

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
    var_proc_op = None
    
g = CPCPlot() 
g.init( init_args = ( grid_file, data_file, varname, height_varname, var_proc_op ), n_overview_points=n_overview_points, n_cores=1  )

cfgManager = ConfigManager()
cfgManager.connect( cfgManager, QtCore.SIGNAL("ConfigCmd"), g.processConfigCmd )
cfgManager.build()
cfgManager.initParameters()

g.processCategorySelectionCommand( [ 'Subsets' ] )

renderWindow = g.renderWindow

g.start()

# verification code:
# displayRenderWindowQt( renderWindow )