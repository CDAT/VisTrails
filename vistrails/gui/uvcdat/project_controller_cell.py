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
from core.uvcdat.plotmanager import get_plot_manager

class ControllerCell(object):
    
    def __init__(self, variables=[], plots=[], templates=[], current_parent_version=0L):
        self.plots = plots
        self._current_version=current_parent_version
        
        self.variableQ = []
        self.templateQ = []
        
        for v in variables: self.add_variable(v)
        for t in templates: self.add_template(t)

    def _get_current_parent_version(self):
        return self._current_version    
    def _set_current_parent_version( self, version ):
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
        get_plot_manager().remove_plot_instance(plot)
        self.plots.remove(plot)
        
    def clear_plots(self):
        for i in reversed(range(len(self.plots))):
            self.remove_plot(self.plots[i])
    
    def clear(self):
        self.clear_plots()
        self.variableQ = []
        self.templateQ = []
        
    def acceptsPlotPackage(self, pkg):
        """ Returns true if pkg does not conflict with existing
        plot packages
        """
        return (len(self.plots) == 0 or self.plots[0].package == pkg)
        