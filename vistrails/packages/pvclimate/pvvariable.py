# Not sure if this is required
import vtk

# This is required to convert a instance to string representation
import pickle

# Qt is required for widget
from PyQt4 import QtCore, QtGui

# Vistails import
import core.modules.module_registry
from gui.modules.constant_configuration import ConstantWidgetMixin
from core.modules.basic_modules import new_constant, init_constant, Module, Constant
from packages.uvcdat.init import Variable
from core.utils import InstanceObject
from packages.pvclimate import identifier

# Not sure why we need these
import math

# Import paraview
import paraview.simple as pvsp

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    reg = core.modules.module_registry.get_module_registry()
    out_specs = []
    for port_spec in port_specs:
        if len(port_spec) == 2:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier)))
        elif len(port_spec) == 3:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier),
                              port_spec[2])) 
    return out_specs

class PVConstant(Constant):
    def __init__(self):
        Constant.__init__(self)
        self.name = 'pvinfo'
        self.reader = None
    
    @staticmethod
    def translate_to_python(x):
        result = PVConstant()
        result.name = x
        result.reader = None
        result.setResult("value", result)
        return result

    @staticmethod
    def translate_to_string(x):
        return str(x.name)

    @staticmethod
    def validate(v):        
        return isinstance(v, PVConstant)

    def get_name(self):
        return self.name
    
    def set_reader(self, reader):
        print 'Setting reader ', reader        
        self.reader = reader
    
    def get_reader(self):
        print 'reader is ', self.reader
        return self.reader    
    
PVConstant.default_value = PVConstant()


class PVVariable(Variable):
    _input_ports = expand_port_specs([
          ("vartype", "basic:String"),
          ("pvinfo", "PVConstant"),
          ])
    
    def __init__(self, filename=None, name=None, vartype=None, reader=None):
        Variable.__init__(self, filename, None, None, name, False)        
        self.varname = name
        self.vartype = vartype
        pvinfo = PVConstant()
        pvinfo.set_reader(reader)
        self.pvinfo = pvinfo
        
    @staticmethod
    def translate_to_python(self, x):
      return pickle.loads(self.decode('hex'))
      
    @staticmethod
    def translate_to_string(v):
      return pickle.dumps(self).encode('hex')
      
    @staticmethod
    def validate(x):
      isinstance(self, PVVariable)  
        
    def compute(self):
        print 'Compute got called'
        self.filename = self.forceGetInputFromPort("filename")
        self.name = self.forceGetInputFromPort("name")
        self.pvinfo = self.forceGetInputFromPort("pvinfo")    
        print 'Getting reader ', self.pvinfo.get_reader()    
        self.varname = self.name
        self.vartype = self.forceGetInputFromPort("vartype")
        self.setResult("self", self)        
        
    def set_reader(self, reader):
        self.pvinfo.set_reader(reader)
        
    def get_reader(self):
        return self.pvinfo.get_reader() 
    
    def set_variable_name(self, variableName):
        self.varname = variableName
        self.name = variableName
        
    def get_variable_name(self):        
        return self.varname
    
    def set_variable_type(self, type):                
        self.vartype = type
        
    def get_variable_type(self):        
        return self.vartype
    
    def to_module(self, controller):
        module = Variable.to_module(self, controller, identifier)
        functions = []
        if self.vartype is not None:
            functions.append(("vartype", [self.vartype]))
        if self.pvinfo is not None:
            print 'reader is ', self.pvinfo.get_reader()
            functions.append(("pvinfo", [self.pvinfo]))    
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module
    
    def __copy__(self):
        print "COPY"
      
def registerSelf(): 
    print 'REGISTERING... '
    registry = core.modules.module_registry.get_module_registry()
    registry.add_module(PVConstant)
    registry.add_input_port(PVConstant, "value", PVConstant)
    registry.add_output_port(PVConstant, "value", PVConstant)
    registry.add_module(PVVariable)    
    registry.add_output_port(PVVariable, "self", PVVariable)
          
