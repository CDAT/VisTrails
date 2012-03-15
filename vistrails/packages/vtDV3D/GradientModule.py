'''
Created on Jan 3, 2011

@author: tpmaxwel
'''
'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter

from core.modules.basic_modules import Integer, Float, String, File, Variant, Color

from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import *
        
class PM_Gradient(PersistentVisualizationModule):
    """

    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, createColormap=False, **args)
 
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        print " Gradient.execute, input Arrays: "
        pointData = self.input.GetPointData()
        for iA in range( pointData.GetNumberOfArrays() ):
            array_name = pointData.GetArrayName(iA)
            array = pointData.GetArray(iA)
            print " Array %s: ntup = %d, ncomp = %d, type = %s, range = %s " % ( array_name, array.GetNumberOfTuples(), array.GetNumberOfComponents(), array.GetDataTypeAsString(), str(array.GetRange()) )
             
        computeVorticity = wmod.forceGetInputFromPort( "computeVorticity", 1 ) 
        self.gradient = vtk.vtkGradientFilter() 
        self.gradient.SetComputeVorticity( computeVorticity ) 
        self.inputModule.inputToAlgorithm( self.gradient )
        if computeVorticity: self.gradient.SetResultArrayName('vorticity')     
        
        self.set3DOutput( output=self.gradient.GetOutput() )

from packages.vtDV3D.WorkflowModule import WorkflowModule

class Gradient(WorkflowModule):
    
    PersistentModuleClass = PM_Gradient
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
                
if __name__ == '__main__':
    executeVistrail( 'VorticityPlotDemo' )