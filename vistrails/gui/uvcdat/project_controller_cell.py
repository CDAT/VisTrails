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

import sys
from datetime import datetime

import api
from core.uvcdat.plotmanager import get_plot_manager

class ControllerCell(object):
    
    def __init__(self, variables=[], plots=[], templates=[], current_parent_version=0L):
        self.plots = plots
        self._current_version=current_parent_version
        
        self.undoVersion = current_parent_version
        self.redoVersion = current_parent_version
        
        self.variableQ = []
        self.templateQ = []
        
        for v in variables: self.add_variable(v)
        for t in templates: self.add_template(t)

    def _get_current_parent_version(self):
        return self._current_version    
    def _set_current_parent_version( self, version ):
        if version != self._current_version:
            self.undoVersion = version
            self.redoVersion = version
            self._current_version = version
#        print "\n ****************** Set Cell current_parent_version: %d ****************** \n" % version    
    current_parent_version = property( _get_current_parent_version, _set_current_parent_version ) 
    
    def add_variable(self, varname):
        for plot in self.plots:
            if len(plot.variables) < plot.varnum:
                plot.variables.append(varname)
                return len(plot.variables) == plot.varnum
            
        self.variableQ.append(varname)
        return False
    
    def add_template(self, template):
        for plot in self.plots:
            if plot.template is None:
                plot.template = template
                return len(plot.variables) == plot.varnum
            
        self.templateQ.append(template)
        return False
    
    def add_plot(self, plot):
        self.plots.append(plot)
        
        #add template from queue
        if plot.template is None and len(self.templateQ) > 0:
            plot.template = self.templateQ.pop(0)
        
        #add vars from queue
        for i in range(plot.varnum - len(plot.variables)):
            if len(self.variableQ) > 0:
                plot.variables.append(self.variableQ.pop(0))
            else:
                return False
        return len(plot.variables) == plot.varnum
            
    def is_ready(self):
        for p in self.plots:
            if p.varnum == len(p.variables):
                return True
        return False
    
    def variables(self):
        """
        Returns list of all variables in plots and queue
        """
        plot_vars = [v for p in self.plots for v in p.variables] 
        return plot_vars + self.variableQ
    
    def remove_plot(self, plot):
        try:
            get_plot_manager().remove_plot_instance(plot)
            self.plots.remove(plot)
        except ValueError, err:
            print>>sys.stderr, " -- Error Removing plot (probably removing the plot more then once from the same list)-- "
        
    def clear_plots(self):
        for i in reversed(range(len(self.plots))):
            self.remove_plot(self.plots[i])
    
    def clear(self):
        self.clear_plots()
        self.clear_queues()
        self.clear_stacks()
        
    def clear_queues(self):
        self.variableQ = []
        self.templateQ = []
        
    def clear_stacks(self):
        self.undoStack = []
        self.redoStack = []
        
    def acceptsPlotPackage(self, pkg):
        """ Returns true if pkg does not conflict with existing
        plot packages
        """
        return (len(self.plots) == 0 or self.plots[0].package == pkg)
    
    DATE_FORMAT = "%d/%m/%y %H:%M:%S.%f"
    def pushUndoVersion(self, version = None):
        """adds timestamp annotation to mark this version as an undo point"""
        if version is None:
            version = self.current_parent_version
        controller = api.get_current_controller()
        controller.vistrail.set_action_annotation(version, 'uvcdat-last-visit',
               datetime.strftime(datetime.now(), ControllerCell.DATE_FORMAT))
#        print "Set undo version: %d" % version
        

        
    def getUndoVersion(self):
        """returns first ancestor that has uvcdat-last-visit annotation"""
        try:
            vistrail = api.get_current_controller().vistrail
        except api.NoVistrail:
            return None
            
        def _getParent(version):
            if version != 0:
                return vistrail.actionMap[version].parent
            return None

        parent = _getParent(self.current_parent_version)
        while parent is not None:
            if vistrail.get_action_annotation(parent,'uvcdat-last-visit'):
#                print "Found undo version %d" % parent
                return parent
            parent = _getParent(parent)
        return None
        
    def getRedoVersion(self):
        """looks at all child versions, and returns that which has the most
        recent uvcdat-last-visit annotation, if any """
        try:
            vistrail = api.get_current_controller().vistrail
        except api.NoVistrail:
            return None
        
        graph = vistrail.tree.getVersionTree()
        
        maxes = [datetime.min, None] #time, version
        def _findMostRecent(version):
            children = graph.edges_from(version)
            for (child, _) in children:
                annotation = vistrail.get_action_annotation(child,
                        'uvcdat-last-visit')
                if annotation is not None:
                    time = datetime.strptime(annotation.value, 
                                             ControllerCell.DATE_FORMAT)
                    if time > maxes[0]:
                        maxes[0] = time
                        maxes[1] = child
                else:
                    _findMostRecent(child)
        
        _findMostRecent(self.current_parent_version)
#        if maxes[1]:
#            print "Found redo version: %d" % maxes[1]
        return maxes[1]
            
    def canUndo(self):
        """search up the version tree for undo points, and sets 
        next undo version"""
        if self.undoVersion == self.current_parent_version:
            self.undoVersion = self.getUndoVersion()
        return self.undoVersion is not None
    
    def canRedo(self):
        """search down the version tree for undo points, and sets 
        next redo version"""
        if self.redoVersion == self.current_parent_version:
            self.redoVersion = self.getRedoVersion()
        return self.redoVersion is not None
            
    def undo(self):
        """changes the current_parent_version if possible, must call
        canUndo prior"""
        if self.undoVersion is not None:
            self.redoVersion = self.current_parent_version
            self._current_version = self.undoVersion
            
    def redo(self):
        """changes the current_parent_version and set uvcdat-last-visit 
        annotation, if possible. Must call canRedo prior"""
        if self.redoVersion is not None:
            self.undoVersion = self.current_parent_version
            self._current_version = self.redoVersion
            self.pushUndoVersion()
