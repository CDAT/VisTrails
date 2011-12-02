'''
Created on Nov 30, 2011

@author: emanuele
'''

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
                return module.functions[i].params[0].strValue
        return None

    @staticmethod
    def find_modules_by_type(pipeline, moduletype):
        result = []
        for module in pipeline.module_list:
            desc = module.module_descriptor
            if issubclass(desc.module, moduletype):
                result.append(module)
        return result
    
    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, 
                                   plot_obj, row, col):
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
            
            varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
            axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')
            aliases[plot_obj.files[i]] = filename
            aliases[plot_obj.cells[i].row_name] = str(row+1)
            aliases[plot_obj.cells[i].col_name] = str(col+1)
            aliases[plot_obj.vars[i]] = varname
            if len(plot_obj.axes) > i:
                aliases[plot_obj.axes[i]] = axes

        for a,w in plot_obj.alias_widgets.iteritems():
            aliases[a] = w.contents()

        actions = plot_obj.applyChanges(aliases)
        action = actions.pop()
        
        #get the most recent action that is not None
        while action == None:
            action = actions.pop()
        
        return action
    
    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        from gui.uvcdat.plot_configuration import AliasesPlotWidget
        return AliasesPlotWidget(controller,version,plot_obj)
            

    