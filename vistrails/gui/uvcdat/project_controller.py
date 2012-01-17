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
import copy
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
from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper

class ProjectController(QtCore.QObject):
    """ProjecController is the class that interfaces between GUI actions in
    UVCDATWindow and SpreadsheetWindow and the VistrailController.
    
    """
    def __init__(self, vt_controller, name=''):
        QtCore.QObject.__init__(self)
        self.vt_controller = vt_controller
        self.name = name
        self.defined_variables = {}
        self.computed_variables = {}
        self.computed_variables_ops = {}
        self.sheet_map = {}
        self.plot_registry = get_plot_registry()
        self.plot_manager = get_plot_manager()
        
    def add_defined_variable(self, var):
        self.defined_variables[var.name] = var

    def rename_defined_variable(self, oldname, newname):
        """rename_defined_variable(oldname, newname) -> None
        This will rename a variable as long as oldname is present and newname
        is not already used. It will update the computed variables that depend
        on oldname accordingly.
        """
        if oldname in self.defined_variables:
            if (newname not in self.defined_variables and
                newname not in self.computed_variables):
                var = self.defined_variables[oldname]
                del self.defined_variables[oldname]
                var.name = newname
                self.add_defined_variable(var)
                #if there are any computed variables using the old one we need
                #to update them with the new name
                (res, cvars) = self.var_used_in_computed_variable(oldname)
                if res:
                    for c in cvars:
                        (vars, txt, st, varname) = self.computed_variables[c]
                        i = vars.index(oldname)
                        while i >= 0:
                            vars[i] = newname
                            try:
                                i = vars.index(oldname)
                            except ValueError:
                                i = -1
                        
            else:
                debug.warning("Variable was not renamed: name '%s' already used." %newname)
        elif oldname in self.computed_variables:
            if (newname not in self.defined_variables and
                newname not in self.computed_variables):
                (vars, txt, st, varname) = self.computed_variables[oldname]
                del self.computed_variables[oldname]
                self.computed_variables[newname] = (vars, txt, st, newname)
                #if there are any computed variables using the old one we need
                #to update them with the new name
                (res, cvars) = self.var_used_in_computed_variable(oldname)
                if res:
                    for c in cvars:
                        (vars, txt, st, varname) = self.computed_variables[c]
                        i = vars.index(oldname)
                        while i >= 0:
                            vars[i] = newname
                            try:
                                i = vars.index(oldname)
                            except ValueError:
                                i = -1
                if oldname in self.computed_variables_ops:
                    var = self.computed_variables_ops[oldname]
                    del self.computed_variables_ops[oldname]
                    var.name = newname
                    self.computed_variables_ops[newname] = var
            else:
                debug.warning("Variable was not renamed: name '%s' already used." %newname)
        else:
            debug.warning("Variable was not renamed: variable named '%s' not found." %oldname)
            
    def remove_defined_variable(self, name):
        """remove_defined_variable(name: str) -> None
        This will remove the variable only if it is not used to create other
        variables.
        
        """
        if name in self.defined_variables:
            (res, cvars) = self.var_used_in_computed_variable(name)
            if not res:
                del self.defined_variables[name]
        elif name in self.computed_variables:
            (res, cvars) = self.var_used_in_computed_variable(name)
            if not res:
                del self.computed_variables[name]
                if name in self.computed_variables_ops:
                    del self.computed_variables_ops[name]
        
    def var_used_in_computed_variable(self, varname):
        """var_used_in_computed_variable(varname:str) -> (bool, [var])
        If varname is used in other computed variables it will return True and 
        the list of variable names that depend on varname. Else, it will return
        False and an empty list.
        """
        result = False
        cvars = []
        for (vars, txt, st, cname) in self.computed_variables.itervalues():
            if varname in vars:
                result = True
                cvars.append(cname)
        return (result, cvars)
            
    def change_defined_variable_attribute(self, varname, attr, attrval):
        from packages.uvcdat_cdms.init import CDMSVariable
        if varname in self.defined_variables:
            var = self.defined_variables[varname]
            if var.attributes is None:
                var.attributes = {}
            var.attributes[attr] = attrval
        elif varname in self.computed_variables:
            if not varname in self.computed_variables_ops:
                var = CDMSVariable(name=varname)
                self.computed_variables_ops[varname] = var
            var = self.computed_variables_ops[varname]
            if var.attributes is None:
                var.attributes = {}
            var.attributes[attr] = attrval
            
    def remove_defined_variable_attribute(self, varname, attr):
        if varname in self.defined_variables:
            var = self.defined_variables[varname]
            if var.attributes is not None and attr in var.attributes:
                del var.attributes[attr]
        elif varname in self.computed_variables:
            if varname in self.computed_variables_ops:
                var = self.computed_variables_ops[varname]
                if var.attributes is not None and attr in var.attributes:
                    del var.attributes[attr]
                
    def change_defined_variable_axis_attribute(self, varname, axname, attr, 
                                               attrval):
        from packages.uvcdat_cdms.init import CDMSVariable
        if varname in self.defined_variables:
            var = self.defined_variables[varname]
            if var.axisAttributes is None:
                var.axisAttributes = {}
            if axname not in var.axisAttributes:
                var.axisAttributes[axname] = {}    
            var.axisAttributes[axname][attr] = attrval
        elif varname in self.computed_variables:
            if not varname in self.computed_variables_ops:
                var = CDMSVariable(name=varname)
                self.computed_variables_ops[varname] = var
            var = self.computed_variables_ops[varname]
            if var.axisAttributes is None:
                var.axisAttributes = {}
            if axname not in var.axisAttributes:
                var.axisAttributes[axname] = {}    
            var.axisAttributes[axname][attr] = attrval
                
    def remove_defined_variable_axis_attribute(self, varname, axname, attr):
        if varname in self.defined_variables:
            var = self.defined_variables[varname]
            if var.axisAttributes and axname in var.axisAttributes:
                if var.axisAttributes[axname] and attr in var.axisAttributes[axname]:
                    del var.axisAttributes[axname][attr]
                
    def change_defined_variable_time_bounds(self, varname, timebounds):
        if varname in self.defined_variables:
            var = self.defined_variables[varname]
            var.timeBounds = timebounds
           
    def calculator_command(self, vars, txt, st, varname):
        #if the variable was added to defined_variables, we have to remove it 
        #from there
        self.remove_defined_variable(varname)
        self.computed_variables[varname] = (vars, txt, st, varname)
        
    def copy_computed_variable(self, oldname, newname, axes=None, 
                               axesOperations=None):
        from packages.uvcdat_cdms.init import CDMSVariable
        if oldname in self.computed_variables:
            (vars, txt, st, varname) = self.computed_variables[oldname]
            self.computed_variables[newname] = (vars, txt, st, newname)
            if oldname in self.computed_variables_ops:
                oldops = self.computed_variables_ops[oldname]
                self.computed_variables_ops[newname] = copy.copy(oldops)
                self.computed_variables_ops[newname].name = newname
            if axes is not None and axesOperations is not None:
                if newname not in self.computed_variables_ops:
                    var = CDMSVariable(name=newname)
                    self.computed_variables_ops[newname] = var
                self.computed_variables_ops[newname].axes = axes
                self.computed_variables_ops[newname].axesOperations = axesOperations
                  
                
    def emit_defined_variable(self, var):
        from packages.uvcdat_cdms.init import CDMSVariable, CDMSVariableOperation
        from packages.uvcdat_pv.init import PVVariable
        from api import _app
        if isinstance(var, CDMSVariable):
            _app.uvcdatWindow.dockVariable.widget().addVariable(var.to_python())
        elif isinstance(var, PVVariable):
            _app.uvcdatWindow.dockVariable.widget().addVariable(var.name, type_='PARAVIEW')
        elif isinstance(var, CDMSVariableOperation):
            _app.uvcdatWindow.dockVariable.widget().addVariable(var.to_python())
            
    def load_variables_from_modules(self, var_modules, helper):
        for varm in var_modules:
            varname = helper.get_value_from_function(varm, 'name')
            if varname not in self.defined_variables:
                var = varm.module_descriptor.module.from_module(varm)
                self.defined_variables[varname] = var
                self.emit_defined_variable(var)
                
    def load_computed_variables_from_modules(self, op_modules, info, op_info, helper):
        for (opm,op) in op_modules:
            varname = helper.get_value_from_function(opm, 'varname')
            if (varname not in self.defined_variables and
                varname not in self.computed_variables):
                self.computed_variables[varname] = info[varname]
                if varname in op_info:
                    self.computed_variables_ops[varname] = op_info[varname]
                self.emit_defined_variable(op)
                
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
        self.connect(tabController, QtCore.SIGNAL("request_plot_source"),
                     self.request_plot_source)
        self.connect(tabController, QtCore.SIGNAL("cell_deleted"),
                     self.clear_cell)
        self.connect(tabController, QtCore.SIGNAL("sheet_size_changed"),
                     self.sheetsize_was_changed)
        self.connect(tabController, QtCore.SIGNAL("current_cell_changed"),
                     self.current_cell_changed)
        
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
        self.disconnect(tabController, QtCore.SIGNAL("request_plot_source"),
                     self.request_plot_source)
        self.disconnect(tabController, QtCore.SIGNAL("cell_deleted"),
                     self.clear_cell)
        self.disconnect(tabController, QtCore.SIGNAL("sheet_size_changed"),
                     self.sheetsize_was_changed)
        self.disconnect(tabController, QtCore.SIGNAL("current_cell_changed"),
                     self.current_cell_changed)
        
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
        """vis_was_dropped(info: (controller, version, sheetName, row, col) """
        (controller, version, sheetName, row, col, plot_type) = info
        
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
        pipeline = controller.vistrail.getPipeline(version)

        if controller == self.vt_controller:
            #controllers are the same, just point cell to the version
            cell.current_parent_version = version
            helper.load_pipeline_in_location(pipeline,self.vt_controller,
                                             sheetName, row, col, plot_type, cell)
        else:
            #copy pipeline to this controller.vistrail
            action = helper.copy_pipeline_to_other_location(pipeline, self.vt_controller,
                                                            sheetName, row, col, 
                                                            plot_type, cell)
            #cell.current_parent_version was updated in copy_pipeline_to_other_location
            
        #check if a new var was added:
        self.search_and_emit_new_variables(cell)
                    
        if controller == self.vt_controller:
            self.execute_plot_pipeline(pipeline, cell)
        else:
            self.execute_plot(cell.current_parent_version)

        self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col, None, None,
                  plot_type, cell.current_parent_version)
        
    def search_and_emit_new_variables(self, cell):
        """search_and_emit_new_variables(cell) -> None
        It will go through the variables in the cell and define them if they are 
        not defined. Sometimes it is necessary to reconstruct the variable 
        because some workflows are not using the Variable modules yet. """
        not_found = False
        for var in cell.variables:
            if var not in self.defined_variables:
                not_found = True
        if not_found:
            from packages.uvcdat.init import Variable
            from packages.uvcdat_pv.init import PVVariable
            from packages.uvcdat_cdms.init import CDMSVariable, CDMSVariableOperation
            helper = self.plot_manager.get_plot_helper(cell.plot.package)
            pipeline = self.vt_controller.vistrail.getPipeline(cell.current_parent_version)
            var_modules = helper.find_modules_by_type(pipeline, 
                                                      [Variable])
            op_modules = helper.find_modules_by_type(pipeline, 
                                                     [CDMSVariableOperation])
            op_tuples = []
            if len(var_modules) > 0:
                self.load_variables_from_modules(var_modules, helper)
            if len(op_modules) > 0:
                info = {}
                op_info = {}
                for opm in op_modules:
                    varname = helper.get_variable_name_from_module(opm)
                    mvars= helper.find_variables_connected_to_operation_module(self.vt_controller,
                                                                               pipeline, opm.id)
                    ivars= [helper.get_variable_name_from_module(iv) for iv in mvars]
                    op = opm.module_descriptor.module.from_module(opm)
                    opvars = []
                    for mv in mvars:
                        var = mv.module_descriptor.module.from_module(mv)
                        var.var = var.to_python()
                        opvars.append(var)
                    op.set_variables(opvars)
                    op_tuples.append((opm,op))
                    txt = opm.get_annotation_by_key("__desc__").value
                    info[varname] = (ivars, txt, op.python_command, varname)
                    if (op.axes is not None or op.axesOperations is not None or
                        op.attributes is not None or op.axisAttributes is not None or
                        op.timeBounds is not None):
                        #we store the attributes in a variable
                        op_info[varname] = CDMSVariable(name=varname, axes=op.axes,
                                               axesOperations=op.axesOperations,
                                               attributes=op.attributes,
                                               axisAttributes=op.axisAttributes,
                                               timeBounds=op.timeBounds)
                self.load_computed_variables_from_modules(op_tuples, info, op_info, 
                                                          helper)
            if len(var_modules) == 0:
                #when all workflows are updated to include the variable modules.
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
                    aliases = {}
                    for a in pipeline.aliases:
                        aliases[a] = pipeline.get_alias_str_value(a)
                            
                    if cell.plot.serializedConfigAlias:
                        cell.plot.unserializeAliases(aliases)
                        
                    for i in range(len(cell.variables)):
                        filename = aliases[cell.plot.files[i]]
                        varname = aliases[cell.plot.vars[i]]
                        axes = None
                        if len(cell.plot.axes) > i:
                            axes = aliases[cell.plot.axes[i]]
                        if varname not in self.defined_variables:
                            var =  CDMSVariable(filename=filename, 
                                                name=varname, axes=axes)
                            self.defined_variables[varname] = var
                            self.emit_defined_variable(var)
        
    def clear_cell(self, sheetName, row, col):
        if sheetName in self.sheet_map:
            if (row,col) in self.sheet_map[sheetName]:
                cell = self.sheet_map[sheetName][(row,col)]
                self.reset_workflow(cell)
                cell.variables = []
                cell.plot = None
                cell.template = None
                self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col)
                self.update_plot_configure(sheetName, row, col)

    def sheetsize_was_changed(self, sheet, dim):
        self.emit(QtCore.SIGNAL("sheet_size_changed"), sheet, dim)

    def current_cell_changed(self, sheetName, row, col):
        self.update_plot_configure(sheetName, row, col)

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
        from gui.vistrails_window import _app
        _app.notify('execution_updated')
            
    def execute_plot_pipeline(self, pipeline, cell):
        from packages.spreadsheet.spreadsheet_execute import executePipelineWithProgress
        executePipelineWithProgress(pipeline, 'Execute Cell',
                                    locator=self.vt_controller.locator,
                                    current_version=cell.current_parent_version,
                                    reason='UV-CDAT Drop Visualization')
        from gui.vistrails_window import _app
        _app.notify('execution_updated')
        
    def request_plot_configure(self, sheetName, row, col):
        from gui.uvcdat.plot import PlotProperties
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None:
            widget = self.get_plot_configuration(sheetName,row,col)
            plot_prop = PlotProperties.instance()
            plot_prop.set_controller(self)
            plot_prop.updateProperties(widget, sheetName,row,col)
            plot_prop.set_visible(True)
            
    def update_plot_configure(self, sheetName, row, col):
        from gui.uvcdat.plot import PlotProperties
        cell = self.sheet_map[sheetName][(row,col)]
        plot_prop = PlotProperties.instance()
        if cell.plot is not None:
            widget = self.get_plot_configuration(sheetName,row,col)
            plot_prop.set_controller(self)
            plot_prop.updateProperties(widget, sheetName,row,col)
        else:
            plot_prop.set_controller(None)
            plot_prop.updateProperties(None, sheetName,row,col)
                
    def get_python_script(self, sheetName, row, col):
        script = None
        cell = self.sheet_map[sheetName][(row,col)]
        if cell.plot is not None:
            helper = self.plot_manager.get_plot_helper(cell.plot.package)
            script = helper.build_python_script_from_pipeline(self.vt_controller, 
                                                              cell.current_parent_version, 
                                                              cell.plot)
        return script
        
    def request_plot_source(self, sheetName, row, col):
        from gui.uvcdat.plot_source import PlotSource
        source = self.get_python_script(sheetName, row, col)
        plot_source = PlotSource.instance()
        plot_source.showSource(source, sheetName, row, col)
        plot_source.show()
            
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
        def get_var_module(varname):
            if varname not in self.computed_variables:
                var = self.defined_variables[varname]
                return var.to_module(self.vt_controller)
            else:
                (_vars, txt, st, name) = self.computed_variables[varname] 
                opvar = None
                if varname in self.computed_variables_ops:
                    opvar = self.computed_variables_ops[varname]   
                varms = [] 
                for v in _vars:
                    varms.append(get_var_module(v))
                
                res = CDMSPipelineHelper.build_variable_operation_pipeline(self.vt_controller,
                                                                            cell.current_parent_version,
                                                                            varms, 
                                                                            txt, 
                                                                            st,
                                                                            varname,
                                                                            opvar)
                if type(res) == type((1,)):
                    actions = res[1]
                    action = actions[-1]
                    if action:
                        cell.current_parent_version = action.id 
                    varm = res[0]
                else:
                    varm = res
                return varm
                        
        vars = []
        for i in range(cell.plot.varnum):
            vars.append(cell.variables[i])
        
        if (cell.plot is not None and
            len(cell.variables) == cell.plot.varnum):
            var_modules = []
            for var in vars:
                res = get_var_module(var)
                var_modules.append(res)
            
            # plot_module = plot.to_module(self.vt_controller)
            self.update_workflow(var_modules, cell, sheetName, row, col)
            self.emit(QtCore.SIGNAL("update_cell"), sheetName, row, col, None, 
                      None, cell.plot.package, cell.current_parent_version)
            
    def update_workflow(self, var_modules, cell, sheetName, row, column):
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
                self.update_plot_configure(sheetName, row, column)
                
        
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
