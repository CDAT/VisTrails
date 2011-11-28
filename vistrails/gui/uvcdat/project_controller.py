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
import os, os.path
from PyQt4 import QtCore
from core.uvcdat.variable import VariableWrapper
from core.uvcdat.plot_registry import get_plot_registry
from core.utils import InstanceObject
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from core.db.locator import FileLocator
import core.db.action
from core.db.io import load_vistrail
from core.vistrail.controller import VistrailController
import api
from core import debug

class ProjectController(QtCore.QObject):
    """ProjecController is the class that interfaces between GUI actions in
    UVCDATWindow and SpreadsheetWindow and the VistrailController.
    
    """
    def __init__(self, vt_controller, name=''):
        QtCore.QObject.__init__(self)
        self.vt_controller = vt_controller
        self.name = name
        self.defined_variables = {}
        self.sheet_map = {}
        self.plot_registry = get_plot_registry()
        
    def add_defined_variable(self, filename, name, kwargs):
        var = VariableWrapper(filename, name, kwargs)
        self.defined_variables[name] = var

    def has_defined_variable(self, name):
        if name in self.defined_variables:
            return True
        return False
    
    def get_defined_variable(self, name):
        if name in self.defined_variables:
            return self.defined_variables[name]
        else:
            return None  
        
    def connect_spreadsheet(self):
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller()
        self.connect(tabController, QtCore.SIGNAL("dropped_variable"),
                     self.variable_was_dropped)
        self.connect(tabController, QtCore.SIGNAL("dropped_plot"),
                     self.plot_was_dropped)
        
    def disconnect_spreadsheet(self):
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller()
        self.disconnect(tabController, QtCore.SIGNAL("dropped_variable"),
                     self.variable_was_dropped)
        self.disconnect(tabController, QtCore.SIGNAL("dropped_plot"),
                     self.plot_was_dropped)
        
    def variable_was_dropped(self, info):
        """variable_was_dropped(info: (varName, sheetName, row, col) """
        (varName, sheetName, row, col) = info
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                self.sheet_map[sheetName][(row,col)].variable = varName
                self.update_variable(sheetName,row,col)
            else:
                self.sheet_map[sheetName][(row,col)] = InstanceObject(variable=varName,
                                                                      plot_type=None,
                                                                      gm=None,
                                                                      template=None)
        else:
            self.sheet_map[sheetName] = {}
            self.sheet_map[sheetName][(row,col)] = InstanceObject(variable=varName,
                                                                      plot_type=None,
                                                                      gm=None,
                                                                      template=None)
            
    def plot_was_dropped(self, info):
        """plot_was_dropped(info: (plot_type, gm, sheetName, row, col) """
        (plot_type, gm, sheetName, row, col) = info
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                self.sheet_map[sheetName][(row,col)].plot_type = plot_type
                self.sheet_map[sheetName][(row,col)].gm = gm
                self.update_plot(sheetName,row,col)
            else:
                self.sheet_map[sheetName][(row,col)] = InstanceObject(variable=None,
                                                                      plot_type=plot_type,
                                                                      gm=gm,
                                                                      template=None)
        else:
            self.sheet_map[sheetName] = {}
            self.sheet_map[sheetName][(row,col)] = InstanceObject(variable=None,
                                                                      plot_type=plot_type,
                                                                      gm=gm,
                                                                      template=None)
    
    def update_variable(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot_type is not None and cell.gm is not None:
            self.update_cell(sheetName, row, col)
    
    def update_plot(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.variable != None:
            self.update_cell(sheetName, row, col)
            
    def update_cell(self, sheetName, row, col):
        
        cell = self.sheet_map[sheetName][(row,col)]
        var = self.defined_variables[cell.variable]
        aliases = {'filename': var.filename,
                   'varName': var.name,
                   'axes': var.get_kwargs_str(),
                   'row': str(row),
                   'col': str(col),
                   'plot_type': cell.plot_type,
                   'gm': cell.gm,
                   'template': 'starter'}
        if (cell.variable is not None and 
            cell.plot_type is not None and
            cell.gm is not None):
            self.applyChanges(aliases)
            
    def load_workflow_templates(self):
        vt_file = "/Users/emanuele/Desktop/CDMS_Plot.vt"
        locator = FileLocator(os.path.abspath(vt_file))
        (plot_vistrail, abstractions , thumbnails, mashups) = load_vistrail(locator)
        controller = VistrailController()
        controller.set_vistrail(plot_vistrail, locator, 
                                abstractions, thumbnails, mashups) 
    
        version = plot_vistrail.get_version_number('vcs')
        #print " Loaded CDMS_Plot version: %s" % ( str( version ) )
        controller.change_selected_version(version)
        self.workflow_template = controller.current_pipeline
             
        
    def writePipelineToCurrentVistrail(self, aliases):
        """writePipelineToVistrail(aliases: dict) -> None 
        It will compute necessary actions and add to the current vistrail, 
        starting at self.parent_version. In the case self.parent_version
        does not contain a valid workflow, we will start from the root with
        a new pipeline.
        
        """
        #print self.vt_controller
        if self.vt_controller is None:
            self.vt_controller = api.get_current_controller()
            self.current_parent_version = 0L
        else:
            if self.current_parent_version > 0L:
                pipeline = self.vt_controller.vistrail.getPipeline(self.current_parent_version)
                if len(pipeline.aliases) >= len(self.workflow_template.aliases):
                    paliases = set(pipeline.aliases.keys())
                    waliases = set(self.workflow_template.aliases.keys())
                    if len(waliases - paliases) != 0:
                        self.current_parent_version = 0
        # print "writePipelineToCurrentVistrail: controller ", self.vt_controller
        #print "version ", self.current_parent_version 
        if self.current_parent_version == 0L:
            #create actions and paste them in current vistrail
            vistrail = self.vt_controller.vistrail
            if vistrail:
                newid = self.addPipelineAction(self.workflow_template,
                                               self.vt_controller,
                                               vistrail, 
                                               self.current_parent_version)
                #newtag = self.name
                #count = 1
                #while vistrail.hasTag(newtag):
                #    newtag = "%s %s"%(self.name, count)
                #    count += 1 
                #vistrail.addTag(newtag, newid)
                self.current_parent_version = newid
                
        #now we update pipeline with current parameter values
        pipeline = self.vt_controller.vistrail.getPipeline(self.current_parent_version)
        #self.addMergedAliases( aliases, pipeline )
        newid = self.addParameterChangesFromAliasesAction(pipeline, 
                                        self.vt_controller, 
                                        self.vt_controller.vistrail, 
                                        self.current_parent_version, aliases)
        self.current_parent_version = newid
            
                
    def applyChanges(self, aliases):
#        print "applyChanges"
        self.writePipelineToCurrentVistrail(aliases)
        pipeline = self.vt_controller.vistrail.getPipeline(self.current_parent_version)
        #print "Controller changed ", self.vt_controller.changed
        controller = VistrailController()
        controller.set_vistrail(self.vt_controller.vistrail,
                                self.vt_controller.locator)
        controller.change_selected_version(self.current_parent_version)
        (results, _) = controller.execute_current_workflow()
        
    def addPipelineAction(self, pipeline, controller, vistrail, 
                             parent_version):
        """addPipelineAction(pipeline: Pipeline, controller: VistrailController,
                             vistrail: Vistrail, parent_version: long) -> long
        
        """
        #print "addPipelineAction(%s,%s,%s,%s)"%(pipeline, controller, vistrail, parent_version)
        id_remap = {}
        action = core.db.action.create_paste_action(pipeline,
                                                    vistrail.idScope, 
                                                    id_remap)
                
        vistrail.add_action(action, parent_version, 
                            controller.current_session)
        controller.set_changed(True)
        controller.recompute_terse_graph()
        controller.invalidate_version_tree()
        #print "will return ", action.id
        return action.id
        #print results[0]
        
    def addParameterChangesFromAliasesAction(self, pipeline, controller, vistrail, parent_version, aliases):
        param_changes = []
        newid = parent_version
        #print "addParameterChangesFromAliasesAction()"
        #print "Aliases: %s " % str( aliases )
        #print "Pipeline Aliases: %s " % str( pipeline.aliases )
        aliasList = aliases.iteritems()
        for k,value in aliasList:
            alias = pipeline.aliases.get(k,None) # alias = (type, oId, parentType, parentId, mId)
            if alias:
                module = pipeline.modules[alias[4]]
                function = module.function_idx[alias[3]]
                old_param = function.parameter_idx[alias[1]]
                #print alias, module, function, old_param
                if old_param.strValue != value:
                    new_param = VistrailController.update_parameter(controller, 
                                                                    old_param, 
                                                                    value)
                    if new_param is not None:
                        op = ('change', old_param, new_param, 
                              function.vtType, function.real_id)
                        param_changes.append(op)
#                        print "Added parameter change for alias=%s, value=%s" % ( k, value  )
                    else:
                        debug.warning("CDAT Package: Change parameter %s in widget %s was not generated"%(k, self.name))
            else:
                debug.warning( "CDAT Package: Alias %s does not exist in pipeline" % (k) )
        if len(param_changes) > 0:
            action = core.db.action.create_action(param_changes)
            vistrail.add_action(action, parent_version, controller.current_session)
            controller.set_changed(True)
            controller.recompute_terse_graph()
            controller.invalidate_version_tree()
            newid = action.id
        return newid