from PyQt4 import QtGui, QtCore

import os
import customizeUVCDAT
import uvcdatCommons


class QCommandsRecorderWidget(uvcdatCommons.QCommandsFileWidget):
    def __init__(self,parent,title="UVCDAT Recorded Commands",readOnly=True):
        uvcdatCommons.QCommandsFileWidget.__init__(self,parent,title,readOnly)
        #self.initCommands()

    def initCommands(self):
        
        txt = """## This file records all user commands
## First a few necessary imports
import vcs,cdms2,MV2,genutil,cdutil
vcs_canvas=[]
for i in range(4):
   vcs_canvas.append(vcs.init())

## And now whatever the user decides to do...
## Thanks for using UVCDAT have fun
"""
   
        self.addText(txt)
                
        
    def record(self,commands,*vistrails):
        if False:
            for a in self.root.mainMenu.tools.actions():
                if a.text() == 'Record Commands' and a.isChecked():
                    self.addText(commands)
                    break
            if uvcdatCommons.useVistrails:
                self.emit(QtCore.SIGNAL("recordCommands"),commands)
        return
