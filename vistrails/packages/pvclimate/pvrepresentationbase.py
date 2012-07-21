# Import base class
from core.modules.vistrails_module import Module

# Import registry
from core.modules.module_registry import get_module_registry

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

def registerSelf():    
    registry = get_module_registry()    
    registry.add_module(PVRepresentationBase)
    registry.add_output_port(PVRepresentationBase, "self", PVRepresentationBase)