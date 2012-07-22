from info import identifier

from packages.uvcdat.init import Variable, Plot
from packages.uvcdat.init import expand_port_specs as _expand_port_specs

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    return _expand_port_specs(port_specs, pkg_identifier)

class PVPlot(Plot):
    _input_ports = expand_port_specs([("variable", "com.kitware.pvclimate:PVVariable"),
                                      ])

    def to_module(self, controller):
        return Plot.to_module(self, controller, identifier)

_modules = [PVPlot]
