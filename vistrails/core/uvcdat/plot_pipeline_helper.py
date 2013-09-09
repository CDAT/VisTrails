'''
Created on Nov 30, 2011

@author: emanuele
'''
import core.db.io, sys
import core.modules.basic_modules
from core.modules.module_registry import get_module_registry
from core.utils import unimplemented

class PlotPipelineHelper(object):
    '''
    This will take care of pipeline manipulation for plots.
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
    @staticmethod
    def update_plot_pipeline_action(controller, version, var_modules, plot_objs,
                                     row, column):
        unimplemented()
        
    @staticmethod
    def find_module_by_name(pipeline, module_name):
        for module in pipeline.module_list:
            if module.name == module_name:
                return module

    @staticmethod
    def find_module_by_id( pipeline, id ):
        for module in pipeline.module_list:
            if module.id == id:
                return module
    
    @staticmethod
    def get_value_from_function(module, fun):
        for i in xrange(module.getNumFunctions()):
            if fun == module.functions[i].name:
                return module.functions[i].params[0].value()
        return None

    @staticmethod
    def get_value_from_function_as_str(module, fun):
        for i in xrange(module.getNumFunctions()):
            if fun == module.functions[i].name:
                return module.functions[i].params[0].strValue
        return None

    @staticmethod
    def find_modules_by_type(pipeline, moduletypes):
        result = []
        for module in pipeline.module_list:
            desc = module.module_descriptor
            if issubclass(desc.module, tuple(moduletypes)):
                result.append(module)
        return result
    
    @staticmethod
    def find_topo_sort_modules_by_types(pipeline, moduletypes):
        modules = []
        for m in pipeline.module_list:
            desc = m.module_descriptor
            if issubclass(desc.module,tuple(moduletypes)):
                modules.append(m.id)
        ids = pipeline.graph.vertices_topological_sort()
        result = []
        for i in ids:
            if i in modules:
                module = pipeline.modules[i] 
                result.append(module)
        return result
    
    @staticmethod
    def find_sink_modules_by_type(pipeline, moduletype):
        res = []
        for mid in pipeline.graph.sinks():
            module = pipeline.modules[mid]
            desc = module.module_descriptor
            if issubclass(desc.module, moduletype):
                res.append(module)
        return res
    
    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules,  plot_objs, 
                                   row, col):
        from packages.uvcdat_cdms.init import CDMSVariableOperation 
        #for now, this helper will generate change parameter actions based on the
        #alias dictionary
        #first set the plot:
        #assuming that the list of plots has a single plot
        plot_obj = plot_objs[0] 
        plot_obj.current_parent_version = version
        plot_obj.current_controller = controller
        aliases = {}
        for i in range(len(var_modules)):
            if issubclass( var_modules[i].module_descriptor.module, CDMSVariableOperation):
                varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varname' )
                python_command = PlotPipelineHelper.get_value_from_function( var_modules[i], 'python_command' )
                aliases[plot_obj.vars[i]] = varname
                aliases[ "%s.cmd" % plot_obj.vars[i] ] = python_command
            else:
                filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'filename')
                if filename is None:
                    filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'file')
                if isinstance( filename, core.modules.basic_modules.File ):
                    filename = filename.name
                url = PlotPipelineHelper.get_value_from_function( var_modules[i], 'url')            
                varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
                file_varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varNameInFile')
                axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')
                aliases[plot_obj.files[i]] = filename
                aliases[ ".".join( [plot_obj.files[i],"url"] )  ] = url if url else ""
                aliases[plot_obj.vars[i]] = varname
                aliases[ "%s.file" % plot_obj.vars[i] ] = file_varname if file_varname else ""
                if len(plot_obj.axes) > i:
                    aliases[plot_obj.axes[i]] = axes
#                if var_modules[i].descriptor_info[1].endswith( 'VariableOperation' ):
#                    pass
            
#                module = var_modules[i].summon()
#                module.update()
#                output_var = PlotPipelineHelper.get_value_from_function( var_modules[i], 'output_var' )
#                print " "
                


        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                aliases[plot_obj.cells[j].row_name] = str(row+1)
                aliases[plot_obj.cells[j].col_name] = str(col+1+j)
            elif plot_obj.cells[j].address_name:
                aliases[plot_obj.cells[j].address_name] = "%s%s" % ( chr(ord('A') + col+j ), row+1)
            
        for a,w in plot_obj.alias_widgets.iteritems():
            try:    aliases[a] = w.contents()
            except Exception, err: print>>sys.stderr, "Error updating alias %s:" % str( a ), str(err)

        actions = plot_obj.applyChanges(aliases)
        action = actions.pop()
        
        #get the most recent action that is not None
        while action == None:
            action = actions.pop()
        
        return action
    
    @staticmethod
    def copy_pipeline_to_other_location(pipeline, controller, sheetName, row, col, 
                                        plot_type, cell):
        #for now this helper will copy the workflow and change the location
        #based on the alias dictionary
        from core.uvcdat.plotmanager import get_plot_manager
        pip_str = core.db.io.serialize(pipeline)
        controller.change_selected_version(cell.current_parent_version)
        modules = controller.paste_modules_and_connections(pip_str, (0.0,0.0))
        cell.current_parent_version = controller.current_version
        pipeline = controller.current_pipeline
        
        plot_obj = get_plot_manager().get_plot_by_vistrail_version(plot_type, 
                                                                   controller.vistrail,
                                                                   controller.current_version)
        plot_obj.current_parent_version = cell.current_parent_version
        plot_obj.current_controller = controller
        cell.plots = [plot_obj]
        
        aliases = {}
        for a in pipeline.aliases:
            aliases[a] = pipeline.get_alias_str_value(a)
        
        if (plot_obj.serializedConfigAlias and 
            plot_obj.serializedConfigAlias in aliases):
            plot_obj.unserializeAliases(aliases)
            
        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                aliases[plot_obj.cells[j].row_name] = str(row+1)
                aliases[plot_obj.cells[j].col_name] = str(col+1+j)
            elif plot_obj.cells[j].address_name:
                aliases[plot_obj.cells[j].address_name] = "%s%s"%(chr(ord('A') + col+j),
                                                                  row+1)
        
        actions = plot_obj.applyChanges(aliases)
        
        #this will update the variables
        for i in range(plot_obj.varnum):
            cell.add_variable(aliases[plot_obj.vars[i]])
            
        #get the most recent action that is not None
        if len(actions) > 0:
            action = actions.pop()
            while action == None and len(actions) > 0:
                action = actions.pop()
            if action is not None:
                cell.current_parent_version = action.id
                return action
        return None
    
    @staticmethod
    def load_pipeline_in_location(pipeline, controller, sheetName, row, col, 
                                        plot_type, cell):
        #for now this helper will change the location in place
        #based on the alias dictionary
        from core.uvcdat.plotmanager import get_plot_manager
        controller.change_selected_version(cell.current_parent_version)
        plot_obj = get_plot_manager().get_plot_by_vistrail_version(plot_type, 
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
            cell.add_variable(pipeline.get_alias_str_value(plot_obj.vars[i]))            

    
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
    def show_configuration_widget(controller, version, plot_objs=[]):
        from gui.uvcdat.plot_configuration import AliasesPlotWidget
        #FIXME: This will create the widget for the first plot object
        return AliasesPlotWidget(controller,version,plot_objs[0])
    
    @staticmethod
    def create_plot_workflow_items(workflow, controller, row, col):
        """Creates new modules and connections to mimic the workflow
        and adds the location module, and finds the ports that accept
        CDMSVariable modules. Caller should use these to match up
        variables with plot inputs.
        
        returns (module_list, connection_list), [(module, portSpec)]
        """
        
        from packages.spreadsheet.basic_widgets import SpreadsheetCell  
        
        #keep a map between new and old modules so we can make sure
        #our new connections connect the correct modules
        new_modules = {}
        
        cell_module = None
        
        cdms_ports = []
        
        #create new modules, map based on original id
        for module in workflow.module_list:
            new_module = module.do_copy(True, controller.vistrail.idScope, {})
            
            #find cell module
            if issubclass(new_module.module_descriptor.module, SpreadsheetCell):
                if cell_module is not None:
                    print "Warning: found multiple cell modules in workflow"
                else:
                    cell_module = new_module
                    
            #check input ports for those accepting CDMSVariable
            for port_spec in new_module.module_descriptor.port_specs_list + new_module.port_spec_list:
                if port_spec.short_sigstring == '(CDMSVariable)' and port_spec.type == 'input':
                    cdms_ports.append((new_module, port_spec))
            
            #map based on original id
            new_modules[module.id] = new_module
        
        #create connections
        connections = []
        for connection in workflow.connection_list:
            connections.append(controller.create_connection(
                    new_modules[connection.sourceId],
                    connection.source.spec,
                    new_modules[connection.destinationId],
                    connection.destination.spec))
            
        #create location module
        reg = get_module_registry()
        location_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
                                       'CellLocation'))
        functions = controller.create_functions(location_module,
                [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        for f in functions:
            location_module.add_function(f)
            
        #create location-to-cell connection
        location_connection = controller.create_connection(location_module,
                'self' ,cell_module, 'Location')
            
        return (new_modules.values() + [location_module], 
                connections + [location_connection]), cdms_ports
        
    @staticmethod
    def finish_plot_workflow(controller, pipeline_items, variable_matches, version):
        """Creates connections for the variable_matches and
        adds all pipeline_items to the vistrail
    
        Arguments:
        pipeline_items -- tuple of (modules, connections), usually from
            the create_plot_workflow_items function
        variable_matches -- list of tuples, each containing a variable-port
            pair for which connections will be made
            variable -- vistrails module
            port -- tuple of moduleId, portSpec
        """
                
        #create variable connections
        for module, (in_module, in_port_spec) in variable_matches:
            out_port_spec = module.module_descriptor.port_specs[('self', 'output')]
            connection = controller.create_connection(module,
                                                      out_port_spec,
                                                      in_module,
                                                      in_port_spec)
            pipeline_items[1].append(connection)
            
        #create add operations
        operations = []
        for item in pipeline_items[0] + pipeline_items[1]:
            operations.append(('add', item))
            
        #create layout operations
        #there appear to be issues with PythonSource and the layout algorithm
#        layout_operations = controller.layout_modules_ops(
#                preserve_order=True, 
#                no_gaps=True, 
#                new_modules=pipeline_items[0],
#                new_connections=pipeline_items[1])
            
        action = core.db.action.create_action(operations)# + layout_operations)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action