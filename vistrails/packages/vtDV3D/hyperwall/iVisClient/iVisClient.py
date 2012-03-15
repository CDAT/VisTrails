import PyQt4.QtNetwork
import packages
import gui, core, os, sys
from PyQt4 import QtCore, QtGui
from PyQt4.QtNetwork import QTcpSocket, QHostAddress, QHostInfo, QAbstractSocket
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from displaywall_tab import DisplayWallSheetTab
import packages.vtDV3D.ModuleStore as ModuleStore
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.hyperwall.iVisServer.DeviceServer import MessageTokenSep

class QiVisClient(QtCore.QObject):
    def __init__(self, name, server, serverPort, x, y, width, height ):
        """__init__() -> None
        initializes the client class"""


        QtCore.QObject.__init__(self)

        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.start()
        self.socket = QTcpSocket()

        self.server = server # os.environ.get( 'DV3D_HW_SERVER_NAME', server )
        self.serverPort = int(serverPort)

        self.buffer = ""
        self.pipelineQueue = []
        current_pipeline = None

        self.deviceName = name
        self.currentTab = None
        self.mainWindow = None
        print " Init VisClient, server=%s, serverPort=%s, name=%s " % ( str(self.server), str(self.serverPort), str(name) )

        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow( False )
        self.spreadsheetWindow.setWindowFlags( self.spreadsheetWindow.windowFlags() | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Window )
#        self.spreadsheetWindow.setWindowFlags( self.spreadsheetWindow.windowFlags() | QtCore.Qt.Window )
        self.spreadsheetWindow.activateWindow()
        self.spreadsheetWindow.showMaximized()
        
        self.dimensions = ( x, y, width, height )
        self.connectSignals()       
        
    def createTab( self,  displayWidth, displayHeight, fullScreenEnabled ):
        self.spreadsheetWindow.addTabController('DV3D')
        tabController = self.spreadsheetWindow.get_current_tab_controller()
        tabController.clearTabs()
        self.currentTab = DisplayWallSheetTab( tabController, self.dimensions[0], self.dimensions[1], self.dimensions[2], self.dimensions[3], displayWidth, displayHeight, fullScreenEnabled )
        tabController.addTabWidget(self.currentTab, self.deviceName)
        self.size = self.currentTab.getDimension()
        print " Startup VisClient, size=%s, dims=%s, fullScreen=%s " % ( str(self.size), str(self.dimensions), str(fullScreenEnabled) )

    def updateCurrentTab(self):
        if self.currentTab == None:
            tabController = self.spreadsheetWindow.get_current_tab_controller()            
#            self.currentTab = tabController.tabWidgets[1]
            self.currentTab = tabController.widget ( 1 )
            if self.currentTab:
                self.dims = self.currentTab.getDimension()
                print " UpdateCurrentTab: ntabs=%d, dims=%s " % ( len( tabController.tabWidgets ), str( self.dims ) )
                return True
        return False
            
    def connectSignals(self):
        """connectSignals() -> None
        Connects all relevant signals to this class"""
        self.connect(self.socket, QtCore.SIGNAL("connected()"), self.connected)
        self.connect(self.socket, QtCore.SIGNAL("disconnected()"), self.disconnected)
        self.connect(self.socket, QtCore.SIGNAL("readyRead()"), self.readDataFromSocket)
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.retryConnection)
        self.connect(self, QtCore.SIGNAL("executeNextPipeline()"), self.executeNextPipeline)

    def retryConnection(self):
        """retryConnection() -> None
        this method is called once everytime self.timer ticks. It
        tries to connect to the server again"""
        print "retryConnection"
        sys.stdout.flush()
        if self.socket.state()!=QTcpSocket.ConnectedState:
            if self.socket.state()==QTcpSocket.UnconnectedState:
                port = int( self.serverPort )
                print " HWClient connecting to server at %s:%d" % ( self.server, port )
                self.socket.connectToHost(self.server, port )
            self.timer.start()
        elif core.system.systemType in ['Windows', 'Microsoft']:
            self.socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)

    def connected(self):
        """connected() -> None
        this method is called when self.socket emits the connected() signal. It means that a succesful connection
        has been established to the server"""
        sender = "displayClient"
        receiver = "server"
        tokens = MessageTokenSep.join( [ "dimensions", self.deviceName, str(self.dimensions[0]), str(self.dimensions[1]), str(self.dimensions[2]), str(self.dimensions[3]) ] )
        reply = sender + "-" + receiver + "-" + str(len(tokens)) + ":" + tokens
        print "   ****** Connected to server!  CellCoords = ( %d, %d ), reply: %s " % ( self.dimensions[0], self.dimensions[1], reply )
        self.socket.write(reply)

    def disconnected(self):
        """disconnected() -> None
        this method is called when self.socket emits disconnected(). It means that the socket is no longer connected to the server"""
        print "Disconnected from server"
        self.timer.start()

    def readDataFromSocket(self):
        """readDataFromSocket() -> None
        This method is called everytime the socket sends the readyRead() signal"""
        incoming = str(self.socket.readAll().data())
        while incoming != "":
            self.buffer += incoming
            while self.buffer != "":
                tokens = self.buffer.split(":")
                header = tokens[0]
                rest = ""
                for piece in tokens[1:]:
                    rest += piece+":"
                rest = rest[:-1]
                info = header.split("-")
                if len(info)<3:
                    break
                (sender, receiver, size) = (info[0], info[1], info[2])
                if int(size) > len(rest):
                    break
                tokens = rest[:int(size)]
                self.buffer = rest[int(size):]
#                print " ********* CLIENT--> gotMessage: %s %s %s ********* " % ( str( receiver ), str( sender ), str( tokens ) )
                sys.stdout.flush()

                if (receiver == "displayClient"):
                    reply = self.processMessage((sender, tokens), self.socket)

                    if reply != ("","",""):
                        reply = reply[0] + "-" + reply[1] + "-" + str(len(reply[2])) + ":" + reply[2]
                        self.socket.write(reply)
                
            incoming = str(self.socket.readAll().data())


    def processCommand(self, terms):
        print " processCommand: %s " % str( terms )
        if terms[0] == "reltimestep":
            relTimeValue = float( terms[1] )  
            displayText =  terms[2] 
            for module in self.current_pipeline.module_list:
                persistentCellModule = ModuleStore.getModule( module.id ) 
                persistentCellModule.updateAnimation( relTimeValue, displayText  )
        else:
            for module in self.current_pipeline.module_list:
                persistentCellModule = ModuleStore.getModule( module.id ) 
                persistentCellModule.updateConfigurationObserver( terms[0], terms[1:] )
#        if terms[0] == 'colormap':
#             cmapData = terms[1]
#             displayText =  terms[2]  
#             for module in self.current_pipeline.module_list:
#                persistentCellModule = ModuleStore.getModule( module.id ) 
#                persistentCellModule.setColormap( cmapData  )
#                persistentCellModule.updateTextDisplay( displayText )

    def processEvent(self, terms):
        """processEvent(message: String) -> None
        decodifies the event received by the server and posts it to QT's event handler. In order
        to do this, we must send three events: the first one disables this client's method that
        would send events to the server. The second is the actual event we want processed and the third
        reenables event sending to the server. This must be done to avoid a deadlock"""
        def decodeMouseEvent( event, screenDims ):
            """decodeMouseEvent(event: String) -> QtGui.QMouseEvent
            this method receives a string and returns the corresponding mouse event"""
            pos = ( int( float( event[2] ) * screenDims[0] ), int( float( event[3] ) * screenDims[1] ) )
            if event[1] == "left":
                button = QtCore.Qt.LeftButton
            elif event[1] == "right":
                button = QtCore.Qt.RightButton

            if event[0] == "singleClick": 
                t = QtCore.QEvent.MouseButtonPress
            elif event[0] == "mouseMove": 
                t = QtCore.QEvent.MouseMove
                button = QtCore.Qt.NoButton
            elif event[0] == "mouseRelease": 
                t = QtCore.QEvent.MouseButtonRelease

            button = QtCore.Qt.MouseButton(button)
            m = QtCore.Qt.NoModifier
            if event[4] == "shift": 
                m = QtCore.Qt.ShiftModifier
            elif event[4] == "ctrl": 
                m = QtCore.Qt.ControlModifier
            elif event[4] == "alt": 
                m = QtCore.Qt.AltModifier
            print " Client process %s %s event: pos = %s, screenDims=%s " % ( button, event[0], str( pos ), str( screenDims ) )

            return QtGui.QMouseEvent(t, QtCore.QPoint(pos[0], pos[1]), button, button, m)

        def decodeKeyEvent(event):
            """decodeKeyEvent(event: String) -> QtGui.QKeyEvent
            this method receives a string and returns the corresponding Key event"""
            type = None
            if event[0] == "keyPress":
                type = QtCore.QEvent.KeyPress
            elif event[0] == "keyRelease":
                type = QtCore.QEvent.KeyRelease
                
            key = int( event[1] )
            
            m = QtCore.Qt.NoModifier
            if event[2] == "shift": 
                m = QtCore.Qt.ShiftModifier
            elif event[2] == "ctrl": 
                m = QtCore.Qt.ControlModifier
            elif event[2] == "alt": 
                m = QtCore.Qt.AltModifier
            print " Client process key event: %s " % str( event )

            return QtGui.QKeyEvent( type, key, QtCore.Qt.KeyboardModifiers(m) )

        app = QtCore.QCoreApplication.instance()
        newTab = self.updateCurrentTab()
        widget = self.currentTab.getCellWidget( 0, 0 ) if self.currentTab else None
                  
        print " ------------- QiVisClient.processEvent: %s-%s, widget: %x  ---------------------" % ( terms[2], terms[3], id(widget) )
        sys.stdout.flush()
        
        if terms[2] == "singleClick":
            cellModules = self.getCellModules()
            cpos = [ float(terms[i]) for i in range(7,10) ]
            cfol = [ float(terms[i]) for i in range(10,13) ]
            cup  = [ float(terms[i]) for i in range(13,16) ]
#            print " >>> QiVisClient.cellModules: %s, modules: %s" % ( str( [ cellMod.id for cellMod in cellModules ] ), str( ModuleStore.getModuleIDs() ) )           
            for cellMod in cellModules:
                persistentCellModule = ModuleStore.getModule( cellMod.id ) 
                if persistentCellModule: persistentCellModule.syncCamera( cpos, cfol, cup )            
        if terms[2] in ["singleClick", "mouseMove", "mouseRelease"]:
            if self.currentTab:
                screenRect = self.currentTab.getCellRect( 0, 0 )
                screenDims = ( screenRect.width(), screenRect.height() )
                newEvent = decodeMouseEvent( terms[2:], screenDims )
        elif terms[2] in ["keyPress", "keyRelease" ]:
            newEvent = decodeKeyEvent(terms[2:])

        if widget: 
            cellWidget = widget.widget()
            app.postEvent( cellWidget, newEvent)
            cellWidget.setFocus()
            cellWidget.update()

    def executeNextPipeline(self):
        if len(self.pipelineQueue) == 0:
            return
        pipeline = self.pipelineQueue[-1]
        self.pipelineQueue.pop()
        self.executePipeline(pipeline)
        self.emit(QtCore.SIGNAL("executeNextPipeline()"))

    def getCellModules(self):
        cellModules = []
        for module in self.current_pipeline.module_list:
            if ( module.name == "MapCell3D" ): cellModules.append( module )
        return cellModules
        
    def getCurrentPipeline(self):
        return self.current_pipeline
    
    def setCellLocation(self):
        cellModule = None
        print " Executing Client Workflow, modules: "
        for module in self.current_pipeline.module_list:
            print str( module )
#            if : cellModule = module


    def executePipeline(self,pipeline):
        from core.db.io import unserialize
        from core.vistrail.pipeline import Pipeline
        from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
        from core.utils import DummyView
        import api

        tabController = self.spreadsheetWindow.get_current_tab_controller()
        pip = unserialize(str(pipeline), Pipeline)
#        print " **** Client-%s ---Received Pipeline--- modules:" % str( self.dimensions )
#        for module in pip.module_list:
#            print "     ", str(module.id)
        self.current_pipeline = pip
        interpreter = getDefaultInterpreter()
        kwargs = { "locator":           None,
                   "current_version":   None,
                   "view":              DummyView(),
                   "aliases":           {} }
        interpreter.execute( pip, **kwargs )
        print "Finished Executing Pipeline"

    def processMessage(self, message, socket):
        (sender, tokens) = message
        print " ********* CLIENT--> processMessage: %s ********* " % str( tokens )
        tokens = tokens.split( MessageTokenSep )
#        print " ********* CLIENT--> splitMessage: %s ********* " % str( tokens )
        if len(tokens) == 0: return
        
        if tokens[0] == "exit":
            print "Received shutdown message"
            sys.stdout.flush()
            socket.close()
            gui.application.get_vistrails_application().quit()
            gui.application.stop_application()
            sys.exit(0)

        if tokens[0] == "pipeline":
#            print " $$$$$$$$$$$ Client-- pipeline message: %s " % str(tokens)
            ### we must execute a pipeline
#            return ("", "", "")
            if len(tokens[2:]) != 0:
                for t in tokens[2:]:
                    tokens[1] += t + "@"
                tokens[1] = tokens[1][:-1]
            
            self.executePipeline(tokens[1])
        elif tokens[0] == "interaction":
            self.processEvent(tokens[1:])
            
        elif tokens[0] == "command":
            self.processCommand(tokens[3:])
            
        elif tokens[0] == "refresh":
            self.updateCurrentTab()
            if self.currentTab:
                widget = self.currentTab.getCell(int(tokens[1]), int(tokens[2]))
#                if widget:
#                    widget.swapBuffers()
        return ("", "", "")
