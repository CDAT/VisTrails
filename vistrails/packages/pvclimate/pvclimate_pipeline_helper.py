# Import vistrails / cdms modules
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

import pvclimatecell

import sys

class PVClimatePipelineHelper(PlotPipelineHelper):

    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        print 'Calling show_configuration_widget'

        # Grab the pipeline
        pipeline = controller.vt_controller.vistrail.getPipeline(version)

        #plots = VisItPipelineHelper.find_plot_modules(pipeline)
        # Fine the cell
        cell = CDMSPipelineHelper.find_modules_by_type(pipeline,[pvclimatecell.PVClimateCell])
        vars = CDMSPipelineHelper.find_modules_by_type(pipeline,
                                                       [CDMSVariable,
                                                        CDMSVariableOperation])

        # FIXME: Remove this hack
        if len(cell) == 0:
          print >> sys.stderr, 'cell is empty'
          return None

        if len(cell) == 0:
            return pvclimatecell.PVClimateCellConfigurationWidget(None,controller)
        else:
            pvcell = cell[0].module_descriptor.module()
            return pvclimatecell.PVClimateCellConfigurationWidget(cell[0],controller)

    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plot_obj,row, col, template=None):
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        print 'Calling build_plot_pipWeline_action'

        plot_type = plot_obj[0].parent
        plot_gm = plot_obj[0].name

        # Get controller
        if controller is None:
            controller = api.get_current_controller()
            version = 0L

        # Get module registry
        reg = get_module_registry()
        ops = []                

        # Create the module from the descriptor          
        plot_descriptor = reg.get_descriptor_by_name('com.kitware.pvclimate','PVClimateCell')
        plot_module = controller.create_module_from_descriptor(plot_descriptor)
        
        # Get the variable and the plot and create the pipeline connection
        #if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
        #    ops.append(('add', var_modules[0]))
        #ops.append(('add', var_modules[0]))
        ops.append(('add', plot_module))

        print >> sys.stderr, 'var_modules[0] ', var_modules[0]

        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
            conn = controller.create_connection(var_modules[0], 'self',
                                                plot_module, 'variable')
        else:
            conn = controller.create_connection(var_modules[0], 'self',
                                                plot_module, 'variable')
        ops.append(('add', conn))

        type_of_plot = str(plot_gm)
        print 'Type of plot is ', type_of_plot

        # Aashish: I don't think this is required
#        param_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('gov.lbl.visit',
#                                       'VisItParams'))
#
#        functions = controller.create_functions(param_module,
#            [('renderType', [type_of_plot])])
#        for f in functions:
#            param_module.add_function(f)
#        param_conn = controller.create_connection(param_module, 'self',
#                                                        plot_module, 'visitparams')
#        ops.extend([('add', param_module),
#                    ('add', param_conn)])
#
        loc_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet',
                                       'CellLocation'))
        functions = controller.create_functions(loc_module,
            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        for f in functions:
            loc_module.add_function(f)
        loc_conn = controller.create_connection(loc_module, 'self',
                                                plot_module, 'Location')
        ops.extend([('add', loc_module),
                    ('add', loc_conn)])

        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action

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
       print "Load pipeline is called"
       cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, [CellLocation])
       cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [SpreadsheetCell])
       #plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])

       # we assume that there is only one CellLocation and one SpreadsheetCell
       # update location values in place.
       loc_module = cell_locations[0]
       for i in xrange(loc_module.getNumFunctions()):
           if loc_module.functions[i].name == 'Row':
               loc_module.functions[i].params[0].strValue = str(row+1)
           elif loc_module.functions[i].name == "Column":
               loc_module.functions[i].params[0].strValue = str(col+1)

       # Update project controller cell information
       #cell.variables = []
       #for plot in plot_modules:
       #    vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(controller,
       #                                                               pipeline,
       #                                                               plot.id)
       #    for var in vars:
       #        cell.variables.append(CDMSPipelineHelper.get_variable_name_from_module(var))

       #FIXME: This will return only the first plot type it finds.
       #gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_modules[0])
       #ptype = CDMSPipelineHelper.get_plot_type_from_module(plot_modules[0])
       #cell.plot = get_plot_manager().get_plot(plot_type, ptype, gmName)


    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot=None):
        print "build_python_script"
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
            text += ident + "kwargs = %s\n"%plot.kwargs
            text += ident + "canvas.plot(gm%s,*args, **kwargs)\n"%(plot.plot_type)
        text += '    sys.exit(app.exec_())'
        return text



    @staticmethod
    def copy_pipeline_to_other_location(pipeline, controller, sheetName, row, col,plot_type, cell):
        print "copyt pipeline to other location"
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
        #for plot in plot_modules:
        #    vars = CDMSPipelineHelper.find_variables_connected_to_plot_module(controller,
        #                                                               pipeline,
        #                                                               plot.id)
        #    for var in vars:
        #        cell.variables.append(CDMSPipelineHelper.get_variable_name_from_module(var))

        #FIXME: This does not consider if the workflow has more than one plot
        #gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_modules[0])
        #ptype = CDMSPipelineHelper.get_plot_type_from_module(plot_modules[0])
        #cell.plot = get_plot_manager().get_plot(plot_type, ptype, gmName)
        return action


