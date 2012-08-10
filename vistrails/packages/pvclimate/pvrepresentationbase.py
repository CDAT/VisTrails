# Import base class
from core.modules.vistrails_module import Module

# Import registry
from core.modules.module_registry import get_module_registry

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class PVRepresentationBase(Module):        
    def __init__(self):
        Module.__init__(self)
        self.view = None
        self.reader = None;
        self.variables = None;
        
    def compute(self):
        # TODO:
        pass
        
    def setView(self, view):
        self.view = view
        
    def setReader(self, reader):
        self.reader = reader;
        
    def setVariables(self, variables):
        self.variables = variables
    
    def execute(self):
        pass

    @staticmethod
    def name():
        pass
    
    @staticmethod
    def configuration_widget(parent):
        pass

class RepresentationBaseConfigurationWidget(QWidget):
    def __init__(self, parent, rep_module):
        self.rep_module = rep_module
        self.controller = parent.controller
        QWidget.__init__(self, parent)
    
    def update_vistrails(self, module, functions):
        action = None
        action = self.controller.update_functions(module, functions)
        return action
    
    def function_value(self, name):
        value = None
        function_names = [f.name for f in self.rep_module.functions]
        if name in function_names:
            function = self.rep_module.functions[function_names.index(name)]
            value = function.params[0].strValue
        return value

def registerSelf():
    registry = get_module_registry()    
    registry.add_module(PVRepresentationBase)
    registry.add_output_port(PVRepresentationBase, "self", PVRepresentationBase)