from PyQt4 import QtCore, QtGui

from gui.uvcdat.ui_workspace import Ui_Workspace
from gui.uvcdat.project_controller import ProjectController
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from core.vistrail.action_annotation import ActionAnnotation

import customizeUVCDAT

def toAnnotation(sheet, x, y, w=None, h=None):
    """ toAnnotation(sheet: str, x: int/str, y: int/str, w: int, h: int): str
        escapes sheet string and puts all in a comma-separated string
    """
    sheet = ''.join(map(lambda i: {'\\':'\\\\', ',':'\,'}.get(i, i), sheet))
    if w is None or h is None:
        return ','.join(map(str, [sheet, x, y]))   
    return ','.join(map(str, [sheet, x, y, w, h]))

def fromAnnotation(s):
    """ fromAnnotation(s: str): list
        un-escapes annotation value string and reads all values into list
    """
    res = []
    s = list(s)
    i=0
    while i<len(s)-1:
        f = s[i:i+2]
        if f == ['\\','\\']:
            s[i:i+2] = ['\\']
            i += 1
        elif f == ['\\',',']:
            s[i:i+2] = [',']
            i += 1
        elif f[1] == ',':
            res.append(''.join(s[:i+1]))
            s = s[i+2:]
            i = -1
        i += 1
    res.append(''.join(s))
    return res

def add_annotation(vistrail, version, sheet, row, col, w=None, h=None):
    if w or h:
        cell = toAnnotation(sheet, row, col, w, h)
    else:
        cell = toAnnotation(sheet, row, col)
    new_id = vistrail.idScope.getNewId(ActionAnnotation.vtType)
    annotation = ActionAnnotation(id=new_id,
                                    action_id=version,
                                    key='uvcdatCell',
                                    value=cell,
                                    date=vistrail.getDate(),
                                    user=vistrail.getUser())
    vistrail.db_add_actionAnnotation(annotation)
    vistrail.changed = True

class QProjectItem(QtGui.QTreeWidgetItem):
    def __init__(self, view=None, name='', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        self.view = view
        #i = QtGui.QIcon(customizeVCDAT.appIcon)
        icon = QtGui.QIcon()
        closedPixmap, openPixmap = [QtGui.QPixmap(":/icons/resources/icons/" +
            f + ".png") for f in ['folder_blue', 'folder_blue_open']]
        icon.addPixmap(closedPixmap, state=QtGui.QIcon.Off)
        icon.addPixmap(openPixmap, state=QtGui.QIcon.On)
        self.setIcon(0,icon)
        if view.controller.locator:
            name = view.locator.short_name 
        self.setText(0,name)
        self.controller = ProjectController(view.controller, name)
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)
        self.currentSheet = None
        self.namedPipelines = QtGui.QTreeWidgetItem(['Named Visualizations'])
        self.namedPipelines.setIcon(0,icon)
        self.addChild(self.namedPipelines)
        self.tag_to_item = {}
        self.sheet_to_item = {}
        self.sheet_to_tab = {}

    def update_cell(self, sheetName, row, col, w=None, h=None, plot_type=None, version=0):
        if sheetName not in self.sheet_to_item:
            return
        sheetItem = self.sheet_to_item[sheetName]
        vistrail = self.view.controller.vistrail
        if plot_type and version:
            vistrail.set_action_annotation(version, 'uvcdatType', plot_type)
        
        if (row, col) not in sheetItem.pos_to_item:
            item = QWorkflowItem(version, (row, col))
            sheetItem.addChild(item)
            sheetItem.pos_to_item[(row, col)] = item
            item.update_title()
            # add actionAnnotation
            add_annotation(vistrail, version, sheetName, row, col, w, h)
        else:
            # always remove old even if updating
            for annotation in vistrail.action_annotations:
                if annotation.db_key == 'uvcdatCell':
                    cell = fromAnnotation(annotation.db_value)
                    if cell[0] == sheetName and \
                        cell[1] == row and cell[2] == col:
                        vistrail.db_delete_actionAnnotation(annotation)
            item = sheetItem.pos_to_item[(row, col)]
            if version:
                # update actionAnnotation (add new)
                add_annotation(vistrail, version, sheetName, row, col, w, h)
                item.workflowVersion = version
                item.workflowPos = (row, col)
                item.update_title()
            else:
                sheetItem.takeChild(sheetItem.indexOfChild(item))
                del sheetItem.pos_to_item[(row, col)]
                # TODO delete actionAnnotation 
            
class QSpreadsheetItem(QtGui.QTreeWidgetItem):
    def __init__(self, name='sheet 1', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/map-icon.png"))
        self.setIcon(0, icon)
        self.sheetName = name
        self.setText(0, name)
        self.pos_to_item = {}
        self.setExpanded(True)

class QWorkflowItem(QtGui.QTreeWidgetItem):
    def __init__(self, version, position=None, span=None, parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        # workflowVersion is the vistrail version id
        self.workflowVersion = version
        # workflowPos is a spreadsheet location like ("A", "2")
        self.workflowPos = position
        # workflowSpan is a spreadsheet span like ("1", "2") default is ("1", "1")
        self.workflowSpan = span
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/resources/icons/pipeline.png"))
        self.setIcon(0, icon)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsDragEnabled)


    def update_title(self):
        project = self.parent()
        while type(project) != QProjectItem:
            project = project.parent()

        tag_map = project.view.controller.vistrail.get_tagMap()
        action_map = project.view.controller.vistrail.actionMap
        count = 0
        version = self.workflowVersion
        while True:
            if version in tag_map or version <= 0:
                if version in tag_map:
                    name = tag_map[version]
                else:
                    name = "untitled"
                count_str = ""
                if count > 0:
                    count_str = "*"
                    name = name + count_str
                break
            version = action_map[version].parent
            count += 1
        
#        name = project.view.controller.get_pipeline_name(self.workflowVersion)[10:]
        if self.workflowPos is not None:
            name = name + ' @ %s%s' % (chr(ord('A') + self.workflowPos[1]),
                                        self.workflowPos[0]+1)
        if self.workflowSpan is not None:
            name = name + ' to %s%s' % (chr(ord('A') + self.workflowPos[1] +
                                                   self.workflowSpan[1]-1),
                                 self.workflowPos[0] + self.workflowSpan[0])
        self.setText(0, name)
                        
class QDragTreeWidget(QtGui.QTreeWidget):
    
    def __init__(self,parent=None):
        QtGui.QTreeWidget.__init__(self,parent=parent)
        
    def mimeData(self, items):
        if not len(items) == 1 or type(items[0]) != QWorkflowItem:
            return
        item = items[0]
        project = item.parent()
        while type(project) != QProjectItem:
            project = project.parent()
        m = QtCore.QMimeData()
        m.version = item.workflowVersion
        m.controller = project.view.controller
        return m
        
class Workspace(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.root=parent.root
        self.viewToItem = {}
        self.numProjects = 1
        self.current_controller = None
        self.setupUi(self)
        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow(
                                                                show=False)
        self.connectSignals()
        self.currentProject = None

    def setupUi(self, Workspace):
        Workspace.resize(404, 623)
        Workspace.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|
                                  QtCore.Qt.RightDockWidgetArea)
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

        spacerItem = QtGui.QSpacerItem(100, 20, QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.toolsProject)
        self.treeProjects = QDragTreeWidget(self.dockWidgetContents)
        self.treeProjects.setRootIsDecorated(True)
        self.treeProjects.setExpandsOnDoubleClick(False)
        self.treeProjects.header().setVisible(False)
        self.treeProjects.setDragEnabled(True)

        self.verticalLayout.addWidget(self.treeProjects)
        Workspace.setWidget(self.dockWidgetContents)

    def connectSignals(self):
        #self.treeProjects.currentItemChanged.connect(self.selectedNewProject)
        self.btnNewProject.clicked.connect(self.addProject)
        self.btnOpenProject.clicked.connect(self.openProject)
        self.btnSaveProject.clicked.connect(self.saveProject)
        self.btnSaveProjectAs.clicked.connect(self.saveProjectAs)
        self.btnCloseProject.clicked.connect(self.closeProject)
        self.treeProjects.itemClicked.connect(self.item_selected)
        self.connect(self, QtCore.SIGNAL("project_changed"),
                     self.spreadsheetWindow.changeTabController)
        self.connect(self, QtCore.SIGNAL("project_added"),
                     self.spreadsheetWindow.addTabController)
        self.connect(self, QtCore.SIGNAL("project_removed"),
                     self.spreadsheetWindow.removeTabController)
        self.connect(self.treeProjects,
                QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *, int)'),
                     self.item_double_clicked)

    def add_project(self, view):
        # vistrails calls this when a project is opened/created/saved
        print view, id(view), self.viewToItem
        if id(view) not in self.viewToItem:
            if self.currentProject:
                self.setBold(self.currentProject, False)
            p_name = "Project %i" % self.numProjects
            item = QProjectItem(view, p_name)
            self.currentProject = item
            self.viewToItem[id(view)] = item
            self.treeProjects.addTopLevelItem(item)
            item.setExpanded(True)
            item.namedPipelines.setExpanded(True)
            self.numProjects += 1
            # TODO add sheets from vistrail actionAnnotations
            for annotation in view.controller.vistrail.action_annotations:
                if annotation.db_key == 'uvcdatCell':
                    cell = fromAnnotation(annotation.db_value)
                    print "Found uvcdatCell:", cell, annotation, view

            # TODO read and add Variables

            self.emit(QtCore.SIGNAL("project_added"), item.controller.name)
            self.state_changed(view)
            self.connect(item.controller, QtCore.SIGNAL("update_cell"),
                     item.update_cell)
        if view.controller.locator:
            name = view.controller.locator.short_name
            self.viewToItem[id(view)].setText(0, name)
        self.treeProjects.setCurrentItem(self.viewToItem[id(view)])

    def remove_project(self, view):
        # vistrails calls this when a project is removed
        if id(view) in self.viewToItem:
            index = self.treeProjects.indexOfTopLevelItem(
                                        self.viewToItem[id(view)])
            self.treeProjects.takeTopLevelItem(index)
            self.emit(QtCore.SIGNAL("project_removed"),
                      self.viewToItem[id(view)].controller.name)
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
                if self.current_controller:
                #disconnect signals
                    self.current_controller.disconnect_spreadsheet() 
            self.currentProject = self.viewToItem[id(view)]
            self.setBold(self.currentProject, True)
            self.current_controller = self.currentProject.controller
            self.current_controller.connect_spreadsheet()
            self.emit(QtCore.SIGNAL("project_changed"),
                      self.current_controller.name)
        p = self.treeProjects.currentItem()
        defVars = self.root.dockVariable.widget()
        for i in range(defVars.varList.count()):
            v = defVars.varList.item(i)
            if not str(p.text(0)) in v.projects:
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

        for tag in item.tag_to_item:
            if tag not in tags:
                item.namedPipelines.takeChild(item.indexOfChild(
                                                item.tag_to_item[tag]))
                del item.tag_to_item[tag]
                break
        # check if a tag has been added
        tags = view.controller.vistrail.get_tagMap().iteritems()
        for i, tag in tags:
            if tag not in item.tag_to_item:
                wfitem = QWorkflowItem(i)
                item.namedPipelines.addChild(wfitem)
                wfitem.update_title()
                item.tag_to_item[tag] = wfitem

    def item_selected(self, widget_item, column):
        """ opens the selected item if possible
            item can be either project, saved workflow, spreadsheet,
            spreadsheet cell, or the Saved Workflows item
        """
        from gui.vistrails_window import _app
        sheet = None
        if not widget_item:
            self.currentProject = None
            self.current_controller = None
            return
        elif type(widget_item)==QProjectItem:
            project = widget_item
        elif type(widget_item)==QSpreadsheetItem:
            sheet = widget_item
            project = sheet.parent()
        elif type(widget_item)==QWorkflowItem:
            project = widget_item.parent().parent()
        else: # is a Saved Workflows item
            project = widget_item.parent()
        view = project.view
        locator = project.view.controller.locator
        if project != self.currentProject:            
            _app.change_view(view)
        # do we ever need to change the vistrail version?
#            version = str(widget_item.text(0))
#            if type(version) == str:
#                try:
#                    version = \
#                        view.controller.vistrail.get_version_number(version)
#                except:
#                    version = None
        #if version:
        #    view.version_selected(version, True, double_click=True)
        
        if sheet and sheet != project.currentSheet:
            project.currentSheet = sheet
            tab = project.sheet_to_tab[sheet.sheetName]
            self.spreadsheetWindow.get_current_tab_controller(
                                                    ).setCurrentWidget(tab)
            
    def add_sheet_tab(self, title, widget):
        if title not in self.currentProject.sheet_to_tab:
            self.currentProject.sheet_to_tab[title] = widget
            item = QSpreadsheetItem(title)
            self.currentProject.addChild(item)
            item.setExpanded(True)
            self.currentProject.sheet_to_item[title] = item

    def remove_sheet_tab(self, widget):
        title = None
        for t, tab in self.currentProject.sheet_to_tab.items():
            if tab == widget:
                title = t
                break
        if title and title in self.currentProject.sheet_to_tab:
            item = self.currentProject.sheet_to_item[title]
            # Remove all actionannotations associated with this sheet
            vistrail = self.currentProject.view.controller.vistrail
            for annotation in vistrail.action_annotations:
                if annotation.db_key == 'uvcdatCell':
                    cell = fromAnnotation(annotation.db_value)
                    if cell[0] == title:
                        vistrail.db_delete_actionAnnotation(annotation)
            index = self.currentProject.indexOfChild(item)
            self.currentProject.takeChild(index)
            del self.currentProject.sheet_to_tab[title]
            del self.currentProject.sheet_to_item[title]

    def change_tab_text(self, oldtitle, newtitle):
        if oldtitle in self.currentProject.sheet_to_item:
            item = self.currentProject.sheet_to_item[oldtitle]
            tab = self.currentProject.sheet_to_tab[oldtitle]
            del self.currentProject.sheet_to_item[oldtitle]
            del self.currentProject.sheet_to_tab[oldtitle]
            item.sheetName = newtitle
            item.setText(0, newtitle)
            self.currentProject.sheet_to_item[newtitle] = item
            self.currentProject.sheet_to_tab[newtitle] = tab
            # Update actionannotations
            vistrail = self.currentProject.view.controller.vistrail
            for annotation in vistrail.action_annotations:
                if annotation.db_key == 'uvcdatCell':
                    cell = fromAnnotation(annotation.db_value)
                    if cell[0] == oldtitle: # remove and update
                        vistrail.db_delete_actionAnnotation(annotation)
                        add_annotation(vistrail, annotation.db_action_id, newtitle, *cell[1:])

    def contextMenuEvent(self, event):
        """ Not used """
        item = self.treeProjects.itemAt(event.pos())
        if item and type(item) == QWorkflowItem:
            # tag this visualization with a name
            menu = QtGui.QMenu(self)
            act = QtGui.QAction("Give name", self,
                                triggered=item.tag_version)
            act.setStatusTip("Tag this visualization with a name")
            menu.addAction(act)
            menu.exec_(event.globalPos())

    def item_double_clicked(self, widget, col):
        if widget and type(widget) == QWorkflowItem:
            # tag this visualization with a name
            tag, ok = QtGui.QInputDialog.getText(self, 'Visualization "%s"' %
                                             str(widget.text(0)), "Rename to")
            if ok and str(tag).strip():
                tag = str(tag).strip()
                project = widget.parent()
                while type(project) != QProjectItem:
                    project = project.parent()
                vistrail = project.view.controller.vistrail
                if vistrail.hasTag(widget.workflowVersion):
                    vistrail.changeTag(tag, widget.workflowVersion)
                else:
                    vistrail.addTag(tag, widget.workflowVersion)
                # loop through all existing item and update
                self.state_changed(project.view)
                for sheet in project.sheet_to_item.itervalues():
                    for i in xrange(sheet.childCount()):
                        child = sheet.child(i)
                        if child.workflowVersion == widget.workflowVersion:
                            child.update_title()


    def dropEvent(self, event):
        """ Not used """
        """ Execute the pipeline at the particular location or sends events to
        project controller so it can set the workflows """
        mimeData = event.mimeData()       
        if (hasattr(mimeData, 'versionId') and
            hasattr(mimeData, 'controller')):
            event.accept()
            versionId = mimeData.versionId
            controller = mimeData.controller
            pipeline = controller.vistrail.getPipeline(versionId)

            inspector = PipelineInspector()
            inspector.inspect_spreadsheet_cells(pipeline)
            inspector.inspect_ambiguous_modules(pipeline)
            if len(inspector.spreadsheet_cells)==1:
                print "one cell only"
            print "cells", inspector.spreadsheet_cells

    def get_current_project_controller(self):
        return self.current_controller


