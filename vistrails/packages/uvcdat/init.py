# can we always make sure this enabled

from info import identifier
from core.modules.basic_modules import new_constant, string_compare, String
from core.modules.vistrails_module import Module
from core.modules.module_registry import get_module_registry

def expand_port_specs(port_specs):
    reg = get_module_registry()
    out_specs = []
    for port_spec in port_specs:
        out_specs.append((port_spec[0],
                          reg.expand_port_spec_string(port_spec[1],
                                                      identifier)))
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
    _input_ports = expand_port_specs([("file", "basic:File"), 
                                      ("url", "URL"),
                                      ("source", "VariableSource"),
                                      ("load", "basic:Boolean")])
    _output_ports = expand_port_specs([("attributes", "basic:Dictionary"),
                                       ("dimensions", "basic:List"),
                                       ("self", "Variable")])

class Plot(Module):
    _input_ports = expand_port_specs([("variable", "Variable")])

class Extract(Module):
    _input_ports = expand_port_specs([("variable", "Variable"),
                                      # want dimension and range
                                      ])
    _output_ports = expand_port_specs([("variable", "Variable")])

_modules = [URL, VariableSource, Variable, Plot, Extract]
