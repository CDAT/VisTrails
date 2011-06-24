'''
Created on May 16, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
import sys, copy, os, argparse, gui, subprocess
from gui.application import VistrailsApplication
from packages.spreadsheet.spreadsheet_config import configuration as spreadsheet_configuration
from vtDV3DConfiguration import configuration as dv3d_configuration
from vtUtilities import *
HYPERWALL_SRC_PATH = os.path.join( os.path.dirname(__file__),  'hyperwall')

class HyperwallManagerSingleton(QtCore.QObject):

    def __init__( self, **args ):
        self.connected = False
        self.cells = {}
        self.cellIds = {}
        self.rowCount = spreadsheet_configuration.rowCount
        self.columnCount = spreadsheet_configuration.columnCount
        self.nCells = self.rowCount * self.columnCount
        self.server = None
        self.client = None
        self.deviceName = None
        self.resource_path = None
        self.isServer = False
        self.isClient = False
        
    def getDimensions(self):
        return ( self.columnCount, self.rowCount )
        
    def getCellCoordinates(self, cellIndex ):
        row = cellIndex / self.columnCount
        col = cellIndex % self.columnCount
        return ( col, row )

    def getCellIndex(self, dims ):
        return dims[1] * self.columnCount + dims[0]
        
    def getCellCoordinatesForModule( self, moduleId ):
        cellData = self.cells.get( moduleId, None )
        if cellData == None:
            for cellIndex in range( self.nCells ):
                if not cellIndex in self.cellIds: 
                    return self.getCellCoordinates( cellIndex )
        else: return cellData[2] 
        
    def addCell( self, moduleId, vistrailName, versionName, dimensions ):
        self.cells[ moduleId ] = ( vistrailName, versionName, dimensions )
        self.cellIds[ self.getCellIndex( dimensions ) ] = moduleId
        print " HyperwallManager--> addCell: %s " % str( ( moduleId, vistrailName, versionName, dimensions ) )
        
    def initialize( self ):
        app = gui.application.VistrailsApplication
        app.resource_path = None
        hwConfig = app.temp_configuration
        self.processList = []

        self.deviceName = dv3d_configuration.hw_name
        role = hwConfig.hw_role if hasattr( hwConfig, 'hw_role' ) else None
        self.isServer = ( role == 'server' )
        self.isClient = ( role == 'client' )
        set_hyperwall_role( role )
        hw_port = dv3d_configuration.hw_server_port
        hw_server = dv3d_configuration.hw_server
        hw_dims = [ dv3d_configuration.hw_width, dv3d_configuration.hw_height ]

        if self.isServer:
            from hyperwall.iVisServer.iVisServer import QiVisServer
            app.resource_path = os.path.expanduser( dv3d_configuration.hw_resource_path )           
            self.server = QiVisServer( self.deviceName, hw_dims, hw_port, app.resource_path )
            self.connectSignals()
            
            nodeList = dv3d_configuration.hw_nodes.split(',')
            print "hwServer initialization, server: %x, mgr: %x, dims=%s, nodes=%s" % ( id(self.server), id( self ), str(hw_dims), str(nodeList) )
            nodeIndex = 0
            for node in nodeList:
                if node:
                    nodeName = node.strip()
                    self.spawnRemoteViewer( nodeName, nodeIndex )
                    nodeIndex = nodeIndex + 1
                
        if self.isClient:
            node_index = hwConfig.hw_node_index
            hw_x = node_index / hw_dims[1]
            hw_y = node_index % hw_dims[1]
            from hyperwall.iVisClient.iVisClient import QiVisClient
            self.client = QiVisClient(   self.deviceName, hw_x, hw_y, 1, 1, hw_server, hw_port,
                                         dv3d_configuration.hw_displayWidth, dv3d_configuration.hw_displayHeight )
                

    def spawnRemoteViewer( self, node, nodeIndex, debug=False ):
        localhost = os.uname()[1]
        debugStr = ('/usr/X11/bin/xterm -sb -sl 20000 -display :0.0 -e ') if debug else ''
        optionsStr = "-Y" if debug else ''  
#            cmd = "ssh %s %s '%s /usr/local/bin/bash -c \"source ~/.vistrails/hw_env; export HW_NODE_INDEX=%d; export DISPLAY=:0.0; python %s/main/client.py\" ' " % ( optionsStr, node, debugStr, nodeIndex, HYPERWALL_SRC_PATH )
#        cmd = "ssh %s %s '%s /usr/local/bin/bash -c \"export HW_NODE_INDEX=%d; export DISPLAY=:0.0; ~/dev/exe/hw_vistrails_client\" ' " % ( optionsStr, node, debugStr, nodeIndex )
        cmd = [ "ssh", node, '/usr/local/bin/bash -c \"export HW_NODE_INDEX=%d; export DISPLAY=:0.0; ~/dev/exe/hw_vistrails_client\" ' % ( nodeIndex ) ]
        print " --- Executing: ", ' '.join(cmd)
        try:
#            os.system( cmd )
            p = subprocess.Popen( cmd, stdout=sys.stdout, stderr=sys.stderr ) 
        except Exception, err:
            print>>sys.stderr, " Exception in spawnRemoteViewer: %s " % str( err )
        self.processList.append( p )  
 
    
#    def registerPipeline(self):
#        buildWin = VistrailsApplication.builderWindow
#        buildWin.viewManager.open_vistrail(f) 
        
    def connectSignals(self):
        if not self.connected:
            try:
                buildWin = VistrailsApplication.builderWindow
                buildWin.connect( buildWin.viewToolBar.executeAction(), QtCore.SIGNAL('triggered(bool)'), onExecute )
                buildWin.connect( buildWin.executeCurrentWorkflowAction, QtCore.SIGNAL('triggered(bool)'), onExecute )
                self.connected = True
                print " Hyperwall Manager connected to control signals "
            except:
                pass
        
    def executeCurrentWorkflows( self ):
        if self.isServer:  
            for moduleId in self.cells: 
                self.executeCurrentWorkflow( moduleId )

    def executeCurrentWorkflow( self, moduleId ):
        if self.isServer: 
           ( vistrailName, versionName, dimensions ) = self.cells[ moduleId ] 
           print "  *** ExecuteWorkflow--> cell: %s" % str( moduleId )
           self.server.executePipeline( self.deviceName, vistrailName, versionName, moduleId, dimensions )
        
    def processInteractionEvent( self, event, screen_dims  ):
        print "HyperwallManager:processInteractionEvent"
        if self.isServer: self.server.processInteractionEvent( self.deviceName, event, screen_dims )        
    
HyperwallManager = HyperwallManagerSingleton()

def onExecute( ):
    pass
#    HyperwallManager.executeCurrentWorkflows()


