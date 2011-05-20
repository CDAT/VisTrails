from PyQt4 import Qt, QtCore, QtGui
from PyQt4.QtNetwork import QTcpSocket, QHostAddress, QHostInfo, QAbstractSocket
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from displaywall_tab import DisplayWallSheetTab

import PyQt4.QtNetwork
import packages
import gui
import core

class QiVisClient(QtCore.QObject):
    def __init__(self, name, x, y, width, height, server, serverPort, displayWidth, displayHeight):
        """__init__() -> None
        initializes the client class"""


        QtCore.QObject.__init__(self)

        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.start()
        self.socket = QTcpSocket()

        self.server = server
        self.serverPort = serverPort

        self.buffer = ""
        self.pipelineQueue = []

        self.deviceName = name

        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
        self.spreadsheetWindow.tabController.clearTabs()
        self.currentTab = DisplayWallSheetTab(self.spreadsheetWindow.tabController,
                                              width, height, displayWidth, displayHeight)
        self.spreadsheetWindow.tabController.addTabWidget(self.currentTab, self.deviceName)

        size = self.currentTab.getDimension()
        self.dimensions = (x, y, size[1], size[0])

        self.connectSignals()

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
        if self.socket.state()!=QTcpSocket.ConnectedState:
            if self.socket.state()==QTcpSocket.UnconnectedState:
                print " HWClient connecting to server at %s:%s" % ( self.server, str( self.serverPort ) )
                self.socket.connectToHost(self.server, self.serverPort)
            self.timer.start()
        elif core.system.systemType in ['Windows', 'Microsoft']:
            self.socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)

    def connected(self):
        """connected() -> None
        this method is called when self.socket emits the connected() signal. It means that a succesful connection
        has been established to the server"""
        print "Connected to server"
        sender = "displayClient"
        receiver = "server"
        tokens = "dimensions," + self.deviceName + "," + str(self.dimensions[0]) + "," + str(self.dimensions[1]) + "," + str(self.dimensions[2]) + "," + str(self.dimensions[3])
        reply = sender + "-" + receiver + "-" + str(len(tokens)) + ":" + tokens
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

                if (receiver == "displayClient"):
                    reply = self.processMessage((sender, tokens), self.socket)

                    if reply != ("","",""):
                        reply = reply[0] + "-" + reply[1] + "-" + str(len(reply[2])) + ":" + reply[2]
                        self.socket.write(reply)
                
            incoming = str(self.socket.readAll().data())

    def processEvent(self, terms):
        """processEvent(message: String) -> None
        decodifies the event received by the server and posts it to QT's event handler. In order
        to do this, we must send three events: the first one disables this client's method that
        would send events to the server. The second is the actual event we want processed and the third
        reenables event sending to the server. This must be done to avoid a deadlock"""
        def decodeMouseEvent(event):
            """decodeMouseEvent(event: String) -> QtGui.QMouseEvent
            this method receives a string and returns the corresponding mouse event"""
            pos = (int(event[2]), int(event[3]))
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
            keyboard = QtCore.Qt.NoModifier

            return QtGui.QMouseEvent(t, QtCore.QPoint(pos[0], pos[1]), button, button, keyboard)

        app = QtCore.QCoreApplication.instance()

        cell = (int(terms[0]), int(terms[1]))
        if terms[2] in ["singleClick", "mouseMove", "mouseRelease"]:
            newEvent = decodeMouseEvent(terms[2:])

        if self.currentTab:
             (rCount, cCount) = self.currentTab.getDimension()
             widget = self.currentTab.getCell(cell[0]-1, cell[1]-1)
             if widget:
                 app.postEvent(widget, newEvent)

    def executeNextPipeline(self):
        if len(self.pipelineQueue) == 0:
            return
        pipeline = self.pipelineQueue[-1]
        self.pipelineQueue.pop()
        self.executePipeline(pipeline)
        self.emit(QtCore.SIGNAL("executeNextPipeline()"))

    def executePipeline(self,pipeline):
        from core.db.io import unserialize
        from core.vistrail.pipeline import Pipeline
        from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
        from core.utils import DummyView

        pip = unserialize(str(pipeline), Pipeline)
        print "Executing Workflow"
        interpreter = getDefaultInterpreter()
        kwargs = {"locator":None,
                  "current_version":None,
                  "view":DummyView(),
                  "aliases":{} }
        interpreter.execute(pip, **kwargs)
        print "Finished Executing Pipeline"

    def processMessage(self, message, socket):
        (sender, tokens) = message
        tokens = tokens.split(",")
        if len(tokens) == 0: return

        if tokens[0] == "pipeline":
            ### we must execute a pipeline
#            return ("", "", "")
            if len(tokens[2:]) != 0:
                for t in tokens[2:]:
                    tokens[1] += t + ","
                tokens[1] = tokens[1][:-1]

            self.executePipeline(tokens[1])
        elif tokens[0] == "interaction":
            self.processEvent(tokens[1:])
            
        elif tokens[0] == "refresh":
            if self.currentTab:
                widget = self.currentTab.getCell(int(tokens[1]), int(tokens[2]))
#                if widget:
#                    widget.swapBuffers()
        return ("", "", "")
