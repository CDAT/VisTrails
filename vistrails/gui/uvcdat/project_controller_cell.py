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
class ControllerCell(object):
    def __init__(self, variables=[], plots=[], templates=[], 
                 current_parent_version=0L):
        self.variables = variables
        self.plots = plots
        self.templates = templates
        self.current_parent_version=current_parent_version
        
    def get_plots_varnum(self):
        res = 0
        for plot in self.plots:
            res += plot.varnum
        return res
    
    def add_variable(self, varname):
        replaced = False
        if len(self.variables) < self.get_plots_varnum():
            self.variables.append(varname)
        else:
            if len(self.variables) > 0:
                self.variables.pop()
                replaced = True
            self.variables.append(varname)
        return replaced
    
    def add_template(self, template):
        if len(self.templates) < len(self.plots):
            self.templates.append(template)
        else:
            if len(self.templates) > 0:
                self.templates.pop()
            self.templates.append(template)
    def is_ready(self):
        if len(self.plots) > 0 and self.has_enough_variables():
            return True
        return False
    
    def has_enough_variables(self):
        for plot in self.plots:
            if plot.varnum > len(self.variables):
                return False
        return True