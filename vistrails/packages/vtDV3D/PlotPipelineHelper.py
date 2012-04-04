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
from packages.vtDV3D.CDMS_VariableReaders import CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader, CDMS_VectorReader
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
    def build_plot_pipeline_action(controller, version, var_modules, plot_objs, row, col, templates=[]):
#        from packages.uvcdat_cdms.init import CDMSVariableOperation 
        controller.change_selected_version(version)
#        print "build_plot_pipeline_action[%d,%d], version=%d, controller.current_version=%d" % ( row, col, version, controller.current_version )
#        print " --> plot_modules = ",  str( controller.current_pipeline.modules.keys() )
#        print " --> var_modules = ",  str( [ var.id for var in var_modules ] )
        #Considering that plot_objs has a single plot_obj
        plot_obj = plot_objs[0]
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
        cell_specs = []
        for j in range(plot_obj.cellnum):
            cell = plot_obj.cells[j] 
            location = cell.address_name if cell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
            cell_spec = "%s%s" % ( chr(ord('A') + col+j ), row+1)
#            aliases[ location ] = cell_spec
            cell_specs.append( '%s!%s' % ( location, cell_spec ) )
#            cell_specs.append( 'location%d!%s' % ( j, cell_spec ) )
#            
#        for a,w in plot_obj.alias_widgets.iteritems():
#            try:    aliases[a] = w.contents()
#            except Exception, err: print>>sys.stderr, "Error updating alias %s:" % str( a ), str(err)

        if plot_obj.serializedConfigAlias and var_modules: aliases[ plot_obj.serializedConfigAlias ] = ';;;' + ( '|'.join( cell_specs) )
        pip_str = core.db.io.serialize(plot_obj.workflow)
        controller.paste_modules_and_connections(pip_str, (0.0,0.0))

        action = plot_obj.addParameterChangesFromAliasesAction( controller.current_pipeline,  controller,  controller.vistrail, controller.current_version, aliases)        
        if action: controller.change_selected_version( action.id )   
        
        reader_1v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader ] )
        reader_2v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VectorReader ] )
#        cell_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ MapCell3D ] )
        reader_modules = reader_1v_modules + reader_2v_modules
        iVarModule = 0
        ops = []
        for module in reader_modules:
            nInputs = 1 if module in reader_1v_modules else 2
            for iInput in range( nInputs ):
                try:
                    var_module = var_modules[ iVarModule ]
                    var_module_in_pipeline = PlotPipelineHelper.find_module_by_id( controller.current_pipeline, var_module.id )
                    if var_module_in_pipeline == None: 
                        ops.append( ( 'add', var_module ) )
                    inputPort = 'variable' if (iInput == 0) else "variable%d" % ( iInput + 1)
                    conn1 = controller.create_connection( var_module, 'self', module, inputPort )
                    ops.append( ( 'add', conn1 ) )
                    iVarModule = iVarModule+1
                except Exception, err:
                    print>>sys.stderr, "Exception adding CDMSVaraible input:", str( err)
                    break
                                   
        try:
            action = core.db.action.create_action(ops)
            controller.add_new_action(action)
            controller.perform_action(action)
        except Exception, err:
            print " Error connecting CDMSVariable to workflow: ", str(err)
            traceback.print_exc()
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
        
        var_modules = DV3DPipelineHelper.find_modules_by_type(pipeline, 
                                                              [CDMSVariable,
                                                               CDMSVariableOperation])
        
        # This assumes that the pipelines will be different except for variable 
        # modules
        controller.change_selected_version(cell.current_parent_version)
        plot_obj = DV3DPipelineHelper.get_plot_by_vistrail_version(plot_type, 
                                                                   controller.vistrail, 
                                                                   controller.current_version)
        if plot_obj is not None:
            plot_obj.current_parent_version = cell.current_parent_version
            plot_obj.current_controller = controller
            cell.plots = [plot_obj]
            #FIXME: this will always spread the cells in the same row
            cell_specs = []
            for j in range(plot_obj.cellnum):
                ccell = plot_obj.cells[j] 
                location = ccell.address_name if ccell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
                cell_spec = "%s%s" % ( chr(ord('A') + col+j ), row+1)
                cell_specs.append( '%s!%s' % ( location, cell_spec ) )
            
            # Update project controller cell information    
            cell.variables = []
            #FIXME: this doesn't work as expected... DV3D should provide a way 
            #to find the variables connected to a plot module so that only the
            # operation or variable connected is added.
            for var in var_modules:
                cell.variables.append(DV3DPipelineHelper.get_variable_name_from_module(var))
        else:
            print "Error: Could not find DV3D plot type based on the pipeline"
            print "Visualizations can't be loaded."            

    
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
                if (DV3DPipelineHelper.are_workflows_compatible(vistrail_a, vistrail_b, 
                                                                version_a, version_b) and
                    len(pipeline.aliases) == len(pl.workflow.aliases)):
                    return pl
        return None
    
    @staticmethod
    def get_variable_name_from_module(module):
        desc = module.module_descriptor.module
        if issubclass(desc, CDMSVariable):
            result = DV3DPipelineHelper.get_value_from_function(module, "name")
        elif issubclass(desc, CDMSVariableOperation):
            result = DV3DPipelineHelper.get_value_from_function(module, "varname")
        else:
            result = None
        return result