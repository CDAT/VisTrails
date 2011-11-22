# Not sure if this is required
import vtk

# This is required to convert a instance to string representation
import pickle

# Qt is required for widget
from PyQt4 import QtCore, QtGui
from core.modules.constant_configuration import ConstantWidgetMixin
from core.modules.basic_modules import new_constant, init_constant, Module

# Not sure why we need these
import math

class PVVariable(object):
    def __init__(self):
        self._reader = 0
        self._variable = ''
        self._variableType = ''
        
    def set_reader(self, reader):
        self._reader = reader
        
    def get_reader(self):
        return self._reader
    
    def set_variable_name(self, variableName):
        self._variableName = variableName
        
    def get_variable_name(self):
        return self._variableName
    
    def set_variable_type(self, type):
        # @NOTE: Make a check here if the type is of
        # CELL or POINTS type
        self._variableType = type
        
    def get_variable_type(self):
        return self._variableType

default_pvv = PVVariable()    
    
class PVVariableWidget(QtGui.QWidget, ConstantWidgetMixin):
    def __init__(self, param, parent=None):
        QtGui.QWidget.__init__(self, parent)
        ConstantWidgetMixin.__init__(self, param.strValue)
        if not param.strValue:
            self._tf = copy.copy(default_pvv)
        else:
            self._tf = pickle.loads(param.strValue.decode('hex'))

    def contents(self):
        return pickle.dumps(self).encode('hex')    
    
    
string_conversion = staticmethod(lambda x: pickle.dumps(x).encode('hex'))
conversion = staticmethod(lambda x: pickle.loads(x.decode('hex')))
validation = staticmethod(lambda x: isinstance(x, PVVariableConstant))    
PVVariableConstant = new_constant('PVVariable',
                                  conversion,
                                  default_pvv,
                                  validation,
                                  PVVariableWidget)

PVVariableConstant.translate_to_string = string_conversion
    
def initialize():
    init_constant(PVVariableConstant)
