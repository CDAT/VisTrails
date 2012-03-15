'''
Created on May 16, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
import sys, copy, os, argparse, gui, subprocess, socket
from gui.application import get_vistrails_application
from packages.spreadsheet.spreadsheet_config import configuration as spreadsheet_configuration
from packages.vtDV3D.vtUtilities import *
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
        self.decimation = None
        self.screen_dims = None
        self.resource_path = None
        self.isServer = False
        self.isClient = False
        self.levelingState = None
        self.altMode = False
        self.opening_event = None
        self.intial_camera_pos = None
        
#    def __del__(self):
#        self.shutdown()

    def setLevelingState( self, state, altMode=False ):
        self.levelingState = state
        self.altMode = altMode

    def getLevelingState():
        return self.levelingState
        
    def shutdown(self):
        if self.isServer: 
            print "Shutting down hyperwall nodes."
            self.server.shutdownClients()
#        for proc in self.processList:
#            proc[0].kill()
#            proc[1].close()
        
    def getDimensions(self):
        return ( self.columnCount, self.rowCount )
        
    def getCellCoordinates(self, cellIndex ):
        row = cellIndex / self.columnCount
        col = cellIndex % self.columnCount
        return ( col, row )

    def getCellIndex(self, dims ):
        return dims[1] * self.columnCount + dims[0]
        
    def getCellCoordinatesForModule( self, moduleId ):
        if self.isClient: return ( 0, 0 )
        cellData = self.cells.get( moduleId, None )
        if cellData == None:
            for cellIndex in range( self.nCells ):
                if not cellIndex in self.cellIds: 
                    return self.getCellCoordinates( cellIndex )
        else: return cellData[2] 
        
    def addCell( self, moduleId, vistrailName, versionName, dimensions ):
        self.cells[ moduleId ] = ( vistrailName, versionName, dimensions )
        self.cellIds[ self.getCellIndex( dimensions ) ] = moduleId
#        print " HyperwallManager--> addCell: %s " % str( ( moduleId, vistrailName, versionName, dimensions ) )
        
    def initialize_from_config( self ):
        from packages.vtDV3D.vtDV3DConfiguration import configuration as dv3d_configuration
        app = gui.application.get_vistrails_application()
        app.resource_path = None
        hwConfig = app.temp_configuration
        self.processList = []

        self.deviceName = dv3d_configuration.hw_name
        role = hwConfig.hw_role if hasattr( hwConfig, 'hw_role' ) else None
        debug = (hwConfig.debug[0].upper()=='T') if hasattr( hwConfig, 'debug' ) else False
        self.isServer = ( role == 'hw_server' )
        self.isClient = ( role == 'hw_client' )
        set_hyperwall_role( role )
        hw_port = dv3d_configuration.hw_server_port
        hw_server = dv3d_configuration.hw_server
        hw_dims = [ dv3d_configuration.hw_width, dv3d_configuration.hw_height ]

        if self.isServer:
            from hyperwall.iVisServer.iVisServer import QiVisServer
            app.resource_path = os.path.expanduser( dv3d_configuration.hw_resource_path )           
            self.server = QiVisServer( self.deviceName, hw_dims, hw_port, app.resource_path )
            self.connectSignals()
            
            if not debug:
                nodeList = dv3d_configuration.hw_nodes.split(',')
#                nodeList = [ 'visrend01', 'visrend02', 'visrend03' ]
                print "hwServer initialization, server: %x, mgr: %x, dims=%s, nodes=%s" % ( id(self.server), id( self ), str(hw_dims), str(nodeList) )
                nodeIndex = 0
                for node in nodeList:
                    if node:
                        nodeName = node.strip()
                        self.spawnRemoteViewer( nodeName, nodeIndex )
                        nodeIndex = nodeIndex + 1
                
        if self.isClient:
            fullScreen = (hwConfig.fullScreen[0].upper()=='T') if hasattr( hwConfig, 'fullScreen' ) else True
            node_index = hwConfig.hw_node_index
            hw_x = node_index / hw_dims[1]
            hw_y = node_index % hw_dims[1]
            from hyperwall.iVisClient.iVisClient import QiVisClient
            print " QiVisClient startup, full screen = %s " % str( fullScreen )
            self.client = QiVisClient(  self.deviceName,  hw_server, hw_port, hw_x, hw_y, 1, 1  )
#            self.client.createTab(  int(dv3d_configuration.hw_displayWidth), int(dv3d_configuration.hw_displayHeight), fullScreen )

    def initialize( self, hw_role  ):
        defaults = { 'hw_debug': False, 'hw_resource_path':'', 'hw_device_name': "Hyperwall",  'hw_x':0, 'hw_y':0, 'hw_width':1, 'hw_height':1,
                                     'hw_displayWidth':-1, 'hw_displayHeight':-1, 'hw_nodes':"", 'hw_server':"localhost",  'hw_server_port':50000 }
        datasetConfig, appConfig = getConfiguration( defaults )
        app = gui.application.get_vistrails_application()
        self.processList = []               
                
        self.deviceName = datasetConfig.get( hw_role, 'hw_device_name' )        
        debug = datasetConfig.get( hw_role, 'hw_debug' )    
        self.isServer = ( hw_role == 'hw_server' )
        self.isClient = ( hw_role == 'hw_client' )
        set_hyperwall_role( hw_role )
        hw_port = datasetConfig.get( hw_role, 'hw_server_port' )
        hw_server = datasetConfig.get( hw_role, 'hw_server' )
        hw_dims = [ datasetConfig.getint( hw_role, 'hw_width' ), datasetConfig.getint( hw_role, 'hw_height' ) ]

        if self.isServer:
            from hyperwall.iVisServer.iVisServer import QiVisServer
            app.resource_path = os.path.expanduser( datasetConfig.get( hw_role, 'hw_resource_path' ) )           
            self.server = QiVisServer( self.deviceName, hw_dims, hw_port, app.resource_path )
            self.connectSignals()
            
            if not debug:
                hw_nodes = datasetConfig.get( hw_role, 'hw_nodes' )
                nodeList = hw_nodes.split(',')
#                nodeList = [ 'visrend01', 'visrend02', 'visrend03' ]
                print "hwServer initialization, server: %x, mgr: %x, dims=%s, nodes=%s" % ( id(self.server), id( self ), str(hw_dims), str(nodeList) )
                nodeIndex = 0
                for node in nodeList:
                    if node:
                        nodeName = node.strip()
                        self.spawnRemoteViewer( nodeName, nodeIndex )
                        nodeIndex = nodeIndex + 1
                
        if self.isClient:
            fullScreen = (appConfig.fullScreen[0].upper()=='T') if hasattr( appConfig, 'fullScreen' ) else True
            node_index = appConfig.hw_node_index
            hw_x = node_index / hw_dims[1]
            hw_y = node_index % hw_dims[1]
            from hyperwall.iVisClient.iVisClient import QiVisClient
            print " QiVisClient startup: %s %s %s " % ( self.deviceName, hw_server, hw_port )
            hw_displayWidth = int( datasetConfig.get( hw_role, 'hw_displayWidth' ) )
            hw_displayHeight = int( datasetConfig.get( hw_role, 'hw_displayHeight' ) )
            self.client = QiVisClient( self.deviceName, hw_server, hw_port, hw_x, hw_y, 1, 1 )
#            self.client.createTab( hw_displayWidth, hw_displayHeight, fullScreen )
                
    def spawnRemoteViewer( self, node, nodeIndex, debug=False ):
        localhost = os.uname()[1]
        debugStr = ('/usr/X11/bin/xterm -sb -sl 20000 -display :0.0 -e ') if debug else ''
        optionsStr = "-Y" if debug else ''  
        f = open( os.path.expanduser( '~/.vistrails/dv3d-%d.log' % ( nodeIndex ) ), 'w')
#            cmd = "ssh %s %s '%s /usr/local/bin/bash -c \"source ~/.vistrails/hw_env; export HW_NODE_INDEX=%d; export DISPLAY=:0.0; python %s/main/client.py\" ' " % ( optionsStr, node, debugStr, nodeIndex, HYPERWALL_SRC_PATH )
        cmd = [ "ssh", node, '~/.vistrails/hw_vistrails_client %d' % ( nodeIndex ) ] #  socket.gethostname()
        print " --- Executing: ", ' '.join(cmd)
        try:
            p = subprocess.Popen( cmd, stdout=f, stderr=f ) 
#            p = subprocess.Popen( cmd ) 
        except Exception, err:
            print>>sys.stderr, " Exception in spawnRemoteViewer: %s " % str( err )
            return
        self.processList.append( ( p, f ) )  
 
    
#    def registerPipeline(self):
#        buildWin = get_vistrails_application().builderWindow
#        buildWin.open_vistrail(f) 
        
    def connectSignals(self):
        if not self.connected:
            try:
                buildWin = get_vistrails_application().builderWindow
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
        
    def processInteractionEvent( self, name, event, screen_pos, screen_dims, camera_pos  ):
        if self.isServer:
            isKeyPress = ( event.type() == QtCore.QEvent.KeyPress )
            isButtonRelease = ( event.type() == QtCore.QEvent.MouseButtonRelease ) 
            isLevelingState = ( self.levelingState <> None ) and not isButtonRelease
            sheetTabWidget = getSheetTabWidget()
            selected_cells = [ screen_pos, ] if ( isLevelingState or isKeyPress ) else sheetTabWidget.getSelectedLocations()
            print " processInteractionEvent, type = %s, leveling = %s, selected_cells = %s" % ( name, str(self.levelingState <> None), str(selected_cells) )
            self.server.processInteractionEvent( self.deviceName, event, screen_dims, selected_cells, camera_pos  ) 
#            if (event.type() == QtCore.QEvent.MouseButtonPress):
#                self.screen_dims = screen_dims
#                self.opening_event = event
#                self.intial_camera_pos = camera_pos
#            elif event.type() == QtCore.QEvent.MouseButtonRe:
                       

    def processGuiCommand( self, command, activeCellsOnly=True  ):
        sheetTabWidget = getSheetTabWidget()
        selected_cells = sheetTabWidget.getSelectedLocations() if activeCellsOnly else None
        if self.isServer: self.server.processGuiCommand( self.deviceName, command, selected_cells )        

#    def clearLevelingState(self):
#        self.levelingState = None
#        if self.isServer and self.opening_event:            
#            selected_cells = sheetTabWidget.getSelectedLocations()
#            closing_event = 
#            self.server.processInteractionEvent( self.deviceName, closing_event, self.screen_dims, selected_cells, self.intial_camera_pos  )  
#            self.opening_event = None      
    
singleton = HyperwallManagerSingleton()

    
def onExecute( ):
    pass
#    HyperwallManager.executeCurrentWorkflows()


