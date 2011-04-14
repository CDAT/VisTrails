'''
Created on Mar 15, 2011

@author: tpmaxwel
'''
import vtk, sys, time, threading, inspect
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from core.modules.vistrails_module import Module, ModuleError
from vtUtilities import *

class AddTest( Module ):
    
    def __init__( self ):
        Module.__init__(self) 
        self.currentValue  = 0

    def compute(self):
        arg = self.forceGetInputFromPort( "arg", self.currentValue ) 
        parm = self.forceGetInputFromPort( "parm", 1 ) 
        layer = self.forceGetInputFromPort( "layer", 0 ) 
        self.currentValue = arg + parm
        self.setResult( 'out', self.currentValue )
        self.printDiagnostics( arg, parm, layer )
        
    def printDiagnostics(self, arg, parm, layer ):
        import api
        controller = api.get_current_controller()
        version = controller.current_version
        mid = self.moduleInfo['moduleId'] 
        print " AddTest[mid=%d] exec{v.%d}: arg = %d, parm = %d, layer = %d, out = %d " % ( mid, version, arg, parm, layer, self.currentValue )
#        versions, tags = api.get_available_versions()
#        print " --- Versions: %s " % str( versions )
        
if __name__ == '__main__':
    executeVistrail( 'TestPipeline' )
