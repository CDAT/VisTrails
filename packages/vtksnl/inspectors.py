############################################################################
##
## Copyright (C) 2006-2010 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at contact@vistrails.org.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################

##############################################################################
# Data inspectors for VTK

from core.modules.vistrails_module import ModuleError
from core.utils import VistrailsInternalError
from core.modules.basic_modules import Module, Float, Integer
from core.modules.module_registry import get_module_registry
import vtksnl
from base_module import vtkBaseModule
from hasher import vtk_hasher

class vtkBaseInspector(Module):

    @classmethod
    def register_self(cls, **kwargs):
        registry = get_module_registry()
        def resolve_type(t):
            if type(t) == tuple:
                return registry.get_descriptor_by_name(*t).module
            elif type(t) == type:
                return t
            else:
                assert False, ("Unknown type " + str(type(t)))

        registry.add_module(cls, **kwargs)
        try:
            ips = cls.input_ports
        except AttributeError:
            pass
        else:
            for (port_name, types) in ips:
                registry.add_input_port(cls,
                                        port_name,
                                        list(resolve_type(t) for t in types))

        try:
            ops = cls.output_ports
        except AttributeError:
            pass
        else:
            for (port_name, types) in ops:
                registry.add_output_port(cls,
                                         port_name,
                                         list(resolve_type(t) for t in types))

    def auto_set_results(self, vtk_object):
        for function in self.outputPorts.keys():
            if hasattr(vtk_object, function):
                retValues = getattr(vtk_object, function)()
                if issubclass(retValues.__class__, vtksnl.vtkObject):
                    className = retValues.GetClassName()
                    output  = vtkBaseModule.wrapperModule(className, retValues)
                    self.setResult(function, output)
                elif type(retValues) in [tuple, list]:
                    result = list(retValues)
                    for i in xrange(len(result)):
                        if issubclass(result[i].__class__, vtksnl.vtkObject):
                            className = result[i].GetClassName()
                            result[i] = vtkBaseModule.wrapperModule(className,
                                                                    result[i])
                    self.setResult(function, type(retValues)(result))
                else:
                    self.setResult(function, retValues)

class vtkDataSetInspector(vtkBaseInspector):

    def compute(self):
        vtk_object = None
        if self.hasInputFromPort("SetInputConnection0"):
            ic = self.getInputFromPort("SetInputConnection0")
            port_object = ic.vtkInstance
            ix = port_object.GetIndex()
            producer = port_object.GetProducer()
            try:
                vtk_object = producer.GetOutput()
            except AttributeError:
                raise ModuleError(self, 
                                  "expected a module that supports GetOutput")
        elif self.hasInputFromPort("SetInput"):
            port_object = self.getInputFromPort("SetInput")
            if hasattr(port_object, "vtkInstance"):
                vtk_object = port_object.vtkInstance
            else:
                raise ModuleError(self, "expected a vtk module")
        if vtk_object:
            self.auto_set_results(vtk_object)

    input_ports = [('SetInputConnection0',
                    [('edu.utah.sci.vistrails.vtksnl', 'vtkAlgorithmOutput')]),
                   ('SetInput',
                    [('edu.utah.sci.vistrails.vtksnl', 'vtkDataSet')]),
                   ]
    output_ports = [('GetBounds', [Float] * 6),
                    ('GetScalarRange', [Float] * 2),
                    ('GetLength', [Float]),
                    ('GetCenter', [Float] * 3),
                    ('GetNumberOfPoints', [Integer]),
                    ('GetNumberOfCells', [Integer]),
                    ('GetPointData', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkPointData')]),
                    ('GetCellData',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkCellData')]),
                    ]

class vtkDataSetAttributesInspector(vtkBaseInspector):
    
    def compute(self):
        vtk_object = None
        if self.hasInputFromPort("SetInput"):
            port_object = self.getInputFromPort("SetInput")
            if hasattr(port_object, "vtkInstance"):
                vtk_object = port_object.vtkInstance
            else:
                raise ModuleError(self, "expected a vtk module")
        if vtk_object:
            self.auto_set_results(vtk_object)

    input_ports = [('SetInput',
                    [('edu.utah.sci.vistrails.vtksnl', 'vtkDataSetAttributes')]),
                   ]
    output_ports = [('GetScalars', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetVectors', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetNormals', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetTCoords', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetTensors', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetGlobalIds', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')]),
                    ('GetPedigreeIds', 
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkAbstractArray')]),
                    ]

class vtkDataArrayInspector(vtkBaseInspector):

   def compute(self):
        vtk_object = None
        if self.hasInputFromPort("SetInput"):
            port_object = self.getInputFromPort("SetInput")
            if hasattr(port_object, "vtkInstance"):
                vtk_object = port_object.vtkInstance
            else:
                raise ModuleError(self, "expected a vtk module")
        if vtk_object:
            self.auto_set_results(vtk_object)

   input_ports = [('SetInput',
                   [('edu.utah.sci.vistrails.vtksnl', 'vtkDataArray')])]
   output_ports = [('GetMaxNorm', [Float]),
                   ('GetRange', [Float] * 2)]
                   
class vtkPolyDataInspector(vtkDataSetInspector):

    def compute(self):
        vtk_object = None
        if self.hasInputFromPort("SetInputConnection0"):
            ic = self.getInputFromPort("SetInputConnection0")
            port_object = ic.vtkInstance
            ix = port_object.GetIndex()
            producer = port_object.GetProducer()
            try:
                vtk_object = producer.GetOutput()
            except AttributeError:
                raise ModuleError(self, 
                                  "expected a module that supports GetOutput")
        elif self.hasInputFromPort("SetInput"):
            port_object = self.getInputFromPort("SetInput")
            if hasattr(port_object, "vtkInstance"):
                vtk_object = port_object.vtkInstance
            else:
                raise ModuleError(self, "expected a vtk module")
        if vtk_object:
            self.auto_set_results(vtk_object)

    input_ports = [('SetInputConnection0',
                    [('edu.utah.sci.vistrails.vtksnl', 'vtkAlgorithmOutput')]),
                   ('SetInput',
                    [('edu.utah.sci.vistrails.vtksnl', 'vtkDataSet')]),
                   ]
    output_ports = [('GetVerts',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkCellArray')]),
                    ('GetLines',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkCellArray')]),
                    ('GetPolys',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkCellArray')]),
                    ('GetStrips',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkCellArray')]),
                    ('GetPoints',
                     [('edu.utah.sci.vistrails.vtksnl', 'vtkPoints')]),
                    ('GetNumberOfVerts', [Integer]),
                    ('GetNumberOfLines', [Integer]),
                    ('GetNumberOfPolys', [Integer]),
                    ('GetNumberOfStrips', [Integer]),
                    ]

def initialize():
    vtkBaseInspector.register_self(abstract=True, signatureCallable=vtk_hasher)
    vtkDataSetInspector.register_self(abstract=False, 
                                      signatureCallable=vtk_hasher)
    vtkDataSetAttributesInspector.register_self(abstract=False, 
                                                signatureCallable=vtk_hasher)
    vtkDataArrayInspector.register_self(abstract=False, 
                                        signatureCallable=vtk_hasher)
    vtkPolyDataInspector.register_self(abstract=False,
                                       signatureCallable=vtk_hasher)
    
