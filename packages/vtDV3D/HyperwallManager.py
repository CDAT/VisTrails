'''
Created on May 16, 2011

@author: tpmaxwel
'''
from PyQt4 import QtCore, QtGui
import sys, copy, os
from gui.application import VistrailsApplication
from packages.spreadsheet.spreadsheet_config import configuration as spreadsheet_configuration
from vtDV3DConfiguration import configuration as dv3d_configuration
from vtUtilities import *

class HyperwallManagerSingleton(QtCore.QObject):

    def __init__( self, **args ):
        self.connected = False
        self.deviceName = dv3d_configuration.hw_name
        role = dv3d_configuration.hw_role
        self.isServer = ( role == 'server' )
        self.isClient = ( role == 'client' )
        self.cells = {}
        self.cellIds = {}
        self.rowCount = spreadsheet_configuration.rowCount
        self.columnCount = spreadsheet_configuration.columnCount
        self.nCells = self.rowCount * self.columnCount
        self.server = None
        self.client = None
        
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
        if self.isServer:
            from hyperwall.iVisServer.iVisServer import QiVisServer
            if dv3d_configuration.check('resource_path'): 
                resource_path = dv3d_configuration.hw_resource_path 
            else: 
                resource_path = None
            self.server = QiVisServer( resource_path, dv3d_configuration.hw_server_port )
            print "hwServer initialization, server: %x, mgr: %x" % ( id(self.server), id( self ) )
            self.connectSignals()
        if self.isClient:
            from hyperwall.iVisClient.iVisClient import QiVisClient
            self.client = QiVisClient(   dv3d_configuration.hw_name,
                                         dv3d_configuration.hw_x,
                                         dv3d_configuration.hw_y,
                                         dv3d_configuration.hw_width,
                                         dv3d_configuration.hw_height,
                                         dv3d_configuration.hw_server,
                                         dv3d_configuration.hw_server_port,
                                         dv3d_configuration.hw_displayWidth,
                                         dv3d_configuration.hw_displayHeight )
    
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
            for moduleId in self.cells: self.executeCurrentWorkflow( moduleId )

    def executeCurrentWorkflow( self, moduleId ):
        if self.isServer: 
           ( vistrailName, versionName, dimensions ) = self.cells[ moduleId ] 
           print "  *** ExecuteWorkflow--> cell: %s" % str( moduleId )
           self.server.executePipeline( self.deviceName, vistrailName, versionName, moduleId, dimensions )
        
    def processInteractionEvent( self, event, screen_dims  ):
        if self.isServer: self.server.processInteractionEvent( self.deviceName, event, screen_dims )        
    
HyperwallManager = HyperwallManagerSingleton()

def onExecute( ):
    pass
#     HyperwallManager.executeCurrentWorkflow()

if __name__ == '__main__':
    optionsDict = { 'dotVistrails':'~/.vistrails/hwserver' }
    executeVistrail( 'workflows/DemoWorkflow2', options=optionsDict )

