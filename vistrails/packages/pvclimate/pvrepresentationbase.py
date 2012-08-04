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
        self.project_sphere = None;

    def compute(self):
        # TODO:
        pass

    def set_view(self, view):
        self.view = view

    def set_reader(self, reader):
        self.reader = reader;

    def set_variables(self, variables):
        self.variables = variables

    def get_project_sphere_filter(self):
        # Import paraview
        import paraview.simple as pvsp

        if (self.project_sphere is None):
            self.project_sphere = pvsp.ProjectSphere()
        return self.project_sphere

    def execute(self):
        pass

def register_self():
    registry = get_module_registry()
    registry.add_module(PVRepresentationBase)
    registry.add_output_port(PVRepresentationBase, "self", PVRepresentationBase)