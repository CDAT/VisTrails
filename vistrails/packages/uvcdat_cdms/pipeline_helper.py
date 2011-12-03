from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from core.modules.module_registry import get_module_registry
import core.db.action
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot, pyqtSignal
from init import CDMSPlot
from widgets import GraphicsMethodConfigurationWidget
import api

class CDMSPipelineHelper(PlotPipelineHelper):
    @staticmethod
    def show_configuration_widget(controller, version, plot_obj=None):
        pipeline = controller.vistrail.getPipeline(version)
        plots = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSPlot)
        return CDMSPlotWidget(controller,version,plots)
    
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
        
        ops.append(('add', var_modules[0]))
        ops.append(('add', plot_module))     
        conn = controller.create_connection(var_modules[0], 'self',
                                            plot_module, 'variable')
        ops.append(('add', conn))
        if len(var_modules) > 1:
            conn2 = controller.create_connection(var_modules[1], 'self',
                                                    plot_module, 'variable2')
            ops.append(('add', var_modules[1]))
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
    def get_graphics_method_name_from_module(module):
        result = CDMSPipelineHelper.get_fun_value_from_module(module, 
                                                              "graphicsMethodName")
        if result == None:
            result = 'default'
        
        return result
    
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
    def __init__(self,controller, version, plot_list, parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.controller = controller
        self.version = version
        self.plot_table = PlotTableWidget(plot_list,self)
        self.v_layout = QtGui.QVBoxLayout()
        self.v_layout.addWidget(self.plot_table)
        if len(plot_list) > 0:
            self.config_widget = GraphicsMethodConfigurationWidget(plot_list[0],
                                                                   self.controller,
                                                                   self)
            self.connect_signals()
        else:
            self.config_widget = QtGui.QWidget()
        self.v_layout.addWidget(self.config_widget)
        self.plot_table.itemSelectionChanged.connect(self.update_config_widget)
        self.setLayout(self.v_layout)
        
    def connect_signals(self):
        if type(self.config_widget) == GraphicsMethodConfigurationWidget:
            self.connect(self.config_widget, QtCore.SIGNAL("plotDoneConfigure"),
                         self.configure_done)
            self.connect(self.config_widget, QtCore.SIGNAL("stateChanged"),
                         self.state_changed)
    def disconnect_signals(self):
        if type(self.config_widget) == GraphicsMethodConfigurationWidget:
            self.disconnect(self.config_widget, QtCore.SIGNAL("plotDoneConfigure"),
                         self.configure_done)
            self.disconnect(self.config_widget, QtCore.SIGNAL("stateChanged"),
                         self.state_changed)
    @pyqtSlot()
    def update_config_widget(self):
        if self.conf_widget:
            self.conf_widget.setVisible(False)
            self.v_layout.removeWidget(self.conf_widget)
            self.disconnect_signals()
            self.conf_widget.deleteLater()
        if len(self.plot_table.selectedItems()) == 1:
            item = self.plot_table.selectedItems()[0]
            self.config_widget = GraphicsMethodConfigurationWidget(item.module,
                                                                   self.controller,
                                                                   self)
            self.connect_signals()
        else:
            self.conf_widget = QtGui.QWidget()
        self.v_layout.addWidget(self.conf_widget)
    
    def configure_done(self, action):
        self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
        
    def state_changed(self):
        self.emit(QtCore.SIGNAL("stateChanged"))
        
class PlotTableWidget(QtGui.QTreeWidget):
    def __init__(self,plot_list, parent=None):    
        QtGui.QTreeWidget.__init__(self, parent)
        self.plots = plot_list
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setRootIsDecorated(False)
        self.header().setStretchLastSection(True)
        self.setHeaderLabels(QtCore.QStringList() << "Plot Type" << "Graphics Method" << "Template")
        self.populate_from_plots()
        
    def populate_from_plots(self,plots=None):
        if plots is not None:
            self.plots = plots
        for m in self.plots:
            item = self.create_plot_item(m)
            if item.module == self.plots[0]:
                self.setItemSelected(item,True)
            
    def create_plot_item(self, plot_module):
        desc = plot_module.module_descriptor.module()
        gm_name = CDMSPipelineHelper.get_graphics_method_name_from_module(plot_module)
        template = CDMSPipelineHelper.get_template_name_from_module(plot_module)
        labels = QtCore.QStringList() << str(desc.plot_type) << str(gm_name) << \
                                         str(template)
        item = PlotTableWidgetItem(self, plot_module, labels)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        return item
        
class PlotTableWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent, module, labels):
        QtGui.QTreeWidgetItem.__init__(self, parent, labels)
        self.module = module    