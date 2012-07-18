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
from gui.uvcdat.pvreadermanager import PVReaderManager

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

class PVVariable(Variable):
    _input_ports = expand_port_specs([
         ("readerParameters", "basic:Dictionary"),
         ("vartype", "basic:String")])
    
    _output_ports = expand_port_specs([("self", "PVVariable")])
    
    def __init__(self, filename=None, name=None, vartype=None, readerParameters=None):
        Variable.__init__(self, filename, None, None, name, False)        
        self.varname = name
        self.vartype = vartype
        self.readerParameters = readerParameters
        
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
        self.filename = self.forceGetInputFromPort("filename")
        self.name = self.forceGetInputFromPort("name")
        self.readerParameters = self.forceGetInputFromPort("readerParameters")
        self.varname = self.name
        self.vartype = self.forceGetInputFromPort("vartype")
        self.setResult("self", self)        

    def set_reader_parameters(self, readerParameters):
        self.readerParameters = readerParameters

    def get_reader(self):
        return PVReaderManager.get_reader(self.readerParameters)
    
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
        if self.readerParameters is not None:
            functions.append(("readerParameters", [self.readerParameters]))
            
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module
    
    @staticmethod
    def from_module(module):
        from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
        var = Variable.from_module(module)
        readerParameters = PlotPipelineHelper.get_value_from_function_as_str(module,
                                                                             'readerParameters')
        var.set_reader_parameters(readerParameters)

        return var

def registerSelf(): 
    print 'REGISTERING... '
    registry = core.modules.module_registry.get_module_registry()
    registry.add_module(PVVariable)    
    #registry.add_output_port(PVVariable, "self", PVVariable)
          
