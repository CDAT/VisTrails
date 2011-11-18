from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_workspace import Ui_Workspace
import customizeUVCDAT

class QProjectItem(QtGui.QTreeWidgetItem):
    def __init__(self, view=None, name='', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        self.view = view
        #i = QtGui.QIcon(customizeVCDAT.appIcon)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/folder_blue.png"))
        self.setIcon(0,icon)
        if view.controller.locator:
           name = view.locator.short_name 
        self.setText(0,name)

class Workspace(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.root=parent.root
        self.viewToItem = {}
        self.numProjects = 1
        self.setupUi(self)

        self.connectSignals()

    def setupUi(self, Workspace):
        Workspace.resize(404, 623)
        Workspace.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        Workspace.setWindowTitle("Projects")
        self.dockWidgetContents = QtGui.QWidget()
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.toolsProject = QtGui.QFrame(self.dockWidgetContents)
        self.toolsProject.setFrameShape(QtGui.QFrame.StyledPanel)
        self.toolsProject.setFrameShadow(QtGui.QFrame.Raised)
        self.horizontalLayout = QtGui.QHBoxLayout(self.toolsProject)
        self.horizontalLayout.setSpacing(1)
        self.horizontalLayout.setMargin(0)

        self.btnNewProject = QtGui.QToolButton()
        self.btnNewProject.setToolTip("Create New Project")
        self.btnNewProject.setText("New Project")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/new.png"))
        self.btnNewProject.setIcon(icon)
        self.btnNewProject.setIconSize(QtCore.QSize(22, 22))
        self.horizontalLayout.addWidget(self.btnNewProject)

        self.btnOpenProject = QtGui.QToolButton()
        self.btnOpenProject.setToolTip("Open Project")
        self.btnOpenProject.setText("Open Project")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/resources/icons/open.png"))
        self.btnOpenProject.setIcon(icon1)
        self.btnOpenProject.setIconSize(QtCore.QSize(22, 22))
        self.horizontalLayout.addWidget(self.btnOpenProject)

        self.btnSaveProject = QtGui.QToolButton()
        self.btnSaveProject.setToolTip("Save Project")
        self.btnSaveProject.setText("Save Project")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/resources/icons/save.png"))
        self.btnSaveProject.setIcon(icon1)
        self.btnSaveProject.setIconSize(QtCore.QSize(22, 22))
        self.horizontalLayout.addWidget(self.btnSaveProject)

        self.btnSaveProjectAs = QtGui.QToolButton()
        self.btnSaveProjectAs.setToolTip("Save Project As")
        self.btnSaveProjectAs.setText("Save Project As")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/resources/icons/save-as.png"))
        self.btnSaveProjectAs.setIcon(icon1)
        self.btnSaveProjectAs.setIconSize(QtCore.QSize(22, 22))
        self.horizontalLayout.addWidget(self.btnSaveProjectAs)

        self.btnCloseProject = QtGui.QToolButton()
        self.btnCloseProject.setToolTip("Close Project")
        self.btnCloseProject.setText("Close Project")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/resources/icons/close.png"))
        self.btnCloseProject.setIcon(icon1)
        self.btnCloseProject.setIconSize(QtCore.QSize(22, 22))
        self.horizontalLayout.addWidget(self.btnCloseProject)

        spacerItem = QtGui.QSpacerItem(207, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.toolsProject)
        self.treeProjects = QtGui.QTreeWidget(self.dockWidgetContents)
        self.treeProjects.setRootIsDecorated(True)
        self.treeProjects.setExpandsOnDoubleClick(False)
        self.treeProjects.header().setVisible(False)
        self.verticalLayout.addWidget(self.treeProjects)
        Workspace.setWidget(self.dockWidgetContents)

    def connectSignals(self):
        self.treeProjects.currentItemChanged.connect(self.selectedNewProject)
        self.btnNewProject.clicked.connect(self.addProject)
        self.btnOpenProject.clicked.connect(self.openProject)
        self.btnSaveProject.clicked.connect(self.saveProject)
        self.btnSaveProjectAs.clicked.connect(self.saveProjectAs)
        self.btnCloseProject.clicked.connect(self.closeProject)

    
    def add_project(self, view):
        # vistrails calls this when a project is created
        if view not in self.viewToItem:
            item = QProjectItem(view, "Project %i" % self.numProjects)
            self.viewToItem[view] = item
            self.treeProjects.addTopLevelItem(item)
            self.numProjects += 1
        self.treeProjects.setCurrentItem(self.viewToItem[view])

    def remove_project(self, view):
        # vistrails calls this when a project is removed
        if view in self.viewToItem:
            index = self.treeProjects.indexOfTopLevelItem(self.viewToItem[view])
            self.treeProjects.takeTopLevelItem(index)
            del self.viewToItem[view]

    def change_project(self, view):
        # vistrails calls this when a different project is selected
        if view in self.viewToItem:
            self.treeProjects.setCurrentItem(self.viewToItem[view])
            # need to update variables here

    def addProject(self, clicked):
        from gui.vistrails_window import _app
        _app.new_vistrail()
        
    def openProject(self, clicked):
        from gui.vistrails_window import _app
        _app.open_vistrail_default()

    def saveProject(self, clicked):
        from gui.vistrails_window import _app
        _app.qactions['saveFile'].trigger()

    def saveProjectAs(self, clicked):
        from gui.vistrails_window import _app
        _app.qactions['saveFileAs'].trigger()

    def closeProject(self, clicked):
        from gui.vistrails_window import _app
        _app.close_vistrail()

    def selectedNewProject(self, current, previous):
        if not current:
            self.selectedProject=None
            return
        else:
            p = str(current.text(0))
            self.selectedProject=p
            from gui.vistrails_window import _app
            _app.change_view(current.view)
        defVars = self.root.dockVariable.widget()
        for i in range(defVars.varList.count()):
            v = defVars.varList.item(i)
            if not p in v.projects:
                v.setHidden(True)
            else:
                v.setHidden(False)
        defVars.refreshVariablesStrings()
