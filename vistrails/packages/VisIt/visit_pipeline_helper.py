from packages.uvcdat.init import Variable, Plot
from packages.uvcdat_cdms.init import CDMSVariable
from packages.uvcdat.init import expand_port_specs as _expand_port_specs
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper, CDMSPlotWidget

from core.uvcdat.plot_registry import get_plot_registry
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import Module
from core.uvcdat.plotmanager import get_plot_manager
from packages.spreadsheet.basic_widgets import CellLocation, SpreadsheetCell

import core.db.action
import core.db.io
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot, pyqtSignal
from packages.uvcdat_cdms.init import CDMSPlot, CDMSVariable, CDMSCell, CDMSVariableOperation, \
       CDMSUnaryVariableOperation, CDMSBinaryVariableOperation, \
       CDMSNaryVariableOperation
from gui.uvcdat.uvcdatCommons import plotTypes
import api

import visitcell


class VisItPipelineHelper(PlotPipelineHelper):

    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        pipeline = controller.vt_controller.vistrail.getPipeline(version)
        #print pipeline
        #plots = VisItPipelineHelper.find_plot_modules(pipeline)
        cell = CDMSPipelineHelper.find_modules_by_type(pipeline,[visitcell.VisItCell])
        vars = CDMSPipelineHelper.find_modules_by_type(pipeline,
                                                       [CDMSVariable,
                                                        CDMSVariableOperation])
        if len(cell) == 0:
            return visitcell.VisItCellConfigurationWidget(None,controller)
        else:
            vcell = cell[0].module_descriptor.module()
            #print "cellWidget should not be None", vcell, vcell.cellWidget
            return visitcell.VisItCellConfigurationWidget(cell[0],controller)

    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plots,row, col):
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        #plot_type = plots[0].parent
        #plot_gm = plots[0].name

        if controller is None:
            controller = api.get_current_controller()
            version = 0L

        reg = get_module_registry()
        ops = []
        cell_module = None

        pipeline = controller.vistrail.getPipeline(version)

        var_module = var_modules[0]

        try:
            temp_var_module = pipeline.get_module_by_id(var_module.id)
        except KeyError:
            temp_var_module = None

        if temp_var_module is not None:
            var_module = temp_var_module
        else:
            ops.append(('add',var_module))

        for plot in plots:

            plot_type = plot.parent
            plot_gm = plot.name

            import re
            plotname = re.sub(r'\s', '', plot_gm)

            plot_module = PlotPipelineHelper.find_module_by_name(pipeline, plotname)
            if plot_module is not None:
                continue

            plot_descriptor = reg.get_descriptor_by_name('gov.lbl.visit', 'VisItCell')
            plot_module = controller.create_module_from_descriptor(plot_descriptor)

            ops.append(('add',plot_module))

            #if cell_module is None:
            #    cell_module = PlotPipelineHelper.find_module_by_name(pipeline, "VisItCell")

            if cell_module is None:
                #cell_desc = reg.get_descriptor_by_name('gov.lbl.visit', "VisItCell")
                #cell_module = controller.create_module_from_descriptor(cell_desc)
                #ops.append(('add', cell_module))
                cell_module = plot_module

                if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
                    conn = controller.create_connection(var_module, 'self',
                                                        plot_module, 'variable')
                else:
                    conn = controller.create_connection(var_module, 'self',
                                                        cell_module, 'variable')
                ops.append(('add', conn))
                #print 'connection source id is ', conn.sourceId
                #print 'connection dest id is ', conn.destinationId

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

                type_of_plot = str(plot_gm)
                param_module = controller.create_module_from_descriptor(
                    reg.get_descriptor_by_name('gov.lbl.visit', 'VisItParams'))

                functions = controller.create_functions(param_module,
                    [('renderType', [type_of_plot])])
                for f in functions:
                    param_module.add_function(f)

                param_conn = controller.create_connection(param_module, 'self',
                                                        plot_module, 'visitparams')
                ops.extend([('add', param_module),
                            ('add', param_conn)])

            # Create connection between the cell and the representation
            #conn = controller.create_connection(plot_module, 'self',
            #                                    cell_module, 'representation')

            # Add the connection to the pipeline operations
            #ops.append(('add', conn))

        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action

        ##plot_descriptor = reg.get_descriptor_by_name('gov.lbl.visit','VisItCell')
        ##plot_module = controller.create_module_from_descriptor(plot_descriptor)

        #for var_mods in var_modules:
        #    print "mods: ",var_mods

        ##if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
        ##    ops.append(('add', var_modules[0]))
        ##ops.append(('add', plot_module))

        ##if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
        ##    conn = controller.create_connection(var_modules[0], 'self',
        ##                                        plot_module, 'variable')
        ##else:
        ##    conn = controller.create_connection(var_modules[0], 'output_var',
        ##                                        plot_module, 'variable')
        ##ops.append(('add', conn))

        ##type_of_plot = str(plot_gm)
        ##param_module = controller.create_module_from_descriptor(
        ##    reg.get_descriptor_by_name('gov.lbl.visit',
        ##                               'VisItParams'))

        ##functions = controller.create_functions(param_module,
        ##    [('renderType', [type_of_plot])])
        ##for f in functions:
        ##    param_module.add_function(f)
        ##param_conn = controller.create_connection(param_module, 'self',
        ##                                                plot_module, 'visitparams')
        ##ops.extend([('add', param_module),
        ##            ('add', param_conn)])

        ##loc_module = controller.create_module_from_descriptor(
        ##    reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet',
        ##                               'CellLocation'))
        ##functions = controller.create_functions(loc_module,
        ##    [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        ##for f in functions:
        ##    loc_module.add_function(f)
        ##loc_conn = controller.create_connection(loc_module, 'self',
        ##                                                plot_module, 'Location')
        ##ops.extend([('add', loc_module),
        ##            ('add', loc_conn)])

        #type_of_plot = plot_gm
        #param_module = controller.create_module_from_descriptor(
        #    reg.get_descriptor_by_name('gov.lbl.visit',
        #                               'VisItParams'))

        #functions = controller.create_functions(param_module,
        #    [('renderType', [type_of_plot])])
        #for f in functions:
        #    param_module.add_function(f)
        #param_conn = controller.create_connection(param_module, 'self',
         #                                               plot_module, 'visitparams')
        #ops.extend([('add', param_module),
        #            ('add', param_conn)])

        ##action = core.db.action.create_action(ops)
        ##controller.change_selected_version(version)
        ##controller.add_new_action(action)
        ##controller.perform_action(action)
        ##return action

    @staticmethod
    def find_plot_modules(pipeline):
        #find plot modules in the order they appear in the Cell
        res = []
        #cell = CDMSPipelineHelper.find_module_by_name(pipeline, 'VisItCell')
        #plots = pipeline.get_inputPort_modules(cell.id,'plot')
        #for plot in plots:
        #    res.append(pipeline.modules[plot])
        return res


    @staticmethod
    def load_pipeline_in_location(pipeline, controller, sheetName, row, col,plot_type, cell):
        #cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, [CellLocation])
        #cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [SpreadsheetCell])

        # we assume that there is only one CellLocation and one SpreadsheetCell
        # update location values in place.
        #loc_module = cell_locations[0]
        #for i in xrange(loc_module.getNumFunctions()):
        #    if loc_module.functions[i].name == 'Row':
        #        loc_module.functions[i].params[0].strValue = str(row+1)
        #    elif loc_module.functions[i].name == "Column":
        #        loc_module.functions[i].params[0].strValue = str(col+1)
        pass

    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot=None):
        #pipeline = controller.vistrail.getPipeline(version)
        return "unsupported operation"



    @staticmethod
    def copy_pipeline_to_other_location(pipeline, controller, sheetName, row, col,plot_type, cell):
        return None
#        print "copyt pipeline to other location"
#        pip_str = core.db.io.serialize(pipeline)
#        controller.change_selected_version(cell.current_parent_version)
#
#        modules = controller.paste_modules_and_connections(pip_str, (0.0,0.0))
#        cell.current_parent_version = controller.current_version
#        pipeline = controller.current_pipeline
#
#        reg = get_module_registry()
#        cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, [CellLocation])
#        cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [SpreadsheetCell])
#
#        #we assume that there is only one CellLocation and one SpreadsheetCell
#        # delete location and create another one with the right locations
#        action = controller.delete_module_list([cell_locations[0].id])
#        cell.current_parent_version = action.id
#
#        loc_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet',
#                                       'CellLocation'))
#        functions = controller.create_functions(loc_module,
#            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
#        for f in functions:
#            loc_module.add_function(f)
#        loc_conn = controller.create_connection(loc_module, 'self',
#                                                cell_modules[0], 'Location')
#        ops = [('add', loc_module),
#               ('add', loc_conn)]
#
#        action = core.db.action.create_action(ops)
#        controller.change_selected_version(cell.current_parent_version)
#        controller.add_new_action(action)
#        controller.perform_action(action)
#        cell.current_parent_version = action.id
#
#        # Update project controller cell information
#        pipeline = controller.vistrail.getPipeline(action.id)
#        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
#        for plot in cell.plots:
#            plot.variables = []
#        #for plot in plot_modules:
#        #    vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(controller,
#        #                                                               pipeline,
#        #                                                               plot.id)
#        #    for var in vars:
#        #        cell.variables.append(CDMSPipelineHelper.get_variable_name_from_module(var))
#
#        #FIXME: This does not consider if the workflow has more than one plot
#        #gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_modules[0])
#        #ptype = CDMSPipelineHelper.get_plot_type_from_module(plot_modules[0])
#        #cell.plot = get_plot_manager().get_plot(plot_type, ptype, gmName)
#        return action