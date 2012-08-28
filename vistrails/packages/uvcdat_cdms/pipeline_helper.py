from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from core.uvcdat.plot_registry import get_plot_registry
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import Module
from core.uvcdat.plotmanager import get_plot_manager
from packages.spreadsheet.basic_widgets import CellLocation, SpreadsheetCell
        
import core.db.action
import core.db.io
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot, pyqtSignal
from init import CDMSPlot, CDMSVariable, CDMSCell, CDMSVariableOperation, \
       CDMSUnaryVariableOperation, CDMSBinaryVariableOperation, \
       CDMSNaryVariableOperation
from widgets import GraphicsMethodConfigurationWidget
from gui.theme import CurrentTheme
from gui.common_widgets import QDockPushButton
from gui.uvcdat.dockplot import PlotTreeWidgetItem
from gui.uvcdat.uvcdatCommons import plotTypes, gmInfos
import api

class CDMSPipelineHelper(PlotPipelineHelper):
    @staticmethod
    def show_configuration_widget(controller, version, plot_objs=[]):
        pipeline = controller.vt_controller.vistrail.getPipeline(version)
        plots = CDMSPipelineHelper.find_plot_modules(pipeline)
        vars = CDMSPipelineHelper.find_modules_by_type(pipeline, 
                                                       [CDMSVariable,
                                                        CDMSVariableOperation])
        return CDMSPlotWidget(controller,version,plots,vars)
    
    @staticmethod
    def find_plot_modules(pipeline):
        #find plot modules in the order they appear in the Cell
        res = []
        cell = CDMSPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
        plots = pipeline.get_inputPort_modules(cell.id,'plot')
        for plot in plots:
            res.append(pipeline.modules[plot])
        return res
                
    @staticmethod
    def find_variables_connected_to_plot_module(controller, pipeline, plot_id):
        conns = controller.get_connections_to(pipeline, [plot_id], 
                                              port_name="variable")
        vars = []
        for conn in conns:
            vars.append(pipeline.modules[conn.source.moduleId])
        return vars
    
    @staticmethod
    def find_variables_connected_to_operation_module(controller, pipeline, op_id):
        module = pipeline.modules[op_id]
        vars = []
        unary = CDMSPipelineHelper.find_variables_connected_to_unary_operation_module
        binary = CDMSPipelineHelper.find_variables_connected_to_binary_operation_module
        n_ary = CDMSPipelineHelper.find_variables_connected_to_n_ary_operation_module
        if issubclass(module.module_descriptor.module, CDMSUnaryVariableOperation):
            vars = unary(controller, pipeline, op_id)
        elif issubclass(module.module_descriptor.module, CDMSBinaryVariableOperation):
            vars = binary(controller, pipeline, op_id)
        elif issubclass(module.module_descriptor.module, CDMSNaryVariableOperation):
            vars = n_ary(controller, pipeline, op_id)
        return vars
    
    @staticmethod
    def find_variables_connected_to_unary_operation_module(controller, pipeline, op_id):
        conns = controller.get_connections_to(pipeline, [op_id], 
                                              port_name="input_var")
        
        vars = []
        for conn in conns:
            vars.append(pipeline.modules[conn.source.moduleId])
        return vars
    
    @staticmethod
    def find_variables_connected_to_binary_operation_module(controller, pipeline, op_id):
        conns = controller.get_connections_to(pipeline, [op_id], 
                                              port_name="input_var1")
        conns.extend(controller.get_connections_to(pipeline, [op_id], 
                                              port_name="input_var2"))
        
        vars = []
        for conn in conns:
            vars.append(pipeline.modules[conn.source.moduleId])
        return vars
    
    @staticmethod
    def find_variables_connected_to_n_ary_operation_module(controller, pipeline, op_id):
        conns = controller.get_connections_to(pipeline, [op_id], 
                                              port_name="input_vars")        
        vars = []
        for conn in conns:
            vars.append(pipeline.modules[conn.source.moduleId])
        return vars

    @staticmethod
    def create_plot_objs_from_pipeline(pipeline, plot_type):
        plot_objs = []
        helper = CDMSPipelineHelper
        # get to from cell?
        for pl_module in helper.find_plot_modules(pipeline):
            print "pl_module:", pl_module.id, pl_module.name
            gmName = helper.get_graphics_method_name_from_module(pl_module)
            ptype = helper.get_plot_type_from_module(pl_module)
            print "PLOT TYPE:", plot_type, ptype, gmName, \
                get_plot_manager().get_plot(plot_type, ptype, 
                                           gmName)
            plot_objs.append(get_plot_manager().get_plot(plot_type, ptype, 
                                                          gmName))
        return plot_objs
    
    @staticmethod
    def create_plot_module(controller, plot_type, plot_gm):
        reg = get_module_registry()
        ops = []
        plot_descriptor = reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 
                                       'CDMS' + plot_type)
        desc = plot_descriptor.module
        plot_module = controller.create_module_from_descriptor(plot_descriptor)
        plot_functions =  [('graphicsMethodName', [plot_gm])]
        initial_values = desc.get_initial_values(plot_gm)
        for attr in desc.gm_attributes:
            plot_functions.append((attr,[getattr(initial_values,attr)]))
            
        functions = controller.create_functions(plot_module,plot_functions)
        for f in functions:
            plot_module.add_function(f)
        return plot_module
    
    @staticmethod
    def get_input_port_name(num_op_vars, var_num):
        if num_op_vars == 1:
            return 'input_var'
        elif num_op_vars == 2:
            return 'input_var%d' % (var_num + 1)
        else:
            return 'input_vars'

    @staticmethod
    def get_plot_input_port_name(num_plot_vars, var_num):
        if num_plot_vars == 1:
            return 'variable'
        elif num_plot_vars == 2:
            if var_num == 0:
                return 'variable'
            else:
                return 'variable2'
        else:
            # FIXME no case for this right now
            return 'variable'

    @staticmethod
    def get_output_port_name(module):
        if issubclass(module, CDMSVariable):
            return 'self'
        else:
            return 'output_var'

    @staticmethod
    def build_variable_operation_pipeline(controller, version, vars, txt, st, 
                                          varname, varop=None):
        controller.change_selected_version(version)
        axes = None
        axesOperations = None
        attributes = None
        axisAttributes = None
        timeBounds = None
        if varop is not None:
            axes = varop.axes
            axesOperations = varop.axesOperations
            attributes = varop.attributes
            axisAttributes = varop.axisAttributes
            timeBounds = varop.timeBounds
            
        if len(vars) == 1:
            op_class = CDMSUnaryVariableOperation
        elif len(vars) == 2:
            op_class = CDMSBinaryVariableOperation
        else:
            op_class = CDMSNaryVariableOperation
        op_class_inst = op_class(varname=varname,
                                 python_command=st,
                                 axes=axes,
                                 axesOperations=axesOperations,
                                 attributes=attributes,
                                 axisAttributes=axisAttributes,
                                 timeBounds=timeBounds)
        op_module = op_class_inst.to_module(controller)
        ops = []
        ops.append(('add', op_module))
        
        for i, var in enumerate(vars):
            oport = CDMSPipelineHelper.get_output_port_name(
                var.module_descriptor.module)
            iport = CDMSPipelineHelper.get_input_port_name(len(vars), i)
            conn = controller.create_connection(var, oport, op_module, iport)
            ops.append(('add', conn))

        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        actions = [action]
        controller.change_selected_version(action.id)
        action = controller.add_annotation(('__desc__', txt), op_module.id)
        actions.append(action)
        return (op_module, actions)
                
    @staticmethod
    def connect_variables_to_plots(controller, var_modules, plot_modules):
        ops = []
        var_idx = 0
        for i, plot_module in enumerate(plot_modules):
            plot_type = plot_module.module_descriptor.module.plot_type
            var_num = int(gmInfos[plot_type]["nSlabs"])
            for j in xrange(var_num):
                if var_idx < len(var_modules):
                    idx = i
                else:
                    # this is not quite right, but this what was done before
                    # it is not clear what to do when two variables
                    # are missing for example
                    idx = -1

                oport = CDMSPipelineHelper.get_output_port_name(
                    var_modules[idx].module_descriptor.module)
                iport = CDMSPipelineHelper.get_plot_input_port_name(var_num, j)
                conn = controller.create_connection(var_modules[idx], oport,
                                                    plot_module, iport)
                ops.append(('add', conn))
                var_idx += 1
        return ops

    @staticmethod
    def create_actions_from_plot_objs(controller, var_modules, cell_module, 
                                      plot_objs, templates, added_vars, istart=0):
        reg = get_module_registry()
        ops = []
        plot_modules = []
        var_idx = 0
        for i, plot_obj in enumerate(plot_objs):
            if i < istart:
                continue
            plot_type = plot_obj.parent
            plot_gm = plot_obj.name
            plot_descriptor = reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 
                                                         'CDMS' + plot_type)
            desc = plot_descriptor.module
            plot_module = controller.create_module_from_descriptor(plot_descriptor)
            plot_functions =  [('graphicsMethodName', [plot_gm])]
            if i < len(templates):
                plot_functions.append(('template', [templates[i]]))
            elif i >= len(templates) and len(templates) > 0:
                plot_functions.append(('template', [templates[-1]]))

            initial_values = desc.get_initial_values(plot_gm)
            for attr in desc.gm_attributes:
                plot_functions.append((attr,[getattr(initial_values,attr)]))
            
            functions = controller.create_functions(plot_module,plot_functions)
            for f in functions:
                plot_module.add_function(f)

            plot_modules.append(plot_module)
            ops.append(('add', plot_module))

            cell_conn = controller.create_connection(plot_module, 'self',
                                                     cell_module, 'plot')
            ops.append(('add', cell_conn))
            ops.extend(
                CDMSPipelineHelper.connect_variables_to_plots(controller,
                                                              var_modules,
                                                              plot_modules))
        return ops
    
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
        
        This function will create the complete workflow and add it to the
        provenance. You should make sure to update the state of the controller
        so its current_version is version before adding the VisTrails action to 
        the provenance.
        row and col contain the position of the cell in the spreadsheet the 
        workflow should be displayed.
        It will create plot overlays based on the list of plot_objs given. 
        """
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        if controller is None:
            controller = api.get_current_controller()
            version = 0L
        added_vars = []
        reg = get_module_registry()
        cell_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 'CDMSCell'))
        ops = [('add', cell_module)]
        ops2 = CDMSPipelineHelper.create_actions_from_plot_objs(controller, 
                                                                var_modules, 
                                                                cell_module, 
                                                                plot_objs, 
                                                                templates,
                                                                added_vars)
        ops.extend(ops2)
        loc_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
                                       'CellLocation'))
        functions = controller.create_functions(loc_module,
            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        for f in functions:
            loc_module.add_function(f)
        loc_conn = controller.create_connection(loc_module, 'self',
                                                        cell_module, 'Location')
        ops.extend([('add', loc_module),
                    ('add', loc_conn)])
        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
    
    @staticmethod
    def remove_variables_from_pipeline_action(controller, version):
        pipeline = controller.vistrail.getPipeline(version)
        
        variable_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSVariable,
                                                                          CDMSVariableOperation])
        ids = []
        for var in variable_modules:
            ids.append(var.id)
        action = controller.delete_module_list(ids)
        return action
        
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
        
        This function will update the workflow and add it to the
        provenance. It will reuse the plot configurations that are already in 
        the pipeline. You should make sure to update the state of the controller
        so its current_version is version before adding the VisTrails action to 
        the provenance.
        row and col contain the position of the cell in the spreadsheet the 
        workflow should be displayed, but as we keep a single cell, we don't
        use those parameters.
         
        """
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        added_vars = []
        if controller is None:
            controller = api.get_current_controller()
            version = 0L
        # action = CDMSPipelineHelper.remove_variables_from_pipeline_action(controller, version)
        # version = action.id
        version = controller.current_version
        pipeline = controller.vistrail.getPipeline(version)
        ops = []
        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
        cell_module = CDMSPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
        istart = len(plot_modules)
        ops2 = CDMSPipelineHelper.create_actions_from_plot_objs(controller, 
                                                                var_modules, 
                                                                cell_module, 
                                                                plot_objs, 
                                                                templates,
                                                                added_vars,
                                                                istart)
        ops.extend(ops2)
        ops.extend(
            CDMSPipelineHelper.connect_variables_to_plots(controller,
                                                          var_modules,
                                                          plot_modules))

        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
    
    @staticmethod
    def rebuild_pipeline_action(controller, version, plot_modules, var_modules,
                                connections):
        #first clear pipeline except for cell and location modules
        pipeline = controller.vistrail.getPipeline(version)
        controller.change_selected_version(version)
        cell = CDMSPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
        cell_location = CDMSPipelineHelper.find_module_by_name(pipeline, 'CellLocation')
        ids = []
        for module in pipeline.module_list:
            if module.id not in [cell.id,cell_location.id]:
                ids.append(module.id)
        action = controller.delete_module_list(ids)
        version = action.id
        
        #now start adding modules and connections
        ops = []
        for p in plot_modules:
            ops.append(('add', p))
            conn = controller.create_connection(p, 'self', cell, 'plot')
            ops.append(('add', conn))
            
        for v in var_modules:
            ops.append(('add', v))
            
        for (v, v_p, p, p_p) in connections:
            conn = controller.create_connection(v, v_p, p, p_p)
            ops.append(('add', conn))
            
        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
        
    @staticmethod
    def copy_pipeline_to_other_location(pipeline, controller, sheetName, row, col, 
                                        plot_type, cell):
        pip_str = core.db.io.serialize(pipeline)
        controller.change_selected_version(cell.current_parent_version)
        
        modules = controller.paste_modules_and_connections(pip_str, (0.0,0.0))
        cell.current_parent_version = controller.current_version
        pipeline = controller.current_pipeline
        
        reg = get_module_registry()
        cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, [CellLocation])
        cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [SpreadsheetCell]) 
        
        #we assume that there is only one CellLocation and one SpreadsheetCell
        # delete location and create another one with the right locations
        action = controller.delete_module_list([cell_locations[0].id])
        cell.current_parent_version = action.id
        
        loc_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
                                       'CellLocation'))
        functions = controller.create_functions(loc_module,
            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        for f in functions:
            loc_module.add_function(f)
        loc_conn = controller.create_connection(loc_module, 'self',
                                                cell_modules[0], 'Location')
        ops = [('add', loc_module),
               ('add', loc_conn)] 
        
        action = core.db.action.create_action(ops)
        controller.change_selected_version(cell.current_parent_version)
        controller.add_new_action(action)
        controller.perform_action(action)
        cell.current_parent_version = action.id
        
        # Update project controller cell information
        pipeline = controller.vistrail.getPipeline(action.id)
        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
        cell.variables =[]
        for plot in plot_modules:
            vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(controller, 
                                                                       pipeline, 
                                                                       plot.id)
            for var in vars:
                cell.variables.append(CDMSPipelineHelper.get_variable_name_from_module(var))
            
        cell.plots = []
        for pl_module in plot_modules:
            gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(pl_module)
            ptype = CDMSPipelineHelper.get_plot_type_from_module(pl_module)
            cell.plots.append(get_plot_manager().get_plot(plot_type, ptype, gmName))
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
        
        cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, [CellLocation])
        cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [SpreadsheetCell]) 
        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
        
        # we assume that there is only one CellLocation and one SpreadsheetCell
        # update location values in place.
        loc_module = cell_locations[0]
        for i in xrange(loc_module.getNumFunctions()):
            if loc_module.functions[i].name == 'Row':
                loc_module.functions[i].params[0].strValue = str(row+1)
            elif loc_module.functions[i].name == "Column":
                loc_module.functions[i].params[0].strValue = str(col+1)
                    
        # Update project controller cell information
        cell.variables = []
        for plot in plot_modules:
            vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(controller, 
                                                                       pipeline, 
                                                                       plot.id)
            for var in vars:
                cell.variables.append(CDMSPipelineHelper.get_variable_name_from_module(var))
            
        cell.plots = []
        for pl_module in plot_modules:
            gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(pl_module)
            ptype = CDMSPipelineHelper.get_plot_type_from_module(pl_module)
            cell.plots.append(get_plot_manager().get_plot(plot_type, ptype, gmName))
        
#    @staticmethod
#    def update_pipeline_action(controller, version, plot_modules):
#        pipeline = controller.vistrail.getPipeline(version)
#        pip_plots =  CDMSPipelineHelper.find_plot_modules(pipeline)
#        cell = CDMSPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
#        
#        pip_plot_map = {}
#        plot_map = {}
#        
#        to_be_added = []
#        for pm in pip_plots:
#            pip_plot_map[pm.id] = pm
#        for m in plot_modules:
#            plot_map[m.id] = m
#            if m.id not in pip_plot_map:
#                to_be_added.append(m)
#        to_be_removed = []
#        for pm in pip_plots:
#            if pm.id not in plot_map:
#                to_be_removed.append(pm.id)
#        if len(to_be_removed) > 0:
#            action = controller.delete_module_list(to_be_removed)
#            version = action.id
#            pipeline = controller.vistrail.getPipeline(version)
#            
#        
#        ops = []
#        conns_to = controller.get_connections_to(pipeline,[cell.id],"plot")    
#        for conn in conns_to:
#            if conn.source.moduleId not in to_be_removed:
#                ops.append(('delete',conn.id))
#        for m in to_be_added:
#            ops.append(('add', m))
#        for m in plot_modules:
#            conn = controller.create_connection(m, 'self',
#                                                cell, 'plot')
#            ops.append('add',conn)
#        
#        action = core.db.action.create_action(ops)
#        controller.change_selected_version(version)
#        controller.add_new_action(action)
#        controller.perform_action(action)
#        return action
        
    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot_objs=[]):
        """build_python_script_from_pipeline(controller, version, plot_objs) -> str
           
           This will build the corresponding python script for the pipeline
           identified by version in the controller. In this implementation,
           plot_objs list is ignored.
           
        """
        pipeline = controller.vistrail.getPipeline(version)
        plots = CDMSPipelineHelper.find_plot_modules(pipeline)
        text = "from PyQt4 import QtCore, QtGui\n"
        text += "import cdms2, cdutil, genutil\n"
        text += "import vcs\n\n"
        text += "if __name__ == '__main__':\n"
        text += "    import sys\n"
        text += "    app = QtGui.QApplication(sys.argv)\n"
        ident = '    '
        
        var_op_modules = CDMSPipelineHelper.find_topo_sort_modules_by_types(pipeline,
                                                                            [CDMSVariable, 
                                                                             CDMSVariableOperation])
        for m in var_op_modules:
            desc = m.module_descriptor.module
            mobj = desc.from_module(m)
            text += mobj.to_python_script(ident=ident)
                
        text += ident + "canvas = vcs.init()\n"
        for mplot in plots:
            plot = mplot.module_descriptor.module.from_module(mplot)
            text += ident + "gm%s = canvas.get%s('%s')\n"%(plot.plot_type, 
                                                 plot.plot_type.lower(), 
                                                 plot.graphics_method_name)
            text += ident + "args = []\n"
            for varm in CDMSPipelineHelper.find_variables_connected_to_plot_module(controller, pipeline, mplot.id):
                text += ident + "args.append(%s)\n"%CDMSPipelineHelper.get_variable_name_from_module(varm)
#                desc = varm.module_descriptor
#                if issubclass(desc.module, CDMSVariable):
#                    var = CDMSVariable.from_module(varm)
#                    text += ident + "args.append(%s)\n"%var.name
#                else:
#                    #operation
#                    op = desc.module.from_module(varm)
#                    text += ident + "args.append(%s)\n"%op.varname 
                
            if plot.graphics_method_name != 'default':
                for k in plot.gm_attributes:
                    if hasattr(plot,k):
                        kval = getattr(plot,k)
                        if type(kval) == type("str") and k != 'legend':
                            text += ident + "gm%s.%s = '%s'\n"%(plot.plot_type,
                                                            k, kval)
                        else:
                            text += ident + "gm%s.%s = %s\n"%(plot.plot_type,
                                                      k,  kval)
#                        if k in ['level_1', 'level_2', 'color_1',
#                                 'color_2', 'legend', 'levels',
#                                 'missing', 'datawc_calendar', 'datawc_x1', 
#                                 'datawc_x2', 'datawc_y1', 'datawc_y2',
#                                 'fillareacolors', 'fillareaindices']:
#                            text += ident + "gm%s.%s = %s\n"%(plot.plot_type,
#                                                      k,  getattr(plot,k))
#                        else:
#                            text += ident + "gm%s.%s = '%s'\n"%(plot.plot_type,
#                                                            k, getattr(plot,k))
            text += ident + "kwargs = %s\n"%plot.kwargs
            text += ident + "canvas.plot(gm%s,*args, **kwargs)\n"%(plot.plot_type) 
        text += '    sys.exit(app.exec_())'           
        return text
    
    @staticmethod    
    def get_graphics_method_name_from_module(module):
        result = CDMSPipelineHelper.get_value_from_function(module, 
                                                              "graphicsMethodName")
        if result == None:
            result = 'default'
        
        return result
    
    @staticmethod    
    def get_plot_type_from_module(module):
        desc = module.module_descriptor.module
        return desc.plot_type
    
    @staticmethod    
    def get_template_name_from_module(module):
        result = CDMSPipelineHelper.get_value_from_function(module, 
                                                              "template")
        if result == None:
            result = 'starter'
        
        return result
    
    @staticmethod
    def get_variable_name_from_module(module):
        desc = module.module_descriptor.module
        if issubclass(desc, CDMSVariable):
            result = CDMSPipelineHelper.get_value_from_function(module, "name")
        elif issubclass(desc, CDMSVariableOperation):
            result = CDMSPipelineHelper.get_value_from_function(module, "varname")
        else:
            result = None
        return result
    
class CDMSPlotWidget(QtGui.QWidget):
    def __init__(self,controller, version, plot_list, var_list, parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.proj_controller = controller
        self.controller = controller.vt_controller
        self.version = version
        self.plots = plot_list
        self.vars = var_list
        self.to_be_added = []
        self.to_be_removed = []
        self.var_to_be_added = []
        self.var_to_be_removed = []
        self.vars_were_changed = False
        
#        self.tab_widget = QtGui.QTabWidget(self)
#        self.tab_widget.setDocumentMode(True)
#        self.tab_widget.setTabPosition(QtGui.QTabWidget.North)
#        
        main_layout = QtGui.QVBoxLayout()
        main_layout.setMargin(0)
        main_layout.setSpacing(2)
        self.create_plot_widget()
        self.create_var_widget()
        
        var_label = QtGui.QLabel("Variables used in this visualization:")
        plot_label = QtGui.QLabel("Plots used in this visualization")

        self.vars_were_changed = False
        
        main_layout.addWidget(var_label)
        main_layout.addWidget(self.var_widget)
        main_layout.addWidget(plot_label)
        main_layout.addWidget(self.plot_widget)
        
        b_layout = QtGui.QHBoxLayout()
        b_layout.setMargin(5)
        b_layout.addStretch()
        self.btn_save = QDockPushButton('&Apply', self)
        self.btn_save.setFixedWidth(100)
        self.btn_save.setEnabled(True)
        b_layout.addWidget(self.btn_save)
        self.btn_reset = QDockPushButton('&Reset', self)
        self.btn_reset.setFixedWidth(100)
        self.btn_reset.setEnabled(True)
        b_layout.addWidget(self.btn_reset)
        b_layout.addStretch()
        main_layout.addLayout(b_layout)
        self.setLayout(main_layout)

        self.btn_save.clicked.connect(self.save_triggered)
        self.btn_reset.clicked.connect(self.reset_triggered)
        
    def update_version(self, version, plot_list, var_list):
        self.version = version
        self.plots = plot_list
        self.vars = var_list
        self.to_be_added = []
        self.to_be_removed = []
        self.var_to_be_added = []
        self.var_to_be_removed = []
        self.vars_were_changed = False
        self.plot_table.version = version
        self.var_table.populate_from_vars(self.vars)
        selected = None
        if len(self.plot_table.selectedItems()) == 1:
            item = self.plot_table.selectedItems()[0]
            for plot in self.plots:
                if plot.id == item.module.id:
                    selected = plot
        self.plot_table.populate_from_plots(self.plots, selected)
        item = self.plot_table.selectedItems()[0]
        self.update_move_buttons(item)
        self.update_plot_vars(item)
        
    def create_var_widget(self):
        self.var_widget = QtGui.QWidget()
        self.var_table = VarTableWidget(self.vars, self)
        self.btn_add_var = QDockPushButton("Add")
        self.btn_del_var = QDockPushButton("Remove")
        btn_layout = QtGui.QHBoxLayout()
        btn_layout.setSpacing(3)
        btn_layout.setMargin(0)
        btn_layout.addWidget(self.btn_add_var)
        btn_layout.addWidget(self.btn_del_var)
        btn_layout.addStretch()
        
        self.var_layout = QtGui.QVBoxLayout()
        self.var_layout.setMargin(2)
        self.var_layout.setSpacing(2)
        self.var_layout.addWidget(self.var_table)
        self.var_layout.addLayout(btn_layout)
        self.var_widget.setLayout(self.var_layout)
        
        #signals
        self.var_table.itemSelectionChanged.connect(self.update_btn_del_var_state)
        self.btn_add_var.clicked.connect(self.add_var)
        self.btn_del_var.clicked.connect(self.remove_var)
        self.var_table.populate_from_vars(self.vars)
        
    def create_plot_widget(self):
        self.plot_widget = QtGui.QWidget()
        self.btn_move_up = QtGui.QToolButton(self)
        self.btn_move_up.setIcon(CurrentTheme.UP_STRING_ICON)
        self.btn_move_down = QtGui.QToolButton(self)
        self.btn_move_down.setIcon(CurrentTheme.DOWN_STRING_ICON)
        b_layout = QtGui.QVBoxLayout()
        b_layout.setMargin(0)
        b_layout.setSpacing(2)
        b_layout.addStretch()
        b_layout.addWidget(self.btn_move_up)
        b_layout.addWidget(self.btn_move_down)
        b_layout.addStretch()
        self.conf_widget = QtGui.QWidget()
        self.plot_table = PlotTableWidget(self.plots, self.controller, 
                                          self.version, self)
        h_layout = QtGui.QHBoxLayout()
        h_layout.addLayout(b_layout)
        h_layout.addWidget(self.plot_table)
        self.btn_add_plot = QDockPushButton("Add")
        self.btn_del_plot = QDockPushButton("Remove")
        btn_layout = QtGui.QHBoxLayout()
        btn_layout.setSpacing(3)
        btn_layout.setMargin(0)
        btn_layout.addWidget(self.btn_add_plot)
        btn_layout.addWidget(self.btn_del_plot)
        btn_layout.addStretch()
        self.v_layout = QtGui.QVBoxLayout()
        self.v_layout.setMargin(2)
        self.v_layout.setSpacing(2)
        self.selected_label = QtGui.QLabel("Configuration:")
        self.v_layout.addLayout(h_layout)
        self.v_layout.addLayout(btn_layout)
        #self.v_layout.addSpacing(8)
        self.v_layout.addWidget(self.selected_label)
        self.create_plot_vars_widget()
        self.v_layout.addWidget(self.plot_vars_widget)
        self.template_widget = QtGui.QGroupBox("Template")
        template_lbl = QtGui.QLabel("Name:")
        self.template_edt = QtGui.QLineEdit()
        template_layout = QtGui.QHBoxLayout()
        template_layout.addWidget(template_lbl)
        template_layout.addWidget(self.template_edt)
        self.template_widget.setLayout(template_layout)
        self.v_layout.addWidget(self.template_widget)
        self.plot_widget.setLayout(self.v_layout)
         
        #signals
        self.plot_table.itemSelectionChanged.connect(self.update_conf_widget)
        self.template_edt.editingFinished.connect(self.template_edited)
        self.btn_add_plot.clicked.connect(self.add_plot)
        self.btn_del_plot.clicked.connect(self.remove_plot)
        self.btn_move_up.clicked.connect(self.plot_table.move_item_up)
        self.btn_move_down.clicked.connect(self.plot_table.move_item_down)
        self.plot_table.populate_from_plots(self.plots)
        self.plot_table.itemOrderChanged.connect(self.update_move_buttons)
        self.update_btn_del_state()
        
    def create_plot_vars_widget(self):
        self.plot_vars_widget = QtGui.QGroupBox("Variables (drag from the list above)")
        self.var1_label = QtGui.QLabel("Variable 1:")
        self.var1_edt = DropVarLineEdit(0)
        self.var2_label = QtGui.QLabel("Variable 2:")
        self.var2_edt = DropVarLineEdit(1)
        self.connect(self.var1_edt, QtCore.SIGNAL("dropped_var"), 
                     self.variable_dropped)
        self.connect(self.var2_edt, QtCore.SIGNAL("dropped_var"), 
                     self.variable_dropped)
        self.var1_edt.editingFinished.connect(self.variable1_edited)
        self.var2_edt.editingFinished.connect(self.variable2_edited)
        hlayout = QtGui.QHBoxLayout()
        hlayout.addWidget(self.var1_label)
        hlayout.addWidget(self.var1_edt)
        hlayout.addWidget(self.var2_label)
        hlayout.addWidget(self.var2_edt)
        self.plot_vars_widget.setLayout(hlayout)
        
    def askToSaveChanges(self):
        #FIXME: Check if there were changes and save them
        pass
    
    def connect_signals(self):
        if type(self.conf_widget) == GraphicsMethodConfigurationWidget:
            self.connect(self.conf_widget, QtCore.SIGNAL("plotDoneConfigure"),
                         self.configure_done)
            self.connect(self.conf_widget, QtCore.SIGNAL("stateChanged"),
                         self.state_changed)
    def disconnect_signals(self):
        if type(self.conf_widget) == GraphicsMethodConfigurationWidget:
            self.disconnect(self.conf_widget, QtCore.SIGNAL("plotDoneConfigure"),
                         self.configure_done)
            self.disconnect(self.conf_widget, QtCore.SIGNAL("stateChanged"),
                         self.state_changed)
            
    @pyqtSlot(Module, int)
    def variable_dropped(self, var, order):
        self.var_to_be_added.append(var.id)
        plot_item = self.plot_table.selectedItems()[0]
        
        while len(plot_item.vars) <= order:
            plot_item.vars.append(var)
            self.vars_were_changed = True
            
        if plot_item.vars[order] != var:
            plot_item.vars.pop(order)
            plot_item.vars.insert(order,var)
            self.vars_were_changed = True
        
    @pyqtSlot()
    def variable1_edited(self):
        var = self.var_table.get_var_by_name(str(self.var1_edt.text()))
        if var:
            plot_item = self.plot_table.selectedItems()[0]
            if len(plot_item.vars) == 0:
                plot_item.vars.append(var)
                self.vars_were_changed = True
            elif plot_item.vars[0] != var:
                plot_item.vars.pop(0)
                plot_item.vars.insert(0,var)
                self.vars_were_changed = True
                
    @pyqtSlot()
    def variable2_edited(self):
        var = self.var_table.get_var_by_name(str(self.var2_edt.text()))
        if var:
            plot_item = self.plot_table.selectedItems()[0]
            if len(plot_item.vars) < 1:
                plot_item.vars.append(var)
                plot_item.vars.append(var)
                self.vars_were_changed = True
            if plot_item.vars[1] != var:
                plot_item.vars.pop(1)
                plot_item.vars.insert(1,var)
                self.vars_were_changed = True            
        
    @pyqtSlot()
    def template_edited(self):
        from init import get_canvas
        template_list = get_canvas().listelements("template")
        template = str(self.template_edt.text())
        if template in template_list: 
            plot_item = self.plot_table.selectedItems()[0]
            plot_item.template = template
            
    def update_btn_del_state(self):
        if (len(self.plot_table.selectedItems()) > 0 and 
            self.plot_table.topLevelItemCount() > 1):
            self.btn_del_plot.setEnabled(True)
        else:
            self.btn_del_plot.setEnabled(False)
            
    def update_btn_del_var_state(self):
        varnum = 1
        for i in range(self.plot_table.topLevelItemCount()):
            item = self.plot_table.topLevelItem(i)
            varnum = max(varnum,item.reg_plot.varnum)
        if (len(self.var_table.selectedItems()) > 0 and 
            self.var_table.topLevelItemCount() > varnum):
            self.btn_del_var.setEnabled(True)
        else:
            self.btn_del_var.setEnabled(False)
            
    @pyqtSlot()
    def update_conf_widget(self):
        if self.conf_widget:
            if isinstance(self.conf_widget,GraphicsMethodConfigurationWidget):
                if self.conf_widget.checkForChanges():
                    self.conf_widget.saveTriggered()
            #self.conf_widget.setVisible(False)
            self.v_layout.removeWidget(self.conf_widget)
            self.disconnect_signals()
            self.conf_widget.deleteLater()
        if len(self.plot_table.selectedItems()) == 1:
            item = self.plot_table.selectedItems()[0]
            self.controller.change_selected_version(self.version)
            self.conf_widget = GraphicsMethodConfigurationWidget(item.module,
                                                                 self.controller,
                                                                 self,
                                                                 show_buttons=False)
            self.selected_label.setText("%s Configuration:"%item.text(1))
            self.connect_signals()
            self.update_move_buttons(item)
            self.update_plot_vars(item)
            self.btn_del_plot.setEnabled(True)
        else:
            self.conf_widget = QtGui.QWidget()
            self.btn_del_plot.setEnabled(False)
            self.update_move_buttons(None)
            self.update_plot_vars(None)
            self.selected_label.setText("Configuration:")
        self.v_layout.addWidget(self.conf_widget)
    
    def update_move_buttons(self, item):
        if item is None:
            self.btn_move_up.setEnabled(False)
            self.btn_move_down.setEnabled(False)
            return
        if self.plot_table.indexOfTopLevelItem(item) == 0:
            self.btn_move_up.setEnabled(False)
        else:
            self.btn_move_up.setEnabled(True)
        if self.plot_table.indexOfTopLevelItem(item) == self.plot_table.topLevelItemCount()-1:
            self.btn_move_down.setEnabled(False)
        else:
            self.btn_move_down.setEnabled(True)
            
    def update_plot_vars(self, item):
        if item is None:
            self.plot_vars_widget.setVisible(False)
            return
        
        self.show_vars(item.reg_plot.varnum)
        if len(item.vars) >= 1:
            varname = CDMSPipelineHelper.get_variable_name_from_module(item.vars[0])
            self.var1_edt.setText(varname)
        if len(item.vars) > 1:
            varname = CDMSPipelineHelper.get_variable_name_from_module(item.vars[1])
            self.var2_edt.setText(varname)
        self.template_edt.setText(item.template)
            
    def show_vars(self, num):
        self.var1_edt.setText("")
        self.var2_edt.setText("")
        self.plot_vars_widget.setVisible(True)
        if num == 1:
            self.var1_label.setVisible(True)
            self.var1_edt.setVisible(True)
            self.var2_label.setVisible(False)
            self.var2_edt.setVisible(False)
        if num == 2:
            self.var1_label.setVisible(True)
            self.var1_edt.setVisible(True)
            self.var2_label.setVisible(True)
            self.var2_edt.setVisible(True)
        
            
    def configure_done(self, action):
        canceled = []
        
        for a in self.to_be_added:
            if a in self.to_be_removed:
                canceled.append(a)
        for m in canceled:
            self.to_be_added.remove(m)
            self.to_be_removed.remove(m)
        
        canceled = []
        for v in self.var_to_be_added:
            if v in self.var_to_be_removed:
                canceled.append(v)
        for m in canceled:
            self.var_to_be_added.remove(m)
            self.var_to_be_removed.remove(m)

        if (len(self.to_be_added) != 0 or len(self.to_be_removed) != 0 or
            len(self.var_to_be_added) != 0 or len(self.var_to_be_removed) != 0 
            or self.plot_order_changed() or self.vars_were_changed):
            action = self.update_pipeline(action)
        
        action = self.update_templates(action)
                
        self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
        if action is not None:
            version = action.id
            pipeline = self.controller.vistrail.getPipeline(version)
            plots = CDMSPipelineHelper.find_plot_modules(pipeline)
            vars = CDMSPipelineHelper.find_modules_by_type(pipeline, 
                                                           [CDMSVariable,
                                                            CDMSVariableOperation])
            self.controller.change_selected_version(version)
            self.update_version(version, plots, vars)
            
    def plot_order_changed(self):
        plot_modules = self.plot_table.get_plots()
        changed = False
        for p, cp in zip(self.plots,plot_modules):
            if p.id != cp.id:
                changed = True
        return changed
        
    def state_changed(self):
        self.emit(QtCore.SIGNAL("stateChanged"))
        
    @pyqtSlot(bool)
    def add_plot(self, checked):
        dialog = AddCDMSPlotDialog(self)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            plot = dialog.plot
            plot_module = CDMSPipelineHelper.create_plot_module(self.controller, 
                                                                plot.parent, 
                                                                plot.name)
            self.plot_table.add_plot_item(plot_module, copy_vars=True)
            self.to_be_added.append(plot_module.id)
        self.update_btn_del_state()
        
    @pyqtSlot(bool)
    def remove_plot(self, checked):
        module = self.plot_table.remove_current_item()
        if module:
            self.to_be_removed.append(module.id)
        self.update_btn_del_state()
        
    @pyqtSlot(bool)
    def add_var(self, checked):
        var_list = self.var_table.get_varname_list()
        dialog = AddCDMSVarDialog(self.proj_controller, var_list, self)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            varName = dialog.varName
            var_module = dialog.var 
            self.var_table.add_var_item(var_module)
        self.update_btn_del_var_state()
        
    @pyqtSlot(bool)
    def remove_var(self, checked):
        module = self.var_table.remove_current_item()
        if module:
            self.var_to_be_removed.append(module.id)
        self.update_btn_del_var_state()
        
    def update_pipeline(self, action):
        #at this point, the plots should have already be added
        #plot_modules = self.plot_table.get_plots()
        var_modules = self.var_table.get_vars()
        connections = self.plot_table.get_connections()
        if action is not None:
            version = action.id
        else:
            version = self.version
        pipeline = self.controller.vistrail.getPipeline(version)
        pip_plots = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
        plot_modules = []
        for plot in pip_plots:
            if plot.id not in self.to_be_removed:
                plot_modules.append(plot)
        action = CDMSPipelineHelper.rebuild_pipeline_action(self.controller, 
                                                            version, 
                                                            plot_modules, 
                                                            var_modules, 
                                                            connections)    
        return action
    
    def update_templates(self, ori_action):
        if ori_action is not None:
            version = ori_action.id
        else:
            version = self.version
        action = None
        #check if the template changed and update provenance
        for i in range(self.plot_table.topLevelItemCount()):
            plot_item = self.plot_table.topLevelItem(i)
            pipeline = self.controller.vistrail.getPipeline(version)
            if plot_item.module.id in pipeline.modules:
                plot_module = pipeline.modules[plot_item.module.id]
                functions = [('template', [plot_item.template])]
                action = self.controller.update_functions(plot_module, 
                                                          functions)
                if action is not None:
                    version = action.id
        
        if action is not None:
            return action
        else:
            return ori_action
            
    @pyqtSlot(bool)
    def save_triggered(self, checked):
        
        self.conf_widget.saveTriggered(checked)
    
    @pyqtSlot(bool)
    def reset_triggered(self, checked):
        pass

class PlotTableWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent, order, module, labels, plot_type, gm_name, vars,
                 reg_plot, template):
        QtGui.QTreeWidgetItem.__init__(self, parent, labels)
        self.module = module    
        self.order = order
        self.plot_type = plot_type
        self.gm_name = gm_name
        self.vars = vars
        self.reg_plot = reg_plot
        self.template = template
    
class PlotTableWidget(QtGui.QTreeWidget):
    itemOrderChanged = pyqtSignal(PlotTableWidgetItem)
    def __init__(self,plot_list, controller, version, parent=None):    
        QtGui.QTreeWidget.__init__(self, parent)
        self.plots = plot_list
        self.controller = controller
        self.version = version
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setRootIsDecorated(False)
        self.header().setStretchLastSection(True)
        self.setHeaderLabels(QtCore.QStringList() << "Order" << "Plot Type" << "Graphics Method" << "Template")
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        
    def populate_from_plots(self,plots=None, selected=None):
        if plots is not None:
            self.plots = plots
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)
        for i in range(len(self.plots)):
            item = self.create_plot_item(i, self.plots[i])
            if selected is not None:
                if item.module == selected:
                    self.setItemSelected(item,True)
            else:
                #select first element
                if item.module == self.plots[0]:
                    self.setItemSelected(item,True)
            
    def create_plot_item(self, order, plot_module, copy_vars=False):
        manager = get_plot_manager()
        desc = plot_module.module_descriptor.module()
        gm_name = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_module)
        template = CDMSPipelineHelper.get_template_name_from_module(plot_module)
        labels = QtCore.QStringList() << str(order+1) << str(desc.plot_type) << str(gm_name) << \
                                         str(template)
        pipeline = self.controller.vistrail.getPipeline(self.version)
        if plot_module.id in pipeline.modules:
            _vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(self.controller, 
                                                                               pipeline, 
                                                                               plot_module.id)
        else:
            _vars = []
            if copy_vars:
                plot_modules = CDMSPipelineHelper.find_plot_modules(pipeline)
                if len(plot_modules) > 0:
                    p_module = plot_modules[0]
                    _vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(self.controller, 
                                                                                        pipeline, 
                                                                                        p_module.id)
                      
        reg_plot = manager.get_plot_by_name(desc.plot_type, gm_name)
        item = PlotTableWidgetItem(self, order, plot_module, labels, 
                                   desc.plot_type, gm_name, _vars, reg_plot, template)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        return item
    
    def add_plot_item(self, plot_module, copy_vars=False):
        order = self.topLevelItemCount()
        self.plots.append(plot_module)
        self.create_plot_item(order,plot_module, copy_vars)
    
    @pyqtSlot(bool)
    def move_item_up(self, checked):
        self.blockSignals(True)
        item = self.selectedItems()[0]
        pos = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(pos)
        self.insertTopLevelItem(pos-1,item)
        self.setCurrentItem(item)
        self.update_item_ordering()
        self.blockSignals(False)
        self.itemOrderChanged.emit(item)
    
    @pyqtSlot(bool)
    def move_item_down(self, checked):
        self.blockSignals(True)
        item = self.selectedItems()[0]
        pos = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(pos)
        self.insertTopLevelItem(pos+1,item)
        self.setCurrentItem(item)
        self.update_item_ordering()
        self.blockSignals(False)
        self.itemOrderChanged.emit(item)
        
    def update_item_ordering(self):
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setText(0,str(i+1))
            item.order = i
            
    def remove_current_item(self):
        item = self.selectedItems()[0]
        index = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(index)
        self.remove_plot_by_id(item.module.id)
        self.update_item_ordering()
        if index >= self.topLevelItemCount():
            index -= 1
        if index >=0:
            sel_item = self.topLevelItem(index)
            self.setItemSelected(sel_item, True)
        return item.module
    
    def remove_plot_by_id(self, _id):
        found = None
        for plot in self.plots:
            if plot.id == _id:
                found = plot
                break
        if found is not None:
            self.plots.remove(found)
        
    def get_plots(self):
        plots = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            plots.append(item.module)
        return plots
    
    def get_connections(self):
        conns = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if len(item.vars) >= 1:
                conns.append((item.vars[0], 'self', item.module, 'variable'))
            if len(item.vars) > 1:
                conns.append((item.vars[1], 'self', item.module, 'variable2'))            
        return conns
        
class VarTableWidget(QtGui.QTreeWidget):
    def __init__(self, var_list, parent=None):    
        QtGui.QTreeWidget.__init__(self, parent)
        self.vars = var_list
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setRootIsDecorated(False)
        self.header().setStretchLastSection(True)
        self.setHeaderLabels(QtCore.QStringList() << "Name" )
        self.setDragEnabled(True)
        self.flags = QtCore.Qt.ItemIsDragEnabled
        self.setAcceptDrops(False)
        
    def populate_from_vars(self, _vars=None):
        if _vars is not None:
            self.vars = _vars
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)
        for i in range(len(self.vars)):
            item = self.create_var_item(self.vars[i])
            if item.module == self.vars[0]:
                self.setItemSelected(item,True)
            
    def mimeData(self, itemList):
        """ mimeData(itemList) -> None        
        Setup the mime data to contain itemList because Qt 4.2.2
        implementation doesn't instantiate QTreeWidgetMimeData
        anywhere as it's supposed to. It must have been a bug...
        
        """
        data = QtGui.QTreeWidget.mimeData(self, itemList)
        a = QtCore.QByteArray()
        a.append(self.currentItem().text(0))
        data.setData("variable", a)
        data.items = itemList
        return data
    
    def create_var_item(self, var_module):
        varname = CDMSPipelineHelper.get_variable_name_from_module(var_module)
        labels = QtCore.QStringList() << str(varname)
        item = VarTableWidgetItem(self, var_module, labels, varname)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)
        return item
    
    def add_var_item(self, var_module):
        self.vars.append(var_module)
        self.create_var_item(var_module)
        
    def remove_current_item(self):
        item = self.selectedItems()[0]
        index = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(index)
        self.remove_var_by_id(item.module.id)
        return item.module
        
    def remove_var_by_id(self, _id):
        found = None
        for var in self.vars:
            if var.id == _id:
                found = var
                break
        if var is not None:
            self.vars.remove(found)
            
    def get_varname_list(self):
        var_list = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            var_list.append(item.varname)
        return var_list
    
    def get_vars(self):
        vars = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            vars.append(item.module)
        return vars
    
    def get_var_by_name(self, name):
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.varname == name:
                return item.module
        return None
    
class VarTableWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent, module, labels, varname):
        QtGui.QTreeWidgetItem.__init__(self, parent, labels)
        self.module = module    
        self.varname = varname
        
class CDMSTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super(CDMSTreeWidget, self).__init__(parent)
        self.header().hide()
        self.setRootIsDecorated(True)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.create_tree()
        
    def create_tree(self):
        registry = get_plot_registry()
        for plottype in sorted(registry.plots["VCS"].keys()):
            item = QtGui.QTreeWidgetItem(self, 
                                         QtCore.QStringList(plottype),
                                         1)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            ## Special section here for VCS GMs they have one more layer
            for plot in registry.plots["VCS"][plottype].itervalues():
                item2 = PlotTreeWidgetItem(plottype, plot.name, 
                                           QtCore.QStringList(plot.name),
                                           2, plot, item)
class AddCDMSPlotDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(AddCDMSPlotDialog, self).__init__(parent)
        self.setWindowTitle('UVCDAT VCS Plot Composition')
        self.plot = None
        dlg_layout = QtGui.QVBoxLayout()
        label = QtGui.QLabel("Please select a plot type's graphics method:")
        self.tree = CDMSTreeWidget(self)
        self.btn_ok = QtGui.QPushButton("OK")
        self.btn_cancel = QtGui.QPushButton("Cancel")
        btn_layout = QtGui.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        dlg_layout.addWidget(label)
        dlg_layout.addWidget(self.tree)
        dlg_layout.addLayout(btn_layout)
        self.btn_ok.clicked.connect(self.btn_ok_clicked)
        self.btn_cancel.clicked.connect(self.btn_cancel_clicked)
        self.setLayout(dlg_layout)
        
    @pyqtSlot(bool)
    def btn_ok_clicked(self, checked):
        item = self.tree.selectedItems()[0]
        self.plot = item.plot
        self.accept()
       
    @pyqtSlot(bool) 
    def btn_cancel_clicked(self, checked):
        self.reject()
        
class AddCDMSVarDialog(QtGui.QDialog):
    def __init__(self, controller, var_list, parent=None):
        super(AddCDMSVarDialog, self).__init__(parent)
        self.setWindowTitle('UVCDAT VCS Plot Composition')
        self.proj_controller = controller
        self.var = None
        self.varName = None
        self._var_list = var_list
        dlg_layout = QtGui.QVBoxLayout()
        label = QtGui.QLabel("Please select a defined variable:")
        self.var_list= QtGui.QListWidget(self)
        self.btn_ok = QtGui.QPushButton("OK")
        self.btn_cancel = QtGui.QPushButton("Cancel")
        btn_layout = QtGui.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        dlg_layout.addWidget(label)
        dlg_layout.addWidget(self.var_list)
        dlg_layout.addLayout(btn_layout)
        self.btn_ok.clicked.connect(self.btn_ok_clicked)
        self.btn_cancel.clicked.connect(self.btn_cancel_clicked)
        self.setLayout(dlg_layout)
        self.create_list()
        
    @pyqtSlot(bool)
    def btn_ok_clicked(self, checked):
        item = self.var_list.selectedItems()[0]
        self.varName = item.varName
        self.var = item.var
        self.accept()
       
    @pyqtSlot(bool) 
    def btn_cancel_clicked(self, checked):
        self.reject()
        
    def create_list(self):
        for varName in sorted(self.proj_controller.defined_variables):
            if varName not in self._var_list:
                var = self.proj_controller.defined_variables[varName]
                var_module = var.to_module(self.proj_controller.vt_controller)
                item = CDMSVarListWidgetItem(var_module, varName, CDMSVariable, self.var_list)
        for varName in sorted(self.proj_controller.computed_variables):
            if varName not in self._var_list:
                var = self.proj_controller.computed_variables[varName]
                item = CDMSVarListWidgetItem(None, varName, CDMSVariableOperation, self.var_list)
            
        
class CDMSVarListWidgetItem(QtGui.QListWidgetItem):
    def __init__(self, var, varName, t=CDMSVariable, parent=None):
        super(CDMSVarListWidgetItem, self).__init__(varName, parent)
        self.var = var
        self.varName = varName
        self.type = t
        
class DropVarLineEdit(QtGui.QLineEdit):
    
    def __init__(self, order, parent=None): 
        super(DropVarLineEdit, self).__init__(parent) 
        self.setAcceptDrops(True)
        self.order = order
        
    def dropEvent(self, event):
        mimeData = event.mimeData()   
        if mimeData.hasFormat("variable"):
            if hasattr(mimeData, 'items') and len(mimeData.items) == 1:
                event.setDropAction(QtCore.Qt.CopyAction)
                event.accept()
                item = mimeData.items[0]
                self.setText(item.varname)
                self.emit(QtCore.SIGNAL("dropped_var"), item.module, self.order)
                
    def dragEnterEvent(self, event):
        """ dragEnterEvent(event: QDragEnterEvent) -> None
        Set to accept drops from the version tree
        
        """
        mimeData = event.mimeData()
        if mimeData.hasFormat("variable"):
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        """ dragMoveEvent(event: QDragEnterEvent) -> None
        Set to accept drops from the version tree
        
        """
        mimeData = event.mimeData()
        if mimeData.hasFormat("variable"):
            event.accept()
        else:
            event.ignore()