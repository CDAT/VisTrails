'''
Created on Nov 30, 2011

@author: emanuele
'''
import core.db.io, sys
import core.modules.basic_modules

class PlotPipelineHelper(object):
    '''
    This will take care of pipeline manipulation for plots.
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
    @staticmethod
    def find_module_by_name(pipeline, module_name):
        for module in pipeline.module_list:
            if module.name == module_name:
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
    def build_plot_pipeline_action(controller, version, var_modules, 
                                   plot_obj, row, col, template=None):
        #for now, this helper will generate change parameter actions based on the
        #alias dictionary
        #first set the plot:
        plot_obj.current_parent_version = version
        plot_obj.current_controller = controller
        aliases = {}
        for i in range(len(var_modules)):
            filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'filename')
            if filename is None:
                filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'file')
            if isinstance( filename, core.modules.basic_modules.File ):
                filename = filename.name
            url = PlotPipelineHelper.get_value_from_function( var_modules[i], 'url')            
            varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
            axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')
            aliases[plot_obj.files[i]] = filename
            aliases[ ".".join( [plot_obj.files[i],"url"] )  ] = url if url else ""
            aliases[plot_obj.vars[i]] = varname
            if len(plot_obj.axes) > i:
                aliases[plot_obj.axes[i]] = axes

        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                aliases[plot_obj.cells[j].row_name] = str(row+1)
                aliases[plot_obj.cells[j].col_name] = str(col+1+j)
            elif plot_obj.cells[j].address_name:
                aliases[plot_obj.cells[j].address_name] = "%s%s" % ( chr(ord('A') + col+j ), row+1)
            
        for a,w in plot_obj.alias_widgets.iteritems():
            try:    aliases[a] = w.contents()
            except: print>>sys.stderr, "Error updating alias %s", str( a )

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
        cell.plot = plot_obj
        
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
            cell.variables.append(aliases[plot_obj.vars[i]])
            
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
        cell.plot = plot_obj
            
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
    def build_python_script_from_pipeline(controller, version, plot=None):
        from api import load_workflow_as_function
        text = "from api import load_workflow_as_function\n"
        if plot:
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
    def show_configuration_widget(controller, version, plot_obj=None):
        from gui.uvcdat.plot_configuration import AliasesPlotWidget
        return AliasesPlotWidget(controller,version,plot_obj)
            

    