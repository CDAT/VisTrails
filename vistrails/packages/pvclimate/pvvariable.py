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

# Not sure why we need these
import math

# Import paraview
import paraview.simple as pvsp

class PVVariableConstant(Constant):    
    def __init__(self):
        Constant.__init__(self)
        self._reader = 0
        self._variableName = ''
        self._variableType = ''
        
    default_value = InstanceObject()
        
    @staticmethod
    def translate_to_python(x):
      return pickle.loads(self.decode('hex'))
      
    @staticmethod
    def translate_to_string(v):
      return pickle.dumps(self).encode('hex')
      
    @staticmethod
    def validate(x):
      isinstance(self, PVVariableConstant)  
        
    def compute(self):
        self.setResult("self", self)        
        
    def set_reader(self, reader):
        self._reader = reader
        
    def get_reader(self):
        # TODO: Hard coded for now
        #return pvsp.NetCDFPOPreader(FileName=str('/home/aashish/tools/cdat/install/sample_data/clt.nc'))  
        return self._reader
    
    def set_variable_name(self, variableName):
        self._variableName = variableName
        
    def get_variable_name(self):
        # TODO: Hard coded for now
        #return 'clt'
        return self._variableName
    
    def set_variable_type(self, type):
        # @NOTE: Make a check here if the type is of
        # CELL or POINTS type
        self._variableType = type
        
    def get_variable_type(self):
        return self._variableType

default_pvv = PVVariableConstant()    
    
class PVVariableConstantWidget(QtGui.QWidget, ConstantWidgetMixin):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        ConstantWidgetMixin.__init__(self, param.strValue)
        if not param.strValue:
            self._tf = copy.copy(default_pvv)
        else:
            self._tf = pickle.loads(param.strValue.decode('hex'))

    def contents(self): 
        return pickle.dumps(self).encode('hex')
      
def registerSelf(): 
    print 'REGISTERING... '
    registry = core.modules.module_registry.get_module_registry()
    registry.add_module(PVVariableConstant, configureWidgetType=PVVariableConstant)
    registry.add_output_port(PVVariableConstant, "self", PVVariableConstant)
          
