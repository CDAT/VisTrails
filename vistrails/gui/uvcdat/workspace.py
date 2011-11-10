from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_workspace import Ui_Workspace
from qtbrowser import customizeVCDAT

class Workspace(QtGui.QDockWidget, Ui_Workspace):
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.root=parent.root
        self.setupUi(self)
        self.connectSignals()


    def connectSignals(self):
        self.treeProjects.currentItemChanged.connect(self.selectedNewProject)
        pass
    
    def addProject(self,name=None):
        N = self.treeProjects.topLevelItemCount()
        if name is None:
            name = "Project %i" % (N+1)

        p = QtGui.QTreeWidgetItem(0)
        p.setText(0,name)
        i = QtGui.QIcon(customizeVCDAT.appIcon)
        p.setIcon(0,i)
        
        self.treeProjects.addTopLevelItem(p)
        self.treeProjects.setCurrentItem(p)
        
    def renameProject(self,name):
        ## place holder, we will need to edit all defined variables to edit the prject name
        pass

    def selectedNewProject(self):
        p = str(self.treeProjects.currentItem().text(0))
        self.selectedProject=p
        defVars = self.root.dockVariable.widget()
        for i in range(defVars.varList.count()):
            v = defVars.varList.item(i)
            if not p in v.projects:
                v.setHidden(True)
            else:
                v.setHidden(False)
        defVars.refreshVariablesStrings()
