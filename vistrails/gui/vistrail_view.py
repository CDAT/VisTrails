###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: contact@vistrails.org
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
""" The file describes a container widget consisting of a pipeline
view and a version tree for each opened Vistrail """

from PyQt4 import QtCore, QtGui

from core.collection import Collection
from core.db.locator import untitled_locator
from core import debug
from core.debug import critical
from core.data_structures.bijectivedict import Bidict
from core.system import vistrails_default_file_type
from core.thumbnails import ThumbnailCache
from core.vistrail.vistrail import Vistrail
from core.vistrail.pipeline import Pipeline
from core.log.log import Log
from core.log.opm_graph import OpmGraph
from core.db.locator import FileLocator, XMLFileLocator
from core.modules.module_registry import ModuleRegistry

from gui.collection.vis_log import QLogView
from gui.common_widgets import QMouseTabBar
from gui.pipeline_view import QPipelineView
from gui.version_view import QVersionTreeView
from gui.query_view import QQueryView
from gui.paramexplore.pe_view import QParamExploreView
from gui.vis_diff import QDiffView
from gui.paramexplore.param_view import QParameterView
from gui.vistrail_controller import VistrailController
from gui.mashups.mashup_view import QMashupView
from gui.ports_pane import ParameterEntry
from gui.query_view import QueryEntry

################################################################################

class QVistrailView(QtGui.QWidget):
    """
    QVistrailView is a widget containing four stacked widgets: Pipeline View,
    Version Tree View, Query View and Parameter Exploration view
    for manipulating vistrails.
    """
    def __init__(self, vistrail, locator=None, abstraction_files=None,
                 thumbnail_files=None, mashups=None, parent=None):
        """ QVistrailView(parent: QWidget) -> QVistrailView
        
        """
        QtGui.QWidget.__init__(self, parent)

        layout = QtGui.QVBoxLayout(self)
        layout.setMargin(0)
        layout.setSpacing(0)
        self.notifications = {}
        self.tabs = QMouseTabBar(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setExpanding(False)
        #self.tabs.setMovable(True)
        self.tabs.hide()
        self.tabs.tabDoubleClicked.connect(self.tabDoubleClicked)
        layout.addWidget(self.tabs)
        self.stack = QtGui.QStackedWidget(self)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        #this index is for pipeline/diff views
        self.tab_to_stack_idx = {}
        self.tab_state = {}
        self.tab_to_view = {}
        #self.button_to_tab_idx = Bidict()
        self.detached_views = {}

        # Initialize the vistrail controller
        self.controller = VistrailController(vistrail)

        # Create the initial views
        self.version_view = None
        pipeline_view = self.create_pipeline_view()
        self.version_view = self.create_version_view()
        self.query_view = self.create_query_view()
        self.pe_view = self.create_pe_view()
        self.log_view = self.create_log_view()
        self.mashup_view = self.create_mashup_view()
        
        self.set_controller(self.controller)
        self.locator = locator
        self.controller.set_vistrail(vistrail, self.locator, abstraction_files,
                                     thumbnail_files, mashups)
        self.tabs.setCurrentIndex(0)
        self.current_tab = self.stack.setCurrentIndex(0)
        self.pipeline_selected()
        self.connect(self.tabs, QtCore.SIGNAL("currentChanged(int)"),
                     self.tab_changed)
        self.connect(self.tabs, QtCore.SIGNAL("tabCloseRequested(int)"),
                     self.remove_view_by_index)
       
        #self.view_changed()
        #self.tab_changed(0)

        self.connect(self.controller,
                     QtCore.SIGNAL('stateChanged'),
                     self.stateChanged)

        # self.controller = VistrailController()
        # self.controller.vistrail_view = self
        # self.connect(self.controller,
        #              QtCore.SIGNAL('stateChanged'),
        #              self.stateChanged)
        # self.connect(self.controller,
        #              QtCore.SIGNAL('new_action'),
        #              self.new_action)

        # # self.versionTab.versionView.scene()._vistrail_view = self
        # self.connect(self.versionTab.versionView.scene(),
        #              QtCore.SIGNAL('versionSelected(int,bool,bool,bool)'),
        #              self.versionSelected,
        #              QtCore.Qt.QueuedConnection)

        # self.connect(self.versionTab,
        #              QtCore.SIGNAL('twoVersionsSelected(int,int)'),
        #              self.twoVersionsSelected)
        # self.connect(self.queryTab,
        #              QtCore.SIGNAL('queryPipelineChange'),
        #              self.queryPipelineChange)
        # self.connect(self.peTab,
        #              QtCore.SIGNAL('exploreChange(bool)'),
        #              self.exploreChange)

        # # We also keep track where this vistrail comes from
        # # So we can save in the right place
        # self.locator = None
        
        # self.closeEventHandler = None

        # # Keep the state of the execution button and menu items for the view
        # self.execQueryEnabled = False
        # self.execDiffEnabled = False
        # self.execExploreEnabled = False
        # self.execPipelineEnabled = False
        # self.execDiffId1 = -1
        # self.execDiffId2 = -1

    def get_notifications(self):
        return self.notifications

    def set_notification(self, notification_id, method):
        if notification_id not in self.notifications:
            self.notifications[notification_id] = []
        self.notifications[notification_id].append(method)

    def set_controller(self, controller):
        self.controller = controller
        self.controller.vistrail_view = self
        for i in xrange(self.stack.count()):
            view = self.stack.widget(i)
            if hasattr(view, 'set_controller'):
                view.set_controller(controller)

    def get_controller(self):
        return self.controller

    def get_name(self):
        title = self.controller.name
        if title=='':
            title = 'Untitled%s'%vistrails_default_file_type()
        if self.controller.changed:
            title += '*'
        # self.setWindowTitle(title)
        return title

    def set_name(self):
        title = self.get_name()
        self.setWindowTitle(title)

    def reset_version_view(self):
        from gui.vistrails_window import _app
        if self.version_view is not None:
            select_node = True
            if _app._previous_view and _app._previous_view in self.detached_views:
                select_node = False
            self.version_view.scene().setupScene(self.controller, select_node)

    def reset_tab_state(self):
        try:
            qaction = self.tab_state[self.tabs.currentIndex()]
            qaction.trigger()
        except:
            pass
        
    def reset_tab_view_to_current(self):
        index = self.tabs.currentIndex()
        view = self.stack.widget(self.tab_to_stack_idx[index])
        #print "view changed: ", view
        self.set_to_current(view)
         
    def pipeline_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "PIPELINE"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(),
                             self.stack.currentWidget().get_title())
        self.tab_state[self.tabs.currentIndex()] = window.qactions['pipeline']
        self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()

    def pipeline_unselected(self):
        #print "PIPELINE UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(),
                             self.stack.currentWidget().get_title())

    def history_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "VERSION"
        self.stack.setCurrentIndex(self.stack.indexOf(self.version_view))
        self.tabs.setTabText(self.tabs.currentIndex(), "History")
        self.tab_state[self.tabs.currentIndex()] = window.qactions['history']
        self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()

    def history_unselected(self):
        #print "VERSION UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(), 
                             self.stack.currentWidget().get_title())

    def query_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "QUERY"
        self.stack.setCurrentIndex(self.stack.indexOf(self.query_view))
        self.tabs.setTabText(self.tabs.currentIndex(), "Search")
        self.tab_state[self.tabs.currentIndex()] = window.qactions['search']
        self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()

    def query_unselected(self):
        #print "QUERY UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(), 
                             self.stack.currentWidget().get_title())

    def explore_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "EXPLORE"
        self.stack.setCurrentIndex(self.stack.indexOf(self.pe_view))
        self.tabs.setTabText(self.tabs.currentIndex(), "Explore")
        self.tab_state[self.tabs.currentIndex()] = window.qactions['explore']
        self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()

    def explore_unselected(self):
        #print "EXPLORE UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(), 
                             self.stack.currentWidget().get_title())

    def provenance_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "PROVENANCE"
        self.stack.setCurrentIndex(self.stack.indexOf(self.log_view))
        self.tabs.setTabText(self.tabs.currentIndex(), "Provenance")
        self.tab_state[self.tabs.currentIndex()] = window.qactions['provenance']
        self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()

    def provenance_unselected(self):
        #print "PROVENANCE UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(), 
                             self.stack.currentWidget().get_title())

    def mashup_selected(self):
        from gui.vistrails_window import _app
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print "MASHUP"
        #print self.stack.count(), self.stack.indexOf(self.mashup_view)
        try:
            self.stack.setCurrentIndex(self.stack.indexOf(self.mashup_view))
            self.tabs.setTabText(self.tabs.currentIndex(), "Mashup")
            self.tab_state[self.tabs.currentIndex()] = window.qactions['mashup']
            self.mashup_view.updateView()
            self.tab_to_view[self.tabs.currentIndex()] = self.get_current_tab()
        except Exception, e:
            print "EXCEPTION: ", str(e)
    def mashup_unselected(self):
        #print "MASHUP UN"
        self.stack.setCurrentIndex(
            self.tab_to_stack_idx[self.tabs.currentIndex()])
        self.tabs.setTabText(self.tabs.currentIndex(), 
                             self.stack.currentWidget().get_title())
        
    def pipeline_change(self, checked):
        if checked:
            #print "PIPELINE SELECTED"
            self.pipeline_selected()
        else:
            #print "PIPELINE UNSELECTED"
            self.pipeline_unselected()
        self.view_changed()

    def history_change(self, checked):
        from vistrails_window import _app
        if checked:
            #print "HISTORY SELECTED"
            self.history_selected()
        else:
            #print "HISTORY UNSELECTED"
            self.history_unselected()
        self.view_changed()

    def search_change(self, checked):
        if checked:
            self.query_selected()
        else:
            self.query_unselected()
        self.view_changed()

    def explore_change(self, checked):
        if checked:
            self.explore_selected()
        else:
            self.explore_unselected()
        self.view_changed()

    def provenance_change(self, checked):
        if checked:
            self.provenance_selected()
        else:
            self.provenance_unselected()
        self.view_changed()

    def mashup_change(self, checked):
        if checked:
            self.mashup_selected()
        else:
            self.mashup_unselected()
        self.view_changed()
    
    def show_group(self):
        pipelineView = self.controller.current_pipeline_view
        items = pipelineView.get_selected_item_ids(True)
        if items is not None:
            for m_id in items[0]:
                module = pipelineView.current_pipeline.modules[m_id]
                if module.is_group() or module.is_abstraction():
                    newPipelineView = self.add_pipeline_view()
                    newPipelineView.controller.current_pipeline_view = \
                        newPipelineView.scene()
                    module.pipeline.ensure_connection_specs()
                    newPipelineView.scene().setupScene(module.pipeline)
                    newPipelineView.scene().current_pipeline = module.pipeline
                    newPipelineView.scene().fitToView(newPipelineView, True)
                    newPipelineView.setReadOnlyMode(True)
            
    def create_view(self, klass, add_tab=True):
        view = klass(self)
        view.set_vistrail_view(self)
        idx = self.stack.addWidget(view)
        view.set_index(idx)
        if add_tab:
            tab_idx = self.tabs.addTab(view.get_title())
            view.set_tab_idx(tab_idx)
            self.tab_to_stack_idx[tab_idx] = idx
            self.tab_to_view[tab_idx] = view
            if self.isTabDetachable(tab_idx):
                self.tabs.setTabToolTip(tab_idx, "Double-click to detach it")
            
        self.connect(view, QtCore.SIGNAL("windowTitleChanged"),
                     self.view_title_changed)
        if self.tabs.count() == 1:
            #self.tabs.hide()
            self.tabs.setTabsClosable(False)
        else:
            self.tabs.setTabsClosable(True)
        self.updateTabsTooTip()
        self.tabs.show()
        return view

    def detach_view(self, tab_idx):
        from gui.vistrails_window import QBaseViewWindow
        if self.tab_to_stack_idx.has_key(tab_idx):
            stack_index = self.tab_to_stack_idx[tab_idx]
            view = self.stack.widget(stack_index)
            title = view.get_long_title()
            self.remove_view_by_index(tab_idx)
            window = QBaseViewWindow(view=view, parent=None)
            view.set_title(title)
            window.setWindowTitle(title)
            self.connect(window, QtCore.SIGNAL("viewWasClosed"),
                         self.detachedViewWasClosed)
            self.detached_views[view] = window
            window.move(self.rect().center())
            window.show()
        else:
            print "Error detach_view: ", tab_idx, self.tab_to_stack_idx
    
    def isTabDetachable(self, index):
        if self.tab_to_view.has_key(index):
            return self.tabs.count() > 1 and self.tab_to_view[index].detachable
        return False
    
    def closeDetachedViews(self):
        windows = self.detached_views.values()
        for w in windows:
            if w:
                w.close()
            
    def detachedViewWasClosed(self, view):
        if self.controller.current_pipeline_view.parent() == view:
            self.controller.current_pipeline_view = None
            self.activateWindow()
            self.reset_tab_view_to_current()
            self.view_changed()
        del self.detached_views[view]
        
    def updateTabsTooTip(self):
        for i in range(self.tabs.count()):
            if self.isTabDetachable(i):
                self.tabs.setTabToolTip(i, "Double-click to detach it")
            else:
                self.tabs.setTabToolTip(i, "")
    
    def tabDoubleClicked(self, index, pos):
        if self.isTabDetachable(index):
            self.detach_view(index)
            
    def view_title_changed(self, view):
        if self.stack.currentWidget() == view:
            self.tabs.setTabText(self.tabs.currentIndex(), view.windowTitle())

    def update_indexes(self, rm_tab_idx, rm_stack_idx):
        for (t,s) in self.tab_to_stack_idx.iteritems():
            if s > rm_stack_idx:
                self.tab_to_stack_idx[t] -= 1
        tabs = self.tab_to_stack_idx.keys()
        tabs.sort()
        for t in tabs:
            if t > rm_tab_idx:
                self.tab_to_stack_idx[t-1] = self.tab_to_stack_idx[t]
                self.tab_state[t-1] = self.tab_state[t]
        del self.tab_to_stack_idx[tabs[-1]]
        del self.tab_state[tabs[-1]]
        for idx in range(self.stack.count()):
            if idx >= rm_stack_idx:
                view = self.get_tab(idx)
                view.set_index(idx)
                if view.tab_idx > rm_tab_idx:
                    view.set_tab_idx(view.tab_idx-1)
    
    def remove_view_by_index(self, index):
        self.disconnect(self.tabs, QtCore.SIGNAL("currentChanged(int)"),
                     self.tab_changed)
        close_current = False
        if index == self.tabs.currentIndex():
            close_current = True
        stack_idx = self.tab_to_stack_idx[index]
        #print "\n\n >>>>> remove_view_by_index ", index, stack_idx, self.tabs.currentIndex()
        self.tabs.removeTab(index)
        del self.tab_to_view[index]
        if stack_idx >= 0:
            view = self.stack.widget(stack_idx)
            self.disconnect(view, QtCore.SIGNAL("windowTitleChanged"),
                     self.view_title_changed)
            self.stack.removeWidget(view)
        self.update_indexes(index, stack_idx)
        if self.tabs.count() == 1:
            self.tabs.setTabsClosable(False)
            self.updateTabsTooTip()
        if close_current:
            if index >= self.tabs.count():
                new_index = index - 1
            else:
                new_index = index
        
            self.tab_changed(new_index)
        self.connect(self.tabs, QtCore.SIGNAL("currentChanged(int)"),
                     self.tab_changed)
#        self.tabs.setCurrentIndex(new_index)
#        print self.current_tab
        
#        self.view_changed()
        

    def switch_to_tab(self, index):
#        if index < 0:
#            index = self.tabs.count() + index
        self.tabs.setCurrentIndex(index)
        self.tab_changed(index)

    def get_current_tab(self, query_top_level=False):
        window = QtGui.QApplication.activeWindow()
        if window in self.detached_views.values():
            return window.view   
        else:
            #if none of the detached views is active we will assume that the
            #window containing this vistrail has focus
            widget = self.stack.currentWidget()
            if not query_top_level and type(widget) == QQueryView:
                widget = widget.get_current_view()
            return widget
        
    def get_current_outer_tab(self):
        window = QtGui.QApplication.activeWindow()
        if window in self.detached_views.values():
            return window.view   
        else:
            #if none of the detached views is active we will assume that the
            #window containing this vistrail has focus
            return self.stack.currentWidget()
        
    def get_tab(self, stack_idx):
        widget = self.stack.widget(stack_idx)
        if type(widget) == QQueryView:
            widget = widget.get_current_view()
        return widget

    def view_changed(self):
        from gui.vistrails_window import _app
        _app.closeNotPinPalettes()
        #view = self.stack.currentWidget()
        view = self.get_current_outer_tab()
        #print "changing tab from: ",self.current_tab, " to ", view
        #print self.tab_to_stack_idx
        if view != self.current_tab:
            #print "!!unset_action_links of ", self.current_tab
            _app.unset_action_links(self.current_tab)
            self.current_tab = view
#            print "\n!! _app.notifications: "
#            for (k, v) in _app.notifications.iteritems():
#                print "   ", k, "  (%s) "%len(v)
#                for m in v: 
#                    print "     ", m
#            print "\n!!set_action_defaults of ", self.current_tab
            _app.set_action_defaults(self.current_tab)
            #print "\n!!set_action_links of ", self.current_tab 
            _app.set_action_links(self.current_tab.action_links, self.current_tab,
                                  self)

        #else:
           # print "tabs the same. do nothing"
        self.showCurrentViewPalettes()
        if isinstance(view, QQueryView):
            _app.notify("controller_changed", view.p_controller)
            _app.notify("entry_klass_changed", QueryEntry)
        else:
            _app.notify("entry_klass_changed", ParameterEntry)
            _app.notify("controller_changed", self.controller)

        if self.window().isActiveWindow():
            if self.isTabDetachable(self.tabs.currentIndex()):
                self.tabs.setTabToolTip(self.tabs.currentIndex(),
                                        "Double-click to detach it")
            else:
                self.tabs.setTabToolTip(self.tabs.currentIndex(),
                                        "")

    def showCurrentViewPalettes(self):
        current_tab = self.get_current_tab(True)
        for dock_loc, palette_klass in current_tab.palette_layout.iteritems():
            palette_instance = palette_klass.instance()
            window = palette_instance.toolWindow().parentWidget()
            if window:
                current_loc = window.dockWidgetArea(palette_instance.toolWindow())
            else:
                current_loc = QtCore.Qt.NoDockWidgetArea
            #print ">> P:", palette_instance.__class__.__name__, current_loc, \
            #        dock_loc
            
            if current_loc == dock_loc:
                # palette_instance.get_action().trigger()
                palette_instance.set_visible(True)
                    
    def tab_changed(self, index):
        #print 'raw tab_changed', index
        if index < 0 or self.controller is None:
            return

        from gui.vistrails_window import _app, QVistrailViewWindow

        self.stack.setCurrentIndex(self.tab_to_stack_idx[index])
        if isinstance(self.window(),QVistrailViewWindow):
            window = self.window()
        else:
            window = _app
        #print window
        for action in window.view_action_group.actions():
            action.setChecked(False)
        self.selected_mode = None
        action = None
        if index in self.tab_state:
            action = self.tab_state[index]
            # if action is not None:
                # print 'running toggle'
                # action.toggle()
                # action.setChecked(True)
        else:
            self.tab_state[index] = window.qactions['pipeline']
        if action is not None:
            action.setChecked(True)
            # _app.view_triggered(action)

        view = self.stack.widget(self.tab_to_stack_idx[index])
        #print "view changed: ", view
        self.set_to_current(view)
        
    def set_to_current(self, view):
        from gui.vistrails_window import _app, QVistrailViewWindow
        if isinstance(view, QDiffView):
            view.set_to_current()
            #print "view changed!", self.controller, \
            #    self.controller.current_version
            _app.notify("controller_changed", self.controller)
            self.reset_version_view()
        elif isinstance(view, QLogView):
            view.set_to_current()
            #print "view changed!", self.controller, \
            #    self.controller.current_version
            _app.notify("controller_changed", self.controller)
            self.reset_version_view()
        elif isinstance(view, QPipelineView):
            #print "PIPELINE_VIEW NEW SCENE:", id(view.scene())

            # need to set the controller's version, pipeline, view
            # to this view...
            # self.controller.current_version = view.current_version
            # self.controller.current_pipeline = view.current_pipeline
            view.set_to_current()
            #print "view changed!", self.controller, \
            #    self.controller.current_version
            real_view = self.stack.currentWidget()
            if isinstance(real_view, QQueryView):
                _app.notify("controller_changed", real_view.p_controller)
            else:
                _app.notify("controller_changed", self.controller)
            self.reset_version_view()
            
    def create_pipeline_view(self):
        view = self.create_view(QPipelineView)
        self.connect(view.scene(), QtCore.SIGNAL('moduleSelected'), 
                     self.gen_module_selected(view))
        view.set_controller(self.controller)
        view.set_to_current()
        self.set_notification('module_done_configure', view.done_configure)
        #self.switch_to_tab(view.tab_idx)
        return view
    
    def add_pipeline_view(self):
        view = self.create_pipeline_view()
        self.switch_to_tab(view.tab_idx)
        return view

    def create_version_view(self):
        view = self.create_view(QVersionTreeView, False)
        self.connect(view.scene(), 
                     QtCore.SIGNAL('versionSelected(int,bool,bool,bool,bool)'),
                     self.version_selected)
        self.connect(view.scene(),
                     QtCore.SIGNAL('diffRequested(int,int)'),
                     self.diff_requested)
        return view

    def create_query_view(self):
        view = self.create_view(QQueryView, False)
        self.connect(view.pipeline_view.scene(), 
                     QtCore.SIGNAL('moduleSelected'),
                     self.gen_module_selected(view.pipeline_view))
        # self.connect(view.version_result_view.scene(),
        #              QtCore.SIGNAL('versionSelected(int,bool,bool,bool,bool)'),
        #              self.version_selected)
        # self.connect(view.version_result_view.scene(),
        #              QtCore.SIGNAL('diffRequested(int,int)'),
        #              self.diff_requested)
        self.set_notification('query_changed', view.query_changed)
        self.set_notification('version_changed', view.version_changed)
        return view

    def create_diff_view(self):
        view = self.create_view(QDiffView)
        self.connect(view.scene(), QtCore.SIGNAL('moduleSelected'),
                     self.gen_module_selected(view))
        return view

    def create_pe_view(self):
        view = self.create_view(QParamExploreView, False)
        self.set_notification('controller_changed', view.set_controller)
        self.set_notification('pipeline_changed', view.updatePipeline)
        return view

    def create_log_view(self):
        from gui.vistrails_window import _app
        view = self.create_view(QLogView, False)
        self.set_notification('execution_changed', view.execution_changed)
        return view
    
    def create_mashup_view(self):
        #print "******* create mashup view"
        from gui.vistrails_window import _app
        view = self.create_view(QMashupView, False)
        view.set_controller(self.controller)
        self.set_notification('controller_changed', view.controllerChanged)
        self.set_notification('alias_changed', view.aliasChanged)
        self.set_notification('version_changed', view.versionChanged)
        return view
    
    def gen_module_selected(self, view):
        def module_selected(module_id, selection = []):
            from gui.vistrails_window import _app
            pipeline = view.scene().current_pipeline
            if module_id in pipeline.modules:
                module = pipeline.modules[module_id]
                _app.notify('module_changed', module)
            else:
                _app.notify('module_changed', None)
        return module_selected

    def version_selected(self, version_id, by_click, do_validate=True,
                         from_root=False, double_click=False):
        from gui.vistrails_window import _app
        from gui.vis_diff import QDiffView
        if hasattr(self.window(), 'qactions'):
            window = self.window()
        else:
            window = _app
        #print 'got version selected:', version_id
        if _app._focus_owner in self.detached_views.values():
            view = _app._focus_owner.view
        elif _app._previous_view in self.detached_views:
            view = _app._previous_view
        else:
            view = self.stack.widget(
                            self.tab_to_stack_idx[self.tabs.currentIndex()])
        if view and by_click:
            self.controller.change_selected_version(version_id, by_click, 
                                                    do_validate, from_root)

            view.scene().fitToView(view, True)
            if double_click:
                # view = self.create_pipeline_view()
                # view.set_controller(self.controller)
                # view.set_to_current()
                # self.tabs.setCurrentWidget(view.parent())
                window.qactions['pipeline'].trigger()
            self.version_view.redo_stack = []
        if view and not isinstance(view, QDiffView):
            if view not in self.detached_views:
                view.set_title(self.controller.get_pipeline_name())
            else:
                view.set_title(view.get_long_title())
                view.window().setWindowTitle(view.get_long_title())
        _app.notify("version_changed", version_id)
        _app.notify("pipeline_changed", self.controller.current_pipeline)

    def query_version_selected(self, search=None, version_id=None):
        if version_id is None:
            self.query_view.set_result_level(
                self.query_view.query_controller.LEVEL_VISTRAIL)
            self.query_view.query_controller.set_search(search)
        else:
            self.query_view.set_result_level(
                self.query_view.query_controller.LEVEL_WORKFLOW)
            self.query_view.query_controller.set_search(search)
            self.query_view.result_version_selected(version_id, True, 
                                                    double_click=True)

        window = self.window()
        window.qactions['search'].trigger()
        
    def diff_requested(self, version_a, version_b, vistrail_b=None):
        """diff_requested(self, id, id, Vistrail) -> None
        
        Request a diff between two versions.  If vistrail_b is
        specified, the second version will be derived from that
        vistrail instead of the common vistrail controlled by this
        view.
        """

        view = self.create_diff_view()
        view.set_controller(self.controller)
        view.set_diff(version_a, version_b, vistrail_b)
        self.switch_to_tab(view.tab_idx)
        view.scene().fitToView(view, True)
        self.view_changed()

    def save_vistrail(self, locator_class, force_choose_locator=False):
        """
        force_choose_locator=True triggers 'save as' behavior

        """
        locator = self.controller.locator
        if locator is not None:
            locator_class = type(locator)

        #print "CALLED SAVE VISTRAIL", locator_class

        self.flush_changes()
        gui_get = locator_class.save_from_gui
        # get a locator to write to
        if force_choose_locator:
            locator = gui_get(self, Vistrail.vtType,
                              self.controller.locator)
        else:
            locator = (self.controller.locator or
                       gui_get(self, Vistrail.vtType,
                               self.controller.locator))
        if locator == untitled_locator():
            locator = gui_get(self, Vistrail.vtType,
                              self.controller.locator)
        # if couldn't get one, ignore the request
        if not locator:
            return False
        try:
            self.controller.write_vistrail(locator)
        except Exception, e:
            debug.critical('Failed to save vistrail: %s' % str(e))
            raise
            return False
        # update collection
        try:
            thumb_cache = ThumbnailCache.getInstance()
            self.controller.vistrail.thumbnails = \
                self.controller.find_thumbnails(
                    tags_only=thumb_cache.conf.tagsOnly)
            self.controller.vistrail.abstractions = \
                self.controller.find_abstractions(self.controller.vistrail, 
                                                  True)
            self.controller.vistrail.mashups = self.controller._mashups

            collection = Collection.getInstance()
            url = locator.to_url()
            entity = collection.updateVistrail(url, self.controller.vistrail)
            # add to relevant workspace categories
            collection.add_to_workspace(entity)
            collection.commit()
        except Exception, e:
            import traceback
            debug.critical('Failed to index vistrail', traceback.print_exc())

        from gui.vistrails_window import _app
        # update recent files menu items
        if not self.is_abstraction:
            _app.set_current_locator(locator)
        _app.view_changed(self)
        # reload workspace entry
        from gui.collection.workspace import QWorkspaceWindow
        QWorkspaceWindow.instance().add_vt_window(self)
        return locator

    def save_vistrail_as(self, locator_class):
        #print "CALLED SAVE AS VISTRAIL", locator_class
        self.save_vistrail(locator_class, force_choose_locator=True)

    # FIXME normalize workflow/log/registry!!!
    def save_workflow(self, locator_class, force_choose_locator=True):
        self.flush_changes()
        gui_get = locator_class.save_from_gui
        if force_choose_locator:
            locator = gui_get(self, Pipeline.vtType, self.controller.locator)
        else:
            locator = (self.controller.locator or
                       gui_get(self, Pipeline.vtType,
                               self.controller.locator))
        if locator == untitled_locator():
            locator = gui_get(self, Pipeline.vtType, self.controller.locator)
        if not locator:
            return False
        self.controller.write_workflow(locator)

    def save_log(self, locator_class, force_choose_locator=True):
        self.flush_changes()
        gui_get = locator_class.save_from_gui
        if force_choose_locator:
            locator = gui_get(self, Log.vtType,
                              self.controller.locator)
        else:
            locator = (self.controller.locator or
                       gui_get(self, Log.vtType,
                               self.controller.locator))
        if locator == untitled_locator():
            locator = gui_get(self, Log.vtType,
                              self.controller.locator)
        if not locator:
            return False
        self.controller.write_log(locator)

    def save_registry(self, locator_class, force_choose_locator=True):
        self.flush_changes()
        gui_get = locator_class.save_from_gui
        if force_choose_locator:
            locator = gui_get(self, ModuleRegistry.vtType,
                              self.controller.locator)
        else:
            locator = (self.controller.locator or
                       gui_get(self, ModuleRegistry.vtType,
                               self.controller.locator))
        if locator == untitled_locator():
            locator = gui_get(self, ModuleRegistry.vtType,
                              self.controller.locator)
        if not locator:
            return False
        self.controller.write_registry(locator)


    def save_opm(self, locator_class=XMLFileLocator, 
             force_choose_locator=True):
        self.flush_changes()
        gui_get = locator_class.save_from_gui
        if force_choose_locator:
            locator = gui_get(self, OpmGraph.vtType,
                              self.controller.locator)
        else:
            locator = (self.controller.locator or
                       gui_get(self, OpmGraph.vtType,
                               self.controller.locator))
        if locator == untitled_locator():
            locator = gui_get(self, OpmGraph.vtType,
                              self.controller.locator)
        if not locator:
            return False
        self.controller.write_opm(locator)


    def has_changes(self):
        return self.controller.changed

    def flush_changes(self):
        """Flush changes in the vistrail before closing or saving.
        """
        # Quick workaround for notes focus out bug (ticket #182)
        # There's probably a much better way to fix this.
        from gui.version_prop import QVersionProp
        prop = QVersionProp.instance()
        prop.versionNotes.commit_changes()

    def execute(self):
        view = self.get_current_tab()
        if hasattr(view, 'execute'):
            view.setFocus(QtCore.Qt.MouseFocusReason)
            view.execute()      
            
    def publish_to_web(self):
        view = self.get_current_tab()
        if hasattr(view, 'publish_to_web'):
            view.publish_to_web()
                 
    def publish_to_paper(self):
        view = self.get_current_tab()
        if hasattr(view, 'publish_to_paper'):
            view.publish_to_paper()

    def open_mashup_from_mashuptrail_id(self, mashuptrail_id, mashupVersion):
        for mashuptrail in self.controller._mashups:
            if str(mashuptrail.id) == mashuptrail_id:
                mashup = mashuptrail.getMashup(mashupVersion)
                self.open_mashup(mashup)
                break
            
    def open_mashup(self, mashup):
        """open_mashup(mashup: Mashup) -> None
        It will switch to version view, select the corresponding node 
        and run the mashup """
        from gui.version_prop import QVersionProp
        #first we will show the hisotry view and select the version that has
        #this mashup
        vt_version = mashup.version
        window = self.window()
        window.qactions['history'].trigger()
        self.version_selected(vt_version, by_click=True)
        self.version_view.select_current_version()
        #then we will execute the mashup
        version_prop = QVersionProp.instance()
        version_prop.versionMashups.openMashup(mashup.id)
        
    def edit_mashup(self, mashup):
        """edit_mashup(mashup: Mashup) -> None
        It will select the corresponding node, switch to mashup view, 
        and select mashup """
        from gui.mashups.mashups_inspector import QMashupsInspector
        vt_version = mashup.version
        window = self.window()
        window.qactions['history'].trigger()
        self.version_selected(vt_version, by_click=True)
        self.version_view.select_current_version()
        window.qactions['mashup'].trigger()
        inspector = QMashupsInspector.instance()
        inspector.mashupsList.selectMashup(mashup.name)
        
    ##########################################################################
    # Undo/redo
        
    def set_pipeline_selection(self, old_action, new_action, optype):
        # need to check if anything on module changed or
        # any connections changed
        module_types = set(['module', 'group', 'abstraction'])
        module_child_types = set(['function', 'parameter', 'location', 
                                  'portSpec', 'annotation'])
        conn_types = set(['connection'])
        conn_child_types = set(['port'])

        view = self.stack.currentWidget()
        if not isinstance(view, QPipelineView):
            return 
        
        pipeline_scene = view.scene()    

        if old_action is None:
            old_action_id = 0
        else:
            old_action_id = old_action.id
        if new_action is None:
            new_action_id = 0
        else:
            new_action_id = new_action.id
        action = self.controller.vistrail.general_action_chain(old_action_id,
                                                               new_action_id)

        def module_change():
            module_ids = set()
            function_ids = set()
            for op in action.operations:
                if op.what in module_types and \
                        (op.vtType == 'change' or op.vtType == 'add'):
                    module_ids.add(op.objectId)
                elif op.what in module_child_types and \
                        (op.vtType == 'change' or op.vtType == 'add' or
                         op.vtType == 'delete'):
                    if op.what == 'parameter':
                        function_ids.add(op.parentObjId)
                    else:
                        module_ids.add(op.parentObjId)
            if len(function_ids) > 0:
                for m_id, module in \
                        self.controller.current_pipeline.modules.iteritems():
                    to_discard = set()
                    for f_id in function_ids:
                        if module.has_function_with_real_id(f_id):
                            module_ids.add(m_id)
                            to_discard.add(f_id)
                    function_ids -= to_discard

            for id in module_ids:
                if id in pipeline_scene.modules:
                    pipeline_scene.modules[id].setSelected(True)

        def connection_change():
            conn_ids = set()
            for op in action.operations:
                if op.what in conn_types and \
                        (op.vtType == 'change' or op.vtType == 'add'):
                    conn_ids.add(op.objectId)
                elif op.what in conn_child_types and \
                        (op.vtType == 'change' or op.vtType == 'add' or 
                         op.vtType == 'delete'):
                    conn_ids.add(op.parentObjId)
            for id in conn_ids:
                if id in pipeline_scene.connections:
                    pipeline_scene.connections[id].setSelected(True)
                    
        module_change()
        connection_change()
        
    def undo(self):
        """Performs one undo step, moving up the version tree."""
        action_map = self.controller.vistrail.actionMap
        old_action = action_map.get(self.controller.current_version, None)
        self.version_view.redo_stack.append(self.controller.current_version)
        self.controller.show_parent_version()
        new_action = action_map.get(self.controller.current_version, None)
        self.set_pipeline_selection(old_action, new_action, 'undo')
        return self.controller.current_version
        
    def redo(self):
        """Performs one redo step if possible, moving down the version tree."""
        action_map = self.controller.vistrail.actionMap
        old_action = action_map.get(self.controller.current_version, None)
        if not self.version_view.can_redo(None):
            critical("Redo on an empty redo stack. Ignoring.")
            return
        next_version = self.version_view.redo_stack[-1]
        self.version_view.redo_stack = self.version_view.redo_stack[:-1]
        self.controller.show_child_version(next_version)
        new_action = action_map[self.controller.current_version]
        self.set_pipeline_selection(old_action, new_action, 'redo')
        return next_version


    # def updateCursorState(self, mode):
    #     """ updateCursorState(mode: Int) -> None 
    #     Change cursor state in all different modes.

    #     """
    #     self.pipelineTab.pipelineView.setDefaultCursorState(mode)
    #     self.versionTab.versionView.setDefaultCursorState(mode)
    #     self.queryTab.pipelineView.setDefaultCursorState(mode)
    #     if self.parent().parent().parent().pipViewAction.isChecked():
    #         self.pipelineTab.pipelineView.pipFrame.graphicsView.setDefaultCursorState(mode)
    #         self.versionTab.versionView.pipFrame.graphicsView.setDefaultCursorState(mode)


    # def flush_changes(self):
    #     """Flush changes in the vistrail before closing or saving.
    #     """
    #     # Quick workaround for notes focus out bug (ticket #182)
    #     # There's probably a much better way to fix this.
    #     prop = self.versionTab.versionProp
    #     prop.versionNotes.commit_changes()

    # def setup_view(self, version=None):
    #     """setup_view(version = None:int) -> None

    #     Sets up the correct view for a fresh vistrail.

    #     Previously, there was a method setInitialView and another
    #     setOpenView.

    #     They were supposed to do different things but the code was
    #     essentially identical.

    #     FIXME: this means that the different calls are being handled
    #     somewhere else in the code. Figure this out."""

    #     if version is None:
    #         self.controller.select_latest_version()
    #         version = self.controller.current_version
    #     else:
    #         self.versionSelected(version, True, True, False)
    #     self.controller.recompute_terse_graph()
    #     self.controller.invalidate_version_tree(True)
    #     self.setPIPMode(True)
    #     self.setQueryMode(False)
       
    # def setPIPMode(self, on):
    #     """ setPIPMode(on: bool) -> None
    #     Set the PIP state for the view

    #     """
    #     self.pipelineTab.pipelineView.setPIPEnabled(on)
    #     self.versionTab.versionView.setPIPEnabled(on)

    # def setQueryMode(self, on):
    #     """ setQueryMode(on: bool) -> None
    #     Set the Reset Query button mode for the view
        
    #     """
    #     self.pipelineTab.pipelineView.setQueryEnabled(on)
    #     self.versionTab.versionView.setQueryEnabled(on)
    #     self.queryTab.pipelineView.setQueryEnabled(on)

    # def setMethodsMode(self, on):
    #     """ setMethodsMode(on: bool) -> None
    #     Set the methods panel state for the view

    #     """
    #     if on:
    #         self.pipelineTab.methodPalette.toolWindow().show()
    #     else:
    #         self.pipelineTab.methodPalette.toolWindow().hide()

    # def setSetMethodsMode(self, on):
    #     """ setSetMethodsMode(on: bool) -> None
    #     Set the set methods panel state for the view

    #     """
    #     if on:
    #         self.pipelineTab.moduleMethods.toolWindow().show()
    #     else:
    #         self.pipelineTab.moduleMethods.toolWindow().hide()

    # def setPropertiesMode(self, on):
    #     """ setPropertiesMode(on: bool) -> None
    #     Set the properties panel state for the view

    #     """
    #     if on:
    #         self.versionTab.versionProp.toolWindow().show()
    #     else:
    #         self.versionTab.versionProp.toolWindow().hide()

    # def setPropertiesOverlayMode(self, on):
    #     """ setPropertiesMode(on: bool) -> None
    #     Set the properties overlay state for the view

    #     """
    #     if on:
    #         self.versionTab.versionView.versionProp.show()
    #     else:
    #         self.versionTab.versionView.versionProp.hide()
            
    # def setModuleConfigMode(self, on):
    #     """ setModuleConfigMode(on: bool) -> None
    #     Set the Module configuration panel state for the view

    #     """
    #     if on:
    #         self.pipelineTab.moduleConfig.toolWindow().show()
    #     else:
    #         self.pipelineTab.moduleConfig.toolWindow().hide()

    # def viewModeChanged(self, index):
    #     """ viewModeChanged(index: int) -> None        
    #     Slot for switching different views when the tab's current
    #     widget is changed
    #     """
    #     if self.stackedWidget.count()>index:
    #         self.stackedWidget.setCurrentIndex(index)

    def setVistrailVarsMode(self, on):
        """ setVistrailVarsMode(on: bool) -> None
        Set the vistrail variable panel state for the view

        """
        if on:
            self.pipelineTab.vistrailVars.toolWindow().show()
        else:
            self.pipelineTab.vistrailVars.toolWindow().hide()

    # def pasteToCurrentTab(self):
    #     index = self.stackedWidget.currentIndex()
    #     if index == 0:
    #         self.pipelineTab.pipelineView.pasteFromClipboard()
    #     elif index == 2:
    #         self.queryTab.pipelineView.pasteFromClipboard()
            
    # def selectAll(self):
    #     index = self.stackedWidget.currentIndex()
    #     if index == 0:
    #         self.pipelineTab.pipelineView.scene().selectAll()    
    #     elif index == 2:
    #         self.queryTab.pipelineView.scene().selectAll()
            
    # def sizeHint(self):
    #     """ sizeHint(self) -> QSize
    #     Return recommended size of the widget
        
    #     """
    #     return QtCore.QSize(1024, 768)

    # def set_vistrail(self, vistrail, locator=None, abstractions=None, 
    #                  thumbnails=None):
    #     """ set_vistrail(vistrail: Vistrail, locator: BaseLocator) -> None
    #     Assign a vistrail to this view, and start interacting with it
        
    #     """
    #     self.vistrail = vistrail
    #     self.locator = locator
    #     self.controller.set_vistrail(vistrail, locator, abstractions, thumbnails)
    #     self.versionTab.setController(self.controller)
    #     self.pipelineTab.setController(self.controller)
    #     self.peTab.setController(self.controller)

    def stateChanged(self):
        """ stateChanged() -> None
        Handles 'stateChanged' signal from VistrailController """
        from gui.vistrails_window import _app
        _app.notify("state_changed", self)
        _app.state_changed(self)
        

    # def stateChanged(self):
    #     """ stateChanged() -> None

    #     Handles 'stateChanged' signal from VistrailController
        
    #     Update the window and tab title
        
    #     """
    #     title = self.controller.name
    #     if title=='':
    #         title = 'untitled%s'%vistrails_default_file_type()
    #     if self.controller.changed:
    #         title += '*'
    #     self.setWindowTitle(title)
    #     # propagate the state change to the version prop
    #     # maybe in the future we should propagate as a signal
    #     versionId = self.controller.current_version
    #     self.versionTab.versionProp.updateVersion(versionId)

    # def emitDockBackSignal(self):
    #     """ emitDockBackSignal() -> None
    #     Emit a signal for the View Manager to take this widget back
        
    #     """
    #     self.emit(QtCore.SIGNAL('dockBack'), self)

    # def closeEvent(self, event):
    #     """ closeEvent(event: QCloseEvent) -> None
    #     Only close if we save information
        
    #     """
    #     if self.closeEventHandler:
    #         if self.closeEventHandler(self):
    #             event.accept()
    #         else:
    #             event.ignore()
    #     else:
    #         #I think there's a problem with two pipeline views and the same
    #         #scene on Macs. After assigning a new scene just before deleting
    #         #seems to solve the problem
    #         self.peTab.annotatedPipelineView.setScene(QtGui.QGraphicsScene())
    #         return QDockContainer.closeEvent(self, event)
    #         # super(QVistrailView, self).closeEvent(event)

    # def queryVistrail(self, on=True):
    #     """ queryVistrail(on: bool) -> None
    #     Inspecting the query tab to get a pipeline for querying
        
    #     """
    #     if on:
    #         queryPipeline = self.queryTab.controller.current_pipeline
    #         if queryPipeline:
    #             self.controller.query_by_example(queryPipeline)
    #             self.setQueryMode(True)
    #     else:
    #         self.controller.set_search(None)
    #         self.setQueryMode(False)

    # def createPopupMenu(self):
    #     """ createPopupMenu() -> QMenu
    #     Create a pop up menu that has a list of all tool windows of
    #     the current tab of the view. Tool windows can be toggled using
    #     this menu
        
    #     """
    #     return self.stackedWidget.currentWidget().createPopupMenu()

    # def executeParameterExploration(self):
    #     """ executeParameterExploration() -> None
    #     Execute the current parameter exploration in the exploration tab
        
    #     """
    #     self.peTab.performParameterExploration()

    # def versionSelected(self, versionId, byClick, doValidate=True, 
    #                     fromRoot=False):
    #     """ versionSelected(versionId: int, byClick: bool) -> None
    #     A version has been selected/unselected, update the controller
    #     and the pipeline view
        
    #     """
    #     if self.controller:
    #         if byClick:
    #             if self.controller.current_version > 0:
    #                 if self.controller.has_move_actions():
    #                     self.controller.flush_delayed_actions()
    #                     self.controller.invalidate_version_tree(False)
    #             self.controller.reset_pipeline_view = byClick
    #             self.controller.change_selected_version(versionId, True,
    #                                                     doValidate, fromRoot)
    #             versionId = self.controller.current_version
    #             self.controller.current_pipeline_view.fitToAllViews(True)
    #             self.redo_stack = []
    #         self.versionTab.versionProp.updateVersion(versionId)
    #         self.versionTab.versionView.versionProp.updateVersion(versionId)
    #         self.emit(QtCore.SIGNAL('versionSelectionChange'),versionId)
    #         self.execPipelineEnabled = versionId>-1
    #         self.execExploreEnabled = \
    #                     self.controller.vistrail.get_paramexp(versionId) != None
    #         self.execDiffEnabled = False
    #         self.execExploreChange = False
    #         self.emit(QtCore.SIGNAL('execStateChange()'))

    #         return versionId

    # def twoVersionsSelected(self, id1, id2):
    #     """ twoVersionsSelected(id1: Int, id2: Int) -> None
    #     Just echo the signal from the view
        
    #     """
    #     self.execDiffEnabled = True
    #     self.execDiffId1 = id1
    #     self.execDiffId2 = id2
    #     self.emit(QtCore.SIGNAL('execStateChange()'))

    # def queryPipelineChange(self, notEmpty):
    #     """ queryPipelineChange(notEmpty: bool) -> None
    #     Update the status of tool bar buttons if there are
    #     modules on the query canvas
        
    #     """
    #     self.execQueryEnabled = notEmpty
    #     self.emit(QtCore.SIGNAL('execStateChange()'))
                  
    # def exploreChange(self, notEmpty):
    #     """ exploreChange(notEmpty: bool) -> None
    #     Update the status of tool bar buttons if there are
    #     parameters in the exploration canvas
        
    #     """
    #     self.execExploreEnabled = notEmpty
    #     self.emit(QtCore.SIGNAL('execStateChange()'))
        
    # def checkModuleConfigPanel(self):
    #     """ checkModuleConfigPanel(self) -> None 
    #     This will ask if user wants to save changes """
    #     self.pipelineTab.checkModuleConfigPanel()
         

    # def can_redo(self):
    #     return len(self.redo_stack) <> 0

    # def new_action(self, action):
    #     """new_action

    #     Handler for VistrailController.new_action

    #     """
    #     self.redo_stack = []

################################################################################
# FIXME: There is a bug on VisTrails that shows up if you load terminator.vt,
# open the image slices HW, undo about 300 times and then try to redo.
# This should be a test here, as soon as we have an api for that.

if __name__=="__main__":
    # Initialize the Vistrails Application and Theme
    import sys
    from gui import qt, theme
    app = qt.createBogusQtGuiApp(sys.argv)
    theme.initializeCurrentTheme()

    # Now visually test QPipelineView
    vv = QVistrailView(None)
    vv.show()    
    sys.exit(app.exec_())
