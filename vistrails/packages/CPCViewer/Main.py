'''
Created on Nov 26, 2013

@author: tpmaxwell
'''

import sys
import os.path
from PyQt4 import QtCore, QtGui
from packages.CPCViewer.DistributedPointCollections import kill_all_zombies
from packages.CPCViewer.PointCloudViewer import CPCPlot, QVTKAdaptor
from packages.CPCViewer.ControlPanel import CPCConfigGui

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='DV3D Point Cloud Viewer')
    parser.add_argument( 'PATH' )
    parser.add_argument( '-d', '--data_dir', dest='data_dir', nargs='?', default="~/data", help='input data dir')
    parser.add_argument( '-t', '--data_type', dest='data_type', nargs='?', default="CAM", help='input data type')
    ns = parser.parse_args( sys.argv )
    
    kill_all_zombies()

    app = QtGui.QApplication(['Point Cloud Plotter'])
    widget = QVTKAdaptor()
    widget.Initialize()
    widget.Start()        
    point_size = 1
    n_overview_points = 500000
    height_varname = None
    data_dir = os.path.expanduser( ns.data_dir )
    height_varnames = []
    
    if ns.data_type == "WRF":
        data_file = os.path.join( data_dir, "WRF/wrfout_d01_2013-07-01_00-00-00.nc" )
        grid_file = None
        varname = "U"        
    elif ns.data_type == "CAM":
        data_file = os.path.join( data_dir, "CAM/f1850c5_t2_ANN_climo-native.nc" )
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
        
    g = CPCPlot( widget.GetRenderWindow() ) 
    widget.connect( widget, QtCore.SIGNAL('event'), g.processEvent )  
    g.init( init_args = ( grid_file, data_file, varname, height_varname ), n_overview_points=n_overview_points ) # , n_subproc_points=100000000 )
    
    configDialog = CPCConfigGui()
    w = configDialog.getConfigWidget()
    w.connect( w, QtCore.SIGNAL("ConfigCmd"), g.processConfigCmd )
#    configDialog.connect( g, QtCore.SIGNAL("UpdateGui"), configDialog.externalUpdate )
    configDialog.activate()
    
    configDialog.show()
    
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), g.terminate ) 
    app.connect( widget, QtCore.SIGNAL("Close"), configDialog.closeDialog ) 
    widget.show()  
    app.exec_() 
    g.terminate() 
