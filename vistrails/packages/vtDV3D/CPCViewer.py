'''
Created on Oct 29, 2013

@author: tpmaxwel
'''
from packages.vtDV3D.PersistentModule import *
from  packages.vtDV3D.CDMS_VariableReaders import  CDMSReaderConfigurationWidget

class PM_CPCViewer(PersistentVisualizationModule):
    """
        This module wraps the CPCViewer package. 

    """       
    
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.primaryInputPorts = [ 'variable' ] 
        
    def execute(self, **args ):
        cdms_vars = self.getInputValues( "variable"  ) 
        if cdms_vars and len(cdms_vars):
            cdms_var = cdms_vars.pop(0)
        
        
from packages.vtDV3D.WorkflowModule import WorkflowModule

class CPCViewer(WorkflowModule):
    
    PersistentModuleClass = PM_CPCViewer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
class CPCViewerConfigurationWidget(CDMSReaderConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        CDMSReaderConfigurationWidget.__init__(self, module, controller, CDMSDataType.Hoffmuller, parent)

    def getParameters( self, module ):
        CDMSReaderConfigurationWidget.getParameters( self, module ) 

