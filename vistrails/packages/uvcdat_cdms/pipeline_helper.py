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
       CDMSUnaryVariableOperation, CDMSBinaryVariableOperation
from widgets import GraphicsMethodConfigurationWidget
from gui.theme import CurrentTheme
from gui.common_widgets import QDockPushButton
from gui.uvcdat.dockplot import PlotTreeWidgetItem
from gui.uvcdat.uvcdatCommons import plotTypes
import api

class CDMSPipelineHelper(PlotPipelineHelper):
    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        pipeline = controller.vt_controller.vistrail.getPipeline(version)
        plots = CDMSPipelineHelper.find_plot_modules(pipeline)
        vars = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSVariable)
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
    def build_variable_operation_pipeline(controller, version, vars, txt, st, 
                                          varname):
        reg = get_module_registry()
        controller.change_selected_version(version)
        if len(vars) == 1:
            op_desc = reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 
                                       'CDMSUnaryVariableOperation')
        elif len(vars) == 2:
            op_desc = reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 
                                       'CDMSBinaryVariableOperation')
        op_module = controller.create_module_from_descriptor(op_desc)
        op_functions = [('varname', [varname]),
                        ('python_command', [st])]
        functions = controller.create_functions(op_module,op_functions)
        for f in functions:
            op_module.add_function(f)
        ops = []
        ops.append(('add', op_module))
        
        if (len(vars) == 1 and 
            issubclass(vars[0].module_descriptor.module, CDMSVariable)):
                ops.append(('add', vars[0]))
                conn1 = controller.create_connection(vars[0], 'self',
                                                     op_module, 'input_var')
                ops.append(('add', conn1))
        elif len(vars) == 2:
            if issubclass(vars[0].module_descriptor.module, CDMSVariable):
                ops.append(('add', vars[0]))
                conn1 = controller.create_connection(vars[0], 'self',
                                                     op_module, 'input_var1')
                ops.append(('add', conn1))
            else:
                # vars[0] is an operation module
                conn1 = controller.create_connection(vars[0], 'output_var',
                                                     op_module, 'input_var')
                ops.append(('add', conn1))
            if issubclass(vars[1].module_descriptor.module, CDMSVariable):
                ops.append(('add', vars[1]))
                conn2 = controller.create_connection(vars[1], 'self',
                                                     op_module, 'input_var2')
                ops.append(('add', conn2))
        
            else:
                # vars[1] is an operation module
                conn2 = controller.create_connection(vars[1], 'output_var',
                                                     op_module, 'input_var2')
                ops.append(('add', conn2))
                                
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
    def build_plot_pipeline_action(controller, version, var_modules, plot_obj, row, col):
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        plot_type = plot_obj.parent
        plot_gm = plot_obj.name
        if controller is None:
            controller = api.get_current_controller()
            version = 0L
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
        print var_modules[0]
        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
            ops.append(('add', var_modules[0]))
        ops.append(('add', plot_module)) 
        
        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
            conn = controller.create_connection(var_modules[0], 'self',
                                                plot_module, 'variable')
        else:
            conn = controller.create_connection(var_modules[0], 'output_var',
                                                plot_module, 'variable')
        ops.append(('add', conn))
        if len(var_modules) > 1:
            if issubclass(var_modules[1].module_descriptor.module, CDMSVariable):
                conn2 = controller.create_connection(var_modules[1], 'self',
                                                     plot_module, 'variable2')
                ops.append(('add', var_modules[1]))
            else:
                conn2 = controller.create_connection(var_modules[1], 'output_var',
                                                     plot_module, 'variable')
            ops.append(('add', conn2))
             
        cell_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 'CDMSCell'))
        cell_conn = controller.create_connection(plot_module, 'self',
                                                         cell_module, 'plot')
        loc_module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
                                       'CellLocation'))
        functions = controller.create_functions(loc_module,
            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
        for f in functions:
            loc_module.add_function(f)
        loc_conn = controller.create_connection(loc_module, 'self',
                                                        cell_module, 'Location')
        ops.extend([('add', cell_module),
                    ('add', cell_conn),
                    ('add', loc_module),
                    ('add', loc_conn)])
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
        cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, CellLocation)
        cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, SpreadsheetCell) 
        
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
        var_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSVariable)
        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSPlot)
        cell.variables =[]
        for var in var_modules:
            cell.variables.append(CDMSPipelineHelper.get_value_from_function(var, 'name'))
            
        #FIXME: This does not consider if the workflow has more than one plot
        gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_modules[0])
        ptype = CDMSPipelineHelper.get_plot_type_from_module(plot_modules[0])
        cell.plot = get_plot_manager().get_plot(plot_type, ptype, gmName)
        return action
    
    @staticmethod
    def load_pipeline_in_location(pipeline, controller, sheetName, row, col, 
                                 plot_type, cell):
        """load_pipeline_in_location(pipeline, controller, sheetName, row, col, 
                                 plot_type, cell) -> None
        This assumes that the pipeline is already set to run in that location 
        and if not it will update the pipeline in place without generating new 
        actions. It will update the cell with the variables and plot types """
        
        reg = get_module_registry()
        cell_locations = CDMSPipelineHelper.find_modules_by_type(pipeline, CellLocation)
        cell_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, SpreadsheetCell) 
        var_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSVariable)
        plot_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSPlot)
        
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
        for var in var_modules:
            cell.variables.append(CDMSPipelineHelper.get_value_from_function(var, 'name'))
            
        #FIXME: This will return only the first plot type it finds.
        gmName = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_modules[0])
        ptype = CDMSPipelineHelper.get_plot_type_from_module(plot_modules[0])
        cell.plot = get_plot_manager().get_plot(plot_type, ptype, gmName)
        
    @staticmethod
    def update_pipeline_action(controller, version, plot_modules):
        pipeline = controller.vistrail.getPipeline(version)
        pip_plots =  CDMSPipelineHelper.find_plot_modules(pipeline)
        cell = CDMSPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
        
        pip_plot_map = {}
        plot_map = {}
        
        to_be_added = []
        for pm in pip_plots:
            pip_plot_map[pm.id] = pm
        for m in plot_modules:
            plot_map[m.id] = m
            if m.id not in pip_plot_map:
                to_be_added.append(m)
        to_be_removed = []
        for pm in pip_plots:
            if pm.id not in plot_map:
                to_be_removed.append(pm.id)
        if len(to_be_removed) > 0:
            action = controller.delete_module_list(to_be_removed)
            version = action.id
            pipeline = controller.vistrail.getPipeline(version)
            
        
        ops = []
        conns_to = controller.get_connections_to(pipeline,[cell.id],"plot")    
        for conn in conns_to:
            if conn.source.moduleId not in to_be_removed:
                ops.append(('delete',conn.id))
        for m in to_be_added:
            ops.append(('add', m))
        for m in plot_modules:
            conn = controller.create_connection(m, 'self',
                                                cell, 'plot')
            ops.append('add',conn)
        
        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
        
    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot=None):
        pipeline = controller.vistrail.getPipeline(version)
        var_modules = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSVariable)
        var_operations = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSVariableOperation)
        cell = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSCell)
        plots = CDMSPipelineHelper.find_plot_modules(pipeline)
        text = "from PyQt4 import QtCore, QtGui\n"
        text += "import cdms2, cdutil, genutil\n"
        text += "import vcs\n\n"
        text += "if __name__ == '__main__':\n"
        text += "    import sys\n"
        text += "    app = QtGui.QApplication(sys.argv)\n"
        ident = '    '
        for varm in var_modules:
            var = CDMSVariable.from_module(varm)
            text += var.to_python_script(ident=ident)
    
        for varop in var_operations:
            desc = varop.module_descriptor.module
            op = desc.from_module(varop)
            if issubclass(desc, CDMSUnaryVariableOperation):
                varm = CDMSPipelineHelper.find_variables_connected_to_unary_operation_module(controller, pipeline, varop.id)
                var = CDMSVariable.from_module(varm)
                text += op.to_python_script(ident=ident)
            elif issubclass(desc, CDMSBinaryVariableOperation):
                [varm1, varm2] = CDMSPipelineHelper.find_variables_connected_to_binary_operation_module(controller, pipeline, varop.id)
                var1 = CDMSVariable.from_module(varm1)
                var2 = CDMSVariable.from_module(varm2)
                text += op.to_python_script(ident=ident)
                
        text += ident + "canvas = vcs.init()\n"
        for mplot in plots:
            plot = mplot.module_descriptor.module.from_module(mplot)
            text += ident + "gm%s = canvas.get%s('%s')\n"%(plot.plot_type, 
                                                 plot.plot_type.lower(), 
                                                 plot.graphics_method_name)
            text += ident + "args = []\n"
            for varm in CDMSPipelineHelper.find_variables_connected_to_plot_module(controller, pipeline, mplot.id):
                desc = varm.module_descriptor
                if issubclass(desc.module, CDMSVariable):
                    var = CDMSVariable.from_module(varm)
                    text += ident + "args.append(%s)\n"%var.name
                else:
                    #operation
                    op = desc.module.from_module(varm)
                    text += ident + "args.append(%s)\n"%op.varname 
                
            if plot.graphics_method_name != 'default':
                for k in plot.gm_attributes:
                    if hasattr(plot,k):
                        if k in ['level_1', 'level_2', 'color_1',
                                 'color_2', 'legend', 'levels',
                                 'missing', 'datawc_calendar', 'datawc_x1', 
                                 'datawc_x2', 'datawc_y1', 'datawc_y2',
                                 'fillareacolors', 'fillareaindices']:
                            text += ident + "gm%s.%s = %s\n"%(plot.plot_type,
                                                      k,  getattr(plot,k))
                        else:
                            text += ident + "gm%s.%s = '%s'\n"%(plot.plot_type,
                                                            k, getattr(plot,k))
            text += ident + "kwargs = %s\n"%plot.kwargs
            text += ident + "canvas.plot(gm%s,*args, **kwargs)\n"%(plot.plot_type) 
        text += '    sys.exit(app.exec_())'           
        return text
    
    @staticmethod    
    def get_graphics_method_name_from_module(module):
        result = CDMSPipelineHelper.get_fun_value_from_module(module, 
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
        result = CDMSPipelineHelper.get_fun_value_from_module(module, 
                                                              "template")
        if result == None:
            result = 'starter'
        
        return result
    
    @staticmethod
    def get_fun_value_from_module(module, name):
        for i in xrange(module.getNumFunctions()):
            if module.functions[i].name == name:
                return module.functions[i].params[0].strValue
        return None
    
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
        #self.tab_widget.addTab(self.var_widget, "Variables")
        #self.tab_widget.addTab(self.plot_widget, "Plots")
        #main_layout.addWidget(self.tab_widget)
        
        main_layout.addWidget(var_label)
        main_layout.addWidget(self.var_widget)
        main_layout.addWidget(plot_label)
        main_layout.addWidget(self.plot_widget)
        
        b_layout = QtGui.QHBoxLayout()
        b_layout.setMargin(5)
        b_layout.addStretch()
        self.btn_save = QDockPushButton('&Save', self)
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
        
        #signals
        self.plot_table.itemSelectionChanged.connect(self.update_conf_widget)
        self.btn_add_plot.clicked.connect(self.add_plot)
        self.btn_del_plot.clicked.connect(self.remove_plot)
        self.btn_move_up.clicked.connect(self.plot_table.move_item_up)
        self.btn_move_down.clicked.connect(self.plot_table.move_item_down)
        self.plot_widget.setLayout(self.v_layout)
        self.plot_table.populate_from_plots(self.plots)
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
            
        if plot_item.vars[order] != var:
            plot_item.vars.pop(order)
            plot_item.vars.insert(order,var)
            
        
    @pyqtSlot()
    def variable1_edited(self):
        var = self.var_table.get_var_by_name(str(self.var1_edt.text()))
        if var:
            plot_item = self.plot_table.selectedItems()[0]
            if len(plot_item.vars) == 0:
                plot_item.vars.append(var)
            elif plot_item.vars[0] != var:
                plot_item.vars.pop(0)
                plot_item.vars.insert(0,var)
                
    @pyqtSlot()
    def variable2_edited(self):
        var = self.var_table.get_var_by_name(str(self.var2_edt.text()))
        if var:
            plot_item = self.plot_table.selectedItems()[0]
            if len(plot_item.vars) < 1:
                plot_item.vars.append(var)
                plot_item.vars.append(var)
            if plot_item.vars[1] != var:
                plot_item.vars.pop(1)
                plot_item.vars.insert(1,var)            
        
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
            #self.conf_widget.setVisible(False)
            self.v_layout.removeWidget(self.conf_widget)
            self.disconnect_signals()
            self.conf_widget.deleteLater()
        if len(self.plot_table.selectedItems()) == 1:
            item = self.plot_table.selectedItems()[0]
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
        manager = get_plot_manager()
        if item is None:
            self.plot_vars_widget.setVisible(False)
            return
        
        self.show_vars(item.reg_plot.varnum)
        if len(item.vars) >= 1:
            varname = CDMSPipelineHelper.get_value_from_function(item.vars[0], 'name')
            self.var1_edt.setText(varname)
        if len(item.vars) > 1:
            varname = CDMSPipelineHelper.get_value_from_function(item.vars[1], 'name')
            self.var2_edt.setText(varname)
            
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
            len(self.var_to_be_added) != 0 or len(self.var_to_be_removed) != 0):
            action = self.update_pipeline(action)
            
        self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
        
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
            self.plot_table.add_plot_item(plot_module)
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
        plot_modules = self.plot_table.get_plots()
        var_modules = self.var_table.get_vars()
        connections = self.plot_table.get_connections()
        if action is not None:
            version = action.id
        else:
            version = self.version
        action = CDMSPipelineHelper.rebuild_pipeline_action(self.controller, 
                                                            version, 
                                                            plot_modules, 
                                                            var_modules, 
                                                            connections)    
        return action
    
    @pyqtSlot(bool)
    def save_triggered(self, checked):
        
        self.conf_widget.saveTriggered(checked)
    
    @pyqtSlot(bool)
    def reset_triggered(self, checked):
        pass
    
class PlotTableWidget(QtGui.QTreeWidget):
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
        
    def populate_from_plots(self,plots=None):
        if plots is not None:
            self.plots = plots
        for i in range(len(self.plots)):
            item = self.create_plot_item(i, self.plots[i])
            if item.module == self.plots[0]:
                self.setItemSelected(item,True)
            
    def create_plot_item(self, order, plot_module):
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
        reg_plot = manager.get_plot_by_name(desc.plot_type, gm_name)
        item = PlotTableWidgetItem(self, order, plot_module, labels, 
                                   desc.plot_type, gm_name, _vars, reg_plot)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        return item
    
    def add_plot_item(self, plot_module):
        order = self.topLevelItemCount()
        self.plots.append(plot_module)
        self.create_plot_item(order,plot_module)
    
    @pyqtSlot(bool)
    def move_item_up(self, checked):
        item = self.selectedItems()[0]
        pos = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(pos)
        self.insertTopLevelItem(pos-1,item)
        self.update_item_ordering()
    
    @pyqtSlot(bool)
    def move_item_down(self, checked):
        item = self.selectedItems()[0]
        pos = self.indexOfTopLevelItem(item)
        item = self.takeTopLevelItem(pos)
        self.insertTopLevelItem(pos+1,item)
        self.update_item_ordering()
        
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
    
class PlotTableWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent, order, module, labels, plot_type, gm_name, vars,
                 reg_plot):
        QtGui.QTreeWidgetItem.__init__(self, parent, labels)
        self.module = module    
        self.order = order
        self.plot_type = plot_type
        self.gm_name = gm_name
        self.vars = vars
        self.reg_plot = reg_plot
        
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
        varname = CDMSPipelineHelper.get_value_from_function( var_module, 'name')
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
                item = CDMSVarListWidgetItem(var_module, varName, self.var_list)
            
        
class CDMSVarListWidgetItem(QtGui.QListWidgetItem):
    def __init__(self, var, varName, parent=None):
        super(CDMSVarListWidgetItem, self).__init__(varName, parent)
        self.var = var
        self.varName = varName
        
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