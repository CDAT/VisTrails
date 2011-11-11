###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: vistrails@sci.utah.edu
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################

#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import cdms2, vcs
from cdatguiwrap import VCSQtManager

class CDATViewer(QtGui.QMainWindow):
    def __init__(self):
        super(CDATViewer, self).__init__()
        self.setWindowTitle("CDAT Viewer")
        self.cdatwidget = QtGui.QWidget()
        self.windows = []
        self.setCentralWidget(self.cdatwidget)
        cdmsfile = cdms2.open("/Users/emanuele/src/cdat/old/cdat-qt-bin/sample_data/clt.nc")
        self.s = cdmsfile("clt")
        layout = QtGui.QVBoxLayout()
        self.cdatwidget.setLayout(layout)
        self.createActions()
        self.createMenus()

    def createActions(self):
        self.addAct = QtGui.QAction("&Add plot", self, shortcut="Ctrl+A",
                triggered=self.add)
        self.removeAct = QtGui.QAction("&Remove plot", self, shortcut="Ctrl+D",
                triggered=self.remove)

    def createMenus(self):
        self.fileMenu = QtGui.QMenu("&File", self)
        self.fileMenu.addAction(self.addAct)
        self.fileMenu.addAction(self.removeAct)

        self.menuBar().addMenu(self.fileMenu)

    def remove(self):
        print "before remove ", vcs.canvaslist
        window = self.windows.pop()
        self.cdatwidget.layout().removeWidget(window)
        window.setVisible(False)
        print "after remove ", vcs.canvaslist

    @staticmethod
    def get_superclasses(klass):
        res = set()
        for c in klass.__bases__:
            res.add(c)
            res.update(CDATViewer.get_superclasses(c))
        return res

    def add(self):
        print "before add ", vcs.canvaslist
        i = len(self.windows)
        if i >= len(vcs.canvaslist):
            canvas = vcs.init()
        else:
            canvas = vcs.canvaslist[i]
        i+= 1
        
        print dir(VCSQtManager)
        window = VCSQtManager.window(i)
        print window
        wdg = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(window)
        wdg.setLayout(layout)
        self.windows.append(wdg)
        self.cdatwidget.layout().addWidget(wdg)
        canvas.plot(self.s,'ASD', 'boxfill', 'default')
        gm = canvas.getboxfill('default')
        print type(gm)
        all = self.get_superclasses(gm.__class__)
        print all
        print "after add ", vcs.canvaslist

if __name__ == '__main__':

    import sys

    app = QtGui.QApplication(sys.argv)
    imageViewer = CDATViewer()
    imageViewer.show()
    sys.exit(app.exec_())
