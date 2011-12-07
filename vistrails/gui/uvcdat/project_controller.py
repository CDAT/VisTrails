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

import api
import core.db.action
from core.db.io import load_vistrail
from core.db.locator import FileLocator
from core import debug
from core.modules.module_registry import get_module_registry
from core.utils import InstanceObject
from core.uvcdat.variable import VariableWrapper
from core.uvcdat.plot_registry import get_plot_registry
from core.uvcdat.plotmanager import get_plot_manager
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from core.vistrail.controller import VistrailController
from core.configuration import get_vistrails_configuration
from packages.spreadsheet.spreadsheet_controller import spreadsheetController

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
        self.plot_manager = get_plot_manager()
        
    def add_defined_variable(self, var):
        self.defined_variables[var.name] = var

    def emit_defined_variable(self, var):
        from packages.uvcdat_cdms.init import CDMSVariable
        from packages.uvcdat_pv.init import PVVariable
        from api import _app
        if isinstance(var, CDMSVariable):
            _app.uvcdatWindow.dockVariable.widget().addVariable(var.to_python())
        elif isinstance(var, PVVariable):
            _app.uvcdatWindow.dockVariable.widget().addVariable(var.name, type='PARAVIEW')
            
    # def add_defined_variable(self, filename, name, kwargs):
    #     var = VariableWrapper(filename, name, kwargs)
    #     self.defined_variables[name] = var

    def load_variables_from_modules(self, var_modules):
        for varm in var_modules:
            varname = PlotPipelineHelper.get_value_from_function(varm, 'name')
            if varname not in self.defined_variables:
                var = varm.module_descriptor.module.from_module(varm)
                self.defined_variables[varname] = var
                self.emit_defined_variable(var)
                
    def has_defined_variable(self, name):
        if name in self.defined_variables:
            return True
        return False
    
    def get_defined_variable(self, name):
        if name in self.defined_variables:
            return self.defined_variables[name]
        else:
            return None  
        
    def is_variable_in_use(self, name):
        for sheetname in self.sheet_map:
            for cell in self.sheet_map[sheetname].itervalues():
                if name in cell.variables:
                    return True
        return False
    
    def is_cell_ready(self, sheetName, row, col):
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                if cell.plot is not None and len(cell.variables) == cell.plot.varnum:
                    return True
        return False
    
    def cell_has_plot(self, sheetName, row, col):
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                if cell.plot is not None:
                    return True
        return False
    
    def connect_spreadsheet(self):
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller()
        self.connect(tabController, QtCore.SIGNAL("dropped_variable"),
                     self.variable_was_dropped)
        self.connect(tabController, QtCore.SIGNAL("dropped_visualization"),
                     self.vis_was_dropped)
        self.connect(tabController, QtCore.SIGNAL("dropped_plot"),
                     self.plot_was_dropped)
        self.connect(tabController, QtCore.SIGNAL("request_plot_configure"),
                     self.request_plot_configure)
        self.connect(tabController, QtCore.SIGNAL("request_plot_execution"),
                     self.request_plot_execution)
        self.connect(tabController, QtCore.SIGNAL("cell_deleted"),
                     self.clear_cell)
        
    def disconnect_spreadsheet(self):
        ssheetWindow = spreadsheetController.findSpreadsheetWindow(show=False)
        tabController = ssheetWindow.get_current_tab_controller()
        self.disconnect(tabController, QtCore.SIGNAL("dropped_variable"),
                     self.variable_was_dropped)
        self.disconnect(tabController, QtCore.SIGNAL("dropped_visualization"),
                     self.vis_was_dropped)
        self.disconnect(tabController, QtCore.SIGNAL("dropped_plot"),
                     self.plot_was_dropped)
        self.disconnect(tabController, QtCore.SIGNAL("request_plot_configure"),
                     self.request_plot_configure)
        self.disconnect(tabController, QtCore.SIGNAL("request_plot_execution"),
                     self.request_plot_execution)
        self.disconnect(tabController, QtCore.SIGNAL("cell_deleted"),
                     self.clear_cell)
        
    def variable_was_dropped(self, info):
        """variable_was_dropped(info: (varName, sheetName, row, col) """
        (varName, sheetName, row, col) = info
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                if cell.plot:
                    if len(cell.variables) < cell.plot.varnum:
                        cell.variables.append(varName)
                    else:
                        cell.variables.pop()
                        cell.variables.append(varName)
                else:
                    #replace the variable
                    cell.variables = [varName]
                self.update_variable(sheetName,row,col)
            else:
                self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[varName],
                                                                      plot=None,
                                                                      template=None,
                                                                      current_parent_version=0L)
        else:
            self.sheet_map[sheetName] = {}
            self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[varName],
                                                                      plot=None,
                                                                      template=None,
                                                                      current_parent_version=0L)
            
    def vis_was_dropped(self, info):
        """vis_was_dropped(info: (pipeline, sheetName, row, col) """
        (pipeline, sheetName, row, col, plot_type) = info
        
        if sheetName in self.sheet_map:
            if (row,col) not in self.sheet_map[sheetName]:
                self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[],
                                                                      plot=None,
                                                                      template=None,
                                                                      current_parent_version=0L)
        else:
            self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[],
                                                                  plot=None,
                                                                  template=None,
                                                                  current_parent_version=0L)
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None and len(cell.variables) > 0:
            self.reset_workflow(cell)
            
        helper = self.plot_manager.get_plot_helper(plot_type)
        action = helper.copy_pipeline_to_other_location(pipeline, self.vt_controller,
                                                        sheetName, row, col, 
                                                        plot_type,
                                                        cell)
        
        #check if a new var was added:
        not_found = False
        for var in cell.variables:
            if var not in self.defined_variables:
                not_found = True
        if not_found:
            from packages.uvcdat.init import Variable
            from packages.uvcdat_pv.init import PVVariable
            from packages.uvcdat_cdms.init import CDMSVariable
            pipeline = self.vt_controller.vistrail.getPipeline(cell.current_parent_version)
            var_modules = PlotPipelineHelper.find_modules_by_type(pipeline, Variable)
            if len(var_modules) > 0:
                self.load_variables_from_modules(var_modules)
            else:
                #when the workflows are updated to include the variable modules.
                #they will be included in the case above. For now we need to 
                #construct the variables based on the alias values (Emanuele)
                if cell.plot.package == "PVClimate":
                    for i in range(len(cell.variables)):
                        filename = pipeline.get_alias_str_value(cell.plot.files[i])
                        varname = pipeline.get_alias_str_value(cell.plot.vars[i])
                        if varname not in self.defined_variables:
                            var = PVVariable(filename=filename, name=varname)
                            self.defined_variables[varname] = var
                            self.emit_defined_variable(var)
                if cell.plot.package == "DV3D":
                    for i in range(len(cell.variables)):
                        filename = pipeline.get_alias_str_value(cell.plot.files[i])
                        varname = pipeline.get_alias_str_value(cell.plot.vars[i])
                        axes = None
                        if len(cell.plot.axes) > i:
                            axes = pipeline.get_alias_str_value(cell.plot.axes[i])
                        if varname not in self.defined_variables:
                            var =  CDMSVariable(filename=filename, 
                                                name=varname, axes=axes)
                            self.defined_variables[varname] = var
                            self.emit_defined_variable(var)
                    
        self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col, None, None,
                  plot_type, cell.current_parent_version)
        self.execute_plot(cell.current_parent_version)
        
    def clear_cell(self, sheetName, row, col):
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                self.reset_workflow(cell)
                cell.variables = []
                cell.plot = None
                cell.template = None
                self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col)

    def plot_was_dropped(self, info):
        """plot_was_dropped(info: (plot, sheetName, row, col) """
        (plot, sheetName, row, col) = info
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                if cell.plot is not None and len(cell.variables) > 0:
                    self.reset_workflow(cell) 
                self.sheet_map[sheetName][(row,col)].plot = plot
                self.update_plot(sheetName,row,col)
            else:
                self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[],
                                                                      plot=plot,
                                                                      template=None,
                                                                      current_parent_version=0L)
        else:
            self.sheet_map[sheetName] = {}
            self.sheet_map[sheetName][(row,col)] = InstanceObject(variables=[],
                                                                  plot=plot,
                                                                  template=None,
                                                                  current_parent_version=0L)
    
    def reset_workflow(self, cell):
        pipeline = self.vt_controller.vistrail.getPipeline(cell.current_parent_version)
        self.vt_controller.change_selected_version(cell.current_parent_version)
        ids = []
        for module in pipeline.module_list:
            ids.append(module.id)
        action = self.vt_controller.delete_module_list(ids)
        cell.current_parent_version = action.id
        
    def request_plot_execution(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None:
            self.execute_plot(cell.current_parent_version)
            
    def execute_plot(self, version):
        self.vt_controller.change_selected_version(version)
        (results, _) = self.vt_controller.execute_current_workflow()
            
    def request_plot_configure(self, sheetName, row, col):
        from gui.uvcdat.plot import PlotProperties
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None:
            widget = self.get_plot_configuration(sheetName,row,col)
            plot_prop = PlotProperties.instance()
            plot_prop.set_controller(self)
            plot_prop.updateProperties(widget, sheetName,row,col)
            plot_prop.set_visible(True)
            
    def get_plot_configuration(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        helper = self.plot_manager.get_plot_helper(cell.plot.package)
        return helper.show_configuration_widget(self, 
                                                cell.current_parent_version,
                                                cell.plot)
        
    def update_variable(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None and len(cell.variables) == cell.plot.varnum:
            self.update_cell(sheetName, row, col)
    
    def update_plot(self, sheetName, row, col):
        cell = self.sheet_map[sheetName][(row,col)]
        if len(cell.variables) == cell.plot.varnum:
            self.update_cell(sheetName, row, col)

    def update_cell(self, sheetName, row, col):        
        cell = self.sheet_map[sheetName][(row,col)]
        vars = []
        for i in range(cell.plot.varnum):
            vars.append(self.defined_variables[cell.variables[i]])
        
        if (cell.plot is not None and
            len(cell.variables) == cell.plot.varnum):
            var_modules = []
            for var in vars:
                var_module = var.to_module(self.vt_controller)
                var_modules.append(var_module)
            # plot_module = plot.to_module(self.vt_controller)
            self.update_workflow(var_modules, cell, row, col)
            self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col, None, 
                      None, cell.plot.package, cell.current_parent_version)
            
    def update_workflow(self, var_modules, cell, row, column):
        helper = self.plot_manager.get_plot_helper(cell.plot.package)
        action = helper.build_plot_pipeline_action(self.vt_controller, 
                                                   cell.current_parent_version, 
                                                   var_modules, cell.plot,
                                                   row, column)
        print '### setting row/column:', row, column
        #notice that at this point the action was already performed by the helper
        # we need only to update the current parent version of the cell and 
        # execute the workflow if necessary.
        
        if action is not None:
            cell.current_parent_version = action.id
            
            if get_vistrails_configuration().uvcdat.autoExecute:
                self.execute_plot(cell.current_parent_version)
                
        
        #pipeline = self.vt_controller.vistrail.getPipeline(cell.current_parent_version)
        #print "Controller changed ", self.vt_controller.changed
        #controller = VistrailController()
        #controller.set_vistrail(self.vt_controller.vistrail,
        #                        self.vt_controller.locator)
        #controller.change_selected_version(cell.current_parent_version)
        #(results, _) = controller.execute_current_workflow()

    
    def plot_properties_were_changed(self, sheetName, row, col, action):
        if not action:
            return
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                cell.current_parent_version = action.id
                if get_vistrails_configuration().uvcdat.autoExecute:
                    self.execute_plot(cell.current_parent_version)
                self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col,
                      None, None, cell.plot.package, cell.current_parent_version)
        
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
