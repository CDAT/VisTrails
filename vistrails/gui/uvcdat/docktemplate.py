from PyQt4 import QtCore, QtGui

from gui.uvcdat import dockplot
from uvcdatCommons import plotTypes
import editorTemplateWidget

class DockTemplate(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockTemplate, self).__init__(parent)
        self.setWindowTitle("Templates")
        self.root=parent.root
        self.templateTree = TemplateTreeWidget(self)
        self.setWidget(self.templateTree)
        self.initTree()
        
    def initTree(self):
        self.uvcdat_items={}
        for k in sorted(plotTypes.keys()):
            self.uvcdat_items[k]=QtGui.QTreeWidgetItem(None, QtCore.QStringList(k),3)
            self.templateTree.addTopLevelItem(self.uvcdat_items[k])
            for t in self.getMethods(self.uvcdat_items[k]):
                item = QtGui.QTreeWidgetItem(self.uvcdat_items[k], QtCore.QStringList(t),4)
        #self.plotTree.expandAll()

    def getMethods(self,item):
        analyser=item.text(0)
        if analyser == "VCS":
            return self.root.canvas[0].listelements("template")
        else:
            return ["default",]
    
class TemplateTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super(TemplateTreeWidget, self).__init__(parent)
        self.header().hide()
        self.root=parent.root
        self.setRootIsDecorated(False)
        self.delegate = dockplot.PlotTreeWidgetItemDelegate(self, self)
        self.setItemDelegate(self.delegate)
        self.connect(self,
                     QtCore.SIGNAL('itemPressed(QTreeWidgetItem *,int)'),
                     self.onItemPressed)
        self.connect(self,
                     QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *,int)'),
                     self.popupEditor)

    def onItemPressed(self, item, column):
        """ onItemPressed(item: QTreeWidgetItem, column: int) -> None
        Expand/Collapse top-level item when the mouse is pressed
        
        """
        if item and item.parent() == None:
            self.setItemExpanded(item, not self.isItemExpanded(item))
        
        
    def popupEditor(self,item,column):
        if item.type()!=4:
            return
        name = item.text(0)
        analyser = item.parent().text(0)
        editorDock = QtGui.QDockWidget(self.root)
        editorDock.setWindowTitle("%s-%s Template Editor" % (analyser,name))
        ## self.root.addDockWidget(QtCore.Qt.LeftDockWidgetArea,editorDock)
        save=QtGui.QPushButton("Save")
        cancel=QtGui.QPushButton("Cancel")
        w = QtGui.QFrame()
        v=QtGui.QVBoxLayout()
        h=QtGui.QHBoxLayout()
        h.addWidget(save)
        h.addWidget(cancel)
        if analyser == "VCS":
            w.root=self.root
            if editorDock.widget() is not None:
                editorDock.widget().destroy()
            widget = editorTemplateWidget.QEditorTemplateWidget(w,str(name))
            if str(name) == "default":
                widget.setEnabled(False)
            v.addWidget(widget)
            ## Connect Button
            save.clicked.connect(widget.applyChanges)
            cancel.clicked.connect(editorDock.close)
        else:
            print "Put code to popup",analyser,"editor"
            v.addWidget(QtGui.QLabel("Maybe one day?"))
            save.clicked.connect(editorDock.close)
            cancel.clicked.connect(editorDock.close)
        v.addLayout(h)
        w.setLayout(v)
        editorDock.setWidget(w)
        editorDock.setFloating(True)
        editorDock.show()
        
