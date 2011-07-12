from PyQt4 import Qt, QtCore

from PyQt4.QtNetwork import QTcpSocket, QTcpServer, QHostAddress
from PyQt4.QtCore import QObject
from PyQt4.QtGui import QMainWindow

from users import User, UserPool
from iPhoneManager import IPhoneManager
from DeviceServer import Device, StereoDevice
from VistrailServer import VistrailServer
#from pipeline_modifier import PipelineModifier
from vtDV3D.vtUtilities import *

import pickle, os, sys

class QiVisServer(QObject):
    def __init__( self, name, dimensions, port, resource_path ):
        QObject.__init__(self)
        self.port = port
        self.server = QTcpServer(self)
        self.connect(self.server, QtCore.SIGNAL("newConnection()"), self.newConnection)
        self.server.listen(Qt.QHostAddress(Qt.QHostAddress.Any), port)
        print " --- iVisServer ---  << Listening on port %d >> " % port
        self.sockets = {}
        self.buffer = ''

        self.devices = {}

        self.vistrailServer = VistrailServer( resource_path )
        self.summary = None
        self.addDevice( name, dimensions )
        self.userPool = UserPool()
    
    def __del__( self ): 
        for device in self.devices.values(): device.shutdown()
        
    def addDevice(self, name, dimensions ):
        device = Device(name, dimensions)
        self.devices[device.name] = device

    def readDevicesFromFile(self, filename):
        import os.path
        if os.path.isfile(filename):
            f = file(filename, 'r')
        else:
            f = None

        if not f is None:
            lines = f.readlines()
            name = ""
            dimensions = None
            for i in range(len(lines)):
                tokens = lines[i].split()
                if tokens:
                    if tokens[0] == "device":
                        pass
                    elif tokens[0] == "name":
                        name = ''.join([x+" " for x in tokens[1:]])[:-1]
                    elif tokens[0] == "dimensions":
                        dimensions = (int(tokens[1]), int(tokens[2]))
                    elif tokens[0] == "end_device":
                        device = Device(name, dimensions)
                        self.devices[device.name] = device
        f.close()

    def newConnection(self):
        while self.server.hasPendingConnections():
            print " ~~~~~~~~~~~~~~~~~~~~~~Received Connection~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
            socket = self.server.nextPendingConnection()

            print socket.peerAddress().toString()
            self.sockets[str(socket.peerAddress().toString())] = socket

            self.connect(self.sockets[str(socket.peerAddress().toString())], QtCore.SIGNAL("readyRead()"), self.readDataFromSocket)
            self.connect(self.sockets[str(socket.peerAddress().toString())], QtCore.SIGNAL("disconnected()"), self.disconnected)

    def disconnected(self):
        print "Disconnected"

    def readDataFromSocket(self):
        socket = None
        for s in self.sockets:
            if self.sockets[s].bytesAvailable() != 0:
                socket = self.sockets[s]
                break

        if socket is None:
            return

        incoming = str(socket.readAll().data())
        while incoming != "":
            self.buffer += incoming
            while (self.buffer != ""):
                tokens = self.buffer.split(":")
                header = tokens[0]
                rest = ""
                for piece in tokens[1:]:
                    rest += piece+":"
                rest = rest[:-1]
                tmp = header.split("-")
                if len(tmp) == 3:
                    (sender, receiver, size) = header.split("-")
                else:
                    break

                if int(size) > len(rest):
                    break

                tokens = rest[:int(size)]
                self.buffer = rest[int(size):]

                reply = ("", "", "")
                if (receiver == "server"):
                    reply = self.processMessage((sender,tokens), socket)
                elif (receiver == "vistrailServer"):
                    reply = self.vistrailServer.processMessage((sender, tokens), socket)

                if reply != ("","",""):
                    reply = reply[0] + "-" + reply[1] + "-" + str(len(reply[2])) + ":" + reply[2]
                    socket.write(reply)

            incoming = str(socket.readAll().data())

    def executePipeline( self, deviceName, vistrailName, versionName, moduleId, dimensions ):
        import api
        ctrl = api.get_current_controller()
        cellID = self.devices[deviceName].dispatchPipeline( ctrl.current_pipeline, vistrailName, versionName, moduleId, dimensions)
        
#        replyTokens = "localID,"+deviceName+","+str(cellID)+","+tokens[5]+","+tokens[6]+","+tokens[7]+","+tokens[8]

#        broadcastTokens = "addCell,"
#        broadcastTokens += deviceName +","+vistrailName+","+str(versionName)+","+str(moduleId)+","+str(cellID)+","
#        broadcastTokens += str(dimensions[0]) + ","+str(dimensions[1])+","+str(dimensions[2])+","+str(dimensions[3])
#        self.broadcastMessage(("server", sender, broadcastTokens), [self.sockets[x] for x in self.sockets if self.sockets[x] != socket])
#
#        summaryMessageTokens = 'attach,blank_user,'+str(dimensions[1])+','+str(dimensions[3])+','+str(dimensions[0])+','+str(dimensions[2])
#        summaryMessage = 'server-summary-'+str(len(summaryMessageTokens))+':'+summaryMessageTokens
#        if not self.summary is None:
#            self.summary.write(summaryMessage)

 #       return ("server", sender, replyTokens)


    def processMessage(self, message, socket=None):
        (sender, tokens) = message
        tokens = tokens.split(",")
        if len(tokens) == 0: return

        ### connection attempt
        if tokens[0] == "tryConnect":
            #elif sender == "summary":
            #    print "SummarY!!!"
            #    self.summary = socket

            return ("server",sender,"acceptConnect")

        ### disconnection warning
        if tokens[0] == "willDisconnect":
            print "Disconnecting iPhone"
            key = socket.peerAddress().toString()
            if (self.sockets.has_key(key)):
                del self.sockets[key]

        if tokens[0] == "logout":
            print "Logging out"
            key = socket.peerAddress().toString()
            if (self.sockets.has_key(key)):
                del self.sockets[key]
            summaryMessageTokens = "logout,"+tokens[1]
            summaryMessage = 'server-summary-'+str(len(summaryMessageTokens))+':'+summaryMessageTokens
            if not self.summary is None:
                self.summary.write(summaryMessage)

        ### querying for an existing user
        elif tokens[0] == "usernameQuery":
            if self.userPool.queryUser(tokens[1]):
                summaryMessageTokens = 'login,'+str(tokens[1])+','\
                    +str(self.userPool.users[tokens[1]].color[0])+","\
                    +str(self.userPool.users[tokens[1]].color[1])+","\
                    +str(self.userPool.users[tokens[1]].color[2])

                summaryMessage = 'server-summary-'+str(len(summaryMessageTokens))+':'+summaryMessageTokens
                if not self.summary is None:
                    self.summary.write(summaryMessage)

                return ("server",sender,"username,true,"\
                    +str(self.userPool.users[tokens[1]].color[0])+","\
                    +str(self.userPool.users[tokens[1]].color[1])+","\
                    +str(self.userPool.users[tokens[1]].color[2]))
            else:
                return ("server", sender, "username,false")

        ### sender asked to create a new user
        elif tokens[0] == "createUser":
            username = tokens[1]
            color = (float(tokens[2]), float(tokens[3]), float(tokens[4]))
            self.userPool.addUser(User(username, color))

            summaryMessageTokens = 'login,'+str(tokens[1])+','\
                +str(self.userPool.users[tokens[1]].color[0])+","\
                +str(self.userPool.users[tokens[1]].color[1])+","\
                +str(self.userPool.users[tokens[1]].color[2])
            
            summaryMessage = 'server-summary-'+str(len(summaryMessageTokens))+':'+summaryMessageTokens
            if not self.summary is None:
                self.summary.write(summaryMessage)

        ### querying the available devices
        elif tokens[0] == "queryDevices":
            replyTokens = "availableDevices,"
            for device in self.devices.values():
                replyTokens += device.name+","+str(device.dimensions[0])+","+str(device.dimensions[1])+","
            replyTokens = replyTokens[:-1]
            return ("server", sender, replyTokens)

        ### querying the pipeline properties
        elif tokens[0] == "queryProperties":
            deviceName = tokens[1]
            reply = "availableProperties," + self.devices[deviceName].queryProperties(tokens[2])
            return ("server", sender, reply)

        ### querying the pipeline properties
        elif tokens[0] == "updatePipeline":
            deviceName = tokens[1]
            #tokens: 2. LocalID, 3. MedleyXML
            reply = "updatePipeline," + tokens[2] + "," + self.devices[deviceName].updatePipeline(tokens[2], tokens[3])
            return ("server", sender, reply)

        ### saving the visualization layout
        elif tokens[0] == "saveLayout":
            deviceName = tokens[1]
            reply = "layoutSaved,"
            #deviceName, vistrailName, versionName, moduleId, dimensions, pipeline
            #pickle doesnt work. Have to write the file by myself
            #
            #devices amount
            #info, pipeline
            if tokens[2] != "":
                pickle.dump( self.devices, open(self.vistrailServer.resource_path +tokens[2]+".lay","w"))
            print "Save Layout"
            return ("server", sender, reply)

        ### querying the visualization layout available
        elif tokens[0] == "queryLayouts":
            reply = "availableLayouts,"
            for n in self.vistrailServer.querySavedLayouts():
                reply += n + ","
            reply = reply[:-1]
            return ("server", sender, reply)

        ### open the saved layout available
        elif tokens[0] == "openLayout":
            reply = "appliedLayout,"
            print tokens[1]
            return ("server", sender, reply)

        ### sender is a display client advertising its dimensions
        elif tokens[0] == "dimensions":
            deviceName = tokens[1]
            dimensions = (int(tokens[2]), int(tokens[3]), int(tokens[4]), int(tokens[5]))
            print "Dimensions!", deviceName, dimensions
            print self.devices.keys()
            if self.devices.has_key(deviceName):
                self.devices[deviceName].addClient(dimensions, socket)

        ### sender is an iPhone asking to execute a pipeline
        elif tokens[0] == "executePipeline":
            deviceName = tokens[1]
            vistrailName = tokens[2]
            versionName = tokens[3]
            moduleId = int(tokens[4])
            dimensions = (int(tokens[5]), int(tokens[6]), int(tokens[7]), int(tokens[8]))

            pipeline = self.vistrailServer.getPipeline(vistrailName, versionName)

            cellID = self.devices[deviceName].dispatchPipeline(pipeline, vistrailName, versionName, moduleId, dimensions)
            replyTokens = "localID,"+deviceName+","+str(cellID)+","+tokens[5]+","+tokens[6]+","+tokens[7]+","+tokens[8]

            broadcastTokens = "addCell,"
            broadcastTokens += deviceName +","+vistrailName+","+versionName+","+str(moduleId)+","+str(cellID)+","
            broadcastTokens += str(dimensions[0]) + ","+str(dimensions[1])+","+str(dimensions[2])+","+str(dimensions[3])
            self.broadcastMessage(("server", sender, broadcastTokens), [self.sockets[x] for x in self.sockets if self.sockets[x] != socket])

            summaryMessageTokens = 'attach,blank_user,'+str(dimensions[1])+','+str(dimensions[3])+','+str(dimensions[0])+','+str(dimensions[2])
            summaryMessage = 'server-summary-'+str(len(summaryMessageTokens))+':'+summaryMessageTokens
            if not self.summary is None:
                self.summary.write(summaryMessage)

            return ("server", sender, replyTokens)

        ### sender is a device sending an interaction event
        elif tokens[0] == "interaction":
            deviceName = tokens[1]
            self.devices[deviceName].processInteractionMessage(tokens[1:])

        ### sender is an iPhone asking for device occupation on a certain device
        elif tokens[0] == "deviceOccupation":
            deviceName = tokens[1]
            reply = self.devices[deviceName].queryOccupation()
            return ("server", sender, reply)

        ### sender is asking to delete a certain cell
        elif tokens[0] == "deleteCell":
            deviceName = tokens[1]            
            reply = self.devices[deviceName].deleteCell(tokens[2:])
            broadcastTokens = "deleteCell,"+deviceName+","+str(tokens[2])
            self.broadcastMessage(("server", sender, broadcastTokens), [self.sockets[x] for x in self.sockets if self.sockets[x] != socket])
            return ("server", sender, reply)

        ### sender is asking to lock a certain cell for interaction
        elif tokens[0] == "lockCell":
            deviceName = tokens[1]
            reply = self.devices[deviceName].lockCell(tokens[2:])
            reply = ("server", sender, reply)
            self.broadcastMessage(reply, self.sockets.values())

        elif tokens[0] == "unlockCell":
            deviceName = tokens[1]
            reply = self.devices[deviceName].unlockCell(tokens[2:])
            reply = ("server", sender, reply)
            self.broadcastMessage(reply, self.sockets.values())
        return ("", "", "")

    def broadcastMessage(self, message, receivers):
        message = message[0] + "-" + message[1] + "-" + str(len(message[2])) + ":" + message[2]
        for receiver in receivers:
            receiver.write(message)

    def processInteractionEvent( self, deviceName, event, screen_dims, selected_cells, camera_pos   ):
        etype = event.type()
        event_type = "none"
        tokens = ""
        if   etype == QtCore.QEvent.MouseMove:          event_type = "mouseMove" 
        elif etype == QtCore.QEvent.MouseButtonPress:   event_type = "singleClick" 
        elif etype == QtCore.QEvent.MouseButtonRelease: event_type = "mouseRelease" 
        elif etype == QtCore.QEvent.KeyPress:           event_type = "keyPress" 
        elif etype == QtCore.QEvent.KeyRelease:         event_type = "keyRelease" 
        
        if (etype== QtCore.QEvent.KeyRelease) or (etype== QtCore.QEvent.KeyPress):   
            key = event.key() 
            mod = event.modifiers() 
            if mod:
               if   ( mod & QtCore.Qt.ShiftModifier    ): mod = "shift" 
               elif ( mod & QtCore.Qt.ControlModifier  ): mod = "ctrl" 
               elif ( mod & QtCore.Qt.AltModifier      ): mod = "alt" 
               else:                               mod = "none"
            tokens = [ event_type, key, mod ]
#            print ' >>----------iVisServer--> process Key Event:  %s '   % str( ( event_type, key, mod, event.text() ) )
        else:               
            x = event.x()
            y = event.y()
            xf = '%.4f' % (float(x)/screen_dims[0])
            yf = '%.4f' % (float(y)/screen_dims[1])
            b = event.button() 
            button = "none"       
            if b == QtCore.Qt.LeftButton: button = "left"
            if b == QtCore.Qt.RightButton: button = "right" 
            if etype == QtCore.QEvent.MouseButtonPress:
                cpos = camera_pos[0]  
                cfol = camera_pos[1]  
                cup = camera_pos[2]         
                tokens = [ event_type, button, xf, yf, cpos[0], cpos[1], cpos[2], cfol[0], cfol[1], cfol[2], cup[0], cup[1], cup[2]  ]
            else:
                tokens = [ event_type, button, xf, yf ]
#            print ' >>----------iVisServer--> process Mouse Event:  %s '   % str( ( event_type, xf, yf, button, screen_dims, tokens ) )  
                      
        self.devices[deviceName].processInteractionMessage( tokens, selected_cells  )

            
          

