from PyQt4 import QtCore, QtGui

class QTranslator(QtCore.QObject):
    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self._commands = []
        #TODO: connect self.shell to VisTrails shell
        self.shell = None 
        
    def commandsReceived(self, commands):
        # TODO: translate commands and forward that to VisTrails shell
        print "VCDAT VisTrails translator received: "
        print " >>>",  commands