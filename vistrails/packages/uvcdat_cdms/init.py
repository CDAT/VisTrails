from PyQt4 import QtCore, QtGui

from cdatguiwrap import VCSQtManager
import vcs
import genutil
import cdutil
import cdms2
import time
import api
import re
import MV2
import os
import ast
import string
from info import identifier
from widgets import GraphicsMethodConfigurationWidget
from core.configuration import get_vistrails_configuration
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core import debug
from core.utils import InstanceObject
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from packages.uvcdat.init import Variable, Plot
from gui.uvcdat.theme import UVCDATTheme
from gui.uvcdat.cdmsCache import CdmsCache

canvas = None
original_gm_attributes = {}

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    reg = get_module_registry()
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


class CDMSVariable(Variable):
    _input_ports = expand_port_specs([("axes", "basic:String"),
                                      ("axesOperations", "basic:String"),
                                      ("varNameInFile", "basic:String"),
                                      ("attributes", "basic:Dictionary"),
                                      ("axisAttributes", "basic:Dictionary"),
                                      ("setTimeBounds", "basic:String")])
    _output_ports = expand_port_specs([("self", "CDMSVariable")])

    def __init__(self, filename=None, url=None, source=None, name=None, \
                     load=False, varNameInFile=None, axes=None, \
                     axesOperations=None, attributes=None, axisAttributes=None,
                     timeBounds=None):
        Variable.__init__(self, filename, url, source, name, load)
        self.axes = axes
        self.axesOperations = axesOperations
        self.varNameInFile = varNameInFile
        self.attributes = attributes
        self.axisAttributes = axisAttributes
        self.timeBounds = timeBounds
        self.var = None

    def __copy__(self):
        """__copy__() -> CDMSVariable - Returns a clone of itself"""
        cp = CDMSVariable()
        cp.filename = self.filename
        cp.file = self.file
        cp.url = self.url
        cp.source = self.source
        cp.name = self.name
        cp.load = self.load
        cp.varNameInFile = self.varNameInFile
        cp.axes = self.axes
        cp.axesOperations = self.axesOperations
        cp.attributes = self.attributes
        cp.axisAttributes = self.axisAttributes
        cp.timeBounds = self.timeBounds
        return cp
        
    def to_module(self, controller):
        module = Variable.to_module(self, controller, identifier)
        functions = []
        if self.varNameInFile is not None:
            functions.append(("varNameInFile", [self.varNameInFile]))
        if self.axes is not None:
            functions.append(("axes", [self.axes]))
        if self.axesOperations is not None:
            functions.append(("axesOperations", [self.axesOperations]))
        if self.attributes is not None:
            functions.append(("attributes", [self.attributes]))
        if self.axisAttributes is not None:
            functions.append(("axisAttributes", [self.axisAttributes]))
        if self.timeBounds is not None:
            functions.append(("setTimeBounds", [self.timeBounds]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        
    
    def to_python(self):
        if self.source:
            cdmsfile = self.source.var
        elif self.url:
            if self.url in CdmsCache.d:
                #print "Using cache for %s" % self.url
                cdmsfile = CdmsCache.d[self.url]
            else:
                #print "Loading file %s" % self.url
                cdmsfile = CdmsCache.d[self.url] = cdms2.open( os.path.expanduser(self.url) )
        elif self.file:
            if self.file in CdmsCache.d:
                #print "Using cache for %s" % self.file
                cdmsfile = CdmsCache.d[self.file]
            else:
                #print "Loading file %s" % self.file
                cdmsfile = CdmsCache.d[self.file] = cdms2.open( os.path.expanduser(self.file) )
        
        if self.varNameInFile is not None:
            var = cdmsfile.__call__(self.varNameInFile)
        else:
            var = cdmsfile.__call__(self.name)
        if self.axes is not None:
            try:
                var = eval("var(%s)"% self.axes)
            except Exception, e:
                raise ModuleError(self, "Invalid 'axes' specification: %s" % \
                                      str(e))
        if self.axesOperations is not None:
            var = self.applyAxesOperations(var, self.axesOperations)
            
        #make sure that var.id is the same as self.name
        var.id = self.name
        if self.attributes is not None:
            for attr in self.attributes:
                try:
                    attValue=eval(str(self.attributes[attr]).strip())
                except:
                    attValue=str(self.attributes[attr]).strip()
                setattr(var,attr, attValue) 
                       
        if self.axisAttributes is not None:
            for axName in self.axisAttributes:
                for attr in self.axisAttributes[axName]:
                    try:
                        attValue=eval(str(self.axisAttributes[axName][attr]).strip())
                    except:
                        attValue=str(self.axisAttributes[axName][attr]).strip()
                    ax = var.getAxis(var.getAxisIndex(axName))
                    setattr(ax,attr, attValue)
                    
        if self.timeBounds is not None:
            var = self.applySetTimeBounds(var, self.timeBounds)
                    
        return var
    
    def to_python_script(self, include_imports=False, ident=""):
        text = ''
        if include_imports:
            text += ident + "import cdms2, cdutil, genutil\n"
        if self.source:
            cdmsfile = self.source.var
        elif self.url:
            text += ident + "cdmsfile = cdms2.open('%s')\n" % os.path.expanduser(self.url)
        elif self.file:
            text += ident + "cdmsfile = cdms2.open('%s')\n" % os.path.expanduser(self.file)
            
        if self.varNameInFile is not None:
            text += ident + "%s = cdmsfile('%s')\n"%(self.name, self.varNameInFile)
        else:
            text += ident + "%s = cdmsfile('%s')\n"%(self.name, self.name)
        if self.axes is not None:
            text += ident + "%s = %s(%s)\n"% (self.name, self.name, self.axes)
        if self.axesOperations is not None:
            text += ident + "axesOperations = eval(\"%s\")\n"%self.axesOperations
            text += ident + "for axis in list(axesOperations):\n"
            text += ident + "    if axesOperations[axis] == 'sum':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal', action='sum')\n"% (self.name, self.name) 
            text += ident + "    elif axesOperations[axis] == 'avg':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal')\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'wgt':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'gtm':\n"
            text += ident + "        %s = genutil.statistics.geometricmean(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'std':\n"
            text += ident + "        %s = genutil.statistics.std(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
       
        if self.attributes is not None:
            text += "\n" + ident + "#modifying variable attributes\n"
            for attr in self.attributes:
                text += ident + "%s.%s = %s\n" % (self.name, attr,
                                                  repr(self.attributes[attr]))
                
        if self.axisAttributes is not None:
            text += "\n" + ident + "#modifying axis attributes\n"
            for axName in self.axisAttributes:
                text += ident + "ax = %s.getAxis(%s.getAxisIndex('%s'))\n" % (self.name,self.name,axName)
                for attr in self.axisAttributes[axName]:
                    text += ident + "ax.%s = %s\n" % ( attr,
                                        repr(self.axisAttributes[axName][attr]))
        
        if self.timeBounds is not None:
            data = self.timeBounds.split(":")
            if len(data) == 2:
                timeBounds = data[0]
                val = float(data[1])
            else:
                timeBounds = self.timeBounds
            text += "\n" + ident + "#%s\n"%timeBounds
            if timeBounds == "Set Bounds For Yearly Data":
                text += ident + "cdutil.times.setTimeBoundsYearly(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Monthly Data":
                text += ident + "cdutil.times.setTimeBoundsMonthly(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s)\n"%self.name
            elif timeBounds == "Set Bounds For Twice-daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,2)\n"%self.name
            elif timeBounds == "Set Bounds For 6-Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,4)\n"%self.name
            elif timeBounds == "Set Bounds For Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,24)\n"%self.name
            elif timeBounds == "Set Bounds For X-Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,%g)\n"%(self.name,val)
                
        return text
    
    @staticmethod
    def from_module(module):
        from pipeline_helper import CDMSPipelineHelper
        var = Variable.from_module(module)
        var.axes = CDMSPipelineHelper.get_value_from_function(module, 'axes')
        var.axesOperations = CDMSPipelineHelper.get_value_from_function(module, 'axesOperations')
        var.varNameInFile = CDMSPipelineHelper.get_value_from_function(module, 'varNameInFile')
        attrs = CDMSPipelineHelper.get_value_from_function(module, 'attributes')
        if attrs is not None:
            var.attributes = ast.literal_eval(attrs)
        else:
            var.attributes = attrs
            
        axattrs = CDMSPipelineHelper.get_value_from_function(module, 'axisAttributes')
        if axattrs is not None:
            var.axisAttributes = ast.literal_eval(axattrs)
        else:
            var.axisAttributes = axattrs
        var.timeBounds = CDMSPipelineHelper.get_value_from_function(module, 'setTimeBounds')
        var.__class__ = CDMSVariable
        return var
        
    def compute(self):
        self.axes = self.forceGetInputFromPort("axes")
        self.axesOperations = self.forceGetInputFromPort("axesOperations")
        self.varNameInFile = self.forceGetInputFromPort("varNameInFile")
        self.attributes = self.forceGetInputFromPort("attributes")
        self.axisAttributes = self.forceGetInputFromPort("axisAttributes")
        self.timeBounds = self.forceGetInputFromPort("setTimeBounds")
        self.get_port_values()
#        print " ---> CDMSVariable-->compute: ", str(self.file), str(self.url), str(self.name)
        self.var = self.to_python()
        self.setResult("self", self)

    @staticmethod
    def applyAxesOperations(var, axesOperations):
        """ Apply axes operations to update the slab """
        try:
            axesOperations = ast.literal_eval(axesOperations)
        except:
            raise TypeError("Invalid string 'axesOperations': %s" % str(axesOperations) )

        for axis in list(axesOperations):
            if axesOperations[axis] == 'sum':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal',
                                      action='sum')
            elif axesOperations[axis] == 'avg':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal')
            elif axesOperations[axis] == 'wgt':
                var = cdutil.averager(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'gtm':
                var = genutil.statistics.geometricmean(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'std':
                var = genutil.statistics.std(var, axis="(%s)" % axis)
        return var

    @staticmethod
    def applySetTimeBounds(var, timeBounds):
        data = timeBounds.split(":")
        if len(data) == 2:
            timeBounds = data[0]
            val = float(data[1])
        if timeBounds == "Set Bounds For Yearly Data":
            cdutil.times.setTimeBoundsYearly(var)
        elif timeBounds == "Set Bounds For Monthly Data":
            cdutil.times.setTimeBoundsMonthly(var)
        elif timeBounds == "Set Bounds For Daily Data":
            cdutil.times.setTimeBoundsDaily(var)
        elif timeBounds == "Set Bounds For Twice-daily Data":
            cdutil.times.setTimeBoundsDaily(var,2)
        elif timeBounds == "Set Bounds For 6-Hourly Data":
            cdutil.times.setTimeBoundsDaily(var,4)
        elif timeBounds == "Set Bounds For Hourly Data":
            cdutil.times.setTimeBoundsDaily(var,24)
        elif timeBounds == "Set Bounds For X-Daily Data":
            cdutil.times.setTimeBoundsDaily(var,val)
        return var
    
class CDMSVariableOperation(Module):
    _input_ports = expand_port_specs([("varname", "basic:String"),
                                      ("python_command", "basic:String"),
                                      ("axes", "basic:String"),
                                      ("axesOperations", "basic:String"),
                                      ("attributes", "basic:Dictionary"),
                                      ("axisAttributes", "basic:Dictionary"),
                                      ("timeBounds", "basic:String")])
    
    _output_ports = expand_port_specs([("output_var", "CDMSVariable")])
    
    def __init__(self, varname=None, python_command=None, axes=None, 
                 axesOperations=None, attributes=None, axisAttributes=None, 
                 timeBounds=None ):
        Module.__init__(self)
        self.varname = varname
        self.python_command = python_command
        self.axes = axes
        self.axesOperations = axesOperations
        self.attributes = attributes
        self.axisAttributes = axisAttributes
        self.timeBounds = timeBounds

    def to_module(self, controller):
        reg = get_module_registry()
        module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name(identifier, self.__class__.__name__))
        functions = []
        if self.varname is not None:
            functions.append(("varname", [self.varname]))
        if self.python_command is not None:
            functions.append(("python_command", [self.python_command]))
        if self.axes is not None:
            functions.append(("axes", [self.axes]))
        if self.axesOperations is not None:
            functions.append(("axesOperations", [self.axesOperations]))
        if self.attributes is not None:
            functions.append(("attributes", [self.attributes]))
        if self.axisAttributes is not None:
            functions.append(("axisAttributes", [self.axisAttributes]))
        if self.timeBounds is not None:
            functions.append(("timeBounds", [self.timeBounds]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        
    
    @staticmethod
    def from_module(module):
        from pipeline_helper import CDMSPipelineHelper
        op = CDMSVariableOperation()
        op.varname = CDMSPipelineHelper.get_value_from_function(module, 'varname')
        op.python_command = CDMSPipelineHelper.get_value_from_function(module, 'python_command')
        op.axes = CDMSPipelineHelper.get_value_from_function(module, 'axes')
        op.axesOperations = CDMSPipelineHelper.get_value_from_function(module, 'axesOperations')
        attrs = CDMSPipelineHelper.get_value_from_function(module, 'attributes')
        if attrs is not None:
            op.attributes = ast.literal_eval(attrs)
        else:
            op.attributes = attrs
            
        axattrs = CDMSPipelineHelper.get_value_from_function(module, 'axisAttributes')
        if axattrs is not None:
            op.axisAttributes = ast.literal_eval(axattrs)
        else:
            op.axisAttributes = axattrs
        op.timeBounds = CDMSPipelineHelper.get_value_from_function(module, 'setTimeBounds')
        return op
    
    def get_port_values(self):
        if not self.hasInputFromPort("varname"):
            raise ModuleError(self, "'varname' is mandatory.")
        if not self.hasInputFromPort("python_command"):
            raise ModuleError(self, "'python_command' is mandatory.")
        self.varname = self.forceGetInputFromPort("varname")
        self.python_command = self.getInputFromPort("python_command")
        self.axes = self.forceGetInputFromPort("axes")
        self.axesOperations = self.forceGetInputFromPort("axesOperations")
        self.attributes = self.forceGetInputFromPort("attributes")
        self.axisAttributes = self.forceGetInputFromPort("axisAttributes")
        self.timeBounds = self.forceGetInputFromPort("timeBounds")
        
    @staticmethod              
    def find_variable_in_command(v, command, startpos=0):
        """find_variable(v:str,command:str) -> int
        find the first occurrence of v in command, respecting identifier
        names
        Examples:
            >>> find_variable("v","av=clt*2")
            -1
            >>> find_variable("var","self.var=3* clt"
            -1
        """
        bidentchars = string.letters+string.digits+'_.'
        aidentchars = string.letters+string.digits+'_'
        i = command.find(v,startpos)
        if i < 0: #not found
            return i
        #checking before and after
        before = i-1
        after = i+len(v)
        ok_before = True
        ok_after = True
        if before >= 0:
            if command[before] in bidentchars:
                ok_before = False
        
        if after < len(command):
            if command[after] in aidentchars:
                ok_after = False
        
        if ok_after and ok_before:
            return i
        else:
            spos = i+len(v)
            while spos<len(command)-1 and command[spos] in aidentchars:
                spos+=1
            return CDMSVariableOperation.find_variable_in_command(v,command,spos)
        
    @staticmethod
    def replace_variable_in_command(command, oldv, newv):
        newcommand=""
        changedcommand = command
        i = CDMSVariableOperation.find_variable_in_command(oldv,changedcommand)
        while i > -1:
            newcommand += changedcommand[:i]
            newcommand += newv
            changedcommand = changedcommand[i+len(oldv):]
            i = CDMSVariableOperation.find_variable_in_command(oldv,changedcommand)
        newcommand += changedcommand
        return newcommand  
    
    def compute(self):
        pass
    
    def set_variables(self, vars):
        pass
    
    def applyOperations(self, var):
        if self.axes is not None:
            try:
                var = eval("var(%s)"% self.axes)
            except Exception, e:
                raise ModuleError(self, "Invalid 'axes' specification: %s" % \
                                      str(e))
        if self.axesOperations is not None:
            var = CDMSVariable.applyAxesOperations(var, self.axesOperations)
            
        if self.attributes is not None:
            for attr in self.attributes:
                try:
                    attValue=eval(str(self.attributes[attr]).strip())
                except:
                    attValue=str(self.attributes[attr]).strip()
                setattr(var,attr, attValue) 
                       
        if self.axisAttributes is not None:
            for axName in self.axisAttributes:
                for attr in self.axisAttributes[axName]:
                    try:
                        attValue=eval(str(self.axisAttributes[axName][attr]).strip())
                    except:
                        attValue=str(self.axisAttributes[axName][attr]).strip()
                    ax = var.getAxis(var.getAxisIndex(axName))
                    setattr(ax,attr, attValue)
                    
        if self.timeBounds is not None:
            var = CDMSVariable.applySetTimeBounds(var, self.timeBounds)
        return var
    
    def to_python_script(self, ident=""):
        text = ''
        if self.axes is not None:
            text += ident + "%s = %s(%s)\n"% (self.varname, self.varname, self.axes)
        if self.axesOperations is not None:
            text += ident + "axesOperations = eval(\"%s\")\n"%self.axesOperations
            text += ident + "for axis in list(axesOperations):\n"
            text += ident + "    if axesOperations[axis] == 'sum':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal', action='sum')\n"% (self.varname, self.varname) 
            text += ident + "    elif axesOperations[axis] == 'avg':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal')\n"% (self.varname, self.varname)
            text += ident + "    elif axesOperations[axis] == 'wgt':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis)\n"% (self.varname, self.varname)
            text += ident + "    elif axesOperations[axis] == 'gtm':\n"
            text += ident + "        %s = genutil.statistics.geometricmean(%s, axis='(%%s)'%%axis)\n"% (self.varname, self.varname)
            text += ident + "    elif axesOperations[axis] == 'std':\n"
            text += ident + "        %s = genutil.statistics.std(%s, axis='(%%s)'%%axis)\n"% (self.varname, self.varname)
       
        if self.attributes is not None:
            text += "\n" + ident + "#modifying variable attributes\n"
            if 'id' not in self.attributes:
                text += ident + "%s.id = %s\n" % (self.varname, self.varname)
            for attr in self.attributes:
                text += ident + "%s.%s = %s\n" % (self.varname, attr,
                                                  repr(self.attributes[attr]))
                
        if self.axisAttributes is not None:
            text += "\n" + ident + "#modifying axis attributes\n"
            for axName in self.axisAttributes:
                text += ident + "ax = %s.getAxis(%s.getAxisIndex('%s'))\n" % (self.varname,self.varname,axName)
                for attr in self.axisAttributes[axName]:
                    text += ident + "ax.%s = %s\n" % ( attr,
                                        repr(self.axisAttributes[axName][attr]))
        
        if self.timeBounds is not None:
            data = self.timeBounds.split(":")
            if len(data) == 2:
                timeBounds = data[0]
                val = float(data[1])
            else:
                timeBounds = self.timeBounds
            text += "\n" + ident + "#%s\n"%timeBounds
            if timeBounds == "Set Bounds For Yearly Data":
                text += ident + "cdutil.times.setTimeBoundsYearly(%s)\n"%self.varname
            elif timeBounds == "Set Bounds For Monthly Data":
                text += ident + "cdutil.times.setTimeBoundsMonthly(%s)\n"%self.varname
            elif timeBounds == "Set Bounds For Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s)\n"%self.varname
            elif timeBounds == "Set Bounds For Twice-daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,2)\n"%self.varname
            elif timeBounds == "Set Bounds For 6-Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,4)\n"%self.varname
            elif timeBounds == "Set Bounds For Hourly Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,24)\n"%self.varname
            elif timeBounds == "Set Bounds For X-Daily Data":
                text += ident + "cdutil.times.setTimeBoundsDaily(%s,%g)\n"%(self.varname,val)
                
        return text
    
        
class CDMSUnaryVariableOperation(CDMSVariableOperation):
    _input_ports = expand_port_specs([("input_var", "CDMSVariable")
                                      ])
    def __init__(self, varname=None, python_command=None, axes=None, 
                 axesOperations=None, attributes=None, axisAttributes=None, 
                 timeBounds=None ):
        CDMSVariableOperation.__init__(self, varname, python_command, axes, 
                                       axesOperations, attributes, axisAttributes, 
                                       timeBounds)
        self.var = None
        
    def to_python(self):
        self.python_command = self.replace_variable_in_command(self.python_command,
                                                               self.var.name, 
                                                               "self.var.var")
        res = eval(self.python_command)
        if type(res) == tuple:
            for r in res:
                if isinstance(r,cdms2.tvariable.TransientVariable):
                    var = r
                    break
        else:
            var = res 
        
        if isinstance(var, cdms2.tvariable.TransientVariable):
            var.id = self.varname
            var = self.applyOperations(var)
        return var
    
    def to_python_script(self, ident=""):
        text = ident + "%s = %s\n"%(self.varname,
                                    self.python_command)
        text += CDMSVariableOperation.to_python_script(self, ident)
        return text
    
    def compute(self):
        if not self.hasInputFromPort('input_var'):
            raise ModuleError(self, "'input_var' is mandatory.")
        
        self.var = self.getInputFromPort('input_var')
        self.get_port_values()
        self.outvar = CDMSVariable(filename=None,name=self.varname)
        self.outvar.var = self.to_python()
        self.setResult("output_var", self.outvar)
    
    def set_variables(self, vars):
        self.var = vars[0]
        
    @staticmethod
    def from_module(module):
        op = CDMSVariableOperation.from_module(module)
        op.__class__ = CDMSUnaryVariableOperation
        op.var = None
        return op
        
    def to_module(self, controller):
        module = CDMSVariableOperation.to_module(self, controller)   
        return module        
            
class CDMSBinaryVariableOperation(CDMSVariableOperation):
    _input_ports = expand_port_specs([("input_var1", "CDMSVariable"),
                                      ("input_var2", "CDMSVariable")
                                      ])
    def __init__(self, varname=None, python_command=None, axes=None, 
                 axesOperations=None, attributes=None, axisAttributes=None, 
                 timeBounds=None ):
        CDMSVariableOperation.__init__(self, varname, python_command, axes, 
                                       axesOperations, attributes, axisAttributes, 
                                       timeBounds)
        self.var1 = None
        self.var2 = None
    
    def compute(self):
        if not self.hasInputFromPort('input_var1'):
            raise ModuleError(self, "'input_var1' is mandatory.")
        
        if not self.hasInputFromPort('input_var2'):
            raise ModuleError(self, "'input_var2' is mandatory.")
        
        self.var1 = self.getInputFromPort('input_var1')
        self.var2 = self.getInputFromPort('input_var2')
        self.get_port_values()
        self.outvar = CDMSVariable(filename=None,name=self.varname)
        self.outvar.var = self.to_python()
        self.setResult("output_var", self.outvar)
        
    def set_variables(self, vars):
        self.var1 = vars[0]
        self.var2 = vars[1]
        
    def to_python(self):
        replace_map = {self.var1.name: "self.var1.var",
                       self.var2.name: "self.var2.var"}
        
        vars = [self.var1,self.var2]
        for v in vars:
            self.python_command = self.replace_variable_in_command(self.python_command,
                                                                   v.name, replace_map[v.name])

        res = eval(self.python_command)
        if type(res) == tuple:
            for r in res:
                if isinstance(r,cdms2.tvariable.TransientVariable):
                    var = r
                    break
        else:
            var = res
        
        if isinstance(var, cdms2.tvariable.TransientVariable):
            var.id = self.varname
            var = self.applyOperations(var)
        return var
        
    def to_python_script(self, ident=""):
        text = ident + "%s = %s\n"%(self.varname,
                                    self.python_command)
        text += CDMSVariableOperation.to_python_script(self, ident)
        return text
    
    @staticmethod
    def from_module(module):
        op = CDMSVariableOperation.from_module(module)
        op.__class__ = CDMSBinaryVariableOperation
        op.var1 = None
        op.var2 = None
        return op
    
    def to_module(self, controller, pkg_identifier=None):
        module = CDMSVariableOperation.to_module(self, controller)
        return module
        
class CDMSNaryVariableOperation(CDMSVariableOperation):
    _input_ports = expand_port_specs([("input_vars", "CDMSVariable"),
                                      ])
    def __init__(self, varname=None, python_command=None, axes=None, 
                 axesOperations=None, attributes=None, axisAttributes=None, 
                 timeBounds=None ):
        CDMSVariableOperation.__init__(self, varname, python_command, axes, 
                                       axesOperations, attributes, axisAttributes, 
                                       timeBounds)
        self.vars = None
        
    def compute(self):
        if self.hasInputFromPort('input_vars'):
            self.vars = self.getInputListFromPort('input_vars')
        else:
            self.vars = []
        self.get_port_values()
        self.outvar = CDMSVariable(filename=None,name=self.varname)
        self.outvar.var = self.to_python()
        self.setResult("output_var", self.outvar)
        
    def set_variables(self, vars):
        for v in vars:
            self.vars.append(v)
        
    def to_python(self):
        replace_map = {}
        for i in range(len(self.vars)):
            replace_map[self.vars[i].name] = "self.vars[%s].var"%i
            
        for v in self.vars:
            self.python_command = self.replace_variable_in_command(self.python_command,
                                                                   v.name, replace_map[v.name])
 
        res = eval(self.python_command)
        if type(res) == tuple:
            for r in res:
                if isinstance(r,cdms2.tvariable.TransientVariable):
                    var = r
                    break
        else:
            var = res
        
        if isinstance(var, cdms2.tvariable.TransientVariable):
            var.id = self.varname
            var = self.applyOperations(var)
        return var
        
    def to_python_script(self, ident=""):
        text = ident + "%s = %s\n"%(self.varname,
                                    self.python_command)
        text += CDMSVariableOperation.to_python_script(self, ident)
        return text
    
    @staticmethod
    def from_module(module):
        op = CDMSVariableOperation.from_module(module)
        op.__class__ = CDMSNaryVariableOperation
        op.vars = []
        return op
    
    def to_module(self, controller, pkg_identifier=None):
        module = CDMSVariableOperation.to_module(self, controller)
        return module
        
class CDMSPlot(Plot, NotCacheable):
    _input_ports = expand_port_specs([("variable", "CDMSVariable"),
                                      ("variable2", "CDMSVariable", True),
                                      ("plotOrder", "basic:Integer", True),
                                      ("graphicsMethodName", "basic:String"),
                                      ("template", "basic:String"),
                                      ('datawc_calendar', 'basic:Integer', True),
                                      ('datawc_timeunits', 'basic:String', True),
                                      ('datawc_x1', 'basic:Float', True),
                                      ('datawc_x2', 'basic:Float', True),
                                      ('datawc_y1', 'basic:Float', True),
                                      ('datawc_y2', 'basic:Float', True),
                                      ('xticlabels1', 'basic:String', True),
                                      ('xticlabels2', 'basic:String', True),
                                      ('yticlabels1', 'basic:String', True),
                                      ('yticlabels2', 'basic:String', True),
                                      ('xmtics1', 'basic:String', True),
                                      ('xmtics2', 'basic:String', True),
                                      ('ymtics1', 'basic:String', True),
                                      ('ymtics2', 'basic:String', True),
                                      ('projection', 'basic:String', True),
                                      ('continents', 'basic:Integer', True),
                                      ('ratio', 'basic:String', True),
                                      ("colorMap", "CDMSColorMap", True)])
    _output_ports = expand_port_specs([("self", "CDMSPlot")])

    gm_attributes = [ 'datawc_calendar', 'datawc_timeunits',
                      'datawc_x1', 'datawc_x2', 'datawc_y1', 'datawc_y2',
                      'xticlabels1', 'xticlabels2', 'yticlabels1', 'yticlabels2', 
                      'xmtics1', 'xmtics2', 'ymtics1', 'ymtics2', 'projection']
    
    plot_type = None

    def __init__(self):
        Plot.__init__(self)
        NotCacheable.__init__(self)
        self.template = "starter"
        self.graphics_method_name = "default"
        self.plot_order = -1
        self.kwargs = {}
        self.default_values = {}
        
    def compute(self):
        Plot.compute(self)
        self.graphics_method_name = \
                self.forceGetInputFromPort("graphicsMethodName", "default")
        #self.set_default_values()
        self.template = self.forceGetInputFromPort("template", "starter")
        
        if not self.hasInputFromPort('variable'):
            raise ModuleError(self, "'variable' is mandatory.")
        self.var = self.getInputFromPort('variable')
        
        self.var2 = None
        if self.hasInputFromPort('variable2'):
            self.var2 = self.getInputFromPort('variable2')

        if self.hasInputFromPort("plotOrder"):
            self.plot_order = self.getInputFromPort("plotOrder")
            
        for attr in self.gm_attributes:
            if self.hasInputFromPort(attr):
                setattr(self,attr,self.getInputFromPort(attr))
            
        self.colorMap = None
        if self.hasInputFromPort('colorMap'):
            self.colorMap = self.getInputFromPort('colorMap')
            
        self.kwargs['continents'] = 1
        if self.hasInputFromPort('continents'):
            self.kwargs['continents'] = self.getInputFromPort('continents')
            
        self.kwargs['ratio'] = 'autot'
        if self.hasInputFromPort('ratio'):
            self.kwargs['ratio'] = self.getInputFromPort('ratio')
            if self.kwargs['ratio'] != 'autot':
                try:
                    float(self.kwargs['ratio'])
                except ValueError:
                    self.kwargs['ratio'] = 'autot'

    def to_module(self, controller):
        module = Plot.to_module(self, controller, identifier)
        functions = []
        
        #only when graphics_method_name is different from default the user can
        #change the values of the properties
        if self.graphics_method_name != "default":
            functions.append(("graphicsMethodName", [self.graphicsMethodName]))
            for attr in self.gm_attributes:
                functions.append((attr, [str(getattr(self,attr))]))
        if self.template != "starter":
            functions.append(("template", [self.template]))
            
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        
    
    @classmethod
    def from_module(klass, module):
        from pipeline_helper import CDMSPipelineHelper
        plot = klass()
        plot.graphics_method_name = CDMSPipelineHelper.get_graphics_method_name_from_module(module)
        for attr in plot.gm_attributes:
            setattr(plot,attr, CDMSPipelineHelper.get_value_from_function(module, attr))
        plot.template = CDMSPipelineHelper.get_template_name_from_module(module)
        return plot

    def set_default_values(self, gmName=None):
        self.default_values = {}
        if gmName is None:
            gmName = self.graphics_method_name
        if self.plot_type is not None:
            canvas = get_canvas()
            method_name = "get"+str(self.plot_type).lower()
            gm = getattr(canvas,method_name)(gmName)
            for attr in self.gm_attributes:
                setattr(self,attr,getattr(gm,attr))
                self.default_values[attr] = getattr(gm,attr)
    
    @staticmethod
    def get_canvas_graphics_method( plotType, gmName):
        method_name = "get"+str(plotType).lower()
        return getattr(get_canvas(),method_name)(gmName)
    
    @classmethod    
    def get_initial_values(klass, gmName):
        global original_gm_attributes
        return original_gm_attributes[klass.plot_type][gmName]
#        cgm = CDMSPlot.get_canvas_graphics_method(klass.plot_type, gmName)
#        attribs = {}
#        for attr in klass.gm_attributes:
#            attribs[attr] = getattr(cgm,attr)
#        return InstanceObject(**attribs)
      
class CDMSTDMarker(Module):
    _input_ports = expand_port_specs([("status", "basic:List", True),
                                      ("line", "basic:List", True),
                                      ("id", "basic:List", True),
                                      ("id_size", "basic:List", True),
                                      ("id_color", "basic:List", True),
                                      ("id_font", "basic:List", True),
                                      ("symbol", "basic:List", True),
                                      ("color", "basic:List", True),
                                      ("size", "basic:List", True),
                                      ("xoffset", "basic:List", True),
                                      ("yoffset", "basic:List", True),
                                      ("linecolor", "basic:List", True),
                                      ("line_size", "basic:List", True),
                                      ("line_type", "basic:List", True)])
    _output_ports = expand_port_specs([("self", "CDMSTDMarker")])

class CDMSColorMap(Module):
    _input_ports = expand_port_specs([("colorMapName", "basic:String"),
                                      ("colorCells", "basic:List")])
    _output_ports = expand_port_specs([("self", "CDMSColorMap")])
    
    def __init__(self):
        Module.__init__(self)
        self.colorMapName = None
        self.colorCells = None
        
    def compute(self):
        self.colorMapName = self.forceGetInputFromPort('colorMapName')
        self.colorCells = self.forceGetInputFromPort("colorCells")
        self.setResult("self", self)
    
    def to_module(self, controller): 
        reg = get_module_registry()   
        module = controller.create_module_from_descriptor(
        reg.get_descriptor_by_name(identifier, self.__class__.__name__))
        functions = []
        if self.colorMapName is not None:
            functions.append(("colorMapName", [self.colorMapName]))
        if self.colorCells is not None:
            functions.append(("colorCells", [self.colorCells]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module
     
class CDMSCell(SpreadsheetCell):
    _input_ports = expand_port_specs([("plot", "CDMSPlot")])

    def compute(self):
        input_ports = []
        plots = []
        for plot in sorted(self.getInputListFromPort('plot'), 
                           key=lambda obj: obj.plot_order):
            plots.append(plot)
        input_ports.append(plots)
        self.cellWidget = self.displayAndWait(QCDATWidget, input_ports)

class QCDATWidget(QCellWidget):
    """ QCDATWidget is the spreadsheet cell widget where the plots are displayed.
    The widget interacts with the underlying C++, VCSQtManager through SIP.
    This enables QCDATWidget to get a reference to the Qt MainWindow that the
    plot will be displayed in and send signals (events) to that window widget.
    windowIndex is an index to the VCSQtManager window array so we can 
    communicate with the C++ Qt windows which the plots show up in.  If this 
    number is no longer consistent with the number of C++ Qt windows due to 
    adding or removing vcs.init() calls, then when you plot, it will plot into a
    separate window instead of in the cell and may crash.
    vcdat already creates 5 canvas objects
    
    """
    startIndex = 2 #this should be the current number of canvas objects created 
    maxIndex = 6
    usedIndexes = []
    
    def __init__(self, parent=None):
        QCellWidget.__init__(self, parent)
        self.toolBarType = QCDATWidgetToolBar
        self.window = None
        self.canvas =  None
        self.windowId = -1
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout) 
         
    def createCanvas(self):
        windowIndex = self.startIndex
        while (windowIndex in QCDATWidget.usedIndexes and 
                   windowIndex <= QCDATWidget.maxIndex):
            windowIndex += 1
        if windowIndex > QCDATWidget.maxIndex:
            raise ModuleError(self, "Maximum number of vcs.Canvas objects achieved.\
Please delete unused CDAT Cells in the spreadsheet.")
        else:
            print "using canvas ", windowIndex
            if windowIndex > len(vcs.canvaslist):
                self.canvas = vcs.init()
            else:
                self.canvas = vcs.canvaslist[windowIndex-1]
            self.windowId = windowIndex
            QCDATWidget.usedIndexes.append(self.windowId)

    def prepExtraDims(self,var):
        k={}
        for d,i in zip(self.extraDimsNames,self.extraDimsIndex):
            if d in var.getAxisIds():
                k[d]=slice(i,i+1)
        return k
    
    def updateContents(self, inputPorts, fromToolBar=False):
        """ Get the vcs canvas, setup the cell's layout, and plot """        
        spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
        spreadsheetWindow.setUpdatesEnabled(False)
        # Set the canvas
        # if inputPorts[0] is not None:
        #     self.canvas = inputPorts[0]
        if self.canvas is None:
            try:
                self.createCanvas()
            except ModuleError, e:
                spreadsheetWindow.setUpdatesEnabled(True)
                raise e
        #print self.windowId, self.canvas
        if self.window is not None:
            self.layout().removeWidget(self.window)
            
        self.window = VCSQtManager.window(self.windowId)
        self.layout().addWidget(self.window)
        self.window.setVisible(True)    
        # Place the mainwindow that the plot will be displayed in, into this
        # cell widget's layout
           
        self.canvas.clear()
        if not fromToolBar:
            self.extraDimsNames=inputPorts[0][0].var.var.getAxisIds()[:-2]
            self.extraDimsIndex=[0,]*len(self.extraDimsNames)
            self.extraDimsLen=inputPorts[0][0].var.var.shape[:-2]
            self.inputPorts = inputPorts
            if hasattr(self.parent(),"toolBar"):
                t = self.parent().toolBar
                if hasattr(t,"dimSelector"):
                    while (t.dimSelector.count()>0):
                        t.dimSelector.removeItem(0)
                    t.dimSelector.addItems(self.extraDimsNames)
        # Plot
        for plot in inputPorts[0]:
            cmd = "#Now plotting\nvcs_canvas[%i].plot(" % (self.canvas.canvasid()-1)
            # print "PLOT TYPE:", plot.plot_type
            print "Self:",self
            k1 = self.prepExtraDims(plot.var.var)
            args = [plot.var.var(**k1)]
            cmd+="%s(**%s), " % (args[0].id,str(k1))
            if hasattr(plot, "var2") and plot.var2 is not None:
                k2 = self.prepExtraDims(plot.var2.var)
                args.append(plot.var2.var(**k2))
                cmd+="%s(**%s), " % (args[-1].id,str(k2))
            args.append(plot.template)
            cgm = self.get_graphics_method(plot.plot_type, plot.graphics_method_name)
            if plot.graphics_method_name != 'default':
                for k in plot.gm_attributes:
                    if hasattr(plot,k):
                        if k in ['legend']:
                            setattr(cgm,k,eval(getattr(plot,k)))
                        else:
                            if getattr(plot,k)!=getattr(cgm,k):
                                #print "Setting:",k,getattr(plot,k)
                                setattr(cgm,k,getattr(plot,k))
                        #print k, " = ", getattr(cgm,k)
                            
            kwargs = plot.kwargs
                    
            #record commands
            cmd+=" '%s', '%s'" %( plot.template,cgm.name)
            for k in kwargs:
                cmd+=", %s=%s" % (k, repr(kwargs[k]))
            cmd+=")"
            from gui.application import get_vistrails_application
            _app = get_vistrails_application()
            conf = get_vistrails_configuration()
            interactive = conf.check('interactiveMode')
            if interactive:
                _app.uvcdatWindow.record(cmd)                
            
            #apply colormap
            if plot.colorMap is not None:
                if plot.colorMap.colorMapName is not None:
                    self.canvas.setcolormap(str(plot.colorMap.colorMapName))
                    
                if plot.colorMap.colorCells is not None:
                    for (n,r,g,b) in plot.colorMap.colorCells:
                        self.canvas.canvas.setcolorcell(n,r,g,b);
                    #see vcs.Canvas.setcolorcell
                    self.canvas.canvas.updateVCSsegments(self.canvas.mode) # pass down self and mode to _vcs module
                    self.canvas.flush() # update the canvas by processing all the X events
                
            self.canvas.plot(cgm,*args,**kwargs)
            
        spreadsheetWindow.setUpdatesEnabled(True)
        self.update()
        
    def get_graphics_method(self, plotType, gmName):
        method_name = "get"+str(plotType).lower()
        return getattr(self.canvas,method_name)(gmName)
    
    def deleteLater(self):
        """ deleteLater() -> None        
        Make sure to free render window resource when
        deallocating. Overriding PyQt deleteLater to free up
        resources
        """
        #we need to re-parent self.window or it will be deleted together with
        #this widget. The immediate parent is also deleted, so we will set to
        # parent of the parent widget
        if self.window is not None:
            self.window.setParent(self.parent().parent())
            self.window.setVisible(False)
        self.canvas = None
        self.window = None
        
        QCDATWidget.usedIndexes.remove(self.windowId)
        QCellWidget.deleteLater(self)    
        
    def dumpToFile(self, filename):
        """ dumpToFile(filename: str, dump_as_pdf: bool) -> None
        Dumps itself as an image to a file, calling grabWindowPixmap """
        self.saveToPNG(filename)
        
    def saveToPNG(self, filename):
        """ saveToPNG(filename: str) -> bool
        Save the current widget contents to an image file
        
        """
        
        self.canvas.png(filename)
        
    def saveToPDF(self, filename):
        """ saveToPDF(filename: str) -> bool
        Save the current widget contents to a pdf file
        
        """   
        self.canvas.pdf(filename)#, width=11.5)
        
    def exportToFile(self):
        file = QtGui.QFileDialog.getSaveFileName(
                self, "Select a File to Export the Plot",
                ".", "Images (*.png *.gif);;PDF file (*.pdf);;Postscript file (*.ps);;SVG file (*.svg)")
        if not file.isNull():
            filename = str(file)
            (_,ext) = os.path.splitext(filename)
            if  ext.upper() == '.PDF':
                self.canvas.pdf(filename)#, width=11.5)
            elif ext.upper() == ".PNG":
                self.canvas.png(filename)#, width=11.5)
            elif ext.upper() == ".SVG":
                self.canvas.svg(filename)#, width=11.5)
            elif ext.upper() == ".GIF":
                self.canvas.gif(filename)#, width=11.5)
            elif ext.upper() == ".PS":
                self.canvas.postscript(filename)#, width=11.5)
        
class QCDATWidgetToolBar(QCellToolBar):
    """
    QCDATWidgetToolBar derives from QCellToolBar to give CDMSCell
    a customizable toolbar
    
    """
    def createToolBar(self):
        """ createToolBar() -> None
        This will get call initially to add customizable widgets
        
        """
        cell = self.parent().getCell(self.parent().parentRow,self.parent().parentCol)
        if cell.inputPorts[0][0].var.var.rank()>2:
            self.prevAction=QCDATWidgetPrev(self)
            self.prevAction.setEnabled(False)
            self.appendAction(self.prevAction)
            self.dimSelector = QCDATDimSelector(self,cell)
            self.addWidget(self.dimSelector)
            self.nextAction=QCDATWidgetNext(self)
            self.addWidget(self.nextAction)
            self.nextAction.toolBar = self
            

        self.appendAction(QCDATWidgetPrint(self))
        self.appendAction(QCDATWidgetExport(self))
        self.appendAction(QCDATWidgetColormap(self))
        self.appendAction(QCDATWidgetAnimation(self))

class QCDATDimSelector(QtGui.QComboBox):
    """ list of dims to put here"""
    def __init__(self,parent=None,cell=None):
        QtGui.QComboBox.__init__(self,parent)
        self.addItems(cell.extraDimsNames)
        #self.connect(self,QtCore.SIGNAL("currentIndexChanged(int)"),self.valueChanged)
    def valueChanged(self, *args):
        print "Args:",args
        #self.parent().nextAction.wAction.updateLabels()

class QCDATWidgetPrev(QtGui.QAction):
    """
    QCDATWidgetColormap is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetAnimation(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetAnimation
        Brings up the naimation
        
        """
        QtGui.QAction.__init__(self,
                               UVCDATTheme.PLOT_PREVIOUS_ICON,
                               "Previous",
                               parent)
        self.setStatusTip("Move to Previous Dimensions")
        

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        #make sure we get the canvas object used in the cell
        cellWidget = self.toolBar.getSnappedWidget()
        selectedDim = str(self.parent().dimSelector.currentText())
        i = cellWidget.extraDimsNames.index(selectedDim)
        cellWidget.extraDimsIndex[i]-=1
        cellWidget.updateContents(cellWidget.inputPorts,True)
        self.parent().nextAction.setEnabled(True)
        if  cellWidget.extraDimsIndex[i]==0:
            self.setEnabled(False) 
        
    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)
class QDimsSlider(QtGui.QWidget):
    def updateLabels(self):
        print self.parent().parent().parent()
        selectedDim = str(self.parent().parent().parent().dimSelector.currentText())
        for a in self.V.getAxisList():
            if a.id == selectedDim:
                break
        index = self.slider.value()
        if a.isTime():
            a = a.asComponentTime()
            self.current.setText(str(a[index]))
            self.first.setText(str(a[0]))
            self.last.setText(str(a[-1]))
        else:
            self.current.setText("%g %s" % (a[i],a.units))
            self.first.setText("%g" % a[0])
            self.last.setText("%g" % a[-1])


    def __init__(self,parent):
        super(QDimsSlider,self).__init__(parent)
        toolBar = parent.parent().parent()
        cell = toolBar.parent().getCell(toolBar.parent().parentRow,toolBar.parent().parentCol) 
        self.V = cell.inputPorts[0][0].var.var
        l = QtGui.QVBoxLayout()
        self.current = QtGui.QLabel("Date")
        l.addWidget(self.current)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.first = QtGui.QLabel("First")
        self.last = QtGui.QLabel("Last")
        h=QtGui.QHBoxLayout()
        h.addWidget(self.first)
        h.addWidget(self.slider)
        h.addWidget(self.last)
        l.addLayout(h)
        self.setLayout(l)
        self.updateLabels()
        self.connect(self.slider,QtCore.SIGNAL("valueChanged(int)"),self.updateLabels)
        
class QDIMSSliderAction(QtGui.QWidgetAction):
    def __init__(self,parent):
        super(QDIMSSliderAction,self).__init__(parent)
    def createWidget(self,parent):
        t = QDimsSlider(parent)
        self.parent().wAction = t
        return t


class QCDATWidgetNext(QtGui.QToolButton):
    """
    QCDATWidgetColormap is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetAnimation(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetAnimation
        Brings up the naimation
        
        """
        super(QCDATWidgetNext,self).__init__(parent)
        #QtGui.QAbstractButton.__init__(self,
                #UVCDATTheme.PLOT_NEXT_ICON,
                #             "Next",
                    #           parent)
        self.setIcon(UVCDATTheme.PLOT_NEXT_ICON)
        self.setStatusTip("Move to Next Dimensions")
        self.connect(self, QtCore.SIGNAL("clicked(bool)"),self.clicked)
        menu = QtGui.QMenu(self)
        wAction = QDIMSSliderAction(self)
        menu.addAction(wAction)
        self.setMenu(menu)

    def clicked(self, value):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        print "value:",value
        #make sure we get the canvas object used in the cell
        cellWidget = self.toolBar.getSnappedWidget()
        selectedDim = str(self.parent().dimSelector.currentText())
        i = cellWidget.extraDimsNames.index(selectedDim)
        cellWidget.extraDimsIndex[i]+=1
        cellWidget.updateContents(cellWidget.inputPorts,True)
        self.parent().prevAction.setEnabled(True)
        if  cellWidget.extraDimsIndex[i]==cellWidget.extraDimsLen[i]-1:
            self.setEnabled(False) 
        
    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)

class QCDATWidgetPrint(QtGui.QAction):
    """
    QCDATWidgetExport is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetExport(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetExport
        Setup the image, status tip, etc. of the action
        
        """
        QtGui.QAction.__init__(self,
                               UVCDATTheme.PLOT_PRINTER_ICON,
                               "Print the current plot",
                               parent)
        self.setStatusTip("Print the current plot")

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        
        cellWidget = self.toolBar.getSnappedWidget()
        printer,ok = QtGui.QInputDialog.getText(self.parent(),"Send Picture To A Printer",
                                             "Printer",text=os.environ.get("PRINTER",""))
        if ok:
            cellWidget.canvas.printer(str(printer))

    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)

class QCDATWidgetAnimation(QtGui.QAction):
    """
    QCDATWidgetColormap is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetAnimation(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetAnimation
        Brings up the naimation
        
        """
        QtGui.QAction.__init__(self,
                               UVCDATTheme.PLOT_ANIMATION_ICON,
                               "Animate",
                               parent)
        self.setStatusTip("Animate this plot")
        self.setEnabled(False) # For now because it hangs
        

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        #make sure we get the canvas object used in the cell
        cellWidget = self.toolBar.getSnappedWidget()
        canvas = cellWidget.canvas
        _app.uvcdatWindow.dockAnimate.widget().setCanvas(canvas)
        _app.uvcdatWindow.dockAnimate.show()
        
    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)

class QCDATWidgetColormap(QtGui.QAction):
    """
    QCDATWidgetColormap is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetColormap(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetColormap
        Setup the colormapeditor
        
        """
        QtGui.QAction.__init__(self,
                               UVCDATTheme.PLOT_COLORMAP_ICON,
                               "Colormap Editor",
                               parent)
        self.setStatusTip("Brings up the colormap editor")

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        #make sure we get the canvas object used in the cell
        cellWidget = self.toolBar.getSnappedWidget()
        canvas = cellWidget.canvas
        _app.uvcdatWindow.colormapEditor.activateFromCell(canvas)
        

    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)


class QCDATWidgetExport(QtGui.QAction):
    """
    QCDATWidgetExport is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetExport(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetExport
        Setup the image, status tip, etc. of the action
        
        """
        QtGui.QAction.__init__(self,
                               UVCDATTheme.PLOT_EXPORT_ICON,
                               "Export the current plot as an image",
                               parent)
        self.setStatusTip("Export the current plot as an image")

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        
        cellWidget = self.toolBar.getSnappedWidget()
        cellWidget.exportToFile()

    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from gui.application import get_vistrails_application
        _app = get_vistrails_application()
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)

_modules = [CDMSVariable, CDMSPlot, CDMSCell, CDMSTDMarker, CDMSVariableOperation,
            CDMSUnaryVariableOperation, CDMSBinaryVariableOperation, 
            CDMSNaryVariableOperation, CDMSColorMap]

def get_input_ports(plot_type):
    if plot_type == "Boxfill":
        return expand_port_specs([('boxfill_type', 'basic:String', True),
                                  ('color_1', 'basic:Integer', True),
                                  ('color_2', 'basic:Integer', True),
                                  ('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('level_1', 'basic:Float', True),
                                  ('level_2', 'basic:Float', True),
                                  ('missing', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ])
    elif plot_type == "Isofill":
        return expand_port_specs([('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('missing', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Isoline":
        return expand_port_specs([('label', 'basic:String', True),
                                  ('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('level', 'basic:List', True),
                                  ('line', 'basic:List', True),
                                  ('linecolors', 'basic:List', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('linewidths', 'basic:List', True),
                                  ('text', 'basic:List', True),
                                  ('textcolors', 'basic:List', True),
                                  ('clockwise', 'basic:List', True),
                                  ('scale', 'basic:List', True),
                                  ('angle', 'basic:List', True),
                                  ('spacing', 'basic:List', True)
                                  ]) 
    elif plot_type == "Meshfill":
        return expand_port_specs([('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('missing', 'basic:Integer', True),
                                  ('mesh', 'basic:String', True),
                                  ('wrap', 'basic:List', True)
                                  ]) 
    elif plot_type == "Outfill":
        return expand_port_specs([('outfill', 'basic:List', True),
                                  ('fillareacolor', 'basic:List', True),
                                  ('fillareaindex', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Outline":
        return expand_port_specs([('outline', 'basic:List', True),
                                  ('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Scatter":
        return expand_port_specs([('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Vector":
        return expand_port_specs([('scale', 'basic:Float', True),
                                  ('alignment', 'basic:String', True),
                                  ('type', 'basic:String', True),
                                  ('reference', 'basic:Float', True),
                                  ('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "XvsY":
        return expand_port_specs([('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Xyvsy":
        return expand_port_specs([('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Yxvsx":
        return expand_port_specs([('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type=="Taylordiagram":
        return expand_port_specs([('detail', 'basic:Integer', True),
                                  ('max', 'basic:String', True),
                                  ('quadrans', 'basic:Integer', True),
                                  ('skillColor', 'basic:Integer', True),
                                  ('skillValues', 'basic:List', True),
                                  ('skillDrawLabels', 'basic:String', True),
                                  ('skillCoefficient', 'basic:List', True),
                                  ('referencevalue', 'basic:Float', True),
                                  ('arrowlength', 'basic:Float', True),
                                  ('arrowangle', 'basic:Float', True),
                                  ('arrowbase', 'basic:Float', True),
                                  ('cmtics1', 'basic:String', True),
                                  ('cticlabels1', 'basic:String', True),
                                  ('Marker', 'CDMSTDMarker', True),
                                  ]) 
    else:
        return []
def get_gm_attributes(plot_type):
    if plot_type == "Boxfill":
        return  ['boxfill_type', 'color_1', 'color_2' ,'datawc_calendar', 
                    'datawc_timeunits', 'datawc_x1', 'datawc_x2', 'datawc_y1', 
                    'datawc_y2', 'levels','ext_1', 'ext_2', 'fillareacolors', 
                    'fillareaindices', 'fillareastyle', 'legend', 'level_1', 
                    'level_2', 'missing', 'projection', 'xaxisconvert', 'xmtics1', 
                    'xmtics2', 'xticlabels1', 'xticlabels2', 'yaxisconvert', 
                    'ymtics1', 'ymtics2', 'yticlabels1', 'yticlabels2']
        
    elif plot_type == "Isofill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'levels','ext_1', 'ext_2', 
                'fillareacolors', 'fillareaindices', 'fillareastyle', 'legend', 
                'missing', 'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
        
    elif plot_type == "Isoline":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'projection', 'xaxisconvert', 'xmtics1', 
                'xmtics2', 'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2', 'label', 'level', 'levels', 
                'line', 'linecolors','linewidths','text','textcolors','clockwise',
                'scale', 'angle','spacing']
    elif plot_type == "Meshfill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'levels','ext_1', 'ext_2', 
                'fillareacolors', 'fillareaindices', 'fillareastyle', 'legend', 
                'missing', 'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2', 'mesh', 'wrap']
    elif plot_type == "Outfill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'outfill',
                'fillareacolor', 'fillareaindex', 'fillareastyle',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Outline":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'outline',
                'linecolor', 'line', 'linewidth',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Scatter":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 
                'markercolor', 'marker', 'markersize',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Vector":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','scale','alignment','type','reference',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "XvsY":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Xyvsy":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Yxvsx":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'xaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Taylordiagram":
        return ['detail','max','quadrans',
                'skillValues','skillColor','skillDrawLabels','skillCoefficient',
                'referencevalue','arrowlength','arrowangle','arrowbase',
                'xmtics1', 'xticlabels1', 'ymtics1', 
                'yticlabels1','cmtics1', 'cticlabels1', 'Marker']
    
def get_canvas():
    global canvas
    if canvas is None:
        from gui.uvcdat import customizeUVCDAT
        canvas = vcs.init()
        try:
            canvas.createtemplate(customizeUVCDAT.defaultTemplateName)
        except:
            pass
    return canvas
    
for plot_type in ['Boxfill', 'Isofill', 'Isoline', 'Meshfill', 'Outfill', \
                  'Outline', 'Scatter', 'Taylordiagram', 'Vector', 'XvsY', \
                  'Xyvsy', 'Yxvsx']:
    def get_init_method():
        def __init__(self):
            CDMSPlot.__init__(self)
            #self.plot_type = pt
        return __init__
    def get_is_cacheable_method():
        def is_cacheable(self):
            return False
        return is_cacheable
    
    klass = type('CDMS' + plot_type, (CDMSPlot,), 
                 {'__init__': get_init_method(),
                  'plot_type': plot_type,
                  '_input_ports': get_input_ports(plot_type),
                  'gm_attributes': get_gm_attributes(plot_type),
                  'is_cacheable': get_is_cacheable_method()})
    # print 'adding CDMS module', klass.__name__
    _modules.append((klass,{'configureWidgetType':GraphicsMethodConfigurationWidget}))

def initialize(*args, **keywords):
    global original_gm_attributes
    for plot_type in ['Boxfill', 'Isofill', 'Isoline', 'Meshfill', 'Outfill', \
                  'Outline', 'Scatter', 'Taylordiagram', 'Vector', 'XvsY', \
                  'Xyvsy', 'Yxvsx']:
        canvas = get_canvas()
        method_name = "get"+plot_type.lower()
        attributes = get_gm_attributes(plot_type)
        gms = canvas.listelements(str(plot_type).lower())
        original_gm_attributes[plot_type] = {}
        for gmname in gms:
            gm = getattr(canvas,method_name)(gmname)
            attrs = {}
            for attr in attributes:
                attrs[attr] = getattr(gm,attr)
                if attr == 'linecolor' and attrs[attr] == None:
                    attrs[attr] = 241
                elif attr == 'linewidth' and attrs[attr] == None:
                    attrs[attr] = 1
                elif attr == 'line' and attrs[attr] == None:
                    attrs[attr] = 'solid'
                elif attr == 'markercolor' and attrs[attr] == None:
                    attrs[attr] = 241
                elif attr == 'markersize' and attrs[attr] == None:
                    attrs[attr] = 1
                elif attr == 'marker' and attrs[attr] == None:
                    attrs[attr] = 'dot'
            original_gm_attributes[plot_type][gmname] = InstanceObject(**attrs)
   
    
