from info import identifier

from packages.uvcdat.init import Variable, Plot
from packages.uvcdat.init import expand_port_specs as _expand_port_specs

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    return _expand_port_specs(port_specs, pkg_identifier)

#class PVVariable(Variable):
#    _output_ports = expand_port_specs([("self", "PVVariable")])
#
#    def __init__(self, filename=None, url=None, source=None, name=None, \
#                     load=False):
#        Variable.__init__(self, filename, url, source, name, load)
#
#    def to_module(self, controller):
#        # note that the correct module is returned because we use
#        # self.__class__.__name__
#        module = Variable.to_module(self, controller, identifier)
#        return module
#
#    def compute(self):
#        self.get_port_values()
#        self.setResult("self", self)

class PVPlot(Plot):
    _input_ports = expand_port_specs([("variable", "PVVariableConstant"),
                                      ])

    def to_module(self, controller):
        return Plot.to_module(self, controller, identifier)

_modules = [PVPlot]
