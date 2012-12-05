from PyQt4 import QtCore, QtGui

from gui.uvcdat.project_controller import ProjectController
from gui.uvcdat.theme import UVCDATTheme
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from core.vistrail.action_annotation import ActionAnnotation
from core.thumbnails import ThumbnailCache
from packages.spreadsheet.spreadsheet_tab import StandardWidgetSheetTab
import customizeUVCDAT, traceback

def toAnnotation(sheet, x, y, w=None, h=None):
    """ toAnnotation(sheet: str, x: int/str, y: int/str,
                                 w: int/str, h: int/str) -> str
    Escapes sheet string and puts all in a comma-separated string
    """
    sheet = ''.join(map(lambda i: {'\\':'\\\\', ',':'\,'}.get(i, i), sheet))
    if w is None or h is None:
        return ','.join(map(str, [sheet, x, y]))   
    return ','.join(map(str, [sheet, x, y, w, h]))

def fromAnnotation(s):
    """ fromAnnotation(s: String) -> List
    Un-escapes annotation value string and reads all values into list
    List contains [sheetName, x, y (, w, h)]
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
    return [res[0]]+map(int,res[1:])

def add_annotation(vistrail, version, sheet, row, col, w=None, h=None):
    """ add_annotation(vistrail: Vistrail, version: int, sheet: str,
                 row: int/str, col: int/str, w: int/str, h: int/str) -> None
    Adds corresponding actionAnnotation to vistrail
    """
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
    """ QProjectItem represents a uv-cdat project containing a set of
        sheets with visualizations
    """
    def __init__(self, view=None, name='', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        self.view = view
        #i = QtGui.QIcon(customizeVCDAT.appIcon)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsSelectable)
        icon = QtGui.QIcon()
        openPixmap = UVCDATTheme.WORKSPACE_FOLDER_OPEN_PIXMAP
        closedPixmap = UVCDATTheme.WORKSPACE_FOLDER_CLOSED_PIXMAP 
        icon.addPixmap(closedPixmap, state=QtGui.QIcon.Off)
        icon.addPixmap(openPixmap, state=QtGui.QIcon.On)
        self.setIcon(0,icon)
        if view.controller.locator:
            name = view.locator.short_name 
        self.setText(0,str(name)+'*')
        self.controller = ProjectController(view.controller, name)
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)
        self.namedPipelines = QtGui.QTreeWidgetItem(['Named Visualizations'])
        self.namedPipelines.setIcon(0,icon)
        self.namedPipelines.setFlags(self.flags()&~QtCore.Qt.ItemIsSelectable)

        self.addChild(self.namedPipelines)
        self.tag_to_item = {}
        self.sheet_to_item = {}
        self.sheet_to_tab = {}

    def update_cell(self, sheetName, row, col, w=None, h=None, plot_type=None,
                    version=0, annotate=True):
        """ update_cell(sheetName: str, row: int, col: int, w: int, h: int,
                         plot_type: str, version: int, annotate: bool) -> None
        Called when a cell is updated
        Updates cell item, annotation, cell title, and sheet icon.
        """
        if sheetName not in self.sheet_to_item:
            return
        sheetItem = self.sheet_to_item[sheetName]
        vistrail = self.view.controller.vistrail
        if plot_type and version and annotate:
            vistrail.set_action_annotation(version, 'uvcdatType', plot_type)
        
        if (row, col) not in sheetItem.pos_to_item:
            item = QWorkflowItem(version, (row, col), plot_type=plot_type)
            sheetItem.addChild(item)
            sheetItem.pos_to_item[(row, col)] = item
            item.update_title()
            # add actionAnnotation
            if annotate:
                add_annotation(vistrail, version, sheetName, row, col, w, h)
        elif annotate:
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
                item.plotType = plot_type
                item.update_title()
            else:
                sheetItem.takeChild(sheetItem.indexOfChild(item))
                del sheetItem.pos_to_item[(row, col)]
        sheetItem.update_icon()
        self.view.controller.set_changed(True)

    def sheetSizeChanged(self, sheet, dim=[]):
        """ sheetSizeChanged(sheet: str, dim: List) -> None
        Called when current sheet tab dimensions are changed
        Updates uvcdatSheetSize annotation and removes out of bounds item
        """
        if sheet not in self.sheet_to_item:
            return
        key = 'uvcdatSheetSize:' + sheet
        value = ','.join(map(str, dim))
        vistrail = self.view.controller.vistrail
        vistrail.set_annotation(key, value)
        # remove cells outside new range
        sheetItem = self.sheet_to_item[sheet]
        for annotation in vistrail.action_annotations:
            if annotation.db_key == 'uvcdatCell':
                cell = fromAnnotation(annotation.db_value)
                if dim and cell[0] == sheet and \
                    (cell[1] >= dim[0] or cell[2] >= dim[1]):
                    vistrail.db_delete_actionAnnotation(annotation)
                    item = sheetItem.pos_to_item[(cell[1], cell[2])]
                    sheetItem.takeChild(sheetItem.indexOfChild(item))
                    del sheetItem.pos_to_item[(cell[1], cell[2])]
        sheetItem.update_icon()
        self.view.controller.set_changed(True)

    def sheetSize(self, sheet):
        """ sheetSize(sheet: str) -> 2-List
        Reads uvcdatSheetSize annotation and returns its value
        """
        dimval = self.view.controller.vistrail.get_annotation(
                                                     'uvcdatSheetSize:'+sheet)
        return map(int, dimval.value.split(',')) if dimval else (2,1)
    
    def show_provenance(self, sheetName, row, col):
        """show_provenance(sheetName: str, row: int, col: int)  -> None
        Will display pipeline for current item.
        """
        if sheetName not in self.sheet_to_item:
            return
        
        sheetItem = self.sheet_to_item[sheetName]
        if (row, col) not in sheetItem.pos_to_item:
            return
        
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        _app.uvcdatWindow.showBuilderWindowActTriggered()
        
        item = sheetItem.pos_to_item[(row, col)]
        version = item.workflowVersion
        self.view.version_selected(version, True, double_click=True)
        
        
class QSpreadsheetItem(QtGui.QTreeWidgetItem):
    """ QSpreadsheetItem represents a uv-cdat spreadsheet tab containing
        visualizations
    """
    def __init__(self, name='sheet 1', parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        self.sheetName = name
        self.setText(0, name)
        self.pos_to_item = {}
        self.setExpanded(True)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsSelectable)

    def update_icon(self):
        """ update_icon() -> None
        Compose workflow icons into a spreadsheet icon
        """
        size = 24
        pic = QtGui.QPixmap(size, size)
        cols, rows = self.parent().sheetSize(self.sheetName)
        w, h = size/cols, size/rows
        painter = QtGui.QPainter(pic)
        painter.fillRect(0, 0, size, size, QtCore.Qt.lightGray)
        vistrail = self.parent().view.controller.vistrail
        for pos, item in self.pos_to_item.iteritems(): 
            if vistrail.has_thumbnail(item.workflowVersion):
                x, y = pos
                tname = vistrail.get_thumbnail(item.workflowVersion)
                cache = ThumbnailCache.getInstance()
                path = cache.get_abs_name_entry(tname)
                if path:
                    pixmap = QtGui.QPixmap(path)
                    painter.fillRect(h*y, w*x, h, w, QtCore.Qt.white)
                    painter.drawPixmap(h*y, w*x, h, w, pixmap.scaled(h, w, transformMode=QtCore.Qt.SmoothTransformation))
        # draw spreadsheet grid
        painter.setPen(QtCore.Qt.black)
        for x in xrange(rows+1):
            painter.drawLine(x*h-0.01, 0, x*h-0.01, size)
        for y in xrange(cols+1):
            painter.drawLine(0, y*w-0.01, size, y*w-0.01)
        painter.end()
        self.setIcon(0, QtGui.QIcon(pic))
       
        #tooltip = """<html>%(name)s<br/><img border=0 src='%(path)s'/></html>
        #                    """ % {'name':name, 'path':path}
        #self.setToolTip(0, tooltip)


class QWorkflowItem(QtGui.QTreeWidgetItem):
    """ QWorkflowItem represents a uv-cdat visualization
    """
    def __init__(self, version, position=None, span=None, plot_type=None, parent=None):
        QtGui.QTreeWidgetItem.__init__(self)
        # workflowVersion is the vistrail version id
        self.workflowVersion = version
        # workflowPos is a spreadsheet location like ("A", "2")
        self.workflowPos = position
        # workflowSpan is a spreadsheet span like ("1", "2") default is ("1", "1")
        self.workflowSpan = span
        # plotType is the package type of a plot, like VCS, PVClimate, DV3D
        self.plotType = plot_type
        icon = UVCDATTheme.WORKSPACE_PIPELINE_ICON
        self.setIcon(0, icon)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsDragEnabled)


    def update_title(self):
        """ update_title() -> None
        Update title using version, tag name, position and span
        """
        project = self.parent()
        while type(project) != QProjectItem:
            project = project.parent()
            vistrail = project.view.controller.vistrail
        tag_map = vistrail.get_tagMap()
        action_map = vistrail.actionMap
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

        version = self.workflowVersion
        if vistrail.has_thumbnail(version):
            tname = vistrail.get_thumbnail(version)
            cache = ThumbnailCache.getInstance()
            path = cache.get_abs_name_entry(tname)
            if path:
                pixmap = QtGui.QPixmap(path)
                self.setIcon(0, QtGui.QIcon(pixmap.scaled(24, 24, transformMode=QtCore.Qt.SmoothTransformation)))
                tooltip = """<html>%(name)s<br/><img border=0 src='%(path)s'/></html>
                        """ % {'name':name, 'path':path}
                self.setToolTip(0, tooltip)

class QProjectsWidget(QtGui.QTreeWidget):
    """ QProjectsWidget
        A tree containing project items
    """
    def __init__(self,parent=None, workspace=None):
        QtGui.QTreeWidget.__init__(self,parent=parent)
        self.workspace = workspace

    def mimeData(self, items):
        """ mimeData() -> QMimeData
        Sets mimedata for QWorkflowItem's including:
            version: int, controller: ProjectController, plot_type: str
        """
        if not len(items) == 1 or type(items[0]) != QWorkflowItem:
            return
        item = items[0]
        project = item.parent()
        while type(project) != QProjectItem:
            project = project.parent()
        m = QtCore.QMimeData()
        m.version = item.workflowVersion
        m.controller = project.view.controller
        m.plot_type = item.plotType
        return m
    
    def keyPressEvent(self, event):
        """ keyPressEvent(event: QKeyEvent) -> None
            Handles keypresses on items
            Currently handles deletes of named visualizations
        """
        if event.key() in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            items = self.selectedItems()
            if len(items) == 1:
                item = items[0]
                if type(item) == QWorkflowItem and \
                   type(item.parent()) != QSpreadsheetItem:
                    # remove tag
                    view = item.parent().parent().view
                    view.controller.vistrail.set_tag(item.workflowVersion, '')
                    view.stateChanged()
        else:
            QtGui.QTreeWidget.keyPressEvent(self, event)

class Workspace(QtGui.QDockWidget):
    """ Workspace
    A dock widget containing a tree widget that handles project interactions
    """
    def __init__(self, parent=None):
        super(Workspace, self).__init__(parent)
        self.root=parent.root
        self.viewToItem = {}
        self.numProjects = 1
        self.setupUi(self)
        self.spreadsheetWindow = spreadsheetController.findSpreadsheetWindow(
                                                                show=False)
        self.connectSignals()
        self.currentProject = None
        self.current_controller = None

    def setupUi(self, Workspace):
        """ setupUi(Workspace: Widget) -> None
        Sets up the gui elements for the Workspace Widget
        """
        Workspace.resize(404, 623)
        Workspace.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|
                                  QtCore.Qt.RightDockWidgetArea)
        Workspace.setWindowTitle("Projects")
        self.dockWidgetContents = QtGui.QWidget()
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.toolsProject = QtGui.QToolBar(self.dockWidgetContents)
        self.toolsProject.setIconSize(QtCore.QSize(24,24))
        
        icon = UVCDATTheme.WORKSPACE_NEW_PROJECT_ICON
        self.btnNewProject = QtGui.QAction(icon, "New Project",self)
        self.btnNewProject.setToolTip("Create New Project")
        self.toolsProject.addAction(self.btnNewProject)
        
        icon1 = UVCDATTheme.WORKSPACE_OPEN_PROJECT_ICON
        self.btnOpenProject = QtGui.QAction(icon1,"Open Project", self)
        self.btnOpenProject.setToolTip("Open Project")
        self.toolsProject.addAction(self.btnOpenProject)

        icon1 = UVCDATTheme.WORKSPACE_SAVE_PROJECT_ICON
        self.btnSaveProject = QtGui.QAction(icon1, "Save Project", self)
        self.btnSaveProject.setToolTip("Save Project")
        self.toolsProject.addAction(self.btnSaveProject)

        #the save as action will be added to the menu only
        self.btnSaveProjectAs = QtGui.QAction("Save Project As", self)
        self.btnSaveProjectAs.setToolTip("Save Project As")
        #self.toolsProject.addAction(self.btnSaveProjectAs)

        icon1 = UVCDATTheme.WORKSPACE_CLOSE_PROJECT_ICON
        self.btnCloseProject = QtGui.QAction(icon1, "Close Project", self)
        self.btnCloseProject.setToolTip("Close Project")
        self.toolsProject.addAction(self.btnCloseProject)

        self.verticalLayout.addWidget(self.toolsProject)
        self.treeProjects = QProjectsWidget(self.dockWidgetContents, self)
        self.treeProjects.setRootIsDecorated(True)
        self.treeProjects.setExpandsOnDoubleClick(False)
        self.treeProjects.header().setVisible(False)
        self.treeProjects.setDragEnabled(True)

        self.verticalLayout.addWidget(self.treeProjects)
        Workspace.setWidget(self.dockWidgetContents)

    def connectSignals(self):
        """ connectSignals() -> None
        Connects the Qt signals for the Workspace Widgets
        """
        #self.treeProjects.currentItemChanged.connect(self.selectedNewProject)
        self.btnNewProject.triggered.connect(self.addProject)
        self.btnOpenProject.triggered.connect(self.openProject)
        self.btnSaveProject.triggered.connect(self.saveProject)
        self.btnSaveProjectAs.triggered.connect(self.saveProjectAs)
        self.btnCloseProject.triggered.connect(self.closeProject)
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
        """ add_project(view: QVistrailView) -> None
        vistrails calls this when a project is opened/created/saved
        Items and spreadsheets are updated
        """
        try:
            if id(view) not in self.viewToItem:
                if self.currentProject:
                    self.setBold(self.currentProject, False)
                p_name = "Project %i" % self.numProjects
                item = QProjectItem(view, p_name)
                self.currentProject = item
                self.current_controller = item.controller
                self.viewToItem[id(view)] = item
                self.treeProjects.addTopLevelItem(item)
                item.setExpanded(True)
                item.namedPipelines.setExpanded(True)
                self.numProjects += 1
                self.emit(QtCore.SIGNAL("project_added"), item.controller.name)
                self.state_changed(view)
                # add sheets from vistrail actionAnnotations
                tc = self.spreadsheetWindow.get_current_tab_controller()
                for annotation in view.controller.vistrail.action_annotations:
                    if annotation.db_key != 'uvcdatCell':
                        continue
                    cell = fromAnnotation(annotation.db_value)
                    plot_type = view.controller.vistrail.get_action_annotation(
                                    annotation.db_action_id, "uvcdatType")
                    if cell[0] not in item.sheet_to_item:
                        rows, cols = self.currentProject.sheetSize(cell[0])
                        tc.setCurrentIndex(tc.addTabWidget(
                                             StandardWidgetSheetTab(tc), cell[0]))
                        tab = tc.currentWidget()
                        tab.sheet.stretchCells()
                        tab.setDimension(rows, cols)
                        tab.sheet.setRowCount(rows)
                        tab.sheet.setColumnCount(cols)
                        tab.sheet.stretchCells()
                        tab.displayPrompt()
                        tab.setEditingMode(tab.tabWidget.editingMode)
                    else:
                        tab = item.sheet_to_tab[cell[0]]
                        self.spreadsheetWindow.get_current_tab_controller(
                                                           ).setCurrentWidget(tab)
                    # Add cell
                   
                    if len(cell)<5:
                        item.controller.vis_was_dropped((view.controller, 
                                     annotation.db_action_id, cell[0],
                                     int(cell[1]), int(cell[2]), plot_type.value))
                        item.update_cell(cell[0], int(cell[1]), int(cell[2]),
                                         None, None, plot_type.value,
                                         annotation.db_action_id, False)
                    else:
                        item.controller.vis_was_dropped((view.controller,
                                     annotation.db_action_id, cell[0],
                                     int(cell[1]), int(cell[2]), plot_type.value))
                        item.update_cell(cell[0], int(cell[1]), int(cell[2]),
                                         int(cell[3]), int(cell[4]),
                                         plot_type.value,
                                         annotation.db_action_id, False)
                if not len(item.sheet_to_item):
                    tc.create_first_sheet()
                self.connect(item.controller, QtCore.SIGNAL("update_cell"),
                         item.update_cell)
                self.connect(item.controller, QtCore.SIGNAL("sheet_size_changed"),
                         item.sheetSizeChanged)
                self.connect(item.controller, QtCore.SIGNAL("show_provenance"),
                             item.show_provenance)
     
            if view.controller.locator:
                name = view.controller.locator.short_name
                self.viewToItem[id(view)].setText(0, name)
            self.treeProjects.setCurrentItem(self.viewToItem[id(view)])
            
        except Exception, err:
            print "Error adding project: ", str(err)
            traceback.print_exc( 100, sys.stderr )

    def remove_project(self, view):
        """ remove_project(view: QVistrailView) -> None
        vistrails calls this when a project is closed
        Items and spreadsheets are removed
        """
        if id(view) in self.viewToItem:
            index = self.treeProjects.indexOfTopLevelItem(
                                        self.viewToItem[id(view)])
            self.treeProjects.takeTopLevelItem(index)
            self.emit(QtCore.SIGNAL("project_removed"),
                      self.viewToItem[id(view)].controller.name)
            del self.viewToItem[id(view)]
            
    def setBold(self, item, value):
        """ setBold(item: Widget, value: bool) -> None
        Toggles the boldness of the widget text
        """
        font = item.font(0)
        font.setBold(value)
        item.setFont(0, font)

    def change_project(self, view):
        """ change_project(view: QVistrailView) -> None
        vistrails calls this when a different project is selected
        Current project is highlighted in bold
        spreadsheet and variables are changed
        """
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
            self.emit(QtCore.SIGNAL("project_changed"),
                      self.current_controller.name)
            self.current_controller.connect_spreadsheet()
        
        defVars = self.root.dockVariable.widget()
        for i in range(defVars.varList.count()):
            v = defVars.varList.item(i)
            if not str(self.current_controller.name) in v.projects:
                v.setHidden(True)
            else:
                v.setHidden(False)
        defVars.refreshVariablesStrings()

    def addProject(self, clicked):
        """ addProject(clicked: bool) -> None
        Creates new project through vistrails
        """
        from gui.vistrails_window import _app
        _app.new_vistrail()
        
    def openProject(self, clicked):
        """ openProject(clicked: bool) -> None
        Opens project using vistrails
        """
        from gui.vistrails_window import _app
        _app.open_vistrail_default()

    def saveProject(self, clicked):
        """ saveProject(clicked: bool) -> None
        Save project using vistrails
        """
        from gui.vistrails_window import _app
        _app.qactions['saveFile'].trigger()

    def saveProjectAs(self, clicked):
        """ saveProjectAs(clicked: bool) -> None
        Save project as new file using vistrails
        """
        from gui.vistrails_window import _app
        _app.qactions['saveFileAs'].trigger()

    def closeProject(self, clicked):
        """ closeProject(clicked: bool) -> None
        Close file using vistrails
        """
        from gui.vistrails_window import _app
        _app.close_vistrail()

    def state_changed(self, view):
        """ state_changed(view: QVistrailView) -> None
        Update tags and project titles
        """
        item = self.viewToItem[id(view)]
        if item.view.controller.locator:
            name = item.view.controller.locator.short_name 
            if item.view.has_changes():
                name += '*'
            item.setText(0,name)
        
        # check if a tag has been deleted
        tags = view.controller.vistrail.get_tagMap().values()
        item.namedPipelines.setHidden(not tags)
        for tag in item.tag_to_item:
            if tag not in tags:
                item.namedPipelines.takeChild(
                      item.namedPipelines.indexOfChild(item.tag_to_item[tag]))
                del item.tag_to_item[tag]
                break
        # check if a tag has been added
        tags = view.controller.vistrail.get_tagMap().iteritems()
        for i, tag in tags:
            if tag not in item.tag_to_item:
                ann = view.controller.vistrail.get_action_annotation(i, 
                                                                "uvcdatType")
                if ann:
                    wfitem = QWorkflowItem(i, plot_type=ann.value)
                    item.namedPipelines.addChild(wfitem)
                    wfitem.update_title()
                    item.tag_to_item[tag] = wfitem
                else:
                    print "Error: No Plot Type specified!"
        for sheet in item.sheet_to_item.itervalues():
            for i in xrange(sheet.childCount()):
                child = sheet.child(i)
                child.update_title()

    def item_selected(self, widget_item, column):
        """ item_selected(widget_item: QTreeWidgetItem, cloumn: int) -> None
        Opens the selected item if possible
        Existing items are: project, saved workflow, spreadsheet,
        spreadsheet cell, or the Saved Workflows item
        """
        from gui.vistrails_window import _app
        sheet = None
        if not widget_item:
            self.currentProject = None
            self.current_controller = None
            return
        elif type(widget_item)==QProjectItem:
            widget_item.setSelected(False)
            project = widget_item
        elif type(widget_item)==QSpreadsheetItem:
            widget_item.setSelected(False)        
            sheet = widget_item
            project = sheet.parent()
        elif type(widget_item)==QWorkflowItem:
            project = widget_item.parent().parent()
            if type(widget_item.parent()) == QSpreadsheetItem:
                sheet = widget_item.parent()
        else: # is a Saved Workflows item
            widget_item.setSelected(False)        
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
        
        if sheet:
            tab = project.sheet_to_tab[sheet.sheetName]
            self.spreadsheetWindow.get_current_tab_controller(
                                                    ).setCurrentWidget(tab)

    def add_sheet_tab(self, title, widget):
        """ add_sheet_tab(title: str, widget: SpreadsheetTab) -> None
        Called when a spreadsheet tab is added
        Add a spreadsheet item and set size annotation
        """
        if self.currentProject:
            if title not in self.currentProject.sheet_to_tab:
                self.currentProject.sheet_to_tab[title] = widget
                item = QSpreadsheetItem(title)
                self.currentProject.addChild(item)
                item.update_icon()
                item.setExpanded(True)
                self.currentProject.sheet_to_item[title] = item
                self.currentProject.controller.sheet_map[title] = {}
                if not self.currentProject.sheetSize(title):
                    self.currentProject.sheetSizeChanged(title, (2,1))

    def remove_sheet_tab(self, widget):
        """ remove_sheet_tab(widget: QTreeWidgetItem) -> None
        Called when a tab is removed from the spreadsheet
        Removes vistrail annotations, tree items, and indexes
        """
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
            del self.currentProject.controller.sheet_map[title]
            self.currentProject.sheetSizeChanged(title)
        self.currentProject.view.controller.set_changed(True)

    def change_tab_text(self, oldtitle, newtitle):
        """ change_tab_text(oldtitle: str, newtitle: str) -> None
        Called when the title of a spreadsheet tab is changed
        Updates vistrail annotations, indexes, and item titles
        """
        
        if oldtitle not in self.currentProject.sheet_to_item:
            return
        item = self.currentProject.sheet_to_item[oldtitle]
        tab = self.currentProject.sheet_to_tab[oldtitle]
        del self.currentProject.sheet_to_item[oldtitle]
        del self.currentProject.sheet_to_tab[oldtitle]
        dimval = self.currentProject.sheetSize(oldtitle)
        self.currentProject.sheetSizeChanged(oldtitle)
        item.sheetName = newtitle
        item.setText(0, newtitle)
        self.currentProject.sheet_to_item[newtitle] = item
        self.currentProject.sheet_to_tab[newtitle] = tab
        self.currentProject.sheetSizeChanged(newtitle, dimval)
        # update controller sheetmap
        sheetmap = self.currentProject.controller.sheet_map[oldtitle]
        del self.currentProject.controller.sheet_map[oldtitle]
        self.currentProject.controller.sheet_map[newtitle] = sheetmap
        # Update actionannotations
        vistrail = self.currentProject.view.controller.vistrail
        for annotation in vistrail.action_annotations:
            if annotation.db_key == 'uvcdatCell':
                cell = fromAnnotation(annotation.db_value)
                if cell[0] == oldtitle: # remove and update
                    vistrail.db_delete_actionAnnotation(annotation)
                    add_annotation(vistrail, annotation.db_action_id,
                                   newtitle, *cell[1:])
        item.update_icon()
        self.currentProject.view.controller.set_changed(True)

    def item_double_clicked(self, widget, col):
        """ item_double_clicked(widget: QTreeWidgetItem, col: integer) -> None
        Handles double-click on tree items
        Currently enables renaming of QWorkflowItem
        """
        if widget and type(widget) == QWorkflowItem:
            # tag this visualization with a name
            tag, ok = QtGui.QInputDialog.getText(self, str(widget.text(0)),
                                                 "New name")
            if not ok or not str(tag).strip():
                return
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
            project.view.stateChanged()

    def get_current_project_controller(self):
        """ get_current_project_controller() -> ProjectController
        Returns current project controller
        """
        return self.current_controller
    
    def get_project_controller_by_name(self, name):
        for i in range(self.treeProjects.topLevelItemCount()):
            controller = self.treeProjects.topLevelItem(i).controller
            if name == controller.name:
                return controller
            
        return None