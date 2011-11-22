from PyQt4 import QtCore, QtGui
from ui_paraviewconnection import Ui_paraviewConnectionDialog
from paraview.simple import *

class ParaViewConnectionDialog(QtGui.QDialog, Ui_paraviewConnectionDialog):
    def __init__(self, parent=None):
        super(ParaViewConnectionDialog, self).__init__(parent)
        self.setupUi(self)
        self.root = self
        self._hostName = "localhost"
        self._portNumber = "11111"
        self._isConnected = False
        self.connectSignals()

    def connectSignals(self):
        self.buttonBox.accepted.connect(self.onAccepted)
        self.buttonBox.rejected.connect(self.close)

    def onAccepted(self):
        hostName = self.host.text()
        portNumber = self.port.value()
        # If hostname or port number are not changed from last time, do nothing.
        if hostName == self._hostName and self._portNumber == portNumber:
            self.close()
            return 1
        else:
            # We have to make a new connection now.
            self._hostName = hostName
            self._portNumber = portNumber
            self._isConnected = False

            # We may need to disconnect from last connection here.
            self.close()
        return 1

    def isConnected(self):
        return self._isConnected

    def connect(self):
        print 'hostname: ', self._hostName
        print 'port number: ', self._portNumber
        success = Connect(self._hostName, self._portNumber)
        # TODO: Handle gracefully when we are unable to connect to a server
        if success is not None:
            self._isConnected = True
            print "Connected to " + self._hostName + " on port " + str(self._portNumber)
        else:
            print "Unable to connect to " + self._hostName + " on port " + str(self._portNumber)
        return self.isConnected()

