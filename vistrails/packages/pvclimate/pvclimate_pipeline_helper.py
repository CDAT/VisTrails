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

# Import PV Generic Cell
from pvgenericcell import PVGenericCell
import pvclimate_widget

import sys

class PVClimatePipelineHelper(PlotPipelineHelper):

    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        print 'Calling show_configuration_widget'
        print 'version: ', version

        # Grab the pipeline
        pipeline = controller.vt_controller.vistrail.getPipeline(version)

        # plots = VisItPipelineHelper.find_plot_modules(pipeline)

        # Find the cell
        cell = CDMSPipelineHelper.find_modules_by_type(pipeline,[PVGenericCell])

        PVClimatePipelineHelper.find_plot_representation(pipeline, PVClimatePipelineHelper.find_plot_modules(pipeline)[0])

        # FIXME: Remove this hack
        if len(cell) == 0:
          print >> sys.stderr, 'cell is empty'
          return None

        if len(cell) == 0:
            return pvclimate_widget.PVClimateCellConfigurationWidget(None,
                                                                  controller.vt_controller)
        else:
            pvcell = cell[0].module_descriptor.module()
            # Create child widgets
            # Attach it to the parent widget
            return pvclimate_widget.PVClimateCellConfigurationWidget(cell[0],
                                                                  controller.vt_controller)

    @staticmethod
    def find_plot_representation(pipeline, representation):
        #print 'rep dir ', dir(representation)
        print 'name ', representation.name
#        print  'output port ', representation.forceGetOutputListFromPort('self')[0]
#        print 'type of ', type(representation.forceGetOutputListFromPort('self')[0])
        return pipeline.modules[pipeline.get_outputPort_modules(representation.id, 'self')[0]]

    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plots,row, col, template=None):
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        #print 'Calling build_plot_pipWeline_action'

        # Get controller
        if controller is None:
            controller = api.get_current_controller()
            version = 0L

        # Get module registry
        reg = get_module_registry()
        ops = []
        cell_module = None

        # First get the pipeline
        pipeline = controller.vistrail.getPipeline(version)

        # FIXME: Add support for multiple variables per plot
        # Use only the first var module for now
        var_module = var_modules[0]

        # Aashish: As of now, very first time var module is being added to the pipeline by the project controller
        # but second time on the same cell, it gets removed and hence we needed to add var module again to pipeline.
        # I need to put this code under try catch because as of now looking for an id that does not exists
        # results in exception.
        try:
            temp_var_module = pipeline.get_module_by_id(var_module.id)
        except KeyError:
            temp_var_module = None

        if temp_var_module is not None:
            var_module = temp_var_module
        else:
            # This time we need to add var module to the pipeline
            ops.append(('add', var_module))

        for plot in plots:
            plot_type = plot.parent
            plot_gm = plot.name

            #
            # Create plot module from the descriptor
            #
            #######################################################################

            # Is there a better way? I looked around and found none
            import re
            plotUsableName = re.sub(r'\s', '', plot_gm)

            plot_module = PlotPipelineHelper.find_module_by_name(pipeline, plotUsableName)
            if plot_module is not None:
                continue

            plot_descriptor = reg.get_descriptor_by_name('com.kitware.pvclimate', plotUsableName)
            plot_module = controller.create_module_from_descriptor(plot_descriptor)

            # Aashish: This is no longer required as of this commit
            # e13bb034ceb302afe3aad3caf20153e1525586db
            # I am not sure though why we still need to add plot module
            #ops.append(('add', var_modules[0]))

            ops.append(('add', plot_module))

            #print >> sys.stderr, 'var_modules[0] ', var_modules[0]

            #
            # Create cell - representation linkage
            #
            #######################################################################

            # Check to see if a cell already exits, if yes then set the input (representation on it) or else
            # create a new one and then set the representation on it.

            if cell_module is None:
                cell_module = PlotPipelineHelper.find_module_by_name(pipeline, "PVGenericCell")

            # If cell module is None, then create a new one
            if cell_module is None:
                cell_desc = reg.get_descriptor_by_name('com.kitware.pvclimate', "PVGenericCell")
                cell_module = controller.create_module_from_descriptor(cell_desc)
                ops.append(('add', cell_module))

                #
                # Create a connection between the cell and the variable
                # Aashish: I am expecting that every time we drop a variable, we will get a
                # pipeline that does not have modules from the previous execution. I need to verify
                # this but for now this assumption seems to hold.
                #
                #######################################################################

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

            # Create connection between the cell and the representation
            conn = controller.create_connection(plot_module, 'self',
                                                cell_module, 'representation')

            # Add the connection to the pipeline operations
            ops.append(('add', conn))

        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action

    @staticmethod
    def find_plot_modules(pipeline):
        # Find plot modules in the order they appear in the Cell
        res = []
        cell = PlotPipelineHelper.find_module_by_name(pipeline, 'PVGenericCell')
        plots = pipeline.get_inputPort_modules(cell.id, 'representation')
        for plot in plots:
            res.append(pipeline.modules[plot])
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


