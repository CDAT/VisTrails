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
from PyQt4 import QtCore, QtGui
from itertools import izip
import os

from core import debug
from core.modules.module_registry import get_module_registry
from core.modules.basic_modules import String
from core.vistrail.port_spec import PortSpec
from core.system import vistrails_root_directory
from gui.modules import get_widget_class
from gui.common_widgets import QToolWindowInterface
from gui.port_documentation import QPortDocumentation
from gui.theme import CurrentTheme

class AliasLabel(QtGui.QLabel):
    """
    AliasLabel is a QLabel that supports hover actions similar
    to a hot link
    """
    def __init__(self, alias='', text='', default_label='', parent=None):
        """ AliasLabel(alias:str , text: str, default_label: str,
                             parent: QWidget) -> QHoverAliasLabel
        Initialize the label with a text
        
        """
        QtGui.QLabel.__init__(self, parent)
        self.alias = alias
        self.caption = text
        self.default_label = default_label
        self.updateText()
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(alias)
        self.palette().setColor(QtGui.QPalette.WindowText,
                                CurrentTheme.HOVER_DEFAULT_COLOR)

    def updateText(self):
        """ updateText() -> None
        Update the label text to contain the alias name when appropriate
        
        """
        if self.alias != '':
            self.setText(self.alias + ': ' + self.caption)
        elif self.default_label != '':
            self.setText(self.default_label + ': ' + self.caption)
        else:
            self.setText(self.caption)

    def event(self, event):
        """ event(event: QEvent) -> Event Result
        Override to handle hover enter and leave events for hot links
        
        """
        if event.type()==QtCore.QEvent.HoverEnter:
            self.palette().setColor(QtGui.QPalette.WindowText,
                                    CurrentTheme.HOVER_SELECT_COLOR)
        if event.type()==QtCore.QEvent.HoverLeave:
            self.palette().setColor(QtGui.QPalette.WindowText,
                                    CurrentTheme.HOVER_DEFAULT_COLOR)
        return QtGui.QLabel.event(self, event)
        # return super(QHoverAliasLabel, self).event(event)

    def mousePressEvent(self, event):
        """ mousePressEvent(event: QMouseEvent) -> None        
        If mouse click on the label, show up a dialog to change/add
        the alias name
        
        """
        if event.button()==QtCore.Qt.LeftButton:
            (text, ok) = QtGui.QInputDialog.getText(self,
                                                    'Set Parameter Alias',
                                                    'Enter the parameter alias',
                                                    QtGui.QLineEdit.Normal,
                                                    self.alias)
            while ok and self.parent().check_alias(str(text)):
                msg =" This alias is already being used.\
 Please enter a different parameter alias "
                (text, ok) = QtGui.QInputDialog.getText(self,
                                                        'Set Parameter Alias',
                                                        msg,
                                                        QtGui.QLineEdit.Normal,
                                                        text)
            if ok and str(text)!=self.alias:
                if not self.parent().check_alias(str(text)):
                    self.alias = str(text).strip()
                    self.updateText()
                    self.parent().updateMethod()

class Parameter(object):
    def __init__(self, desc):
        self.type = desc.name
        self.identifier = desc.identifier
        self.namespace = None if not desc.namespace else desc.namespace
        self.strValue = ''
        self.alias = ''
        self.queryMethod = None
        
class ParameterEntry(QtGui.QTreeWidgetItem):
    plus_icon = QtGui.QIcon(os.path.join(vistrails_root_directory(),
                                         'gui/resources/images/plus.png'))
    minus_icon = QtGui.QIcon(os.path.join(vistrails_root_directory(),
                                          'gui/resources/images/minus.png'))
    def __init__(self, port_spec, function=None, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.setFirstColumnSpanned(True)
        self.port_spec = port_spec
        self.function = function

    def build_widget(self, widget_accessor, with_alias=True):
        reg = get_module_registry()

        # widget = QtGui.QDockWidget()
        # widget.setFeatures(QtGui.QDockWidget.DockWidgetClosable |
        #                    QtGui.QDockWidget.DockWidgetVerticalTitleBar)
        widget = QtGui.QWidget()

        h_layout = QtGui.QHBoxLayout()
        h_layout.insertSpacing(0, 10)
        h_layout.setMargin(2)
        h_layout.setSpacing(2)

        v_layout = QtGui.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignVCenter)
        delete_button = QtGui.QToolButton()
        delete_button.setIconSize(QtCore.QSize(8,8))
        delete_button.setIcon(ParameterEntry.minus_icon)
        def delete_method():
            if self.function is not None:
                self.group_box.parent().parent().parent().delete_method(
                    self, self.port_spec.name, self.function.real_id)
            else:
                self.group_box.parent().parent().parent().delete_method(
                    self, self.port_spec.name, None)
                
        QtCore.QObject.connect(delete_button, QtCore.SIGNAL("clicked()"), 
                               delete_method)
        v_layout.addWidget(delete_button)
        
        add_button = QtGui.QToolButton()
        add_button.setIcon(ParameterEntry.plus_icon)
        add_button.setIconSize(QtCore.QSize(8,8))
        def add_method():
            self.group_box.parent().parent().parent().add_method(
                self.port_spec.name)
        QtCore.QObject.connect(add_button, QtCore.SIGNAL("clicked()"), 
                               add_method)
        v_layout.addWidget(add_button)
        h_layout.addLayout(v_layout)
        
        self.my_widgets = []
        self.my_labels = []
        self.group_box = QtGui.QGroupBox()
        layout = QtGui.QGridLayout()
        layout.setMargin(5)
        layout.setSpacing(5)
        self.group_box.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.group_box.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                     QtGui.QSizePolicy.Fixed)
        self.group_box.palette().setColor(QtGui.QPalette.Window,
                                     CurrentTheme.METHOD_SELECT_COLOR)

        if self.function is not None:
            params = self.function.parameters
        else:
            params = [None,] * len(self.port_spec.descriptors())

        for i, (desc, param) in enumerate(izip(self.port_spec.descriptors(), 
                                               params)):
            #print 'adding desc', desc.name
            # ps_label = ''
            # if port_spec.labels is not None and len(port_spec.labels) > i:
            #     ps_label = str(port_spec.labels[i])
            # label = QHoverAliasLabel(p.alias, p.type, ps_label)

            widget_class = widget_accessor(desc.module)
            if param is not None:
                obj = param
            else:
                obj = Parameter(desc)
            if with_alias:
                label = AliasLabel(obj.alias, obj.type)
                self.my_labels.append(label)
            else:
                label = QtGui.QLabel(obj.type)
            param_widget = widget_class(obj, self.group_box)
            self.my_widgets.append(param_widget)
            layout.addWidget(label, i, 0)
            layout.addWidget(param_widget, i, 1)

        self.group_box.setLayout(layout)
        def updateMethod():
            if self.function is not None:
                real_id = self.function.real_id
            else:
                real_id = -1
            self.group_box.parent().parent().parent().update_method(
                self, self.port_spec.name, self.my_widgets, self.my_labels, real_id)
        def check_alias(name):
            controller = self.group_box.parent().parent().parent().controller
            if controller:
                return controller.check_alias(name)
            return False
        self.group_box.updateMethod = updateMethod
        self.group_box.check_alias = check_alias
        h_layout.addWidget(self.group_box)
        widget.setLayout(h_layout)
        return widget

    def get_widget(self):
        return self.build_widget(get_widget_class, True)

class PortItem(QtGui.QTreeWidgetItem):
    null_icon = QtGui.QIcon()
    eye_icon = QtGui.QIcon(os.path.join(vistrails_root_directory(),
                                        'gui/resources/images/eye.png'))
    eye_disabled_icon = \
        QtGui.QIcon(os.path.join(vistrails_root_directory(),
                                 'gui/resources/images/eye_gray.png'))
    conn_icon = \
        QtGui.QIcon(os.path.join(vistrails_root_directory(),
                                 'gui/resources/images/connection.png'))

    def __init__(self, port_spec, is_connected, is_optional, is_visible,
                 parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        # self.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.setFlags(QtCore.Qt.ItemIsEnabled)
        # self.setCheckState(0, QtCore.Qt.Unchecked)
        self.port_spec = port_spec
        self.is_connected = is_connected
        self.is_optional = is_optional
        self.is_visible = is_visible
        self.build_item(port_spec, is_connected, is_optional, is_visible)

    def visible(self):
        return not self.is_optional or self.is_visible

    def set_visible(self, visible):
        self.is_visible = visible
        if visible:
            self.setIcon(0, PortItem.eye_icon)
        else:
            self.setIcon(0, PortItem.null_icon)

    def get_visible(self):
        return self.visible_checkbox

    def get_connected(self):
        return self.connected_checkbox

    def is_constant(self):
        return get_module_registry().is_method(self.port_spec)

    def build_item(self, port_spec, is_connected, is_optional, is_visible):
        if not is_optional:
            self.setIcon(0, PortItem.eye_disabled_icon)
        elif is_visible:
            self.setIcon(0, PortItem.eye_icon)
            
        # if port_spec is not a method, make it gray
        if is_connected:
            self.setIcon(1, PortItem.conn_icon)
        self.setText(2, port_spec.name)

        if not self.is_constant():
            self.setForeground(2, 
                               QtGui.QBrush(QtGui.QColor.fromRgb(128,128,128)))

        self.visible_checkbox = QtGui.QCheckBox()
        self.connected_checkbox = QtGui.QCheckBox()
        
    def contextMenuEvent(self, event, widget):
        if self.port_spec is None:
            return
        act = QtGui.QAction("View Documentation", widget)
        act.setStatusTip("View method documentation")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.view_documentation)
        menu = QtGui.QMenu(widget)
        menu.addAction(act)
        menu.exec_(event.globalPos())
        
    def view_documentation(self):
        descriptor = self.treeWidget().module.module_descriptor
        port_type = self.treeWidget().port_type
        widget = QPortDocumentation(descriptor,
                                    port_type,
                                    self.port_spec.name)
        widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        widget.exec_()

class PortsList(QtGui.QTreeWidget):
    def __init__(self, port_type, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        self.port_type = port_type
        self.setColumnCount(3)
        self.setColumnWidth(0,24)
        self.setColumnWidth(1,24)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setHeaderHidden(True)
        self.connect(self, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*, int)"),
                     self.item_clicked)
        self.module = None
        self.port_spec_items = {}
        self.entry_klass = ParameterEntry

    def set_entry_klass(self, entry_klass):
        self.entry_klass = entry_klass
        self.update_module(self.module)

    def update_module(self, module):
        """ update_module(module: Module) -> None        
        Setup this tree widget to show functions of module
        
        """
        # this is strange but if you try to clear the widget when the focus is 
        # in one of the items (after setting a parameter for example), 
        # VisTrails crashes on a Mac (Emanuele) This is probably a Qt bug
        w =  QtGui.QApplication.focusWidget()
        if self.isAncestorOf(w):
            w.clearFocus()
        self.clear()
        self.module = module
        self.port_spec_items = {}
        self.function_map = {}
        if module and module.is_valid:
            reg = get_module_registry()
            descriptor = module.module_descriptor
            if self.port_type == 'input':
                port_specs = module.destinationPorts()
                connected_ports = module.connected_input_ports
                visible_ports = module.visible_input_ports
            elif self.port_type == 'output':
                port_specs = module.sourcePorts()
                connected_ports = module.connected_output_ports
                visible_ports = module.visible_output_ports
            else:
                raise Exception("Unknown port type: '%s'" % self.port_type)
            
            for port_spec in sorted(port_specs, key=lambda x: x.name):
                connected = port_spec.name in connected_ports and \
                    connected_ports[port_spec.name] > 0
                item = PortItem(port_spec, 
                                connected,
                                port_spec.optional,
                                port_spec.name in visible_ports)
                self.addTopLevelItem(item)
                self.port_spec_items[port_spec.name] = (port_spec, item)

            if self.port_type == 'input':
                for function in module.functions:
                    if not function.is_valid:
                        debug.critical("function '%s' not valid", function.name)
                        continue
                    port_spec, item = self.port_spec_items[function.name]
                    subitem = self.entry_klass(port_spec, function)
                    self.function_map[function.real_id] = subitem
                    item.addChild(subitem)
                    subitem.setFirstColumnSpanned(True)
                    self.setItemWidget(subitem, 0, subitem.get_widget())
                    item.setExpanded(True)
                
                    # self.setItemWidget(item, 0, item.get_visible())
                    # self.setItemWidget(item, 1, item.get_connected())

                    # i = QTreeWidgetItem(self)
                    # self.addTopLevelItem(i)
                    # i.setText(2, port_spec.name)
                    # visible_checkbox = QtGui.QCheckBox()
                    # self.setItemWidget(i, 0, visible_checkbox)
                    # connceted_checkbox = QtGui.QCheckBox()
                    # connected_checkbox.setEnabled(False)
                    # self.setItemWidget(i, 1, connected_checkbox)
                

            # base_items = {}
            # # Create the base widget item for each descriptor
            # for descriptor in moduleHierarchy:
            #     baseName = descriptor.name
            #     base_package = descriptor.identifier
            #     baseItem = QMethodTreeWidgetItem(None,
            #                                      None,
            #                                      self,
            #                                      (QtCore.QStringList()
            #                                       <<  baseName
            #                                       << ''))
            #     base_items[descriptor] = baseItem

            # method_specs = {}
            # # do this in reverse to ensure proper overloading
            # # !!! NOTE: we have to use ***all*** input ports !!!
            # # because a subclass can overload a port with a 
            # # type that isn't a method
            # for descriptor in reversed(moduleHierarchy):
            #     method_specs.update((name, (descriptor, spec))
            #                         for name, spec in \
            #                             registry.module_ports('input', 
            #                                                   descriptor))

            # # add local registry last so that it takes precedence
            # method_specs.update((spec.name, (descriptor, spec))
            #                     for spec in module.port_spec_list
            #                     if spec.type == 'input')

            # for _, (desc, method_spec) in sorted(method_specs.iteritems()):
            #     if registry.is_method(method_spec):
            #         baseItem = base_items[desc]
            #         sig = method_spec.short_sigstring
            #         QMethodTreeWidgetItem(module,
            #                               method_spec,
            #                               baseItem,
            #                               (QtCore.QStringList()
            #                                << method_spec.name
            #                                << sig))

            # self.expandAll()
            # self.resizeColumnToContents(2) 
        # show invalid module attributes
        if module and not module.is_valid and self.port_type == 'input':
            for function in module.functions:
                if function.name in self.port_spec_items:
                    port_spec, item = self.port_spec_items[function.name]
                else:
                    sigstring = "(" + ",".join(
                        ['edu.utah.sci.vistrails.basic:String'
                         for i in xrange(len(function.parameters))]) + ")"
                    port_spec = PortSpec(name=function.name, type='input',
                                         sigstring=sigstring)
                    item = PortItem(port_spec,  False, False, False)
                self.addTopLevelItem(item)
                self.port_spec_items[port_spec.name] = (port_spec, item)
                subitem = self.entry_klass(port_spec, function)
                self.function_map[function.real_id] = subitem
                item.addChild(subitem)
                subitem.setFirstColumnSpanned(True)
                self.setItemWidget(subitem, 0, subitem.get_widget())
                item.setExpanded(True)

    def item_clicked(self, item, col):
        if item.parent() is not None:
            return

        if self.port_type == 'input':
            visible_ports = self.module.visible_input_ports
        elif self.port_type == 'output':
            visible_ports = self.module.visible_output_ports
        else:
            raise Exception("Unknown port type: '%s'" % self.port_type)

        if col == 0:
            if item.is_optional:
                item.set_visible(not item.is_visible)
                if item.is_visible:
                    visible_ports.add(item.port_spec.name)
                else:
                    visible_ports.discard(item.port_spec.name)
                self.controller.flush_delayed_actions()
                self.controller.current_pipeline_view.recreate_module(
                    self.controller.current_pipeline, self.module.id)
        if col == 2:
            if item.isExpanded():
                item.setExpanded(False)
            elif item.childCount() > 0:
                item.setExpanded(True)
            elif item.childCount() == 0 and item.is_constant():
                subitem = self.entry_klass(item.port_spec)
                item.addChild(subitem)
                subitem.setFirstColumnSpanned(True)
                self.setItemWidget(subitem, 0, subitem.get_widget())
                item.setExpanded(True)
                # need to find port_spec
                if len(item.port_spec.descriptors()) == 0:
                    self.update_method(subitem, item.port_spec.name, [], [])

        
    def set_controller(self, controller):
        self.controller = controller

    def update_method(self, subitem, port_name, widgets, labels, real_id=-1):
        #print 'updateMethod called', port_name
        if self.controller:
            _, item = self.port_spec_items[port_name]
            str_values = []
            query_methods = []
            for w in widgets:
                str_values.append(str(w.contents()))
                if hasattr(w, 'query_method'):
                    query_methods.append(w.query_method())
            if real_id < 0:
                should_replace = False
            else:
                should_replace = True
            self.controller.update_function(self.module,
                                            port_name,
                                            str_values,
                                            real_id,
                                            [str(label.alias)
                                             for label in labels],
                                            query_methods,
                                            should_replace)

            # FIXME need to get the function set on the item somehow
            # HACK for now
            for function in self.module.functions:
                if function.real_id not in self.function_map:
                    self.function_map[function.real_id] = subitem
                    subitem.function = function
                                            
    def delete_method(self, subitem, port_name, real_id=None):
        if real_id is not None and self.controller:
            #print "got to delete"
            self.controller.delete_function(real_id, self.module.id)
        _, item = self.port_spec_items[port_name]
        item.removeChild(subitem)
        # how to delete items...x
        # subitem.deleteLater()
            

    def add_method(self, port_name):
        port_spec, item = self.port_spec_items[port_name]
        subitem = self.entry_klass(port_spec)
        item.addChild(subitem)
        subitem.setFirstColumnSpanned(True)
        self.setItemWidget(subitem, 0, subitem.get_widget())
        item.setExpanded(True)
        if len(port_spec.descriptors()) == 0:
            self.update_method(subitem, port_name, [], [])
            
        
        # if methodBox.controller:
        #     methodBox.lockUpdate()
        #     methodBox.controller.update_function(methodBox.module,
        #                                          self.function.name,
        #                                          [str(w.contents()) 
        #                                           for w in self.widgets],
        #                                          self.function.real_id,
        #                                          [str(label.alias)
        #                                           for label in self.labels])
            
        #     methodBox.unlockUpdate()

    def contextMenuEvent(self, event):
        # Just dispatches the menu event to the widget item
        item = self.itemAt(event.pos())
        if item:
            item.contextMenuEvent(event, self)

class QPortsPane(QtGui.QWidget, QToolWindowInterface):
    def __init__(self, port_type, parent=None, flags=QtCore.Qt.Widget):
        QtGui.QWidget.__init__(self, parent, flags)
        self.port_type = port_type
        self.build_widget()
        self.controller = None

    def build_widget(self):
        self.tree_widget = PortsList(self.port_type)
        layout = QtGui.QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)
        self.setWindowTitle('%s Ports' % self.port_type.capitalize())

    def set_controller(self, controller):
        self.controller = controller
        self.tree_widget.set_controller(controller)

    def update_module(self, module):
        self.tree_widget.update_module(module)
    
