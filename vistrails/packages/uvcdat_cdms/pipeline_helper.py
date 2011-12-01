from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot, pyqtSignal
from init import CDMSPlot
from widgets import GraphicsMethodConfigurationWidget

class CDMSPipelineHelper(PlotPipelineHelper):
    @staticmethod
    def show_configuration_widget(controller, version):
        pipeline = controller.vistrail.getPipeline(version)
        plots = CDMSPipelineHelper.find_modules_by_type(pipeline, CDMSPlot)
        return CDMSPlotWidget(controller,version,plots)
    
    @staticmethod
    def build_plot_pipeline(controller, version, var_module, plot_type, plot_gm):
        pass
    
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
        else:
            self.config_widget = QtGui.QWidget()
        self.v_layout.addWidget(self.config_widget)
        self.plot_table.itemSelectionChanged.connect(self.update_config_widget)
        self.setLayout(self.v_layout)
        
    @pyqtSlot()
    def update_config_widget(self):
        if self.conf_widget:
            self.conf_widget.setVisible(False)
            self.v_layout.removeWidget(self.conf_widget)
            self.conf_widget.deleteLater()
        if len(self.plot_table.selectedItems()) == 1:
            item = self.plot_table.selectedItems()[0]
            self.config_widget = GraphicsMethodConfigurationWidget(item.module,
                                                                   self.controller,
                                                                   self)
        else:
            self.conf_widget = QtGui.QWidget()
        self.v_layout.addWidget(self.conf_widget)
    
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