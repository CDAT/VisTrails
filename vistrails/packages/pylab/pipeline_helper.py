from init import CDMSData
from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper
from packages.uvcdat_cdms.init import CDMSVariableOperation, CDMSVariable
from core.uvcdat.plotmanager import get_plot_manager

import api
import core.db.io
from core import debug
from gui.uvcdat.plot_configuration import AliasesPlotWidget

class MatplotlibPipelineHelper(CDMSPipelineHelper):
    
    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plot_objs, 
                                   row, col, templates=[]):
        """build_plot_pipeline_action(controller: VistrailController,
                                      version: long,
                                      var_modules: [list of modules],
                                      plot_objs: [list of Plot objects],
                                      row: int,
                                      col: int,
                                      templates: [list of str]) -> Action 
        
        This function will build the complete workflow and add it to the
        provenance. You should make sure to update the state of the controller
        so its current_version is version before adding the VisTrails action to 
        the provenance.
        row and col contain the position of the cell in the spreadsheet the 
        workflow should be displayed. 
        """
        plot_obj = plot_objs[0] 
        plot_obj.current_parent_version = version
        plot_obj.current_controller = controller
        controller.change_selected_version(version)
        
        if len(var_modules) == plot_obj.varnum:
            ops = []
            pip_str = core.db.io.serialize(plot_obj.workflow)
            controller.paste_modules_and_connections(pip_str, (0.0,0.0))
            version = controller.current_version
            pipeline = controller.vistrail.getPipeline(version)
            plot_module = MatplotlibPipelineHelper.find_module_by_name(pipeline, 'CDMSData')
            aliases = {}
            for j in range(plot_obj.cellnum):
                if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                    aliases[plot_obj.cells[j].row_name] = str(row+1)
                    aliases[plot_obj.cells[j].col_name] = str(col+1+j)
                elif plot_obj.cells[j].address_name:
                    aliases[plot_obj.cells[j].address_name] = "%s%s" % ( chr(ord('A') + col+j ), row+1)
            for a,w in plot_obj.alias_widgets.iteritems():
                try:    aliases[a] = w.contents()
                except Exception, err: debug.debug("Error updating alias %s:" % str( a ), str(err))
            
            action = MatplotlibPipelineHelper.addParameterChangesFromAliasesAction(controller.current_pipeline,  
                                                                          controller,  
                                                                          controller.vistrail, 
                                                                          controller.current_version, 
                                                                          aliases)
            version = action.id
            added_vars = []
            for i in range(len(var_modules)):
                if issubclass(var_modules[i].module_descriptor.module, CDMSVariable):
                    conn = controller.create_connection(var_modules[i], 'self',
                                                plot_module, 'variable')
                else:
                    conn = controller.create_connection(var_modules[i], 'output_var',
                                                plot_module, 'variable')
                ops.append(('add', conn))
                if plot_obj.varnum > 1:
                    if i + 1 < len(var_modules):
                        idx = i+1
                    else:
                        idx = i
                    if issubclass(var_modules[idx].module_descriptor.module, CDMSVariable):
                        conn2 = controller.create_connection(var_modules[idx], 'self',
                                                     plot_module, 'variable2')
                        if var_modules[idx] not in added_vars:
                            ops.append(('add', var_modules[idx]))
                            added_vars.append(var_modules[idx])
                    else:
                        conn2 = controller.create_connection(var_modules[idx], 'output_var',
                                                     plot_module, 'variable')
                    ops.append(('add', conn2))
            action2 = core.db.action.create_action(ops)
            controller.change_selected_version(version)
            controller.add_new_action(action2)
            controller.perform_action(action2)
            return action2
    
    @staticmethod
    def update_plot_pipeline_action(controller, version, var_modules, plot_objs,
                                    row, col, templates=[]):
        """update_plot_pipeline_action(controller: VistrailController,
                                      version: long,
                                      var_modules: [list of modules],
                                      plot_objs: [list of Plot objects],
                                      row: int,
                                      col: int,
                                      templates: [list of str]) -> Action 
        
        This function will create the complete workflow and add it to the
        provenance. You should make sure to update the state of the controller
        so its current_version is version before adding the VisTrails action to 
        the provenance.
        row and col contain the position of the cell in the spreadsheet the 
        workflow should be displayed.
         
        """
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        # This considers that there's only one type of plot
        plot_obj = plot_objs[0]
        added_vars = []
        if controller is None:
            controller = api.get_current_controller()
            version = 0L
        action = MatplotlibPipelineHelper.remove_variables_from_pipeline_action(controller, version)
        version = action.id
        pipeline = controller.vistrail.getPipeline(version)
        ops = []
        plot_modules = MatplotlibPipelineHelper.find_modules_by_type(pipeline, [CDMSData])
        for i, plot_module in enumerate(plot_modules):
            if i < len(var_modules):    
                if issubclass(var_modules[i].module_descriptor.module, CDMSVariable):
                    ops.append(('add', var_modules[i]))
                    added_vars.append(var_modules[i])
        
                if issubclass(var_modules[i].module_descriptor.module, CDMSVariable):
                    conn = controller.create_connection(var_modules[i], 'self',
                                                plot_module, 'variable')
                else:
                    conn = controller.create_connection(var_modules[i], 'output_var',
                                                plot_module, 'variable')
                ops.append(('add', conn))
                var_num = int(plot_obj.varnum)
                if var_num > 1:
                    if i + 1 < len(var_modules):
                        idx = i+1
                    else:
                        idx = i
                    if issubclass(var_modules[idx].module_descriptor.module, CDMSVariable):
                        conn2 = controller.create_connection(var_modules[idx], 'self',
                                                     plot_module, 'variable2')
                        if var_modules[idx] not in added_vars:
                            ops.append(('add', var_modules[idx]))
                            added_vars.append(var_modules[idx])
                    else:
                        conn2 = controller.create_connection(var_modules[idx], 'output_var',
                                                     plot_module, 'variable')
                    ops.append(('add', conn2))
            else:
                #there are fewer variables than plots. We will use the last
                #variable in the list
                if issubclass(var_modules[-1].module_descriptor.module, CDMSVariable):
                    if var_modules[-1] not in added_vars:
                        ops.append(('add', var_modules[-1]))
                        added_vars.append(var_modules[-1])
                ops.append(('add', plot_module)) 
        
                if issubclass(var_modules[-1].module_descriptor.module, CDMSVariable):
                    conn = controller.create_connection(var_modules[-1], 'self',
                                                plot_module, 'variable')
                else:
                    conn = controller.create_connection(var_modules[-1], 'output_var',
                                                plot_module, 'variable')
                ops.append(('add', conn))
                var_num = int(plot_obj.varnum)
                if var_num > 1:
                    if issubclass(var_modules[-1].module_descriptor.module, CDMSVariable):
                        conn2 = controller.create_connection(var_modules[-1], 'self',
                                                     plot_module, 'variable2')
                        if var_modules[-1] not in added_vars:
                            ops.append(('add', var_modules[-1]))
                            added_vars.append(var_modules[-1])
                        
                    else:
                        conn2 = controller.create_connection(var_modules[-1], 'output_var',
                                                     plot_module, 'variable')
                    ops.append(('add', conn2))
             
        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
    
    @staticmethod
    def load_pipeline_in_location(pipeline, controller, sheetName, row, col, 
                                 plot_type, cell):
        """load_pipeline_in_location(pipeline: Pipeline, 
                                     controller: VistrailController,
                                     sheetName: str, 
                                     row: int, col: int,
                                     plot_type:,
                                     cell: InstanceObject) -> None        
        This function will load the workflow in another location. It will not
        update provenance, because provenance already exists. So it will 
        basically update the CellLocation modules of the workflow with the new
        locations in place without generating actions.
        It will also update the cell object with the variables and plot types so
        this information must also be extracted from the workflow
         
        """
        
        #for now this helper will change the location in place
        #based on the alias dictionary
        controller.change_selected_version(cell.current_parent_version)
        plot_obj = MatplotlibPipelineHelper.get_plot_by_vistrail_version(plot_type, 
                                                                   controller.vistrail,
                                                                   controller.current_version)
        plot_obj.current_parent_version = cell.current_parent_version
        plot_obj.current_controller = controller
        cell.plots = [plot_obj]
            
        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                pipeline.set_alias_str_value(plot_obj.cells[j].row_name, str(row+1))
                pipeline.set_alias_str_value(plot_obj.cells[j].col_name, str(col+1+j))
            elif plot_obj.cells[j].address_name:
                pipeline.set_alias_str_value(plot_obj.cells[j].address_name,
                                             "%s%s"%(chr(ord('A') + col+j),
                                                                  row+1))        
        #this will update the variables
        for i in range(plot_obj.varnum):
            cell.variables.append(pipeline.get_alias_str_value(plot_obj.vars[i])) 
            
    @staticmethod
    def show_configuration_widget(controller, version, plot_objs=[]):
        #FIXME: This will create the widget for the first plot object
        return CDMSAliasesPlotWidget(controller,version,plot_objs[0])
    
    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot_objs=[]):
        from api import load_workflow_as_function
        text = "from api import load_workflow_as_function\n"
        if len(plot_objs) > 0:
            text += "proj_file = '%s'\n"%controller.get_locator().name
            text += "vis_id = %s\n"%version
            text += "vis = load_workflow_as_function(proj_file, vis_id)\n"
            vis = load_workflow_as_function(controller.get_locator().name, version)
            doc = vis.__doc__
            lines = doc.split("\n")
            for line in lines:
                text += "# %s\n"%line                 
            return text
        
    @staticmethod    
    def addParameterChangesFromAliasesAction(pipeline, controller, vistrail, parent_version, aliases):
        param_changes = []
        newid = parent_version
        #print "MatplotlibPipelineHelper.addParameterChangesFromAliasesAction()"
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
                    new_param = controller.create_updated_parameter(old_param, 
                                                                    value)
                    if new_param is not None:
                        op = ('change', old_param, new_param, 
                              function.vtType, function.real_id)
                        param_changes.append(op)
#                        print "Added parameter change for alias=%s, value=%s" % ( k, value  )
                    else:
                        debug.debug("Matplotlib Plot type: Change parameter %s was not generated"%k)
            else:
                debug.debug( "CDAT Package: Alias %s does not exist in pipeline" % (k) )
        action = None
        if len(param_changes) > 0:
            action = core.db.action.create_action(param_changes)
            controller.change_selected_version(parent_version)
            controller.add_new_action(action)
            controller.perform_action(action)
        return action
    
    @staticmethod
    def are_workflows_compatible(vistrail_a, vistrail_b, version_a, version_b):
        #FIXME:
        # This assumes that the workflows will be different by at most variable
        # modules added to the pipeline. If modules can be deleted from original
        # vistrails, then this function needs to be updated.
        diff_versions = ((vistrail_a, version_a), (vistrail_b, version_b))
        diff = core.db.io.get_workflow_diff(*diff_versions)
        (p1, p2, v1Andv2, heuristicMatch, v1Only, v2Only, paramChanged) = diff
        if len(v1Only) == 0 and len(v2Only)==0:
            return True
        elif len(v2Only) == 0 and len(v1Only) > 0:
            moduletypes =  (CDMSVariable, CDMSVariableOperation)
            invalid = []
            for mid in v1Only:
                module = p1.modules[mid]
                desc = module.module_descriptor
                if not issubclass(desc.module, moduletypes):
                    invalid.append(module)
            if len(invalid) == 0:
                return True
        return False
    
    @staticmethod
    def get_plot_by_vistrail_version(plot_type, vistrail, version):
        from core.uvcdat.plotmanager import get_plot_manager
        plots = get_plot_manager()._plot_list[plot_type]
        vistrail_a = vistrail
        version_a = version
        if vistrail_a is None or version_a <=0:
            return None
        pipeline = vistrail.getPipeline(version)
        for pl in plots.itervalues():
            vistrail_b = pl.plot_vistrail
            version_b = pl.workflow_version
            if vistrail_b is not None and version_b > 0:
                if (MatplotlibPipelineHelper.are_workflows_compatible(vistrail_a, vistrail_b, 
                                                                version_a, version_b) and
                    len(pipeline.aliases) == len(pl.workflow.aliases)):
                    return pl
        return None

    @staticmethod
    def create_plot_objs_from_pipeline(pipeline, plot_type):
        plot_objs = []
        helper = MatplotlibPipelineHelper
        # get to from cell?
        for plot_module in helper.find_plot_modules(pipeline):
            plot_objs.append(get_plot_manager().get_plot('Matplotlib', plot_module.name[3:]))
        return plot_objs
    
    @staticmethod
    def find_plot_modules(pipeline):
        #find plot modules in the order they appear in the Cell
        res = []
        cellModule = MatplotlibPipelineHelper.find_module_by_name(pipeline, 'MplFigureCell')
        figureModuleIds = pipeline.get_inputPort_modules(cellModule.id,'FigureManager')
        for figId in figureModuleIds:
            plotModuleIds = pipeline.get_inputPort_modules(figId,'Script')
            for plotId in plotModuleIds:
                res.append(pipeline.modules[plotId])
        return res
    
class CDMSAliasesPlotWidget(AliasesPlotWidget):
    def __init__(self,controller, version, plot_obj, parent=None):
        AliasesPlotWidget.__init__(self,controller, version, plot_obj, parent)
        
    def updateVistrail(self):
        aliases = {}
        pipeline = self.controller.vistrail.getPipeline(self.version)
        for name in pipeline.aliases:
            aliases[name] = pipeline.get_alias_str_value(name)
        for a,w in self.alias_widgets.iteritems():
            aliases[a] = w.contents()
        
        action = MatplotlibPipelineHelper.addParameterChangesFromAliasesAction(self.controller.current_pipeline,  
                                                                          self.controller,  
                                                                          self.controller.vistrail, 
                                                                          self.controller.current_version, 
                                                                          aliases)
        
        return action