from info import identifier
from core.modules.basic_modules import new_constant, string_compare, String
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.utils import getHomeRelativePath, getFullPath

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    reg = get_module_registry()
    out_specs = []
    for port_spec in port_specs:
        out_specs.append((port_spec[0],
                          reg.expand_port_spec_string(port_spec[1],
                                                      pkg_identifier)))
    return out_specs

URL = new_constant("URL", staticmethod(str), "", 
                   staticmethod(lambda x: type(x) == str),
                   base_class=String)

class VariableSource(Module):
    _input_ports = expand_port_specs([("file", "basic:File"),
                                      ("url", "URL")])
    _output_ports = expand_port_specs([("variables", "basic:List"),
                                       ("dimensions", "basic:List"),
                                       ("attributes", "basic:List")])

class Variable(Module):
    # TODO default load to False here...
    _input_ports = expand_port_specs([("file", "basic:File"), 
                                      ("url", "URL"),
                                      ("source", "VariableSource"),
                                      ("name", "basic:String"),
                                      ("load", "basic:Boolean")])
    _output_ports = expand_port_specs([("attributes", "basic:Dictionary"),
                                       ("dimensions", "basic:List"),
                                       ("self", "Variable")])

    def __init__(self, filename=None, url=None, source=None, name=None, 
                 load=False):
        Module.__init__(self)
        self.filename = filename
        self.url = url
        self.source = source
        self.name = name
        self.load = load
        self.file = self.filename
        self.relativizePaths()

    def to_module(self, controller, pkg_identifier=None):
        reg = get_module_registry()
        if pkg_identifier is None:
            pkg_identifier = identifier
        module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name(pkg_identifier, self.__class__.__name__))
        functions = []
        if self.filename is not None:
            functions.append(("file", [self.filename]))
        if self.url is not None:
            functions.append(("url", [self.url]))
        # cannot do source
        if self.name is not None:
            functions.append(("name", [self.name]))
        if self.load is not None:
            functions.append(("load", [str(self.load)]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module
    
    @staticmethod
    def from_module(module):
        from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
        var = Variable()
        var.filename = PlotPipelineHelper.get_value_from_function_as_str(module, 'file')
        var.file = var.filename
        var.url = PlotPipelineHelper.get_value_from_function(module, 'url')
        var.name = PlotPipelineHelper.get_value_from_function(module, 'name')
        var.load = PlotPipelineHelper.get_value_from_function(module, 'load')
        var.relativizePaths()
        return var

    def relativizePaths(self):
        self.file = getHomeRelativePath( self.file ) 
        self.url = getHomeRelativePath( self.url ) 
             
    def get_port_values(self):
        if not self.hasInputFromPort("file") and not self.hasInputFromPort("url") and not self.hasInputFromPort("source"):
            raise ModuleError( self, 'Must set one of "file", "url", "source".')
        if self.hasInputFromPort("file"):
            self.file = self.getInputFromPort("file").name
            self.filename = self.file
        if self.hasInputFromPort("url"):
            self.url = self.getInputFromPort("url")
        if self.hasInputFromPort("source"):
            self.source = self.getInputFromPort("source")
        self.name = self.getInputFromPort("name")
        self.load = self.forceGetInputFromPort("load", False)
        self.relativizePaths()

    def compute(self):
        self.get_port_values()
        self.setResult("self", self)
        
class Plot(Module):
    _input_ports = expand_port_specs([("variable", "Variable")])
    _output_ports = expand_port_specs([("self", "Plot")])

    def __init__(self):
        Module.__init__(self)
        self.var = None

    def to_module(self, controller, pkg_identifier=None):
        reg = get_module_registry()
        if pkg_identifier is None:
            pkg_identifier = identifier
        module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name(pkg_identifier, self.__class__.__name__))
        return module

    def compute(self):
        self.var = self.getInputFromPort('variable').var
        self.setResult("self", self)

class Extract(Module):
    _input_ports = expand_port_specs([("variable", "Variable"),
                                      # want dimension and range
                                      ])
    _output_ports = expand_port_specs([("variable", "Variable")])

_modules = [URL, VariableSource, Variable, Plot, Extract]


