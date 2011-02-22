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
