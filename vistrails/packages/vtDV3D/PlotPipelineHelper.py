'''

PlotPipelineHelper:
Created on Nov 30, 2011
@author: emanuele

DV3DPipelineHelper:
Created on Feb 29, 2012
@author: tpmaxwel

'''

'''

'''
import core.db.io, sys, traceback, api
import core.modules.basic_modules
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from CDMS_VariableReaders import CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader, CDMS_VectorReader
from packages.uvcdat_cdms.init import CDMSVariableOperation, CDMSVariable 
from core.uvcdat.plot_registry import get_plot_registry
from core.modules.module_registry import get_module_registry


class DV3DPipelineHelper(PlotPipelineHelper):
    '''
    This will take care of pipeline manipulation for plots.
    '''


    def __init__(self):
        '''
        Constructor
        '''

#    @staticmethod
#    def build_plot_pipeline_action(controller, version, var_modules, plot_obj, row, col, template=None):
#        if controller is None:
#            controller = api.get_current_controller()
#            version = 0L
#        reg = get_module_registry()
#        ops = []
#
#        plot_module = controller.create_module_from_descriptor(plot_descriptor)
#        plot_functions =  [('graphicsMethodName', [plot_gm])]
#        if template is not None:
#            plot_functions.append(('template', [template]))
#        initial_values = desc.get_initial_values(plot_gm)
#        for attr in desc.gm_attributes:
#            plot_functions.append((attr,[getattr(initial_values,attr)]))
#            
#        functions = controller.create_functions(plot_module,plot_functions)
#        for f in functions:
#            plot_module.add_function(f)
#        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
#            ops.append(('add', var_modules[0]))
#        ops.append(('add', plot_module)) 
#        
#        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
#            conn = controller.create_connection(var_modules[0], 'self',
#                                                plot_module, 'variable')
#        else:
#            conn = controller.create_connection(var_modules[0], 'output_var',
#                                                plot_module, 'variable')
#        ops.append(('add', conn))
#        if len(var_modules) > 1:
#            if issubclass(var_modules[1].module_descriptor.module, CDMSVariable):
#                conn2 = controller.create_connection(var_modules[1], 'self',
#                                                     plot_module, 'variable2')
#                ops.append(('add', var_modules[1]))
#            else:
#                conn2 = controller.create_connection(var_modules[1], 'output_var',
#                                                     plot_module, 'variable')
#            ops.append(('add', conn2))
#             
#        cell_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 'CDMSCell'))
#        cell_conn = controller.create_connection(plot_module, 'self',
#                                                         cell_module, 'plot')
#        loc_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
#                                       'CellLocation'))
#        functions = controller.create_functions(loc_module,
#            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
#        for f in functions:
#            loc_module.add_function(f)
#        loc_conn = controller.create_connection(loc_module, 'self',
#                                                        cell_module, 'Location')
#        ops.extend([('add', cell_module),
#                    ('add', cell_conn),
#                    ('add', loc_module),
#                    ('add', loc_conn)])
#        action = core.db.action.create_action(ops)
#        controller.change_selected_version(version)
#        controller.add_new_action(action)
#        controller.perform_action(action)
#        return action
     
    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plot_obj, row, col, template=None):
#        from packages.uvcdat_cdms.init import CDMSVariableOperation 
        plot_obj.current_parent_version = version
        plot_obj.current_controller = controller
        aliases = {}
#        for i in range(len(var_modules)):
#            aliases[plot_obj.files[i]] = ''
#            aliases[ ".".join( [plot_obj.files[i],"url"] )  ] =  ""
#            aliases[plot_obj.vars[i]] = ''
#            aliases[ "%s.file" % plot_obj.vars[i] ] =  ""
#                filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'filename')
#                if filename is None:
#                    filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'file')
#                if isinstance( filename, core.modules.basic_modules.File ):
#                    filename = filename.name
#                url = PlotPipelineHelper.get_value_from_function( var_modules[i], 'url')            
#                varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
#                file_varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varNameInFile')
#                axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')

        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            cell = plot_obj.cells[j] 
            location = cell.address_name if cell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
            aliases[ location ] = "%s%s" % ( chr(ord('A') + col+j ), row+1)
#            
        for a,w in plot_obj.alias_widgets.iteritems():
            try:    aliases[a] = w.contents()
            except Exception, err: print>>sys.stderr, "Error updating alias %s:" % str( a ), str(err)

        if plot_obj.serializedConfigAlias and var_modules: aliases[ plot_obj.serializedConfigAlias ] = 'None'
        pip_str = core.db.io.serialize(plot_obj.workflow)
        controller.paste_modules_and_connections(pip_str, (0.0,0.0))

        action = plot_obj.addParameterChangesFromAliasesAction( controller.current_pipeline,  controller,  controller.vistrail, controller.current_version, aliases)        
        if action: controller.change_selected_version( action.id )   
        
        print " ++++++++++++++++++++++++ Running DV3DPipelineHelper ++++++++++++++++++++++++ ++++++++++++++++++++++++  "
        sys.stdout.flush()
        reader_1v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader ] )
        reader_2v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VectorReader ] )
#        cell_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ MapCell3D ] )
        reader_modules = reader_1v_modules + reader_2v_modules
        iVarModule = 0
        ops = []
        for module in reader_modules:
            nInputs = 1 if module in reader_1v_modules else 2
            for iInput in range( nInputs ):
                var_module = var_modules[ iVarModule ]
                var_module_in_pipeline = PlotPipelineHelper.find_module_by_id( controller.current_pipeline, var_module.id )
                if var_module_in_pipeline == None: 
                    ops.append( ( 'add', var_module ) )
                inputPort = 'variable' if (iInput == 0) else "variable%d" % ( iInput + 1)
                conn1 = controller.create_connection( var_module, 'self', module, inputPort )
                ops.append( ( 'add', conn1 ) )
                iVarModule = iVarModule+1
                                   
        try:
            action = core.db.action.create_action(ops)
            controller.add_new_action(action)
            controller.perform_action(action)
        except Exception, err:
            print " Error connecting CDMSVariable to workflow: ", str(err)
            traceback.print_exc()
        return action

                           
#                desc = var_module.module_descriptor
#                if issubclass( desc.module, CDMSVariableOperation ):
#                    varname = PlotPipelineHelper.get_value_from_function( var_module, 'varname' )
#                    python_command = PlotPipelineHelper.get_value_from_function( var_module, 'python_command' )
#                    aliases[plot_obj.vars[iVarModule]] = varname
#                    aliases[ "%s.cmd" % plot_obj.vars[iVarModule] ] = python_command
#                else:
#                    filename = PlotPipelineHelper.get_value_from_function( var_module, 'filename')
#                    if filename is None:
#                        filename = PlotPipelineHelper.get_value_from_function( var_module, 'file')
#                    if isinstance( filename, core.modules.basic_modules.File ):
#                        filename = filename.name
#                    url = PlotPipelineHelper.get_value_from_function( var_module, 'url')            
#                    varname = PlotPipelineHelper.get_value_from_function( var_module, 'name')
#                    file_varname = PlotPipelineHelper.get_value_from_function( var_module, 'varNameInFile')
#                    axes = PlotPipelineHelper.get_value_from_function( var_module, 'axes')
#                    aliases[plot_obj.files[iVarModule]] = filename
#                    aliases[ ".".join( [plot_obj.files[iVarModule],"url"] )  ] = url if url else ""
#                    aliases[plot_obj.vars[iVarModule]] = varname
#                    aliases[ "%s.file" % plot_obj.vars[iVarModule] ] = file_varname if file_varname else ""
#                    if len(plot_obj.axes) > iVarModule:
#                        aliases[plot_obj.axes[iVarModule]] = axes
#
#        #FIXME: this will always spread the cells in the same row
#        for j in range(plot_obj.cellnum):
#            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
#                aliases[plot_obj.cells[j].row_name] = str(row+1)
#                aliases[plot_obj.cells[j].col_name] = str(col+1+j)
#            elif plot_obj.cells[j].address_name:
#                aliases[plot_obj.cells[j].address_name] = "%s%s" % ( chr(ord('A') + col+j ), row+1)
#            
#        for a,w in plot_obj.alias_widgets.iteritems():
#            try:    aliases[a] = w.contents()
#            except: print>>sys.stderr, "Error updating alias %s", str( a )
#
#
#        actions = plot_obj.applyChanges(aliases)
#        action = actions.pop()
#        
#        #get the most recent action that is not None
#        while action == None:
#            action = actions.pop()
#        
#        return action
    
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
            

    
