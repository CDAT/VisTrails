from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_workspace import Ui_Workspace
import customizeUVCDAT

class QProjectItem(QtGui.QTreeWidgetItem):
    def __init__(self, view=None, name='', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        self.view = view
        #i = QtGui.QIcon(customizeVCDAT.appIcon)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/folder_blue.png"), state=QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/folder_blue_open.png"), state=QtGui.QIcon.On)
        self.setIcon(0,icon)
        if view.controller.locator:
           name = view.locator.short_name 
        self.setText(0,name)
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)
        self.latestItem = QVisualizationItem()
        self.addChild(self.latestItem)
        self.tag_to_item = {}

class QVisualizationItem(QtGui.QTreeWidgetItem):
    def __init__(self, name='(latest)', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/pipeline.png"))
        self.setIcon(0,icon)
        self.setText(0,name)

class Workspace(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.root=parent.root
        self.viewToItem = {}
        self.numProjects = 1
        self.setupUi(self)
        self.connectSignals()
        self.currentProject = None

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

        spacerItem = QtGui.QSpacerItem(100, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.toolsProject)
        self.treeProjects = QtGui.QTreeWidget(self.dockWidgetContents)
        self.treeProjects.setRootIsDecorated(True)
        self.treeProjects.setExpandsOnDoubleClick(False)
        self.treeProjects.header().setVisible(False)
        self.verticalLayout.addWidget(self.treeProjects)
        Workspace.setWidget(self.dockWidgetContents)

    def connectSignals(self):
#        self.treeProjects.currentItemChanged.connect(self.selectedNewProject)
        self.btnNewProject.clicked.connect(self.addProject)
        self.btnOpenProject.clicked.connect(self.openProject)
        self.btnSaveProject.clicked.connect(self.saveProject)
        self.btnSaveProjectAs.clicked.connect(self.saveProjectAs)
        self.btnCloseProject.clicked.connect(self.closeProject)
        self.treeProjects.itemClicked.connect(self.item_selected)

    def add_project(self, view):
        # vistrails calls this when a project is created
        if id(view) not in self.viewToItem:
            if self.currentProject:
                self.setBold(self.currentProject, False)
            item = QProjectItem(view, "Project %i" % self.numProjects)
            self.currentProject = item
            self.viewToItem[id(view)] = item
            self.treeProjects.addTopLevelItem(item)
            self.numProjects += 1
            self.state_changed(view)
        if view.controller.locator:
            name = view.controller.locator.short_name
            self.viewToItem[id(view)].setText(0, name)
        self.treeProjects.setCurrentItem(self.viewToItem[id(view)])

    def remove_project(self, view):
        # vistrails calls this when a project is removed
        if id(view) in self.viewToItem:
            index = self.treeProjects.indexOfTopLevelItem(self.viewToItem[id(view)])
            self.treeProjects.takeTopLevelItem(index)
            del self.viewToItem[id(view)]

    def setBold(self, item, value):
            font = item.font(0)
            font.setBold(value)
            item.setFont(0, font)

    def change_project(self, view):
        # vistrails calls this when a different project is selected
        if id(view) in self.viewToItem:
            if self.currentProject:
                self.setBold(self.currentProject, False)
            self.currentProject = self.viewToItem[id(view)]
            self.setBold(self.currentProject, True)
        # TODO need to update variables here
        defVars = self.root.dockVariable.widget()
        for i in range(defVars.varList.count()):
            v = defVars.varList.item(i)
            if not id(self.currentProject) in v.projects:
                v.setHidden(True)
            else:
                v.setHidden(False)
        defVars.refreshVariablesStrings()

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

    def state_changed(self, view):
        """ update tags """
        item = self.viewToItem[id(view)]
        # check if a tag has been deleted
        tags = view.controller.vistrail.get_tagMap().values()

        deleted_item = None
        for tag, wf in item.tag_to_item.items():
            if tag not in tags:
                item.takeChild(item.indexOfChild(item.tag_to_item[tag]))
                del item.tag_to_item[tag]
                break
        # check if a tag has been added
        for tag in tags:
            if tag not in item.tag_to_item:
                wfitem = QVisualizationItem(tag)
                item.addChild(wfitem)
                item.tag_to_item[tag] = wfitem

    def item_selected(self, widget_item, column):
        """ opens the selected item if possible """
        from gui.vistrails_window import _app
        if not widget_item:
            self.currentProject=None
            return
        elif type(widget_item)==QProjectItem:
            if widget_item != self.currentProject:            
                _app.change_view(widget_item.view)
                return
        elif type(widget_item)!=QVisualizationItem:
            # unknown widget type
            return
        # select specific version
        project = widget_item.parent()
        view = project.view
        locator = project.view.controller.locator
        if widget_item == project.latestItem:
            version = view.controller.vistrail.get_latest_version()
        else:
            version = str(widget_item.text(0))
            if type(version) == str:
                try:
                    version = \
                        view.controller.vistrail.get_version_number(version)
                except:
                    version = None
        if project != self.currentProject:            
            _app.change_view(view)
        if version:
            view.version_selected(version, True, double_click=True)
