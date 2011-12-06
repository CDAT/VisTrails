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
################################################################################
# This file implements the Spreadsheet Window View, to manage sets of 
# StandardWidgetTabController
################################################################################
from PyQt4 import QtCore, QtGui
from spreadsheet_tabcontroller import StandardWidgetTabController
class TabControllerStack(QtGui.QStackedWidget):
    """
    TabControllerStack inherits from QStackedWidget to contain a
    list of StandardWidgetTabController. This will take care of separating
    sets of tabs per view.

    """
    def __init__(self, parent=None):
        """ TabControllerStack(parent: QWidget) -> TabControllerStack
        
        """
        
        QtGui.QStackedWidget.__init__(self, parent)
        self.tabControllers = {}
        self.create_actions()
        
    def create_actions(self):
        new_icon = QtGui.QIcon(':/images/newsheet.png')
        self.new_tab_action = QtGui.QAction(new_icon, "New tab", self, 
                                            triggered=self.new_tab_action_triggered)
        self.new_tab_action.setToolTip('Create a new tab')
        
    def new_tab_action_triggered(self):
        tabController = self.currentWidget()
        tabController.newSheetActionTriggered()
        
    def add_view(self, name):
        tabcontroller = StandardWidgetTabController()
        self.tabControllers[name] = tabcontroller
        self.addWidget(tabcontroller)
        self.emit(QtCore.SIGNAL('needChangeTitle'),
                  'VisTrails - Spreadsheet - %s' % name)
        self.connectTabControllerSignals(tabcontroller)
        #tabcontroller.create_first_sheet()
        
    def change_selected_view(self, name):
        if name in self.tabControllers:
            widget = self.tabControllers[name]
            self.setCurrentWidget(widget)
            
    def remove_view(self, name):
        if name in self.tabControllers:
            widget = self.tabControllers[name]
            widget.cleanup()
            self.removeWidget(widget)
            self.disconnectTabControllerSignals(widget)
            del self.tabControllers[name]
            
    def cleanup(self):
        for name, widget in self.tabControllers.items():
            widget.cleanup()
            self.removeWidget(widget)
            del self.tabControllers[name]
            
    def get_tab_controller_by_name(self, name):
        if name in self.tabControllers:
            return self.tabControllers[name]
        
    # UV-CDAT Events
    def connectTabControllerSignals(self, widget):
        self.connect(widget, QtCore.SIGNAL("add_tab"),
                     self.emit_add_tab)
        self.connect(widget, QtCore.SIGNAL("remove_tab"),
                     self.emit_remove_tab)
        self.connect(widget, QtCore.SIGNAL("change_tab_text"),
                     self.emit_change_tab_text)
        
    def disconnectTabControllerSignals(self, widget):
        self.disconnect(widget, QtCore.SIGNAL("add_tab"),
                     self.emit_add_tab)
        self.disconnect(widget, QtCore.SIGNAL("remove_tab"),
                     self.emit_remove_tab)
        self.disconnect(widget, QtCore.SIGNAL("change_tab_text"),
                     self.emit_change_tab_text)

    def emit_add_tab(self, sheetLabel, tabWidget):
        """emit_add_tab(sheetLabel: str, tabWidget: QWidget)-> None
        It will forward the signal 
        
        """
        self.emit(QtCore.SIGNAL("add_tab"), sheetLabel, tabWidget)
        
    def emit_remove_tab(self, widget):
        """emit_remove_tab(widget: QWidget)-> None
        It will forward the signal 
        
        """
        self.emit(QtCore.SIGNAL("remove_tab"), widget)
    
    def emit_change_tab_text(self, old, new):
        """emit_remove_tab(widget: QWidget)-> None
        It will forward the signal 
        
        """
        print "emit_change_tab", old, new
        self.emit(QtCore.SIGNAL("change_tab_text"), old, new)
        
    